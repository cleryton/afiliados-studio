"""Verified local delivery bundles. This module never uploads or schedules."""
import hashlib
import json
import re
import threading
from uuid import uuid4
import zipfile
from PIL import Image
import core
import story_library

FILES={'video.mp4':'video.mp4','poster.png':'capa.png','legenda.txt':'legenda.txt','legendas.srt':'legendas.srt'}
LOCK=threading.Lock()


def target():
    with core.db() as c:
        row=c.execute("SELECT value FROM story_settings WHERE key='target_handle'").fetchone()
    handle=row['value'] if row else ''
    if not re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.]{1,22}[A-Za-z0-9_]',handle):
        raise ValueError('Indique o perfil exclusivo do projeto antes de preparar o pacote.')
    return handle


def folder(identifier):
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):
        raise ValueError('Capítulo inválido.')
    path=core.DATA/'story-delivery'/identifier
    if (path.resolve().parent!=(core.DATA/'story-delivery').resolve() or path.is_symlink() or
            not path.resolve().is_relative_to(core.DATA.resolve())):
        raise ValueError('Pasta de entrega inválida.')
    return path


def file_hash(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def snapshot(identifier):
    folder(identifier);handle=target()
    rows=story_library.latest_3d(story_library.entries())
    row=next((r for r in rows.values() if r['id']==identifier),None)
    if not row:raise ValueError('Escolha uma versão 3D completa e atual, com a oferta ainda autorizada.')
    meta=row['meta'];number=meta['episode'];content_key=f'3d:a-chave-do-12:{number}'
    if story_library.native_post_exists(content_key,handle):
        raise ValueError('Este capítulo já possui registro no TikTok. Não será preparado outro envio.')
    with core.db() as c:
        if c.execute("SELECT 1 FROM story_publications WHERE content_key=? AND status!='cancelled'",(content_key,)).fetchone():
            raise ValueError('Este capítulo já está na fila de postagem. Confira o pedido existente.')
    root=core.DATA/'stories'/identifier;fingerprints={};stats={}
    for name in FILES:
        path=root/name
        if path.is_symlink() or not path.is_file() or path.resolve().parent!=root.resolve():
            raise ValueError('Faltam arquivos válidos para preparar o capítulo.')
        stat=path.stat()
        if stat.st_size<=0 or stat.st_size>(128*1024**2 if name=='video.mp4' else 2*1024**2):
            raise ValueError('Um arquivo do capítulo está vazio ou excede o tamanho permitido.')
        fingerprints[name]=file_hash(path);stats[name]=[stat.st_size,stat.st_mtime_ns]
    if fingerprints['video.mp4']!=meta['sha256']:
        raise ValueError('O vídeo mudou depois da geração. O pacote foi retido.')
    caption=(root/'legenda.txt').read_text(encoding='utf-8')
    if len(' '.join(caption.split()))>2200 or not caption.strip():
        raise ValueError('Confira a legenda: ela deve ter conteúdo e até 2.200 caracteres.')
    offer=meta.get('offer')
    if offer and (offer['url'] not in caption or 'PUBLICIDADE' not in caption.upper()):
        raise ValueError('A legenda precisa preservar a publicidade e o link de afiliado.')
    with Image.open(root/'poster.png') as poster:
        if poster.format!='PNG' or poster.size!=(720,1280):raise ValueError('A capa precisa ser PNG vertical de 720 × 1280.')
        poster.verify()
    subtitle=(root/'legendas.srt').read_text(encoding='utf-8')
    if not re.search(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}',subtitle):
        raise ValueError('O arquivo de legendas precisa conter tempos válidos.')
    proof={'id':identifier,'chapter':number,'handle':handle,'content_key':content_key,
           'duration':meta['duration'],'files':fingerprints,'offer_hash':offer.get('product_hash') if offer else None,
           'ai_label_required':True,'third_party_commercial_label_required':bool(offer)}
    digest=hashlib.sha256(json.dumps(proof,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {'proof':proof,'fingerprint':digest,'stats':stats}


def info(identifier):
    """Cheap UI hint; download performs the complete byte and authorization check."""
    try:
        destination=folder(identifier);record=story_library.read_json(destination/'preparacao.json',32768)
        if not record or record['proof']['handle']!=target() or not (destination/'pacote.zip').is_file():return None
        root=core.DATA/'stories'/identifier
        for name in FILES:
            stat=(root/name).stat()
            if [stat.st_size,stat.st_mtime_ns]!=record['stats'][name]:return None
        return {'ready':True,'prepared_at':record['prepared_at'],'url':f'/stories/{identifier}/pacote.zip'}
    except (OSError,ValueError,KeyError,TypeError):return None


def download(identifier):
    current=snapshot(identifier);destination=folder(identifier)
    record=story_library.read_json(destination/'preparacao.json',32768);archive=destination/'pacote.zip'
    if (not record or not archive.is_file() or archive.is_symlink() or archive.resolve().parent!=destination.resolve() or
            current['fingerprint']!=record.get('fingerprint') or file_hash(archive)!=record.get('archive_sha256')):
        raise ValueError('O pacote mudou ou ficou desatualizado. Prepare-o novamente antes de baixar.')
    return archive


def prepare(identifier):
    with LOCK:return _prepare(identifier)


def _prepare(identifier):
    current=snapshot(identifier);destination=folder(identifier)
    try:
        download(identifier)
        return {'ok':True,'existing':True,**info(identifier)}
    except ValueError:pass
    destination.mkdir(parents=True,exist_ok=True)
    temporary=destination/(uuid4().hex+'.new');root=core.DATA/'stories'/identifier
    manifest={**current['proof'],'status':'local_ready_not_sent','scheduled':False,
              'prepared_at':core.stamp(),'fingerprint':current['fingerprint']}
    guide=(f"A CHAVE DO 12 · CAPÍTULO {manifest['chapter']}\nDestino: @{manifest['handle']}\n\n"
           'PACOTE LOCAL. Ainda não enviado nem agendado.\n'
           'video.mp4: capítulo completo; capa.png: quadro original do próprio vídeo.\n'
           'legenda.txt: texto da publicação; legendas.srt: arquivo de legendas.\n'
           'publicacao.json: destino, hashes e marcações necessárias. Não é recibo do TikTok.\n\n'
           'Ativar a identificação de conteúdo gerado por IA.\n'+
           ('Ativar a identificação comercial de terceiros. Há oferta de afiliado separada da ficção.\n' if manifest['third_party_commercial_label_required'] else '')+
           'Depois do envio, conferir o perfil e o resultado no TikTok. Uma data planejada não comprova agendamento.\n')
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED) as archive:
            for name,member in FILES.items():archive.write(root/name,member)
            archive.writestr('publicacao.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            archive.writestr('LEIA.txt',guide)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip():raise ValueError('O pacote não passou na conferência de integridade.')
            for name,member in FILES.items():
                if hashlib.sha256(archive.read(member)).hexdigest()!=current['proof']['files'][name]:
                    raise ValueError('Um arquivo mudou durante a preparação. Tente novamente.')
        if snapshot(identifier)['fingerprint']!=current['fingerprint']:
            raise ValueError('O capítulo ou o destino mudou durante a preparação.')
        record={**current,'prepared_at':manifest['prepared_at'],'archive_sha256':file_hash(temporary)}
        temporary.replace(destination/'pacote.zip')
        note=destination/'preparacao.new';note.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        note.replace(destination/'preparacao.json')
        return {'ok':True,'existing':False,**info(identifier)}
    finally:temporary.unlink(missing_ok=True)
