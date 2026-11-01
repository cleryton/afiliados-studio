"""Checkpoints for owner-authorized TikTok Studio UI actions, never a publisher.

A checkpoint does not prove a remote result. Confirmation must come from an
observed destination list after reload; passing a due date proves nothing.
"""
from datetime import datetime
import hashlib
import json
import re
from urllib.parse import urlsplit
from uuid import uuid4
import core
import story_delivery
import story_library

LABELS={'reserved':'Preparado para envio','upload_started':'Envio do arquivo iniciado',
        'details_checked':'Configurações conferidas','submission_started':'Agendamento solicitado; conferir destino',
        'uncertain':'Resultado precisa de conferência','confirmed':'Agendamento registrado no TikTok'}
REASONS={'login':'Entre no perfil exclusivo para continuar.','captcha':'Conclua pessoalmente a verificação do TikTok.',
         'selector':'O seletor não aceitou o arquivo. Confira a tela e o destino antes de uma recuperação limitada.',
         'file_access':'A integração recusou o arquivo. Confira sua autorização.',
         'network':'A conexão foi interrompida. Confira o destino antes de repetir qualquer envio.',
         'unconfirmed':'O destino ainda não confirmou o agendamento. Não repita o envio.',
         'receipt_write':'O resultado foi registrado, mas o recibo local aguarda reparo. O vídeo não será reenviado.'}


def init():
    with core.db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS story_native_attempts(
          id TEXT PRIMARY KEY,media_id TEXT NOT NULL,content_key TEXT NOT NULL,handle TEXT NOT NULL,
          due_at TEXT NOT NULL,fingerprint TEXT NOT NULL,source_sha256 TEXT NOT NULL,caption_hash TEXT NOT NULL,
          stage TEXT NOT NULL,reason TEXT NOT NULL DEFAULT '',receipt TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          commercial INTEGER NOT NULL DEFAULT 0,submitted_at TEXT,
          UNIQUE(handle,content_key))''')
        if 'selection_retries' not in {r['name'] for r in c.execute('PRAGMA table_info(story_native_attempts)')}:
            c.execute('ALTER TABLE story_native_attempts ADD COLUMN selection_retries INTEGER NOT NULL DEFAULT 0')


def _blocks_api(connection,content_key,handle):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='story_native_attempts'").fetchone():return False
    return bool(connection.execute("SELECT 1 FROM story_native_attempts WHERE content_key=? AND lower(handle)=lower(?)",
                                   (content_key,handle)).fetchone())


def blocks_api(content_key,handle,*,connection=None):
    if connection is not None:return _blocks_api(connection,content_key,handle)
    with core.db() as c:
        return _blocks_api(c,content_key,handle)


def _get(identifier):
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Tentativa inválida.')
    with core.db() as c:row=c.execute('SELECT * FROM story_native_attempts WHERE id=?',(identifier,)).fetchone()
    if not row:raise ValueError('Tentativa não encontrada.')
    return dict(row)


def begin(payload):
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas de envio externo.')
    media=payload.get('media_id');handle=story_delivery.target()
    if payload.get('observed_handle')!=handle:raise ValueError('Confira o perfil no próprio TikTok antes de iniciar.')
    with core.db() as c:
        week=c.execute('SELECT * FROM story_weeks ORDER BY created_at DESC LIMIT 1').fetchone()
        slots=c.execute('SELECT * FROM story_week_slots WHERE week_id=? ORDER BY due_at,number',(week['id'],)).fetchall() if week else []
    if not week or week['paused'] or week['handle']!=handle:raise ValueError('Confira a semana e a pausa antes de enviar.')
    first=next((s for s in slots if not story_library.native_post_exists(f"3d:a-chave-do-12:{s['number']}",handle)),None)
    if not first or first['media_id']!=media or first['status']!='ready':raise ValueError('Comece pelo primeiro capítulo pronto e ainda sem registro da semana.')
    if datetime.fromisoformat(first['due_at'])<=core.now():raise ValueError('A proposta de data passou. Revise o calendário antes de iniciar.')
    proof=story_delivery.snapshot(media)
    if proof['proof']['chapter']!=first['number']:raise ValueError('O arquivo não corresponde ao capítulo do calendário.')
    caption=' '.join((core.DATA/'stories'/media/'legenda.txt').read_text(encoding='utf-8').split())
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT * FROM story_native_attempts WHERE handle=? AND content_key=?',(handle,proof['proof']['content_key'])).fetchone()
        if prior:return {'id':prior['id'],'existing':True,'may_upload':False,'stage':prior['stage']}
        if c.execute("SELECT 1 FROM story_publications WHERE content_key=? AND status!='cancelled'",(proof['proof']['content_key'],)).fetchone():
            raise ValueError('Este capítulo entrou em outra fila durante a preparação. Confira o pedido existente.')
        identifier=uuid4().hex
        c.execute('INSERT INTO story_native_attempts(id,media_id,content_key,handle,due_at,fingerprint,source_sha256,caption_hash,stage,created_at,updated_at,commercial) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                  (identifier,media,proof['proof']['content_key'],handle,first['due_at'],proof['fingerprint'],proof['proof']['files']['video.mp4'],
                   hashlib.sha256(caption.encode()).hexdigest(),'reserved',core.stamp(),core.stamp(),int(proof['proof']['third_party_commercial_label_required'])))
    return {'id':identifier,'existing':False,'may_upload':True,'stage':'reserved','due_at':first['due_at']}


def _unchanged(row):
    if story_delivery.target()!=row['handle']:raise ValueError('O perfil mudou durante a tentativa.')
    current=story_delivery.snapshot(row['media_id'])
    if current['fingerprint']!=row['fingerprint']:raise ValueError('Os arquivos ou a oferta mudaram. Confira a tentativa existente no destino.')
    with core.db() as c:
        slot=c.execute('SELECT s.due_at,w.paused,w.handle FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id WHERE s.media_id=? ORDER BY w.created_at DESC LIMIT 1',(row['media_id'],)).fetchone()
    if not slot or slot['paused'] or slot['handle']!=row['handle'] or slot['due_at']!=row['due_at']:
        raise ValueError('A semana foi pausada ou alterada durante a tentativa.')
    return current


def advance(payload):
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas de envio externo.')
    row=_get(payload.get('id'));target=payload.get('stage')
    previous={'upload_started':'reserved','details_checked':'upload_started','submission_started':'details_checked'}
    if target not in previous:raise ValueError('Etapa inválida.')
    if row['stage']==target:return {'ok':True,'existing':True,'may_dispatch':False}
    if row['stage']!=previous[target]:raise ValueError('A tentativa exige conferência; não repita o envio.')
    proof=_unchanged(row)
    if target in ('details_checked','submission_started'):
        fields=('caption_matches','ai_label','public_visibility','checks_clear')
        if any(payload.get(k) is not True for k in fields) or payload.get('observed_handle')!=row['handle'] or payload.get('due_at')!=row['due_at']:
            raise ValueError('Confira legenda, IA, visibilidade, verificações, perfil, data e horário no TikTok.')
        if proof['proof']['third_party_commercial_label_required'] and payload.get('paid_partnership') is not True:
            raise ValueError('Confira a identificação de publicidade de terceiros no TikTok.')
        if datetime.fromisoformat(row['due_at'])<=core.now():raise ValueError('O horário proposto passou. Não confirme este pedido.')
    with core.db() as c:
        changed=c.execute('UPDATE story_native_attempts SET stage=?,reason=?,updated_at=?,submitted_at=CASE WHEN ? THEN ? ELSE submitted_at END WHERE id=? AND stage=?',
                          (target,'',core.stamp(),target=='submission_started',core.stamp(),row['id'],previous[target])).rowcount
    return {'ok':True,'existing':not bool(changed),'may_dispatch':bool(changed) and target=='submission_started'}


def hold(payload):
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas de envio externo.')
    row=_get(payload.get('id'));reason=payload.get('reason')
    if reason not in REASONS or reason=='receipt_write':raise ValueError('Motivo inválido.')
    if row['stage']=='confirmed':raise ValueError('Um agendamento confirmado não pode voltar para envio.')
    with core.db() as c:
        changed=c.execute("UPDATE story_native_attempts SET stage='uncertain',reason=?,updated_at=? WHERE id=? AND stage=? AND receipt IS NULL",
                          (reason,core.stamp(),row['id'],row['stage'])).rowcount
    if not changed:raise ValueError('A tentativa mudou durante a conferência. Atualize o painel antes de continuar.')
    return {'ok':True}


def resume_preview(payload):
    """Resume an observed, intact editor; never authorize another file upload."""
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas de envio externo.')
    row=_get(payload.get('id'))
    if row['stage']!='uncertain' or row['submitted_at']:
        raise ValueError('Há um pedido de agendamento possível. Confira o destino; não haverá outra autorização de envio.')
    if (payload.get('preview_matches') is not True or payload.get('destination_absent_after_reload') is not True or
            payload.get('observed_handle')!=row['handle'] or payload.get('media_id')!=row['media_id']):
        raise ValueError('Confira o mesmo vídeo aberto no editor, o perfil e a lista do destino.')
    _unchanged(row)
    with core.db() as c:
        changed=c.execute("UPDATE story_native_attempts SET stage='upload_started',reason='',updated_at=? WHERE id=? AND stage='uncertain' AND submitted_at IS NULL",
                          (core.stamp(),row['id'])).rowcount
    return {'ok':bool(changed),'may_upload':False,'may_dispatch':False,'stage':'upload_started' if changed else row['stage']}


def retry_selection(payload):
    """One retry after an explicit pre-transfer selector failure, never a lost upload."""
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas de envio externo.')
    row=_get(payload.get('id'))
    if row['stage']!='uncertain' or row['reason']!='selector' or row['submitted_at'] or row['selection_retries']>=1:
        raise ValueError('A tentativa exige conferência; não há outra autorização de envio.')
    if (payload.get('selector_empty') is not True or payload.get('upload_not_accepted') is not True or
            payload.get('destination_absent_after_reload') is not True or payload.get('observed_handle')!=row['handle'] or
            payload.get('media_id')!=row['media_id']):
        raise ValueError('Confirme a falha explícita anterior à transferência, o seletor vazio, o mesmo arquivo e a lista recarregada do perfil.')
    _unchanged(row)
    if datetime.fromisoformat(row['due_at'])<=core.now():raise ValueError('O horário proposto passou. Revise a agenda antes de tentar outro envio.')
    with core.db() as c:
        changed=c.execute("UPDATE story_native_attempts SET stage='reserved',reason='',selection_retries=selection_retries+1,updated_at=? WHERE id=? AND stage='uncertain' AND reason='selector' AND submitted_at IS NULL AND selection_retries=0 AND receipt IS NULL",
                          (core.stamp(),row['id'])).rowcount
    return {'ok':bool(changed),'may_upload':bool(changed),'may_dispatch':False,'stage':'reserved' if changed else row['stage']}


def _write_receipt(row):
    value=json.loads(row['receipt']);folder=_folder(row);path=folder/'agendamento-tiktok.json'
    if path.exists():
        old=story_library.read_json(path,65536)
        if not old or old.get('url')!=value['url'] or old.get('source_sha256')!=value['source_sha256']:
            raise ValueError('Há outro registro neste arquivo. Confira o destino antes de alterar o recibo.')
        return
    temporary=folder/(uuid4().hex+'.receipt-new')
    try:
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


def _folder(row):
    folder=core.DATA/'stories'/row['media_id']
    if folder.is_symlink() or folder.resolve().parent!=(core.DATA/'stories').resolve() or not folder.resolve().is_relative_to(core.DATA.resolve()):
        raise ValueError('O arquivo original não está na pasta autorizada.')
    return folder


def confirm(payload):
    if core.TESTER:raise ValueError('O modo tester bloqueia registros de envio externo.')
    row=_get(payload.get('id'))
    if row['stage']=='confirmed':
        if json.loads(row['receipt'])['url']!=payload.get('url'):raise ValueError('Esta tentativa já foi confirmada com outro link.')
        _write_receipt(row);return {'ok':True,'existing':True}
    if row['stage'] not in ('submission_started','uncertain') or not row['submitted_at']:raise ValueError('Não há pedido de agendamento para confirmar.')
    url=payload.get('url','')
    if not isinstance(url,str):raise ValueError('Link inválido.')
    parts=urlsplit(url)
    if (parts.scheme!='https' or parts.netloc!='www.tiktok.com' or parts.query or parts.fragment or
            not re.fullmatch('/@'+re.escape(row['handle'])+'/video/[0-9]{15,24}',parts.path)):
        raise ValueError('O link precisa identificar o vídeo no perfil esperado.')
    if payload.get('destination_reloaded') is not True or payload.get('caption_matches') is not True or payload.get('due_at')!=row['due_at']:
        raise ValueError('Recarregue a lista do TikTok e confira legenda, link e horário antes de registrar.')
    # A later pause must not prevent saving a genuine result already accepted.
    root=_folder(row);video=root/'video.mp4';caption_path=root/'legenda.txt'
    if video.is_symlink() or caption_path.is_symlink():raise ValueError('Os arquivos originais foram substituídos por links.')
    caption=' '.join(caption_path.read_text(encoding='utf-8').split())
    if story_delivery.file_hash(video)!=row['source_sha256'] or hashlib.sha256(caption.encode()).hexdigest()!=row['caption_hash']:
        raise ValueError('Os arquivos originais foram alterados; confira o registro.')
    receipt={'media_id':row['media_id'],'handle':row['handle'],'status':'scheduled_confirmed','scheduled_for':row['due_at'],
             'url':url,'source_sha256':row['source_sha256'],'caption_hash':row['caption_hash'],'content_key':row['content_key'],
             'observed_at':core.stamp(),'publication_confirmed':False,'dispatch_count':1,
             'confirmed_via':'Owner-authorized operator observed the TikTok Studio content list after reload.',
             'ai_label_confirmed_in_preview':True,'paid_partnership_confirmed_in_preview':bool(row['commercial'])}
    with core.db() as c:
        changed=c.execute("UPDATE story_native_attempts SET stage='confirmed',reason='',receipt=?,updated_at=? WHERE id=? AND receipt IS NULL",
                  (json.dumps(receipt,ensure_ascii=False),core.stamp(),row['id'])).rowcount
    if not changed and json.loads(_get(row['id'])['receipt'])['url']!=url:raise ValueError('Esta tentativa já foi confirmada com outro link.')
    row=_get(row['id']);_write_receipt(row)
    return {'ok':True,'existing':False,'url':url}


def tick():
    with core.db() as c:rows=[dict(r) for r in c.execute("SELECT * FROM story_native_attempts WHERE stage='confirmed'")]
    for row in rows:
        if not (core.DATA/'stories'/row['media_id']/'agendamento-tiktok.json').exists():
            try:_write_receipt(row)
            except (OSError,ValueError):
                with core.db() as c:c.execute("UPDATE story_native_attempts SET reason='receipt_write',updated_at=? WHERE id=?",(core.stamp(),row['id']))
                continue
        if row['reason']=='receipt_write':
            with core.db() as c:c.execute("UPDATE story_native_attempts SET reason='',updated_at=? WHERE id=?",(core.stamp(),row['id']))


def state():
    with core.db() as c:
        rows=[dict(r) for r in c.execute('SELECT id,media_id,handle,due_at,stage,reason,updated_at FROM story_native_attempts ORDER BY created_at DESC LIMIT 15')]
        unresolved=c.execute("SELECT COUNT(*) FROM story_native_attempts WHERE stage!='confirmed'").fetchone()[0]
    for row in rows:row.update(label=LABELS[row['stage']],message=REASONS.get(row['reason'],''))
    return {'attempts':rows,'unresolved':unresolved,'posts_automatically':False}
