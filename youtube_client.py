"""YouTube OAuth + resumable upload. Credentials encrypted for the Windows user."""
import base64
import hashlib
import json
import re
import secrets
import threading
import time
from datetime import datetime,timedelta,timezone
from urllib.error import HTTPError
from urllib.parse import urlencode,urlparse
from urllib.request import Request,urlopen,build_opener,HTTPRedirectHandler
import core
from buffer_client import crypt

API='https://www.googleapis.com/youtube/v3/'
TOKEN_URL='https://oauth2.googleapis.com/token'
SCOPES='https://www.googleapis.com/auth/youtube.force-ssl'
_pending={}
_lock=threading.Lock()
_token_lock=threading.RLock()


def secret_path(name):return core.DATA/('youtube-'+name+'.secret')


def save_secret(name,value):
    raw=json.dumps(value).encode();encrypted=base64.b64encode(crypt(raw))
    file=secret_path(name);temp=file.with_suffix('.tmp');temp.write_bytes(encrypted);temp.replace(file)


def read_secret(name):
    try:return json.loads(crypt(base64.b64decode(secret_path(name).read_bytes()),decrypt=True))
    except OSError:raise ValueError('Conecte o YouTube na configuração inicial.') from None


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS youtube_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS youtube_jobs(job_id TEXT PRIMARY KEY REFERENCES jobs(id),stage TEXT NOT NULL,video_id TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,next_check TEXT);''')
        c.execute("UPDATE youtube_jobs SET stage='uncertain',error='O programa encerrou durante a criação do envio. Confira o YouTube Studio antes de tentar novamente.' WHERE stage='initializing'")
    import insights
    insights.init()
    import channel_probe
    channel_probe.init()


def settings():
    defaults={'enabled':False,'channel_id':'','channel_name':'','visibility':'public','last_error':'','last_verified_at':None,'channel_verified':False}
    with core.db() as c:rows=c.execute('SELECT * FROM youtube_settings').fetchall()
    return {**defaults,**{r['key']:json.loads(r['value']) for r in rows}}


def put(values):
    with core.db() as c:
        for key,value in values.items():c.execute('INSERT INTO youtube_settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)))


def configure(payload):
    enabled=payload.get('enabled') is True
    if enabled and core.TESTER:raise ValueError('O modo tester permite apenas geração local. Publicações externas estão bloqueadas.')
    if enabled and (not secret_path('tokens').is_file() or not settings()['channel_id']):raise ValueError('Conecte seu canal do YouTube antes de ativar a publicação.')
    visibility=payload.get('visibility','public')
    if visibility not in ('public','unlisted','private'):raise ValueError('Visibilidade inválida.')
    put({'enabled':enabled,'visibility':visibility})


def credentials(document):
    if isinstance(document,str):
        try:document=json.loads(document)
        except ValueError:raise ValueError('Selecione o arquivo JSON OAuth baixado do Google Cloud.') from None
    app=document.get('installed') if isinstance(document,dict) else None
    if not isinstance(app,dict):raise ValueError('Use uma credencial OAuth do tipo Aplicativo para computador.')
    cid=core.clean(app.get('client_id'),300,True);secret=core.clean(app.get('client_secret'),400,True)
    if not cid.endswith('.apps.googleusercontent.com'):raise ValueError('Client ID do Google inválido.')
    disconnect()
    save_secret('client',{'client_id':cid,'client_secret':secret})


def begin(port,run_private_test=False):
    if core.TESTER:raise ValueError('Conexão Google desabilitada no modo tester. Use o modo normal para testar uma conta real.')
    if run_private_test:
        import channel_probe
        item=channel_probe.row()
        if not item or item['stage']!='ready_local':raise ValueError('Prepare o vídeo de teste antes de conectar e testar em privado.')
    client=read_secret('client')
    state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    redirect=f'http://127.0.0.1:{port}/oauth/youtube/callback'
    with _lock:
        pending={'state':state,'verifier':verifier,'redirect':redirect,'expires_at':time.time()+600,'run_private_test':run_private_test is True}
        save_secret('oauth-pending',pending)
        _pending.clear();_pending.update(pending,expires=time.monotonic()+600)
    return 'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client['client_id'],'redirect_uri':redirect,'response_type':'code','scope':SCOPES,'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,'code_challenge_method':'S256'})


def token_request(values):
    request=Request(TOKEN_URL,data=urlencode(values).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'})
    try:
        with urlopen(request,timeout=20) as response:return json.loads(response.read(100_000))
    except (OSError,ValueError):raise ValueError('O Google não confirmou a autorização. Confira o projeto, o usuário de teste e tente conectar novamente.') from None


def complete(state,code):
    with _lock:
        if not _pending:
            try:
                saved=read_secret('oauth-pending')
                valid=(isinstance(saved,dict) and all(isinstance(saved.get(k),str) and saved[k] for k in ('state','verifier','redirect'))
                       and type(saved.get('expires_at')) in (int,float) and 0<saved['expires_at']-time.time()<=600)
                if valid:_pending.update(saved,expires=time.monotonic()+saved['expires_at']-time.time())
            except (OSError,ValueError,TypeError):pass
        if not _pending or time.monotonic()>_pending['expires'] or time.time()>_pending['expires_at'] or not secrets.compare_digest(state,_pending['state']):
            raise ValueError('Autorização inválida ou expirada. Inicie a conexão novamente pelo painel.')
        pending=dict(_pending);_pending.clear()
        secret_path('oauth-pending').unlink(missing_ok=True)
    client=read_secret('client')
    result=token_request({**client,'code':code,'code_verifier':pending['verifier'],'grant_type':'authorization_code','redirect_uri':pending['redirect']})
    if not result.get('access_token') or not result.get('refresh_token'):raise ValueError('A autorização não forneceu acesso persistente. Reconecte concedendo acesso ao canal.')
    if result.get('scope') and SCOPES not in result['scope'].split():raise ValueError('A autorização não concedeu a permissão necessária para gerenciar seus vídeos. Reconecte o canal.')
    result['expires_at']=time.time()+result.get('expires_in',3600)
    save_secret('tokens',result)
    try:
        response=api('channels?'+urlencode({'part':'snippet','mine':'true'}))
        channel=next(iter(response.get('items',[])),None)
        if not channel:raise ValueError('Crie um canal do YouTube nessa conta e conecte novamente.')
        put({'channel_id':channel['id'],'channel_name':channel['snippet']['title'],'last_error':'','last_verified_at':core.stamp(),'channel_verified':True})
    except Exception:
        secret_path('tokens').unlink(missing_ok=True);raise
    if pending.get('run_private_test'):
        import channel_probe
        try:channel_probe.start()
        except (OSError,ValueError):raise ValueError('Canal conectado. O teste privado precisa ser retomado no painel; confira a prévia e o estado do vídeo.') from None


def access_token():
    with _token_lock:return _access_token()


def _access_token():
    tokens=read_secret('tokens')
    if tokens.get('expires_at',0)>time.time()+90:return tokens['access_token']
    client=read_secret('client')
    result=token_request({**client,'refresh_token':tokens['refresh_token'],'grant_type':'refresh_token'})
    if not result.get('access_token'):raise ValueError('Reconecte o YouTube: acesso expirado ou revogado.')
    tokens.update(result);tokens['expires_at']=time.time()+result.get('expires_in',3600)
    save_secret('tokens',tokens)
    return tokens['access_token']


def api(path,body=None,method=None):
    if core.TESTER and (body is not None or method not in (None,'GET')):raise ValueError('Publicações e alterações externas estão bloqueadas no modo tester.')
    request=Request(API+path,data=json.dumps(body).encode() if body is not None else None,method=method,
                    headers={'Authorization':'Bearer '+access_token(),'Content-Type':'application/json'})
    try:
        with urlopen(request,timeout=25) as response:return json.loads(response.read(1_000_000))
    except HTTPError as error:
        if error.code==403:raise ValueError('YouTube recusou o acesso. Confira a ativação da API, permissões e cota no Google Cloud.') from None
        if error.code==401:raise ValueError('Reconecte o canal do YouTube.') from None
        raise ValueError(f'O YouTube recusou a operação (HTTP {error.code}). Confira o YouTube Studio.') from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def session_valid(url):
    parsed=urlparse(url)
    return parsed.scheme=='https' and parsed.hostname=='www.googleapis.com' and parsed.port in (None,443) and parsed.path=='/upload/youtube/v3/videos' and not parsed.username and not parsed.password


def metadata(job,product):
    title=re.sub('[<>]','',product['name']).strip()[:90]+' · Detalhes'
    description='Publicidade · Link de afiliado: posso receber comissão pela compra.\n'+product['url']+'\n\n'+re.sub('[<>]','',job['caption'].replace(product['url'],''))
    while len(description.encode('utf-8'))>4900:description=description[:-1]
    return {'snippet':{'title':title[:100],'description':description,'categoryId':'22','defaultLanguage':'pt-BR'},
            'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':bool(job.get('voice'))},
            'paidProductPlacementDetails':{'hasPaidProductPlacement':True}}


def initialize_upload(job,product,file):
    if core.TESTER:raise ValueError('Uploads estão bloqueados no modo tester.')
    initialize_media(job['id'],metadata(job,product),file)


def initialize_media(media_id,body,file):
    """Shared transport; callers must persist their own claim before this POST."""
    if core.TESTER:raise ValueError('Uploads estão bloqueados no modo tester.')
    url='https://www.googleapis.com/upload/youtube/v3/videos?'+urlencode({'uploadType':'resumable','part':'snippet,status,paidProductPlacementDetails','notifySubscribers':'false'})
    request=Request(url,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+access_token(),'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Type':'video/mp4','X-Upload-Content-Length':str(file.stat().st_size)})
    with build_opener(NoRedirect()).open(request,timeout=25) as response:location=response.headers.get('Location','')
    if not session_valid(location):raise ValueError('O YouTube não confirmou uma sessão de envio válida.')
    save_secret('session-'+media_id,{'url':location})


def transfer(jid,file):
    if core.TESTER:raise ValueError('Uploads estão bloqueados no modo tester.')
    session=read_secret('session-'+jid)['url']
    if not session_valid(session):raise ValueError('Sessão de envio inválida.')
    total=file.stat().st_size
    if total>150_000_000:raise ValueError('O vídeo ultrapassa o limite local de 150 MB.')
    headers={'Authorization':'Bearer '+access_token(),'Content-Length':'0','Content-Range':f'bytes */{total}'}
    offset=0
    try:
        with build_opener(NoRedirect()).open(Request(session,data=b'',headers=headers,method='PUT'),timeout=25) as response:
            return json.loads(response.read(200_000))
    except HTTPError as error:
        if error.code==308:
            match=re.fullmatch(r'bytes=0-(\d+)',error.headers.get('Range',''))
            offset=int(match[1])+1 if match else 0
        elif error.code in (404,410):raise ValueError('A sessão expirou. Confira o YouTube Studio antes de iniciar outro envio.') from None
        else:raise
    if offset>=total:raise ValueError('Upload recebido sem confirmação final. O sistema consultará novamente.')
    headers={'Authorization':'Bearer '+access_token(),'Content-Type':'video/mp4','Content-Length':str(total-offset),'Content-Range':f'bytes {offset}-{total-1}/{total}'}
    with file.open('rb') as stream:
        stream.seek(offset)
        try:
            with build_opener(NoRedirect()).open(Request(session,data=stream,headers=headers,method='PUT'),timeout=90) as response:
                return json.loads(response.read(200_000))
        except HTTPError as error:
            if error.code==308:return None
            raise


def update_job(jid,**values):
    allowed={'stage','video_id','error','next_check'}
    if not values or not set(values)<=allowed:raise ValueError('Atualização interna inválida.')
    with core.db() as c:c.execute('UPDATE youtube_jobs SET '+','.join(f'{k}=?' for k in values)+',updated_at=? WHERE job_id=?',(*values.values(),core.stamp(),jid))


def process(job,product):
    if core.TESTER:return
    import autopilot,catalog,campaigns,quality
    jid=job['id'];config=settings()
    with core.db() as c:
        current=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        if not current or current['status']!='ready':return
        job=dict(current)
        product=dict(c.execute('SELECT * FROM products WHERE id=?',(job['product_id'],)).fetchone())
        row=c.execute('SELECT * FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
    if row and row['stage'] in ('uncertain','failed','published'):return
    if row and row['next_check'] and datetime.fromisoformat(row['next_check'])>core.now():return
    file=core.DATA/'media'/jid/'video.mp4'
    try:
        if not row and not file.is_file():
            import production
            production.refresh_ready(jid)
            return
        if (not row or row['stage']=='uploading') and not file.is_file():raise ValueError('Arquivo MP4 ausente. Gere novamente antes de enviar.')
        with core.db() as c:
            meta=c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()
            authorization=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(product['id'],)).fetchone()
        expected=json.loads(meta['payload']).get('source_hash') if meta else None
        brief=campaigns.for_product(product['id'])
        previous_brief=json.loads(meta['payload']).get('campaign') if meta else None
        changed=expected and expected!=hashlib.sha256(product.get('description','').encode()).hexdigest()
        import content_engine
        prior_product=json.loads(meta['payload']).get('product_hash') if meta else None
        changed=changed or bool(prior_product and prior_product!=content_engine.product_fingerprint(product))
        changed=changed or (brief or {}).get('revision')!=(previous_brief or {}).get('revision')
        approved=authorization and authorization['active'] and authorization['approved'] and catalog.eligible(product['id'])
        approved=approved and (not brief or brief['active'])
        changed=changed or product['url'] not in job['caption'] or product['name'] not in job['caption']
        if row and row['stage']=='held_local' and approved:
            with core.db() as c:c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(jid,))
            row=None
        if not row and approved and changed:
            import production
            production.refresh_ready(jid)
            return
        if not approved or changed:
            if not row:
                with core.db() as c:c.execute('INSERT INTO youtube_jobs(job_id,stage,updated_at) VALUES (?,?,?)',(jid,'held_local',core.stamp()))
                update_job(jid,error='Produto pausado ou catálogo vencido. O envio aguarda uma fonte autorizada atualizada.',next_check=(core.now()+timedelta(minutes=15)).isoformat())
                return
            if row and row['video_id'] and row['stage'] in ('processing','scheduled'):
                api('videos?part=status',{'id':row['video_id'],'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}},'PUT')
                update_job(jid,stage='held')
            raise ValueError('Produto pausado, catálogo vencido ou dados alterados. Publicação retida; confira o catálogo e o YouTube Studio.')
        if row and row['stage']=='held':
            if not quality.inspect(jid,verify_media=True)['allowed']:return
            update_job(jid,stage='processing',error='')
            return
        review=quality.inspect(jid,verify_media=True)
        if not review['allowed']:
            if row:
                if row['video_id'] and row['stage'] in ('processing','scheduled'):
                    api('videos?part=status',{'id':row['video_id'],'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False}},'PUT')
                    update_job(jid,stage='held',error='Publicação retida pelas verificações editoriais. Confira a fila de revisão.')
                else:update_job(jid,error='Envio aguardando verificações editoriais. Confira a fila de revisão.')
            return
        if not row:
            import production
            with core.db() as c:
                c.execute('BEGIN IMMEDIATE')
                current=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
                if not current or current['status']!='ready' or production.block_reason(c,current):return
                if any(current[key]!=job[key] for key in ('scenes','caption','due_at')):return
                c.execute('INSERT INTO youtube_jobs(job_id,stage,updated_at) VALUES (?,?,?)',(jid,'initializing',core.stamp()))
            if not quality.inspect(jid,verify_media=True)['allowed']:
                with core.db() as c:c.execute("DELETE FROM youtube_jobs WHERE job_id=? AND stage='initializing'",(jid,))
                return
            try:initialize_upload(job,product,file)
            except Exception as error:
                update_job(jid,stage='uncertain',error=str(error)[:500]);return
            update_job(jid,stage='uploading')
            with core.db() as c:row=c.execute('SELECT * FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
        if row['stage']=='uploading':
            result=transfer(jid,file)
            if not result:return
            if not result.get('id'):raise ValueError('Upload recebido sem ID confirmado.')
            update_job(jid,stage='processing',video_id=result['id'],error='')
            return
        video_id=row['video_id']
        result=api('videos?'+urlencode({'part':'snippet,status,processingDetails,paidProductPlacementDetails,statistics','id':video_id})).get('items',[])
        if not result:raise ValueError('Vídeo não encontrado no canal conectado.')
        video=result[0]
        if video['snippet'].get('channelId')!=config['channel_id']:raise ValueError('O vídeo pertence a outro canal. Verifique a conexão.')
        status=video.get('status',{})
        if status.get('uploadStatus') in ('failed','rejected','deleted'):
            update_job(jid,stage='failed',error='YouTube informou falha ou rejeição. Confira o Studio.');return
        if status.get('uploadStatus')!='processed':return
        if not video.get('paidProductPlacementDetails',{}).get('hasPaidProductPlacement'):
            api('videos?part=paidProductPlacementDetails',{'id':video_id,'paidProductPlacementDetails':{'hasPaidProductPlacement':True}},'PUT')
            update_job(jid,error='Aguardando confirmação da identificação comercial pelo YouTube.',next_check=(core.now()+timedelta(minutes=15)).isoformat())
            return  # Re-read before changing visibility.
        if status.get('privacyStatus')=='public':
            timestamp=video['snippet'].get('publishedAt') or core.stamp()
            with core.db() as c:
                c.execute("UPDATE jobs SET status='published',published_at=?,tiktok_url=?,views=?,updated_at=? WHERE id=?",(timestamp,'https://www.youtube.com/watch?v='+video_id,int(video.get('statistics',{}).get('viewCount',0)),core.stamp(),jid))
            update_job(jid,stage='published',error='')
            autopilot.event('published','Publicação pública confirmada pelo YouTube.',jid)
            return
        if row['stage']=='processing':
            if config['visibility']=='public':
                due=datetime.fromisoformat(job['due_at'])
                if due<core.now()+timedelta(minutes=5):
                    import planning
                    due=planning.reserve_late(jid,processing=True)
                    if not due:return
                target={'privacyStatus':'private','publishAt':due.astimezone(timezone.utc).isoformat().replace('+00:00','Z'),'selfDeclaredMadeForKids':False,'containsSyntheticMedia':bool(job.get('voice'))}
            else:target={'privacyStatus':config['visibility'],'selfDeclaredMadeForKids':False,'containsSyntheticMedia':bool(job.get('voice'))}
            api('videos?part=status',{'id':video_id,'status':target},'PUT')
            update_job(jid,stage='scheduled' if config['visibility']=='public' else 'uploaded',error='')
            autopilot.event('youtube','Vídeo enviado ao YouTube com publicidade identificada. '+('Publicação agendada.' if config['visibility']=='public' else 'Visibilidade definida na configuração.'),jid)
            return
        update_job(jid,error='')
    except Exception as error:
        if not row:
            with core.db() as c:c.execute('INSERT OR IGNORE INTO youtube_jobs(job_id,stage,updated_at) VALUES (?,?,?)',(jid,'failed',core.stamp()))
        update_job(jid,error=str(error)[:600],next_check=(core.now()+timedelta(minutes=15)).isoformat())


def tick():
    if core.TESTER:return
    config=settings()
    if not config['enabled']:return
    import autopilot
    if not autopilot.settings()['enabled']:return
    with core.db() as c:
        rows=c.execute("""SELECT jobs.* FROM jobs JOIN auto_jobs ON auto_jobs.job_id=jobs.id
            LEFT JOIN youtube_jobs ON youtube_jobs.job_id=jobs.id
            WHERE jobs.status='ready' AND auto_jobs.delivery='local' AND auto_jobs.buffer_id=''
            AND (youtube_jobs.stage IS NULL OR youtube_jobs.stage NOT IN ('uncertain','failed','published'))
            AND (youtube_jobs.next_check IS NULL OR youtube_jobs.next_check<=?)
            ORDER BY jobs.due_at,jobs.id LIMIT 3""",(core.stamp(),)).fetchall()
        products={r['id']:dict(r) for r in c.execute('SELECT * FROM products')}
    for row in rows:process(dict(row),products[row['product_id']])
    import insights
    insights.sync()


def disconnect():
    with _lock:
        _pending.clear()
        secret_path('oauth-pending').unlink(missing_ok=True)
    put({'enabled':False,'channel_id':'','channel_name':'','channel_verified':False,'last_verified_at':None})
    secret_path('tokens').unlink(missing_ok=True)
    with core.db() as c:c.execute('DELETE FROM youtube_metrics')


def verify_channel():
    config=settings()
    if not secret_path('tokens').is_file() or not config['channel_id']:raise ValueError('Conecte seu canal antes de verificar a autorização.')
    try:
        channels=api('channels?'+urlencode({'part':'snippet','mine':'true'})).get('items',[])
        match=next((c for c in channels if c['id']==config['channel_id']),None)
        if not match:raise ValueError('O Google não confirmou acesso a este canal. Reconecte a conta correta.')
        put({'channel_verified':True,'last_verified_at':core.stamp(),'last_error':'','channel_name':match['snippet']['title']})
        return {'ok':True,'checked_at':settings()['last_verified_at']}
    except (ValueError,OSError) as error:
        put({'channel_verified':False,'last_verified_at':core.stamp(),'last_error':str(error)[:500]})
        raise ValueError(str(error)) from None


def reconcile(jid,video_id):
    if not isinstance(video_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',video_id):raise ValueError('Informe o ID de 11 caracteres do vídeo existente no YouTube Studio.')
    video=next(iter(api('videos?'+urlencode({'part':'snippet,status','id':video_id})).get('items',[])),None)
    if not video or video['snippet'].get('channelId')!=settings()['channel_id']:raise ValueError('Vídeo não encontrado no canal conectado.')
    if video.get('status',{}).get('privacyStatus')!='private':raise ValueError('Vincule um vídeo privado. Gerencie vídeos já publicados diretamente no YouTube Studio.')
    with core.db() as c:
        row=c.execute('SELECT stage FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
        if not row or row['stage'] not in ('uncertain','failed','held'):raise ValueError('Este envio não precisa de reconciliação.')
        c.execute("UPDATE youtube_jobs SET stage='processing',video_id=?,error='',next_check=NULL,updated_at=? WHERE job_id=?",(video_id,core.stamp(),jid))


def state():
    import insights,channel_probe
    with core.db() as c:rows=[dict(r) for r in c.execute('SELECT * FROM youtube_jobs ORDER BY updated_at DESC')]
    return {'settings':settings(),'client_configured':secret_path('client').is_file(),'connected':secret_path('tokens').is_file() and bool(settings()['channel_id']),'jobs':rows,'metrics':insights.state(),'test':channel_probe.state(),
            'notice':'Envio direto pela API oficial, com autorização inicial Google. Projetos e contas estão sujeitos a permissões, processamento e cotas do YouTube.'}
