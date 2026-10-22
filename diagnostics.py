"""Local, bounded production checks. Never publishes or fabricates offers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import wave
import core

_lock=threading.Lock()
_thread=None
MIN_FREE=512*1024*1024


def report_path():return core.DATA/'diagnostic-report.json'


def report():
    try:
        value=json.loads(report_path().read_text(encoding='utf-8'))
        if isinstance(value,dict) and value.get('status') in ('idle','running','passed','warning','error') and isinstance(value.get('message'),str):return value
    except (OSError,ValueError):pass
    return {'status':'idle','message':'Faça um teste local para conferir vídeo e narração.','video_url':None}


def write_report(root,value):
    path=root/'diagnostic-report.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8');temporary.replace(path)


def init():
    previous=report()
    if previous['status']=='running':write_report(core.DATA,{'status':'error','message':'O teste anterior foi interrompido. Você pode executá-lo novamente.','video_url':None})


def runtime():
    try:
        import PIL
        import imageio_ffmpeg
        executable=Path(imageio_ffmpeg.get_ffmpeg_exe())
        renderer=executable.is_file()
    except (ImportError,OSError,RuntimeError):renderer=False
    free=shutil.disk_usage(core.DATA).free
    return {'renderer':renderer,'free_mb':free//(1024*1024),'disk_ok':free>=MIN_FREE}


def require_runtime():
    value=runtime()
    if not value['renderer']:raise ValueError('Instale as dependências de vídeo conforme o README.')
    if not value['disk_ok']:raise ValueError('Libere pelo menos 512 MB no disco antes de gerar vídeos.')


def run_probe(root):
    """Use the same local font, speech script and codecs as the product renderer."""
    directory=root/'media'/'diagnostics'
    try:
        directory.mkdir(parents=True,exist_ok=True)
        from PIL import Image,ImageDraw
        import renderer,imageio_ffmpeg
        canvas=Image.new('RGB',(1280,720),'#142725');draw=ImageDraw.Draw(canvas)
        draw.text((70,75),'TESTE LOCAL · NENHUM ENVIO PARA A INTERNET',font=renderer.font(25,True),fill='#cfe9a9')
        renderer.text_block(draw,'Seu estúdio está criando vídeo e narração neste computador.',215,350,maximum=48)
        canvas.save(directory/'poster.png')
        source=directory/'speech.json';audio=directory/'speech.wav'
        source.write_text(json.dumps({'text':'Teste do estúdio. Este vídeo foi criado no seu computador, sem publicar na internet.'},ensure_ascii=False),encoding='utf-8')
        voiced=False;duration=6
        try:
            subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(core.ROOT/'speech.ps1'),str(source),str(audio)],check=True,capture_output=True,timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            with wave.open(str(audio)) as stream:duration=stream.getnframes()/stream.getframerate()+.6
            if not 0<duration<=30:raise ValueError('Duração de teste inválida.')
            voiced=True
        except (OSError,subprocess.SubprocessError,wave.Error,ValueError):duration=6
        executable=imageio_ffmpeg.get_ffmpeg_exe()
        command=[executable,'-y','-hide_banner','-loglevel','error','-loop','1','-framerate','24','-i',str(directory/'poster.png')]
        command+=['-i',str(audio)] if voiced else ['-f','lavfi','-i','anullsrc=r=44100:cl=mono']
        temporary=directory/'building.mp4'
        command+=['-t',str(max(6,duration)),'-vf','fade=t=in:d=0.18','-c:v','libx264','-preset','ultrafast','-crf','25','-pix_fmt','yuv420p','-c:a','aac','-ar','44100','-ac','1','-af','apad','-movflags','+faststart',str(temporary)]
        subprocess.run(command,check=True,capture_output=True,timeout=120,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        subprocess.run([executable,'-v','error','-i',str(temporary),'-f','null','-'],check=True,capture_output=True,timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        temporary.replace(directory/'video.mp4')
        write_report(root,{'status':'passed' if voiced else 'warning','message':'Vídeo e narração criados e arquivo validado.' if voiced else 'Vídeo validado, mas sem voz pt-BR. Instale uma voz portuguesa nas configurações de fala do Windows.',
                          'video_url':'/media/diagnostics/video.mp4','voice':voiced,'checked_at':core.stamp(),'bytes':(directory/'video.mp4').stat().st_size})
    except Exception:
        write_report(root,{'status':'error','message':'O teste local falhou. Confira espaço livre e as dependências de vídeo indicadas no README.','video_url':None,'checked_at':core.stamp()})
    finally:
        for name in ('speech.json','speech.wav','building.mp4'):(directory/name).unlink(missing_ok=True)


def start_probe():
    global _thread
    with _lock:
        if _thread and _thread.is_alive():return {'status':'running'}
        require_runtime()
        with core.db() as c:
            if c.execute("SELECT 1 FROM jobs WHERE status='rendering'").fetchone():raise ValueError('Aguarde o vídeo em produção terminar antes de testar.')
        write_report(core.DATA,{'status':'running','message':'Testando imagem, voz, codificação e reprodução do arquivo…','video_url':None,'started_at':core.stamp()})
        _thread=threading.Thread(target=run_probe,args=(core.DATA,),daemon=True);_thread.start()
        return {'status':'running'}


def retry_render(jid):
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        job=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        if not job or job['status']!='error' or not job['rights']:raise ValueError('A retomada exige um vídeo com erro de geração e materiais autorizados.')
        remote=c.execute('SELECT stage,video_id FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
        if remote:raise ValueError('Este vídeo possui registro de envio externo. Confira o YouTube Studio antes de continuar.')
        auto=c.execute('SELECT * FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
        if auto:
            import autopilot,catalog
            if not autopilot.settings()['enabled']:raise ValueError('Ative a produção automática antes de retomar este vídeo da rotina.')
            authorization=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(job['product_id'],)).fetchone()
            if not authorization or not authorization['active'] or not authorization['approved'] or not catalog.eligible(job['product_id']):raise ValueError('Ative e atualize o produto antes de retomar a geração.')
            if auto['delivery']!='local':raise ValueError('O vídeo já possui tentativa de envio. Confira o destino antes de gerar novamente.')
            c.execute('UPDATE auto_jobs SET render_failures=0,retry_at=NULL WHERE job_id=?',(jid,))
        c.execute("UPDATE jobs SET status='queued',error='',updated_at=? WHERE id=?",(core.stamp(),jid))


def state():
    import autopilot,catalog,youtube_client,production
    resources=runtime();config=autopilot.settings();channel=youtube_client.state();test=report()
    options=autopilot.candidates(config,core.now())
    with core.db() as c:
        active=[r[0] for r in c.execute('SELECT product_id FROM auto_products WHERE active=1 AND approved=1')]
        jobs=[dict(r) for r in c.execute('SELECT jobs.id,products.name,jobs.status,jobs.error,jobs.due_at,jobs.results_recorded_at FROM jobs JOIN products ON products.id=jobs.product_id')]
        product_count=c.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    fresh=sum(catalog.eligible(pid) for pid in active)
    checks=[
        {'label':'Geração de vídeo','status':'ok' if resources['renderer'] else 'error','detail':'Dependências locais disponíveis.' if resources['renderer'] else 'Instale as dependências indicadas no README.','href':'#automation'},
        {'label':'Espaço livre','status':'ok' if resources['disk_ok'] else 'error','detail':f"{resources['free_mb']} MB disponíveis; mínimo de 512 MB.",'href':'#start'},
        {'label':'Produtos autorizados','status':'ok' if fresh else 'pending','detail':f'{fresh} produtos ativos com fonte válida.' if fresh else 'Adicione seu link de afiliado e autorize o produto.','href':'#products'},
        {'label':'Canal YouTube','status':'ok' if channel['connected'] and channel['settings']['channel_verified'] else 'pending','detail':('Acesso confirmado em '+channel['settings']['last_verified_at']) if channel['connected'] and channel['settings']['channel_verified'] else ('Autorização salva; verifique o acesso.' if channel['connected'] else 'Conecte seu canal na etapa 02.'),'href':'#start'},
        {'label':'Teste de vídeo e voz','status':'ok' if test['status']=='passed' else 'warning' if test['status']=='warning' else 'pending','detail':test['message'],'href':'#start'}]
    if core.TESTER:
        checks[2]={'label':'Cadastro local','status':'ok' if product_count else 'pending','detail':f'{product_count} cadastros no banco de testes.' if product_count else 'Crie um vídeo de demonstração para testar o fluxo.','href':'#start'}
        checks[3]={'label':'Proteção contra publicação','status':'ok','detail':'Envios externos bloqueados. Você não precisa conectar contas.','href':'#help'}
    errors=[j for j in jobs if j['status']=='error']
    next_product=None
    if options:
        p=options[0];next_product={'id':p['id'],'name':p['name'],'variant':p['variant']+1,'recorded_results':p['recorded_count'],
                                 'reason':'Primeiro conteúdo deste produto.' if not p['sample_count'] else 'Nova variação elegível; intervalo e limite por produto respeitados.'}
    return {'checks':checks,'test':test,'errors':errors,'next_product':next_product,'timing':autopilot.timing(config),'queue':production.queue(),
            'pending_results':sum(j['status']=='published' and not j['results_recorded_at'] for j in jobs),
            'runtime_ok':resources['renderer'] and resources['disk_ok']}
