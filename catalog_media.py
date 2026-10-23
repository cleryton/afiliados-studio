"""Bounded import of explicitly authorized catalog photos; never store remote code."""
import hashlib
import io
import shutil
import threading
import time
from datetime import datetime,timedelta
from urllib.request import Request,build_opener,ProxyHandler
from uuid import uuid4
from PIL import Image,ImageOps
import core

MAX_BYTES=5_000_000
_lock=threading.Lock()


def init():
    with core.db() as c:c.execute('''CREATE TABLE IF NOT EXISTS catalog_media (
        product_id TEXT PRIMARY KEY REFERENCES products(id), image_url TEXT NOT NULL,
        authorized INTEGER NOT NULL, source_mode TEXT NOT NULL, revision TEXT NOT NULL,
        managed_image TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0, next_check TEXT, last_attempt TEXT,
        last_success TEXT, message TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL DEFAULT '')''')


def revoke(c,pid):
    row=c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone()
    if not row:return
    if row['managed_image']:
        c.execute("UPDATE products SET image='' WHERE id=? AND image=?",(pid,row['managed_image']))
    c.execute("UPDATE catalog_media SET authorized=0,status='disabled',revision=?,next_check=NULL,message=? WHERE product_id=?",(uuid4().hex,'Importação de foto sem autorização ativa.',pid))


def grant(c,pid,url,allowed,source_mode):
    old=c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone()
    if not url:
        if old:revoke(c,pid)
        return
    allowed=bool(allowed)
    if old and old['image_url']==url and bool(old['authorized'])==allowed and old['source_mode']==source_mode:return
    if old:revoke(c,pid)
    c.execute('''INSERT INTO catalog_media(product_id,image_url,authorized,source_mode,revision,status)
        VALUES (?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET image_url=excluded.image_url,
        authorized=excluded.authorized,source_mode=excluded.source_mode,revision=excluded.revision,
        status=excluded.status,attempts=0,next_check=NULL,message='' ''',
        (pid,url,int(allowed),source_mode,uuid4().hex,'pending' if allowed else 'disabled'))


def fetch(url):
    core.public_url(url,resolve=True)
    opener=build_opener(ProxyHandler({}),core.PublicHTTPHandler(),core.PublicHTTPSHandler(),core.PublicRedirect())
    request=Request(url,headers={'Accept':'image/jpeg,image/png,image/webp','User-Agent':'AfiliadosStudioMedia/1.0'})
    with opener.open(request,timeout=12) as response:
        raw=bytearray();deadline=time.monotonic()+20
        while len(raw)<=MAX_BYTES:
            if time.monotonic()>deadline:raise ValueError('A leitura da foto excedeu o prazo. Tentaremos novamente.')
            chunk=response.read1(min(65536,MAX_BYTES+1-len(raw)))
            if not chunk:break
            raw.extend(chunk)
    if len(raw)>MAX_BYTES:raise ValueError('A foto ultrapassa 5 MB.')
    return normalize(bytes(raw))


def normalize(raw):
    if not raw or len(raw)>MAX_BYTES:raise ValueError('Use uma foto válida de até 5 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as original:
            if original.format not in ('JPEG','PNG','WEBP') or getattr(original,'is_animated',False):raise ValueError('Use foto estática JPG, PNG ou WebP.')
            if original.width*original.height>16_000_000 or min(original.size)<64:raise ValueError('Use foto entre 64 pixels por lado e 16 megapixels.')
            image=ImageOps.exif_transpose(original).convert('RGBA')
            image.thumbnail((1600,1600))
            clean=Image.new('RGB',image.size,'white');clean.paste(image,mask=image.getchannel('A'))
            output=io.BytesIO();clean.save(output,format='JPEG',quality=88)
            return output.getvalue()
    except (OSError,Image.DecompressionBombError):
        raise ValueError('A fonte não forneceu uma foto válida e decodificável.') from None


def eligible(c,row):
    import catalog,campaigns
    if not row['authorized'] or not catalog.eligible(row['product_id']):return False
    if row['source_mode']=='remote':
        config=catalog.settings()
        if not (config['enabled'] and config['authorized'] and config['download_images']):return False
    rule=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(row['product_id'],)).fetchone()
    brief=campaigns.for_product(row['product_id'])
    if brief and not brief['active']:return False
    return bool(rule and rule['active'] and rule['approved'])


def claim(pid):
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone()
        if not row or not eligible(c,row):return None
        product=c.execute('SELECT image FROM products WHERE id=?',(pid,)).fetchone()
        if product['image'] and product['image']!=row['managed_image']:
            c.execute("UPDATE catalog_media SET status='manual',message='Foto manual preservada.' WHERE product_id=?",(pid,))
            return None
        missing=row['status']=='ready' and row['managed_image'] and not (core.DATA/'media'/row['managed_image']).is_file()
        if not missing and row['next_check'] and datetime.fromisoformat(row['next_check'])>core.now():return None
        if shutil.disk_usage(core.DATA).free<512*1024*1024:
            c.execute("UPDATE catalog_media SET status='waiting',message='Importação de fotos aguardando 512 MB livres.',next_check=? WHERE product_id=?",((core.now()+timedelta(minutes=5)).isoformat(),pid))
            return None
        c.execute("UPDATE catalog_media SET status='downloading',last_attempt=?,next_check=?,message='Baixando e verificando foto autorizada.' WHERE product_id=?",(core.stamp(),(core.now()+timedelta(minutes=5)).isoformat(),pid))
        return dict(row),product['image']


def process(pid):
    if core.TESTER:return None
    claimed=claim(pid)
    if not claimed:return None
    row,previous_image=claimed;temporary=None
    try:
        raw=fetch(row['image_url'])
        digest=hashlib.sha256(raw).hexdigest()
        filename=hashlib.sha256((pid+digest).encode()).hexdigest()[:32]+'.jpg'
        target=core.DATA/'media'/filename
        temporary=core.DATA/'media'/('photo-'+uuid4().hex+'.tmp')
        temporary.write_bytes(raw)
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            latest=c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone()
            image=c.execute('SELECT image FROM products WHERE id=?',(pid,)).fetchone()[0]
            if not latest or latest['revision']!=row['revision']:return False
            if not eligible(c,latest):
                c.execute("UPDATE catalog_media SET status='paused',message='Foto aguardando produto, campanha ou fonte ativa.' WHERE product_id=?",(pid,))
                return False
            if image!=previous_image:
                c.execute("UPDATE catalog_media SET status='manual',message='Foto manual preservada.' WHERE product_id=?",(pid,))
                return False
            if target.exists():
                if target.stat().st_size>MAX_BYTES or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('A foto local requer conferência antes de substituir o arquivo.')
            else:temporary.replace(target)
            c.execute('UPDATE products SET image=? WHERE id=?',(filename,pid))
            c.execute("UPDATE catalog_media SET managed_image=?,status='ready',attempts=0,last_success=?,next_check=?,message='Foto autorizada verificada e disponível.',sha256=? WHERE product_id=?",(filename,core.stamp(),(core.now()+timedelta(hours=24)).isoformat(),digest,pid))
        return True
    except Exception as error:
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            latest=c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone()
            if latest and latest['revision']==row['revision'] and latest['authorized']:
                attempts=latest['attempts']+1;minutes=(5,15,60,240)[min(attempts-1,3)]
                detail=str(error) if isinstance(error,ValueError) else 'Não foi possível obter a foto da fonte.'
                c.execute("UPDATE catalog_media SET status='error',attempts=?,next_check=?,message=? WHERE product_id=?",(attempts,(core.now()+timedelta(minutes=minutes)).isoformat(),detail[:300]+' O vídeo pode continuar com texto ou a última foto válida.',pid))
        return False
    finally:
        if temporary:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass


def tick():
    if core.TESTER or not _lock.acquire(blocking=False):return
    try:
        with core.db() as c:rows=c.execute('SELECT product_id FROM catalog_media WHERE authorized=1 ORDER BY COALESCE(last_attempt,\'\'),product_id').fetchall()
        started=0
        for row in rows:
            # Two read attempts per cycle, including failures; do not drain 100 URLs at once.
            started+=process(row['product_id']) is not None
            if started>=2:break
    finally:_lock.release()


def state():
    with core.db() as c:
        rows=c.execute('SELECT product_id,status,message,last_success,next_check,authorized FROM catalog_media').fetchall()
    return [dict(row) for row in rows]
