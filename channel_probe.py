"""One explicit, private channel test, without affiliation or public production."""
from datetime import datetime,timedelta
import json
import re
import shutil
import threading
from uuid import uuid4
import core
import diagnostics
import quality
import youtube_client as yt

_lock=threading.Lock()


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS channel_probe (
            id TEXT PRIMARY KEY,slot INTEGER UNIQUE NOT NULL CHECK(slot=1),
            stage TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,channel_id TEXT NOT NULL DEFAULT '',
            sha256 TEXT NOT NULL DEFAULT '',size INTEGER NOT NULL DEFAULT 0,voice INTEGER NOT NULL DEFAULT 0,
            video_id TEXT NOT NULL DEFAULT '',failures INTEGER NOT NULL DEFAULT 0,next_check TEXT,
            error TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);''')
        c.execute("UPDATE channel_probe SET stage='queued' WHERE stage='preparing'")
        c.execute("UPDATE channel_probe SET stage='uncertain',active=0,error='O aplicativo encerrou durante a abertura do envio. Confira o YouTube Studio; o teste não criará outro upload.' WHERE stage='initializing'")


def row():
    with core.db() as c:
        value=c.execute('SELECT * FROM channel_probe WHERE slot=1').fetchone()
        return dict(value) if value else None


def update(pid,**values):
    allowed={'stage','active','channel_id','sha256','size','voice','video_id','failures','next_check','error'}
    if not values or not set(values)<=allowed:raise ValueError('Atualização interna inválida.')
    with core.db() as c:c.execute('UPDATE channel_probe SET '+','.join(k+'=?' for k in values)+',updated_at=? WHERE id=?',(*values.values(),core.stamp(),pid))


def prepare():
    diagnostics.require_runtime()
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        existing=c.execute('SELECT * FROM channel_probe WHERE slot=1').fetchone()
        if existing:
            if existing['stage'] in ('failed_local','queued'):
                c.execute("UPDATE channel_probe SET stage='queued',active=1,error='',failures=0,next_check=NULL,updated_at=? WHERE slot=1",(core.stamp(),))
        else:
            c.execute("INSERT INTO channel_probe(id,slot,stage,created_at,updated_at) VALUES (?,1,'queued',?,?)",(uuid4().hex,core.stamp(),core.stamp()))
    return state()


def start():
    if core.TESTER:raise ValueError('O modo tester bloqueia o envio privado. Use o modo normal para autorizar seu canal.')
    item=row()
    if not item or item['stage'] not in ('ready_local','uploading','processing'):
        raise ValueError('Prepare o vídeo local antes de enviar. Envios incertos exigem conferência no YouTube Studio.')
    yt.verify_channel()
    config=yt.settings()
    if item['channel_id'] and item['channel_id']!=config['channel_id']:
        raise ValueError('Reconecte o canal que autorizou este teste; o destino não será trocado durante o envio.')
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        current=c.execute('SELECT * FROM channel_probe WHERE id=?',(item['id'],)).fetchone()
        if current['stage']!=item['stage']:return state()
        c.execute("UPDATE channel_probe SET active=1,channel_id=?,failures=0,next_check=NULL,error='',updated_at=? WHERE id=?",(config['channel_id'],core.stamp(),item['id']))
    return state()


def pause():
    with core.db() as c:c.execute('UPDATE channel_probe SET active=0,updated_at=? WHERE slot=1',(core.stamp(),))
    return state()


def permitted(item):
    latest=row()
    return bool(latest and latest['id']==item['id'] and latest['active'] and not core.TESTER
                and latest['channel_id'] and latest['channel_id']==yt.settings()['channel_id']
                and yt.secret_path('tokens').is_file())


def build(item):
    diagnostics.require_runtime()
    with core.db() as c:
        if c.execute("SELECT 1 FROM jobs WHERE status='rendering'").fetchone():return
        if not c.execute("UPDATE channel_probe SET stage='preparing',updated_at=? WHERE id=? AND stage='queued' AND active=1",(core.stamp(),item['id'])).rowcount:return
    root=core.DATA/'channel-test'/item['id'];root.mkdir(parents=True,exist_ok=True)
    diagnostics.run_probe(root,channel_test=True)
    report=json.loads((root/'diagnostic-report.json').read_text(encoding='utf-8'))
    if report['status'] not in ('passed','warning'):raise ValueError('local_render')
    source=root/'media'/'diagnostics';folder=core.DATA/'media'/item['id'];folder.mkdir(exist_ok=True)
    shutil.copyfile(source/'video.mp4',folder/'video.mp4')
    shutil.copyfile(source/'poster.png',folder/'scene-0.png')
    file=folder/'video.mp4'
    update(item['id'],stage='ready_local',active=0,sha256=quality.file_hash(file),size=file.stat().st_size,
           voice=int(bool(report.get('voice'))),failures=0,error='',next_check=None)


def metadata(item):
    return {'snippet':{'title':'Afiliados Studio · teste privado '+item['id'][:8],
            'description':'Vídeo próprio para validar geração, narração, envio e processamento. Sem produto, oferta comercial ou link de afiliado.',
            'categoryId':'22','defaultLanguage':'pt-BR'},
            'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':bool(item['voice'])},
            'paidProductPlacementDetails':{'hasPaidProductPlacement':False}}


def tick():
    if not _lock.acquire(blocking=False):return
    try:
        item=row()
        if not item or not item['active']:return
        if item['next_check'] and datetime.fromisoformat(item['next_check'])>core.now():return
        if item['stage']=='queued':
            try:build(item)
            except (OSError,ValueError):update(item['id'],stage='failed_local',active=0,error='Não foi possível criar o vídeo de teste. Confira espaço, vídeo e voz; você pode preparar novamente.')
            return
        if item['stage'] not in ('ready_local','uploading','processing') or core.TESTER:return
        if not permitted(item):
            update(item['id'],active=0,error='Reconecte o canal autorizado e retome o teste privado.');return
        file=core.DATA/'media'/item['id']/'video.mp4'
        try:
            if item['stage'] in ('ready_local','uploading'):
                if not file.is_file() or file.stat().st_size!=item['size'] or quality.file_hash(file)!=item['sha256']:
                    update(item['id'],active=0,error='O arquivo local mudou ou está ausente. Confira o envio antes de alterar este teste.');return
            if item['stage']=='ready_local':
                with core.db() as c:
                    c.execute('BEGIN IMMEDIATE')
                    if not c.execute("UPDATE channel_probe SET stage='initializing',updated_at=? WHERE id=? AND stage='ready_local' AND active=1",(core.stamp(),item['id'])).rowcount:return
                try:
                    if not permitted(item):
                        update(item['id'],stage='ready_local');return
                    yt.initialize_media(item['id'],metadata(item),file)
                except Exception:
                    update(item['id'],stage='uncertain',active=0,error='A abertura do envio não foi confirmada. Confira o YouTube Studio antes de continuar; não criaremos outro upload.');return
                update(item['id'],stage='uploading',failures=0,error='');return
            if item['stage']=='uploading':
                if not permitted(item):return
                result=yt.transfer(item['id'],file)
                if not result:
                    update(item['id'],next_check=(core.now()+timedelta(seconds=15)).isoformat());return
                if not isinstance(result,dict):raise ValueError('invalid_upload_response')
                video_id=result.get('id','')
                if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video_id):raise ValueError('missing_video_id')
                update(item['id'],video_id=video_id,stage='processing',failures=0,error='',next_check=None);return
            result=yt.api('videos?part=snippet,status,processingDetails&id='+item['video_id'])
            if not isinstance(result,dict) or not isinstance(result.get('items'),list):raise ValueError('invalid_processing_response')
            video=next((v for v in result['items'] if isinstance(v,dict) and v.get('id')==item['video_id']),None)
            if not video or video.get('snippet',{}).get('channelId')!=item['channel_id']:raise ValueError('channel_mismatch')
            status=video.get('status',{})
            if status.get('privacyStatus')!='private' or status.get('publishAt'):
                update(item['id'],active=0,error='O destino não confirmou um vídeo privado sem agenda. Confira o vídeo no YouTube Studio.');return
            if status.get('uploadStatus') in ('failed','rejected','deleted') or video.get('processingDetails',{}).get('processingStatus') in ('failed','terminated'):
                update(item['id'],active=0,error='O YouTube não concluiu o processamento. Confira o motivo no YouTube Studio.');return
            if status.get('uploadStatus')=='processed':
                update(item['id'],stage='passed',active=0,failures=0,error='',next_check=None)
            else:update(item['id'],next_check=(core.now()+timedelta(seconds=15)).isoformat(),failures=0,error='')
        except (OSError,ValueError):
            failures=item['failures']+1
            delay=(60,120,300,900,1800)[min(failures-1,4)]
            update(item['id'],failures=failures,active=int(failures<6),next_check=(core.now()+timedelta(seconds=delay)).isoformat(),
                   error='Não foi possível confirmar o próximo passo. A sessão existente será consultada novamente.' if failures<6 else 'Teste pausado após seis falhas. Confira o canal e retome; nenhum novo upload será aberto.')
    finally:_lock.release()


def state():
    item=row()
    if not item:return {'stage':'empty','active':False,'video_url':None,'remote_url':None}
    folder=core.DATA/'media'/item['id']
    return {k:item[k] for k in ('id','stage','active','voice','video_id','failures','next_check','error','updated_at')} | {
        'video_url':'/media/'+item['id']+'/video.mp4' if (folder/'video.mp4').is_file() else None,
        'remote_url':'https://www.youtube.com/watch?v='+item['video_id'] if re.fullmatch(r'[A-Za-z0-9_-]{11}',item['video_id']) else None}
