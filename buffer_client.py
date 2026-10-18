"""Buffer personal API connection. Secrets stay encrypted with Windows DPAPI.

Affiliate videos are sent as drafts: current documented TikTok metadata cannot
set native commercial disclosure. Creating a draft never means publication.
"""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import core

ENDPOINT = 'https://api.buffer.com'
NOTICE = 'A API do Buffer ainda não documenta a identificação nativa de conteúdo comercial do TikTok. Vídeos de afiliados são enviados como rascunho para conclusão da publicidade e publicação.'


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]


def crypt(value, decrypt=False):
    if os.name != 'nt':
        raise ValueError('O armazenamento protegido da chave está disponível no Windows.')
    buffer = ctypes.create_string_buffer(value)
    source = Blob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    if decrypt:
        ok = ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    else:
        ok = ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), 'Afiliados Studio', None, None, None, 1, ctypes.byref(target))
    if not ok:
        raise ValueError('O Windows não conseguiu proteger ou ler a chave. Reconecte o Buffer neste usuário.')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        ctypes.windll.kernel32.LocalFree(target.data)


def key_path():
    return core.DATA / 'buffer.key'


def load_key():
    if not key_path().exists():
        raise ValueError('Conecte uma chave pessoal do Buffer em Modo automático.')
    return crypt(base64.b64decode(key_path().read_bytes()), decrypt=True).decode()


def store_key(key):
    encrypted = base64.b64encode(crypt(key.encode()))
    temporary = key_path().with_suffix('.tmp')
    temporary.write_bytes(encrypted)
    temporary.replace(key_path())


def query(document, variables=None, key=None):
    secret = key or load_key()
    payload = json.dumps({'query': document, 'variables': variables or {}}).encode()
    request = Request(ENDPOINT, data=payload, headers={'Authorization': 'Bearer ' + secret, 'Content-Type': 'application/json', 'User-Agent':'AfiliadosStudio/2.0'})
    try:
        with urlopen(request, timeout=25) as response:
            result = json.loads(response.read(2_000_000))
    except HTTPError as error:
        if error.code in (401,403):
            raise ValueError('O Buffer recusou a chave ou a permissão. Verifique a chave pessoal e a conta.') from None
        if error.code == 429:
            raise ValueError('Limite da API do Buffer atingido. O sistema aguardará para consultar novamente.') from None
        raise ValueError('O Buffer não respondeu à operação. Confira o painel antes de reenviar.') from None
    except (OSError, ValueError):
        raise ValueError('Sem resposta confirmada do Buffer. Confira o painel antes de reenviar para evitar duplicação.') from None
    if result.get('errors'):
        message = '; '.join(str(e.get('message','Operação recusada')) for e in result['errors'])
        raise ValueError(message.replace(secret,'[chave protegida]')[:700])
    return result.get('data') or {}


def connect(key):
    key = core.clean(key, 3000, True)
    account = query('query { account { organizations { id name } } }', key=key).get('account',{})
    channels = []
    for organization in account.get('organizations',[]):
        oid = organization['id']
        doc = 'query($org: OrganizationId!) { channels(input:{organizationId:$org}) { id name service displayName isDisconnected isLocked isQueuePaused } }'
        result = query(doc, {'org':oid}, key=key)
        for channel in result.get('channels',[]):
            if channel.get('service') == 'tiktok':
                channels.append({**channel,'organization_id':oid,'organization_name':organization.get('name','')})
    if not channels:
        raise ValueError('Nenhum TikTok encontrado. Conecte seu TikTok no Buffer e tente novamente.')
    store_key(key)
    return channels


def create_draft(channel_id, caption, video_url, generated_voice=False):
    if core.TESTER:raise ValueError('Envios ao Buffer estão bloqueados no modo tester.')
    core.public_url(video_url)
    if not video_url.startswith('https://'):
        raise ValueError('O arquivo precisa de um endereço HTTPS acessível ao Buffer.')
    document = '''mutation($input:CreatePostInput!) { createPost(input:$input) {
      ... on PostActionSuccess { post { id status schedulingType externalLink sentAt } }
      ... on MutationError { message }
    } }'''
    post_input = {'channelId':channel_id,'text':caption,'schedulingType':'automatic',
                  'mode':'addToQueue','saveToDraft':True,'needsApproval':False,
                  'assets':[{'video':{'url':video_url,'metadata':{'thumbnailOffset':1000}}}],
                  'metadata':{'tiktok':{'isAiGenerated':bool(generated_voice)}}}
    result = query(document, {'input':post_input}).get('createPost',{})
    if not result.get('post'):
        raise ValueError(str(result.get('message','O Buffer não confirmou a criação do rascunho.'))[:500])
    return result['post']


def get_post(post_id):
    return query('query($id:PostId!) { post(input:{id:$id}) { id channelId status schedulingType sentAt externalLink } }', {'id':post_id}).get('post',{})


def metrics(post_id):
    return query('query($id:PostId!) { post(input:{id:$id}) { id metricsUpdatedAt metrics { type value } } }',{'id':post_id}).get('post',{})
