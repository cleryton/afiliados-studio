"""Fixed-host Upload-Post API, local streaming uploads and DPAPI-protected key."""
import base64
import http.client
import json
from urllib.parse import urlencode
from uuid import uuid4
import core
from buffer_client import crypt

HOST='api.upload-post.com'


class ProviderError(ValueError):
    def __init__(self,message,uncertain=False):
        super().__init__(message);self.uncertain=uncertain


def key_path():return core.DATA/'upload-post.key'


def store_key(key):
    temporary=key_path().with_suffix('.tmp')
    temporary.write_bytes(base64.b64encode(crypt(key.encode())))
    temporary.replace(key_path())


def load_key():
    try:return crypt(base64.b64decode(key_path().read_bytes()),decrypt=True).decode()
    except (OSError,ValueError):raise ValueError('Conecte novamente a chave do Upload-Post no painel local.') from None


def response_json(response,mutating=False):
    raw=response.read(2_000_001)
    if response.status>=400:
        message='O provedor não confirmou a operação. Confira a conexão e a cota no Upload-Post.'
        if response.status in (401,403):message='A conexão foi recusada. Confira a chave, o plano e a autorização do TikTok.'
        if response.status==429:message='Limite do provedor atingido. Nenhum novo envio será repetido automaticamente.'
        if response.status==403:
            try:
                reason=str(json.loads(raw).get('message','')).lower()
                if 'tiktok' in reason and 'free' in reason:message='O provedor exige plano pago para TikTok nesta conta. O envio foi retido; nenhum plano foi contratado.'
            except (ValueError,AttributeError):pass
        raise ProviderError(message,uncertain=mutating and response.status>=500)
    try:
        if len(raw)>2_000_000:raise ValueError()
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError()
        return value
    except (ValueError,UnicodeError):raise ProviderError('Resposta incompleta do provedor. Confira o envio antes de tentar novamente.',uncertain=mutating) from None


def get(path,key=None):
    connection=http.client.HTTPSConnection(HOST,timeout=30)
    try:
        connection.request('GET',path,headers={'Authorization':'Apikey '+(key or load_key()),'User-Agent':'AfiliadosStudio'})
        return response_json(connection.getresponse())
    except (OSError,http.client.HTTPException):raise ProviderError('Sem resposta do provedor. A conexão será conferida novamente.') from None
    finally:connection.close()


def profiles(key=None):
    value=get('/api/uploadposts/users',key)
    if value.get('success') is not True or not isinstance(value.get('profiles'),list):raise ValueError('O provedor não confirmou os perfis conectados.')
    return value['profiles']


def destination(rows,handle):
    matches=[]
    for row in rows:
        account=(row.get('social_accounts') or {}).get('tiktok')
        if not isinstance(account,dict) or account.get('reauth_required'):continue
        if str(account.get('handle','')).lstrip('@').lower()!=handle.lower():continue
        if not account.get('username') or not row.get('username'):continue
        matches.append({'profile':str(row['username']),'account_id':str(account['username']),
                        'handle':str(account['handle']).lstrip('@'),'capabilities':account.get('capabilities',[])})
    if len(matches)!=1:raise ValueError('Não foi encontrado um único TikTok com esse @ e identificação confirmada. Reconecte o perfil no Upload-Post.')
    return matches[0]


def upload(path,caption,binding,request_id,commercial):
    if core.TESTER:raise ValueError('O modo tester bloqueia publicações externas.')
    if not path.is_file() or not 0<path.stat().st_size<=128*1024**2:raise ValueError('Vídeo ausente ou acima de 128 MB.')
    if not caption.strip() or len(caption)>2200:raise ValueError('A legenda deve ter até 2.200 caracteres.')
    fields={'user':binding['profile'],'platform[]':'tiktok','title':caption,'tiktok_title':caption,
        'post_mode':'DIRECT_POST','async_upload':'true','request_id':request_id,'external_id':request_id,
        'brand_content_toggle':str(bool(commercial)).lower(),'brand_organic_toggle':'false','is_aigc':'true',
        'disable_inbox_fallback':'true','disable_duet':'true','disable_stitch':'true'}
    if 'video_privacy' in binding.get('capabilities',[]):fields['privacy_level']='PUBLIC_TO_EVERYONE'
    boundary='Afiliados'+uuid4().hex
    head=b''.join((f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n').encode('utf-8') for k,v in fields.items())
    head+=(f'--{boundary}\r\nContent-Disposition: form-data; name="video"; filename="episode.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode()
    tail=f'\r\n--{boundary}--\r\n'.encode();key=load_key()
    connection=http.client.HTTPSConnection(HOST,timeout=120)
    try:
        connection.putrequest('POST','/api/upload')
        for name,value in {'Authorization':'Apikey '+key,'Content-Type':'multipart/form-data; boundary='+boundary,
            'Content-Length':str(len(head)+path.stat().st_size+len(tail)),'Idempotency-Key':request_id,'X-Request-Id':request_id}.items():connection.putheader(name,value)
        connection.endheaders();connection.send(head)
        with path.open('rb') as stream:
            while chunk:=stream.read(256*1024):connection.send(chunk)
        connection.send(tail)
        return response_json(connection.getresponse(),mutating=True)
    except (OSError,http.client.HTTPException):raise ProviderError('Envio sem resposta confirmada. O sistema consultará o mesmo pedido, sem reenviar o vídeo.',uncertain=True) from None
    finally:connection.close()


def status(request_id):return get('/api/uploadposts/status?'+urlencode({'request_id':request_id}))
