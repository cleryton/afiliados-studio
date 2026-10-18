"""Run with python app.py. Binds only to the local computer."""
import argparse
import ctypes
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs
import core
import autopilot
import catalog
import youtube_client
import diagnostics
import support
from version import VERSION

TOKEN = secrets.token_urlsafe(32)
STOP = threading.Event()
MAX_BODY = 12_000_000


def worker():
    next_auto=0
    while not STOP.is_set():
        try:
            if os.name=='nt':
                # The request belongs to this worker; it never edits the power plan.
                flags=0x80000001 if autopilot.settings()['enabled'] else 0x80000000
                ctypes.windll.kernel32.SetThreadExecutionState(flags)
            if time.monotonic()>=next_auto:
                next_auto=time.monotonic()+60
                try:
                    autopilot.cycle()
                except Exception as exc:
                    autopilot.event('attention',str(exc))
            with core.db() as c:
                c.execute("UPDATE jobs SET status='queued', updated_at=? WHERE status='scheduled' AND due_at<=?", (core.stamp(), core.stamp()))
                auto_enabled=autopilot.settings()['enabled']
                row = c.execute("SELECT jobs.* FROM jobs LEFT JOIN auto_jobs ON auto_jobs.job_id=jobs.id WHERE jobs.status='queued' AND (? OR auto_jobs.job_id IS NULL) AND (auto_jobs.retry_at IS NULL OR auto_jobs.retry_at<=?) ORDER BY jobs.created_at LIMIT 1",(int(auto_enabled),core.stamp())).fetchone()
                if row:
                    job = dict(row)
                    c.execute("UPDATE jobs SET status='rendering', updated_at=? WHERE id=?", (core.stamp(), job['id']))
                    product = dict(c.execute('SELECT * FROM products WHERE id=?', (job['product_id'],)).fetchone())
            if row:
                try:
                    from renderer import render
                    voiced, warning = render(job, product)
                    with core.db() as c:
                        c.execute("UPDATE jobs SET status='ready',voice=?,error=?,updated_at=? WHERE id=?", (int(voiced), warning, core.stamp(), job['id']))
                except Exception:
                    traceback.print_exc()
                    with core.db() as c:
                        c.execute("UPDATE jobs SET status='error',error=?,updated_at=? WHERE id=?", ('Não foi possível gerar o MP4. Confira as dependências, reduza o texto se necessário e tente novamente. Veja o terminal para detalhes.', core.stamp(), job['id']))
                    autopilot.render_failed(job['id'])
        except Exception:
            traceback.print_exc()
        STOP.wait(2)


def delivery_worker():
    import media_bridge
    while not STOP.is_set():
        try:
            if core.TESTER:
                STOP.wait(60);continue
            if youtube_client.settings()['enabled']:
                youtube_client.tick()
            else:
                autopilot.sync()
                autopilot.delivery_cycle(media_bridge.media_url)
        except Exception as exc:
            autopilot.put_settings({'status':str(exc)[:800]})
        STOP.wait(60)


def catalog_worker():
    while not STOP.is_set():
        try:catalog.tick()
        except Exception as error:catalog.put({'message':str(error)[:500]})
        STOP.wait(60)


def readiness():
    with core.db() as c:
        ids=[r[0] for r in c.execute('SELECT product_id FROM auto_products WHERE active=1 AND approved=1')]
    count=sum(catalog.eligible(pid) for pid in ids)
    yt=youtube_client.state()
    return {'products':count,'channel':yt['connected'],'ready':bool(count and yt['connected'])}


class Handler(BaseHTTPRequestHandler):
    server_version = 'AfiliadosLocal/'+VERSION

    def log_message(self,fmt,*args):
        # OAuth callback query strings contain a one-time authorization code.
        print(self.command+' '+urlparse(self.path).path,flush=True)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def security_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")

    def respond(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.security_headers()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {'error': 'Acesso permitido apenas pelo endereço local.'})
        path = unquote(urlparse(self.path).path)
        try:
            if path=='/oauth/youtube/callback':
                query=parse_qs(urlparse(self.path).query)
                try:
                    if query.get('error'):raise ValueError('Autorização cancelada no Google. Você pode conectar novamente.')
                    youtube_client.complete(query.get('state',[''])[0],query.get('code',[''])[0])
                    youtube_client.put({'last_error':''})
                except (ValueError,OSError) as error:
                    youtube_client.put({'last_error':str(error)[:500]})
                self.send_response(303);self.security_headers()
                self.send_header('Location','/#start');self.send_header('Content-Length','0');self.end_headers();return
            if path=='/favicon.ico':
                self.send_response(204)
                self.security_headers()
                self.end_headers()
                return
            if path == '/api/state':
                import content_engine
                return self.respond(200, {**core.state(), 'token': TOKEN, 'automation':autopilot.state(),'content':content_engine.state(),'catalog':catalog.state(),'youtube':youtube_client.state(),'setup':readiness(),'operation':diagnostics.state(),'mode':{'tester':core.TESTER,'version':VERSION,'publishing_allowed':not core.TESTER}})
            if path=='/api/support/report':
                return self.respond(200,support.report())
            if path == '/api/export':
                state = core.state()
                automation=autopilot.state()
                return self.respond(200, {'version': 2, 'exported_at': core.stamp(), 'products': state['products'], 'jobs': state['jobs'], 'expenses':automation['expenses'], 'auto_products':automation['products']})
            if path.startswith('/media/'):
                if not re.fullmatch(r'/media/(?:diagnostics/(?:video\.mp4|poster\.png)|[a-f0-9]{32}\.jpg|[a-f0-9]{32}/(?:video\.mp4|scene-[0-6]\.png|legenda\.txt|legendas\.srt|conteudo\.json))', path):
                    return self.respond(404, {'error': 'Arquivo não encontrado.'})
                file = core.DATA / path.lstrip('/')
            else:
                if path=='/manual-tester.md':
                    return self.send_file(core.ROOT/'docs'/'MANUAL_TESTER.md')
                allowed = {'/': 'index.html', '/app.js': 'app.js', '/setup.js':'setup.js', '/automation.js':'automation.js', '/style.css': 'style.css', '/automation.css':'automation.css'}
                if path not in allowed:
                    return self.respond(404, {'error': 'Página não encontrada.'})
                file = core.ROOT / 'web' / allowed[path]
            if not file.is_file():
                return self.respond(404, {'error': 'Arquivo ainda não disponível.'})
            self.send_file(file)
        except (BrokenPipeError, ConnectionResetError,ConnectionAbortedError):
            pass
        except Exception:
            traceback.print_exc()
            self.respond(500, {'error': 'Não foi possível carregar os dados locais.'})

    def send_file(self, file):
        size = file.stat().st_size
        start, end, code = 0, size - 1, 200
        header = self.headers.get('Range', '')
        if header and file.suffix == '.mp4':
            match = re.fullmatch(r'bytes=(\d+)-(\d*)', header)
            if not match:
                return self.respond(416, {'error': 'Intervalo inválido.'})
            start = int(match[1])
            end = min(int(match[2]) if match[2] else end, end)
            if start > end:
                return self.respond(416, {'error': 'Intervalo inválido.'})
            code = 206
        self.send_response(code)
        self.security_headers()
        mime = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        if code == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        with file.open('rb') as handle:
            handle.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_POST(self):
        if not self.valid_host():
            return self.reject_post(403, 'Endereço local inválido.')
        origin = self.headers.get('Origin')
        expected_origins = (f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}')
        if origin and origin not in expected_origins:
            return self.reject_post(403, 'Origem não autorizada.')
        if not secrets.compare_digest(self.headers.get('X-Studio-Token', ''), TOKEN):
            return self.reject_post(403, 'Atualize a página para continuar.')
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length <= 0 or length > MAX_BODY:
                return self.respond(413, {'error': 'Arquivo ou dados excedem o tamanho permitido.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(415, {'error': 'Use JSON para enviar os dados.'})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Dados inválidos.')
            path = urlparse(self.path).path
            external={'/api/setup/start','/api/youtube/credentials','/api/youtube/connect','/api/youtube/verify','/api/youtube/settings','/api/automation/connect','/api/automation/install'}
            if core.TESTER and path in external:
                raise ValueError('O modo tester bloqueia contas e envios externos. Use a demonstração local; a publicação real exige iniciar.bat.')
            if path=='/api/tester/demo':
                return self.respond(201,support.create_demo())
            if path=='/api/diagnostics/test':
                return self.respond(202,diagnostics.start_probe())
            if path=='/api/youtube/verify':
                return self.respond(200,youtube_client.verify_channel())
            retry_match=re.fullmatch(r'/api/diagnostics/retry/([a-f0-9]{32})',path)
            if retry_match:
                diagnostics.retry_render(retry_match[1]);return self.respond(200,{'ok':True})
            if path=='/api/catalog/settings':
                catalog.configure(payload);return self.respond(200,{'ok':True})
            if path=='/api/catalog/import':
                return self.respond(200,catalog.ingest(payload.get('document'),payload.get('authorized') is True))
            if path=='/api/catalog/sync':
                catalog.put({'next_check':None});return self.respond(200,{'ok':True})
            if path=='/api/youtube/credentials':
                youtube_client.credentials(payload.get('document'));return self.respond(200,{'ok':True})
            if path=='/api/youtube/connect':
                return self.respond(200,{'url':youtube_client.begin(self.server.server_port)})
            if path=='/api/youtube/disconnect':
                youtube_client.disconnect();return self.respond(200,{'ok':True})
            if path=='/api/youtube/settings':
                youtube_client.configure(payload);return self.respond(200,{'ok':True})
            yt_match=re.fullmatch(r'/api/youtube/reconcile/([a-f0-9]{32})',path)
            if yt_match:
                youtube_client.reconcile(yt_match[1],payload.get('video_id'));return self.respond(200,{'ok':True})
            if path=='/api/setup/start':
                if not readiness()['ready']:raise ValueError('Autorize pelo menos um produto e conecte seu canal antes de iniciar.')
                diagnostics.require_runtime()
                youtube_client.verify_channel()
                import content_engine
                content_engine.configure({**content_engine.settings(),'format':'landscape'})
                youtube_client.configure({'enabled':True,'visibility':'public'})
                with core.db() as c:custom=c.execute("SELECT 1 FROM automation_settings WHERE key='hours'").fetchone()
                routine={'enabled':True,'send_drafts':False}
                if not custom:routine.update(hours=[18],daily_limit=1,cooldown_days=7,timing_mode='history')
                autopilot.configure(routine)
                return self.respond(200,{'ok':True})
            if path=='/api/setup/pause':
                autopilot.configure({'enabled':False,'send_drafts':False})
                youtube_client.configure({'enabled':False})
                return self.respond(200,{'ok':True})
            if path=='/api/content/settings':
                import content_engine
                content_engine.configure(payload)
                return self.respond(200,{'ok':True})
            if path=='/api/content/check':
                import content_engine
                return self.respond(200,content_engine.availability(force=True))
            if path == '/api/automation/settings':
                autopilot.configure(payload)
                return self.respond(200,{'ok':True})
            if path == '/api/automation/connect':
                import buffer_client
                channels=buffer_client.connect(payload.get('key'))
                autopilot.put_settings({'channels':channels,'buffer_checked_at':core.stamp()})
                return self.respond(200,{'channels':channels})
            if path == '/api/automation/disconnect':
                import buffer_client
                import media_bridge
                autopilot.put_settings({'send_drafts':False,'channel_id':'','channels':[],'buffer_checked_at':None})
                buffer_client.key_path().unlink(missing_ok=True)
                media_bridge.stop()
                return self.respond(200,{'ok':True})
            if path == '/api/automation/install':
                import media_bridge
                media_bridge.install()
                return self.respond(200,{'ok':True})
            if path == '/api/automation/expense':
                autopilot.expense(payload)
                return self.respond(200,{'ok':True})
            auto_match=re.fullmatch(r'/api/automation/products/([a-f0-9]{32})',path)
            if auto_match:
                autopilot.approve_product(auto_match[1],payload)
                return self.respond(200,{'ok':True})
            reconcile_match=re.fullmatch(r'/api/automation/reconcile/([a-f0-9]{32})',path)
            if reconcile_match:
                autopilot.reconcile(reconcile_match[1],payload.get('post_id'))
                return self.respond(200,{'ok':True})
            if path == '/api/import':
                return self.respond(200, core.import_product(payload.get('url')))
            if path == '/api/products':
                return self.respond(201, {'id': core.save_product(payload)})
            if path == '/api/jobs':
                return self.respond(201, {'id': core.create_job(payload)})
            match = re.fullmatch(r'/api/jobs/([a-f0-9]{32})(/results|/cancel)?', path)
            if match:
                jid = match[1]
                if match[2] == '/results':
                    core.record_results(jid, payload)
                elif match[2] == '/cancel':
                    with core.db() as c:
                        changed = c.execute("UPDATE jobs SET status='draft',updated_at=? WHERE id=? AND status IN ('scheduled','queued')", (core.stamp(), jid)).rowcount
                        if not changed:
                            raise ValueError('Este vídeo já iniciou o processamento ou não está agendado.')
                else:
                    core.edit_job(jid, payload)
                return self.respond(200, {'ok': True})
            self.respond(404, {'error': 'Operação não encontrada.'})
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            pass
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(400, {'error': str(exc) or 'Dados inválidos.'})
        except Exception:
            traceback.print_exc()
            self.respond(500, {'error': 'A operação falhou. Confira o terminal e tente novamente.'})


    def reject_post(self,status,message):
        # Drain bounded request bodies before closing to avoid Windows TCP resets
        # hiding the error response from the browser. Never parse rejected data.
        previous=self.connection.gettimeout()
        try:
            length=int(self.headers.get('Content-Length','0'))
            if 0<length<=MAX_BODY:
                self.connection.settimeout(2)
                self.rfile.read(length)
        except (ValueError,OSError):pass
        finally:self.connection.settimeout(previous)
        return self.respond(status,{'error':message})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int)
    parser.add_argument('--tester', action='store_true',help='Usa data-tester e bloqueia publicação externa.')
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.tester:
        core.TESTER=True
        core.DATA=core.ROOT/'data-tester'
    args.port=args.port or (8766 if core.TESTER else 8765)
    try:
        import PIL
        import imageio_ffmpeg
    except ImportError:
        print('Instale as dependências gratuitas: python -m pip install -r requirements.txt')
        raise SystemExit(1)
    core.init()
    autopilot.init()
    catalog.init()
    youtube_client.init()
    diagnostics.init()
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        print(f'A porta {args.port} está ocupada. Use python app.py --port 8766')
        raise SystemExit(1)
    threading.Thread(target=worker, daemon=True).start()
    threading.Thread(target=delivery_worker, daemon=True).start()
    threading.Thread(target=catalog_worker, daemon=True).start()
    url = f'http://127.0.0.1:{args.port}'
    print(f'Afiliados Studio {VERSION} | '+('MODO TESTER · PUBLICAÇÃO BLOQUEADA | ' if core.TESTER else '')+f'{url} | Ctrl+C para encerrar', flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STOP.set()
        import media_bridge
        media_bridge.stop()
        server.server_close()


if __name__ == '__main__':
    main()
