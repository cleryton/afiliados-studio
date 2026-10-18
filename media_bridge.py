"""Only signed MP4 URLs are exposed. The private application is never tunneled."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
import shutil
import subprocess
import threading
import time
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
import core

PROCESS = None
SERVER = None
PUBLIC_URL = ''
LOCK = threading.Lock()


def executable():
    return core.DATA / 'tools' / 'cloudflared.exe'


def installed():
    return executable().is_file() or bool(shutil.which('cloudflared'))


def install():
    if installed():
        return
    request=Request('https://api.github.com/repos/cloudflare/cloudflared/releases/latest',headers={'User-Agent':'AfiliadosStudio'})
    with urlopen(request,timeout=30) as response:
        release=json.load(response)
    asset=next((a for a in release.get('assets',[]) if a['name']=='cloudflared-windows-amd64.exe'),None)
    if not asset or not (asset.get('digest') or '').startswith('sha256:'):
        raise ValueError('Não foi possível verificar a versão oficial. Instale cloudflared pelo site da Cloudflare e tente novamente.')
    destination=executable()
    destination.parent.mkdir(exist_ok=True)
    temporary=destination.with_suffix('.download')
    digest=hashlib.sha256()
    started=time.monotonic()
    try:
        with urlopen(asset['browser_download_url'],timeout=15) as response,temporary.open('wb') as output:
            total=0
            while chunk:=response.read(65536):
                if time.monotonic()-started>90:
                    raise ValueError('O download demorou demais. Tente novamente ou instale cloudflared pelo site oficial.')
                total+=len(chunk)
                if total>150_000_000:
                    raise ValueError('O download excedeu o tamanho esperado.')
                digest.update(chunk)
                output.write(chunk)
        if not hmac.compare_digest(digest.hexdigest(),asset['digest'].split(':')[1]):
            raise ValueError('A verificação do download falhou. O executável não será utilizado.')
        temporary.replace(destination)
    except OSError:
        raise ValueError('Não foi possível baixar cloudflared. Confira sua conexão ou instale pelo site oficial da Cloudflare.') from None
    finally:
        temporary.unlink(missing_ok=True)


def signing_key():
    file=core.DATA/'media-signing.key'
    if not file.exists():
        file.write_bytes(secrets.token_bytes(32))
    return file.read_bytes()


def signature(jid,expires):
    return hmac.new(signing_key(),f'{jid}:{expires}'.encode(),hashlib.sha256).hexdigest()


def validate(path):
    parsed=urlparse(path)
    match=re.fullmatch(r'/video/([a-f0-9]{32})\.mp4',parsed.path)
    if not match:
        return None
    query=parse_qs(parsed.query)
    try:
        expires=int(query.get('expires',['0'])[0])
        supplied=query.get('signature',[''])[0]
    except (ValueError,TypeError):
        return None
    if not time.time()<expires<=time.time()+172800 or not hmac.compare_digest(supplied,signature(match[1],expires)):
        return None
    file=core.DATA/'media'/match[1]/'video.mp4'
    return file if file.is_file() else None


class MediaHandler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # Never log signed URLs.

    def do_GET(self):
        file=validate(self.path)
        if not file:
            self.send_error(404)
            return
        size=file.stat().st_size
        start,end,status=0,size-1,200
        if self.headers.get('Range'):
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
            if not match:
                self.send_error(416)
                return
            start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
            if start>end:
                self.send_error(416)
                return
            status=206
        self.send_response(status)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Cache-Control','private, no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Accept-Ranges','bytes')
        if status==206:
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with file.open('rb') as source:
                source.seek(start)
                remaining=end-start+1
                while remaining:
                    chunk=source.read(min(remaining,65536))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):
            pass

    def do_HEAD(self):
        file=validate(self.path)
        if not file:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Content-Length',str(file.stat().st_size))
        self.end_headers()


def start():
    global SERVER,PROCESS,PUBLIC_URL
    with LOCK:
        if PROCESS and PROCESS.poll() is None and PUBLIC_URL:
            return PUBLIC_URL
        if not installed():
            raise ValueError('Instale a ponte gratuita de mídia em Modo automático para enviar MP4s ao Buffer.')
        if SERVER is None:
            SERVER=ThreadingHTTPServer(('127.0.0.1',0),MediaHandler)
            threading.Thread(target=SERVER.serve_forever,daemon=True).start()
        log=core.DATA/'tunnel.log'
        public=''
        command=str(executable()) if executable().is_file() else shutil.which('cloudflared')
        with log.open('w',encoding='utf-8') as output:
            PROCESS=subprocess.Popen([command,'tunnel','--no-autoupdate','--url',f'http://127.0.0.1:{SERVER.server_port}'],stdout=output,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for _ in range(100):
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',log.read_text(encoding='utf-8',errors='replace'))
            if match:
                public=match[0];break
            if PROCESS.poll() is not None:break
            time.sleep(.2)
        if not public:
            if PROCESS.poll() is None:PROCESS.terminate()
            raise ValueError('Não foi possível abrir a ponte de mídia. Confira a internet; seus vídeos locais foram mantidos.')
        PUBLIC_URL=public
        return public


def media_url(jid):
    base=start()
    expires=int(time.time()+86400)
    return f'{base}/video/{jid}.mp4?expires={expires}&signature={signature(jid,expires)}'


def stop():
    global PROCESS,SERVER,PUBLIC_URL
    if PROCESS and PROCESS.poll() is None:
        PROCESS.terminate()
    PROCESS=None;PUBLIC_URL=''
    if SERVER:
        SERVER.shutdown();SERVER.server_close();SERVER=None
