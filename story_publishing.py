"""Persistent TikTok outbox: fixed destination, no blind retry, explicit publication."""
from datetime import datetime,timedelta
import hashlib
import json
import re
from uuid import uuid4
from urllib.parse import urlsplit
import core
from story_week_catalog import NUMBERS
import upload_post_client as provider

DEFAULTS={'enabled':False,'binding':None,'hour':18,'monthly_limit':10,'auto_3d':False,'checked_at':None,'automation_note':''}


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS story_publishing_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS story_publications(
          id TEXT PRIMARY KEY,media_id TEXT NOT NULL,content_key TEXT NOT NULL,account_id TEXT NOT NULL,
          binding TEXT NOT NULL,media_hash TEXT NOT NULL,caption_hash TEXT NOT NULL,offer TEXT,
          status TEXT NOT NULL,due_at TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
          external_url TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',checked_at TEXT,attempted_at TEXT,
          UNIQUE(account_id,content_key),UNIQUE(account_id,media_hash));''')
        if 'attempted_at' not in {row['name'] for row in c.execute('PRAGMA table_info(story_publications)')}:
            c.execute('ALTER TABLE story_publications ADD COLUMN attempted_at TEXT')
        c.execute("UPDATE story_publications SET status='uncertain',error='O programa encerrou durante o envio. Consultando o pedido sem reenviar.' WHERE status='sending'")


def settings():
    with core.db() as c:rows=c.execute('SELECT key,value FROM story_publishing_settings').fetchall()
    return {**DEFAULTS,**{r['key']:json.loads(r['value']) for r in rows}}


def put(values):
    with core.db() as c:
        for k,v in values.items():c.execute('INSERT INTO story_publishing_settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,json.dumps(v,ensure_ascii=False)))


def connect(payload):
    if core.TESTER:raise ValueError('Conexões externas estão bloqueadas no modo tester.')
    key=core.clean(payload.get('api_key',''),3000,True)
    if len(key)<16 or any(ch.isspace() for ch in key):raise ValueError('Informe uma chave válida, somente neste painel local.')
    handle=core.clean(payload.get('handle',''),25,True).lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_.]{2,24}',handle):raise ValueError('Informe o @ do perfil exclusivo do projeto.')
    with core.db() as c:target=c.execute("SELECT value FROM story_settings WHERE key='target_handle'").fetchone()
    if not target or target[0].lower()!=handle.lower():raise ValueError('O @ deve ser o mesmo perfil exclusivo salvo nesta tela.')
    binding=provider.destination(provider.profiles(key),handle)
    provider.store_key(key);put({'binding':binding,'enabled':False,'checked_at':core.stamp(),'auto_3d':False})
    return {'ok':True,'handle':binding['handle']}


def configure(payload):
    enabled=payload.get('enabled') is True;config=settings()
    if enabled and core.TESTER:raise ValueError('O modo tester bloqueia publicações externas.')
    if enabled:
        if payload.get('approved') is not True:raise ValueError('Confirme a publicação pública e o perfil de destino.')
        if not config['binding'] or not provider.key_path().is_file():raise ValueError('Conecte o TikTok pelo Upload-Post antes de ativar.')
        check_destination(config['binding'])
    hour=core.numeric(payload.get('hour',config['hour']),23,integer=True)
    put({'enabled':enabled,'hour':hour,'auto_3d':enabled and payload.get('auto_3d') is True})
    return {'ok':True,'enabled':enabled}


def check_destination(binding):
    actual=provider.destination(provider.profiles(),binding['handle'])
    if actual['account_id']!=binding['account_id'] or actual['profile']!=binding['profile']:
        raise ValueError('A conta conectada mudou. Reconecte e confirme o perfil antes de publicar.')
    return actual


def media_snapshot(identifier,allow_archive=False):
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Episódio inválido.')
    folder=core.DATA/'stories'/identifier
    for name in ('video.mp4','roteiro.json','legenda.txt'):
        path=folder/name
        if not path.is_file() or path.resolve().parent!=folder.resolve():raise ValueError('Arquivos do episódio ausentes.')
    if (folder/'roteiro.json').stat().st_size>512*1024:raise ValueError('Roteiro inválido.')
    meta=json.loads((folder/'roteiro.json').read_text(encoding='utf-8'))
    if not meta.get('voice') or not 0<float(meta.get('duration',0))<=180:raise ValueError('O episódio deve ter voz e duração verificada.')
    with core.db() as c:row=c.execute('SELECT status,series_id,number FROM story_episodes WHERE id=?',(identifier,)).fetchone()
    if row and row['status']!='ready':raise ValueError('Aguarde a montagem do episódio.')
    if not row:
        from animation3d import preview_state
        archived=allow_archive and meta.get('animation_type')=='original_procedural_3d' and meta.get('character_animation') is True
        preview=None if archived else preview_state()
        if not archived and (not preview or preview['id']!=identifier):raise ValueError('Escolha uma prévia 3D completa e atual.')
    import story_offers
    offer=meta.get('offer')
    if not story_offers.current(offer):raise ValueError('A oferta mudou ou perdeu autorização.')
    if row and story_offers.for_series(row['series_id'])!=offer:raise ValueError('A oferta exportada está desatualizada.')
    caption=' '.join((folder/'legenda.txt').read_text(encoding='utf-8').split())
    if len(caption)>2200:raise ValueError('Reduza a legenda para até 2.200 caracteres antes de publicar.')
    if offer and (offer['url'] not in caption or 'PUBLICIDADE' not in caption.upper()):raise ValueError('A legenda precisa preservar o link e a publicidade.')
    with (folder/'video.mp4').open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=meta.get('sha256'):raise ValueError('O MP4 mudou após a validação. Gere novamente.')
    number=meta.get('episode',1)
    if type(number) is not int or number not in NUMBERS:raise ValueError('Capítulo 3D inválido.')
    if number>=9:
        import story_director
        story_director.validate_metadata(meta)
    content=f"fiction:{row['series_id']}:{row['number']}" if row else f'3d:a-chave-do-12:{number}'
    return {'path':folder/'video.mp4','hash':digest,'caption':caption,'caption_hash':hashlib.sha256(caption.encode()).hexdigest(),
            'offer':offer,'content_key':content}


def queue(identifier,now=False,*,planned_for=None,allow_archive=False):
    config=settings()
    if core.TESTER:raise ValueError('O modo tester bloqueia a fila de publicação externa.')
    if not config['enabled'] or not config['binding']:raise ValueError('Ative a publicação e confirme o perfil primeiro.')
    snapshot=media_snapshot(identifier,allow_archive=allow_archive);current=core.now();account=config['binding']['account_id']
    import story_library
    if story_library.native_post_exists(snapshot['content_key'], config['binding']['handle']):
        raise ValueError('Este capítulo já tem registro de postagem ou agendamento no TikTok Studio. Confira o destino; não haverá novo envio.')
    import story_native
    if story_native.blocks_api(snapshot['content_key'],config['binding']['handle']):
        raise ValueError('Este capítulo tem uma tentativa no TikTok Studio. Confira o pedido original antes de usar outra integração.')
    due=current if now else current.replace(hour=config['hour'],minute=0,second=0,microsecond=0)
    if not now and due<=current:due+=timedelta(days=1)
    if planned_for is not None:
        proposed=datetime.fromisoformat(planned_for)
        if proposed.tzinfo is None:raise ValueError('A proposta precisa informar o fuso horário.')
        proposed=proposed.astimezone(core.TZ)
        # A missed preparation date is not permission to publish immediately.
        due=proposed if proposed>current else due
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT id FROM story_publications WHERE account_id=? AND (content_key=? OR media_hash=?)',
            (account,snapshot['content_key'],snapshot['hash'])).fetchone()
        if prior:return {'id':prior['id'],'existing':True}
        latest=c.execute("SELECT MAX(due_at) FROM story_publications WHERE account_id=? AND status!='cancelled'",(account,)).fetchone()[0]
        if latest:
            last=datetime.fromisoformat(latest)
            if last.date()>=due.date():due=(last+timedelta(days=1)).replace(hour=config['hour'],minute=0,second=0,microsecond=0)
        identifier_request=uuid4().hex
        c.execute('INSERT INTO story_publications(id,media_id,content_key,account_id,binding,media_hash,caption_hash,offer,status,due_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (identifier_request,identifier,snapshot['content_key'],account,json.dumps(config['binding']),snapshot['hash'],snapshot['caption_hash'],json.dumps(snapshot['offer']),
             'queued',due.isoformat(),core.stamp(),core.stamp()))
    return {'id':identifier_request,'existing':False}


def queue_prepared():
    """Feed the outbox from the pinned weekly plan, never the newest preview first."""
    config=settings();binding=config['binding']
    if not config['enabled'] or not binding or not config['auto_3d']:return
    with core.db() as c:
        plan=c.execute('SELECT * FROM story_weeks ORDER BY created_at DESC LIMIT 1').fetchone()
        slots=c.execute('SELECT * FROM story_week_slots WHERE week_id=? ORDER BY due_at,number',
                        (plan['id'],)).fetchall() if plan else []
        jobs={r['content_key']:dict(r) for r in c.execute('SELECT * FROM story_publications WHERE account_id=?',
                                                       (binding['account_id'],))}
    def note(message):
        if config.get('automation_note')!=message:put({'automation_note':message})
    if not plan:
        from animation3d import preview_state
        preview=preview_state()
        if preview:
            import story_library
            snapshot=media_snapshot(preview['id'])
            if not story_library.native_post_exists(snapshot['content_key'],binding['handle']):queue(preview['id'])
        note('Sem semana preparada; somente a prévia atual pode entrar na fila.')
        return
    if plan['handle'].lower()!=binding['handle'].lower():
        note('O perfil da semana difere da conexão. Confira o destino.');return
    import story_delivery
    if story_delivery.target().lower()!=binding['handle'].lower():
        note('O perfil exclusivo mudou. Confira a conexão antes de continuar.');return
    if plan['paused']:
        note('Semana pausada. Nenhum novo capítulo entrará na fila.');return
    import story_offers
    if not story_offers.current(json.loads(plan['offer'])):
        note('A oferta da semana precisa de revisão.');return
    import story_library
    for slot in slots:
        content=f"3d:a-chave-do-12:{slot['number']}"
        if story_library.native_post_exists(content,binding['handle']):continue
        prior=jobs.get(content)
        if prior:
            if prior['status'] in ('queued','published'):continue
            note('Confira o pedido anterior antes de avançar a sequência.');return
        if slot['status']!='ready' or not slot['media_id']:
            note(f"Aguardando o capítulo {slot['number']}; a sequência será preservada.");return
        snapshot=media_snapshot(slot['media_id'],allow_archive=True)
        if snapshot['content_key']!=content or snapshot['offer']!=json.loads(plan['offer']):
            raise ValueError('O arquivo não corresponde ao capítulo ou à oferta da semana.')
        queue(slot['media_id'],planned_for=slot['due_at'],allow_archive=True)
        note('Semana sendo colocada na agenda local, em ordem. Isso ainda não é um agendamento no TikTok.')
        return
    note('Todos os capítulos têm registro nativo ou pedido na fila. Confira a confirmação no destino.')


def check_week_sequence(row,binding):
    """A manually queued later chapter must not jump an unfinished predecessor."""
    with core.db() as c:
        slot=c.execute('SELECT s.*,w.paused,w.handle FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id WHERE s.media_id=? ORDER BY w.created_at DESC LIMIT 1',
                       (row['media_id'],)).fetchone()
        if not slot:return
        if slot['paused']:raise ValueError('A semana foi pausada antes do envio.')
        if slot['handle'].lower()!=binding['handle'].lower():raise ValueError('O destino da semana mudou. Envio retido.')
        prior=c.execute('SELECT number FROM story_week_slots WHERE week_id=? AND (due_at<? OR (due_at=? AND number<?)) ORDER BY due_at,number',
                        (slot['week_id'],slot['due_at'],slot['due_at'],slot['number'])).fetchall()
        published={r['content_key'] for r in c.execute("SELECT content_key FROM story_publications WHERE account_id=? AND status='published'",(binding['account_id'],))}
    import story_library
    for earlier in prior:
        key=f"3d:a-chave-do-12:{earlier['number']}"
        if key not in published and not story_library.native_post_exists(key,binding['handle']):
            raise ValueError('Um capítulo anterior ainda não tem confirmação no destino. Confira a sequência antes de continuar.')


def publication_result(value,binding):
    for warning in value.get('warnings',[]):
        if re.search(r'brand|commercial|is_aigc|ai.generated',str(warning),re.I):
            return 'needs_review','','O provedor avisou sobre a identificação comercial ou de IA. Confira o pedido; não haverá reenvio.'
    results=value.get('results',[])
    if isinstance(results,dict):results=[dict(v,platform=k) for k,v in results.items() if isinstance(v,dict)]
    candidates=[v for v in results if isinstance(v,dict) and v.get('platform')=='tiktok']
    if not candidates and any(k in value for k in ('post_url','post_id','fallback_to_inbox')):candidates=[value]
    for result in candidates:
        if any(re.search(r'brand|commercial|is_aigc|ai.generated',str(w),re.I) for w in result.get('warnings',[])):
            return 'needs_review','','O provedor avisou sobre a identificação comercial ou de IA. Confira o pedido; não haverá reenvio.'
        if result.get('fallback_to_inbox') or str(result.get('post_id','')).startswith('v_inbox'):
            return 'draft','','O provedor entregou um rascunho; não é uma publicação confirmada.'
        if result.get('skipped') or result.get('status')=='skipped':return 'blocked','','TikTok não configurado no perfil do provedor.'
        url=result.get('post_url') or result.get('url') or ''
        parsed=urlsplit(url)
        valid=parsed.scheme=='https' and not parsed.username and parsed.hostname in ('www.tiktok.com','tiktok.com') and re.fullmatch('/@'+re.escape(binding['handle'])+r'/video/\d+',parsed.path)
        if valid and result.get('success') is True:return 'published',url,''
        if result.get('status')=='failed' or result.get('success') is False:return 'blocked','','O provedor informou falha. Confira no painel antes de novo envio.'
    if value.get('status')=='failed' or value.get('success') is False:return 'blocked','','O provedor informou falha. Confira o pedido original.'
    return 'processing','','Aguardando confirmação do link publicado.'


def update(identifier,status,error='',url=''):
    with core.db() as c:c.execute('UPDATE story_publications SET status=?,error=?,external_url=?,updated_at=?,checked_at=? WHERE id=?',
        (status,error,url,core.stamp(),core.stamp(),identifier))


def tick():
    if core.TESTER:return
    config=settings()
    # Accepted/uncertain requests are only read, even while new sends are paused.
    with core.db() as c:pending=c.execute("SELECT * FROM story_publications WHERE status IN ('processing','uncertain','sending') ORDER BY updated_at LIMIT 1").fetchone()
    if pending:
        if pending['checked_at'] and (core.now()-datetime.fromisoformat(pending['checked_at'])).total_seconds()<30:return
        try:
            value=provider.status(pending['id']);status,url,error=publication_result(value,json.loads(pending['binding']))
            update(pending['id'],status,error,url)
        except ValueError:update(pending['id'],'uncertain','Sem confirmação do pedido original. Nenhum vídeo será reenviado.')
        return
    if not config['enabled'] or not config['binding']:return
    if config.get('auto_3d'):
        try:queue_prepared()
        except (ValueError,OSError):
            put({'automation_note':'Não foi possível validar o próximo capítulo. Confira os arquivos e a oferta antes de avançar.'})
            return
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute("SELECT * FROM story_publications WHERE status='queued' AND due_at<=? ORDER BY due_at LIMIT 1",(core.stamp(),)).fetchone()
        if not row:return
        paused=c.execute('SELECT w.paused FROM story_weeks w JOIN story_week_slots s ON s.week_id=w.id WHERE s.media_id=? ORDER BY w.created_at DESC LIMIT 1',
                         (row['media_id'],)).fetchone()
        if paused and paused['paused']:return
        used=c.execute("SELECT COUNT(*) FROM story_publications WHERE substr(attempted_at,1,7)=?",(core.stamp()[:7],)).fetchone()[0]
        today=c.execute("SELECT COUNT(*) FROM story_publications WHERE substr(attempted_at,1,10)=?",(core.stamp()[:10],)).fetchone()[0]
        if used>=config['monthly_limit'] or today:return
        c.execute("UPDATE story_publications SET status='sending',updated_at=? WHERE id=?",(core.stamp(),row['id']))
    try:
        binding=json.loads(row['binding'])
        if binding['account_id']!=config['binding']['account_id']:raise ValueError('O destino da fila difere da conexão atual.')
        binding=check_destination(binding);snapshot=media_snapshot(row['media_id'],allow_archive=True)
        if snapshot['hash']!=row['media_hash'] or snapshot['caption_hash']!=row['caption_hash'] or snapshot['offer']!=json.loads(row['offer']):
            raise ValueError('O vídeo, a legenda ou a oferta mudou. O envio foi retido.')
        # Recheck current authorization and native receipts at the mutation boundary.
        current=settings()
        if not current['enabled']:raise ValueError('Envio pausado antes de transmitir o vídeo.')
        if current['binding']!=config['binding']:raise ValueError('A conexão mudou durante a conferência. Confira o destino.')
        import story_delivery
        import story_library
        if story_delivery.target().lower()!=binding['handle'].lower():raise ValueError('O perfil exclusivo do projeto mudou. Envio retido.')
        if story_library.native_post_exists(snapshot['content_key'],binding['handle']):
            raise ValueError('Este capítulo já tem registro no TikTok Studio. Nenhum novo upload foi feito.')
        import story_native
        if story_native.blocks_api(snapshot['content_key'],binding['handle']):
            raise ValueError('Há uma tentativa do TikTok Studio para este capítulo. Não será transmitida outra cópia pela API.')
        check_week_sequence(row,binding)
        with core.db() as c:
            c.execute('UPDATE story_publications SET attempted_at=? WHERE id=?',(core.stamp(),row['id']))
        value=provider.upload(snapshot['path'],snapshot['caption'],binding,row['id'],bool(snapshot['offer']))
        status,url,error=publication_result(value,binding);update(row['id'],status,error,url)
    except provider.ProviderError as error:update(row['id'],'uncertain' if error.uncertain else 'blocked',str(error))
    except ValueError as error:update(row['id'],'blocked',str(error))
    except Exception:update(row['id'],'uncertain','A execução foi interrompida. Consultando o pedido original sem reenviar.')


def state():
    config=settings()
    with core.db() as c:rows=[dict(r) for r in c.execute('SELECT id,media_id,status,due_at,external_url,error,updated_at FROM story_publications ORDER BY created_at DESC LIMIT 30')]
    return {'enabled':config['enabled'],'connected':bool(config['binding'] and provider.key_path().is_file()),
        'handle':(config['binding'] or {}).get('handle',''),'hour':config['hour'],'auto_3d':config['auto_3d'],
        'monthly_limit':config['monthly_limit'],'jobs':rows,'provider':'Upload-Post','tester_blocked':core.TESTER,
        'automation_note':config['automation_note']}
