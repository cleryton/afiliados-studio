"""Observable content checks and render attestations; no subjective quality score."""
import hashlib
import json
import re
import subprocess
import core
import campaigns


def init():
    with core.db() as c:c.executescript('''
    CREATE TABLE IF NOT EXISTS media_validations(job_id TEXT PRIMARY KEY REFERENCES jobs(id),sha256 TEXT NOT NULL,size INTEGER NOT NULL,mtime_ns INTEGER NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,duration REAL NOT NULL,content_hash TEXT NOT NULL,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS editorial_reviews(job_id TEXT PRIMARY KEY REFERENCES jobs(id),decision TEXT NOT NULL,fingerprint TEXT NOT NULL,note TEXT NOT NULL,reviewed_at TEXT NOT NULL);
    ''')


def content_hash(job):
    scenes=json.loads(job['scenes']) if isinstance(job['scenes'],str) else job['scenes']
    return hashlib.sha256(json.dumps({'scenes':scenes,'caption':job['caption']},ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(262144),b''):digest.update(block)
    return digest.hexdigest()


def validate_media(jid):
    import imageio_ffmpeg,os
    job=core.get_job(jid);folder=core.DATA/'media'/jid;file=folder/'video.mp4'
    if not file.is_file() or not 0<file.stat().st_size<=150_000_000:raise ValueError('Gere um MP4 válido de até 150 MB antes de verificar.')
    try:rendered=json.loads((folder/'conteudo.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):raise ValueError('Metadados da renderização ausentes. Gere o vídeo novamente.') from None
    try:matches=content_hash(rendered)==content_hash(job)
    except (KeyError,TypeError,ValueError):raise ValueError('Metadados incompletos. Gere o vídeo novamente.') from None
    if not matches:raise ValueError('O roteiro mudou depois da renderização. Gere o MP4 novamente.')
    try:result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(file),'-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except (OSError,subprocess.TimeoutExpired):raise ValueError('Não foi possível concluir a verificação do MP4. Confira as dependências e tente novamente.') from None
    dimensions=re.search(r'Video:.*?\b(\d{2,5})x(\d{2,5})\b',result.stderr)
    clock=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',result.stderr)
    if result.returncode or not dimensions or not clock:raise ValueError('O MP4 não passou na decodificação. Gere o vídeo novamente.')
    width,height=map(int,dimensions.groups());duration=int(clock[1])*3600+int(clock[2])*60+float(clock[3])
    expected=(1280,720) if rendered.get('format')=='landscape' else (720,1280)
    if (width,height)!=expected or not 0<duration<=181:raise ValueError('Formato ou duração do vídeo não correspondem ao roteiro.')
    durations=rendered.get('durations',[])
    if not isinstance(durations,list) or len(durations)!=len(json.loads(job['scenes'])) or any(type(d) not in (int,float) or not 0<d<=180 for d in durations) or abs(sum(durations)-duration)>.8:raise ValueError('A duração do MP4 não corresponde às cenas renderizadas. Gere novamente.')
    stat=file.stat()
    digest=file_hash(file)
    if file.stat().st_mtime_ns!=stat.st_mtime_ns or file.stat().st_size!=stat.st_size:raise ValueError('Arquivo alterado durante a verificação. Tente novamente.')
    with core.db() as c:c.execute('INSERT INTO media_validations VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET sha256=excluded.sha256,size=excluded.size,mtime_ns=excluded.mtime_ns,width=excluded.width,height=excluded.height,duration=excluded.duration,content_hash=excluded.content_hash,created_at=excluded.created_at',(jid,digest,stat.st_size,stat.st_mtime_ns,width,height,duration,content_hash(job),core.stamp()))
    return inspect(jid)


def inspect(jid,verify_media=False):
    import catalog,content_engine
    job=core.get_job(jid)
    with core.db() as c:
        product=dict(c.execute('SELECT * FROM products WHERE id=?',(job['product_id'],)).fetchone())
        row=c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()
        artifact=c.execute('SELECT * FROM media_validations WHERE job_id=?',(jid,)).fetchone()
        review=c.execute('SELECT * FROM editorial_reviews WHERE job_id=?',(jid,)).fetchone()
    meta=json.loads(row['payload']) if row else {};campaign=campaigns.for_product(product['id'])
    scenes=json.loads(job['scenes']);file=core.DATA/'media'/jid/'video.mp4'
    current_source=hashlib.sha256(product['description'].encode()).hexdigest()
    current_product=content_engine.product_fingerprint(product)
    saved_campaign=meta.get('campaign')
    campaign_current=(campaign or {}).get('revision')==(saved_campaign or {}).get('revision')
    media_ok=bool(artifact and file.is_file() and file.stat().st_size==artifact['size'] and file.stat().st_mtime_ns==artifact['mtime_ns'] and artifact['content_hash']==content_hash(job))
    if media_ok and verify_media:media_ok=file_hash(file)==artifact['sha256']
    checks=[
      {'label':'Roteiro','passed':4<=len(scenes)<=7 and all(isinstance(s,str) and s.strip() for s in scenes)},
      {'label':'Link de afiliado preservado','passed':product['url'] in job['caption']},
      {'label':'Identificação de publicidade','passed':'publicidade' in job['caption'].lower()},
      {'label':'Materiais autorizados','passed':bool(job['rights'])},
      {'label':'Dados atuais do produto','passed':meta.get('source_hash')==current_source and (not meta.get('product_hash') or meta['product_hash']==current_product) and product['name'] in job['caption'] and catalog.eligible(product['id'])},
      {'label':'Campanha atual e ativa','passed':campaign_current and (not campaign or bool(campaign['active']))},
      {'label':'MP4 verificado e correspondente ao roteiro','passed':media_ok}]
    fingerprint=hashlib.sha256(json.dumps({'content':content_hash(job),'product':current_product,'campaign':campaign,'media':artifact['sha256'] if artifact else None},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    decision=dict(review) if review and review['fingerprint']==fingerprint else None
    manual=bool(campaign and campaign['review_mode']=='manual')
    valid=all(c['passed'] for c in checks)
    approved=bool(decision and decision['decision']=='approved')
    rejected=bool(decision and decision['decision']=='rejected')
    allowed=valid and not rejected and (not manual or approved)
    status='ready' if allowed else 'changes' if rejected else 'blocked' if not valid else 'review'
    return {'allowed':allowed,'status':status,'checks':checks,'manual_required':manual,'decision':decision,'fingerprint':fingerprint,
            'campaign':campaign,'media':{'width':artifact['width'],'height':artifact['height'],'duration':artifact['duration'],'checked_at':artifact['created_at']} if artifact else None,
            'warnings':([] if job['voice'] else ['Vídeo sem narração.'])+([] if product['image'] else ['Composição com texto, sem foto de produto.'])}


def decide(jid,payload):
    if payload.get('decision') not in ('approved','rejected'):raise ValueError('Escolha aprovar ou solicitar ajustes.')
    note=core.clean(payload.get('note',''),500)
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if core.get_job(jid)['status']!='ready':raise ValueError('A revisão exige um MP4 pronto e ainda não publicado.')
        core.ensure_no_buffer_send(c,jid)
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone():
            remote=c.execute('SELECT stage,video_id FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
            if remote and (remote['video_id'] or remote['stage'] not in ('held_local','failed')):raise ValueError('Este vídeo possui envio externo. Gerencie a publicação pelo YouTube Studio.')
        result=inspect(jid,verify_media=True)
        if payload['decision']=='approved' and not all(item['passed'] for item in result['checks']):raise ValueError('Corrija as verificações pendentes antes de aprovar.')
        c.execute('INSERT INTO editorial_reviews VALUES (?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET decision=excluded.decision,fingerprint=excluded.fingerprint,note=excluded.note,reviewed_at=excluded.reviewed_at',(jid,payload['decision'],result['fingerprint'],note,core.stamp()))
    return inspect(jid)
