"""Explicit per-video requests for public delivery without waiting for a slot."""
from datetime import datetime,timedelta
import core


def init():
    with core.db() as c:c.execute('''CREATE TABLE IF NOT EXISTS immediate_publications(
        job_id TEXT PRIMARY KEY REFERENCES jobs(id),channel_id TEXT NOT NULL,requested_at TEXT NOT NULL,content_hash TEXT NOT NULL)''')


def get(jid):
    with core.db() as c:
        item=c.execute('SELECT * FROM immediate_publications WHERE job_id=?',(jid,)).fetchone()
    return dict(item) if item else None


def expired(request):return core.now()>datetime.fromisoformat(request['requested_at'])+timedelta(minutes=30)


def request_now(jid):
    import youtube_client as yt
    with yt._delivery_lock:return _request_now(jid)


def _request_now(jid):
    import autopilot,catalog,campaigns,quality,youtube_client as yt
    if core.TESTER:raise ValueError('O modo tester bloqueia publicações externas.')
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        config=yt.settings()
        if not config['enabled'] or config['visibility']!='public' or not autopilot.settings()['enabled']:
            raise ValueError('Inicie a operação pública antes de pedir a publicação imediata.')
        if not config['channel_id'] or not yt.secret_path('tokens').is_file():raise ValueError('Conecte seu canal do YouTube.')
        job=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        if not job or job['status']!='ready':raise ValueError('Aguarde o MP4 ficar pronto e verificado.')
        auto=c.execute('SELECT * FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
        rule=c.execute('SELECT * FROM auto_products WHERE product_id=?',(job['product_id'],)).fetchone()
        brief=campaigns.for_product(job['product_id'])
        if not auto or auto['delivery']!='local' or auto['buffer_id']:raise ValueError('Use um vídeo da rotina local sem tentativa de envio pelo Buffer.')
        if not job['rights'] or not rule or not rule['active'] or not rule['approved'] or not catalog.eligible(job['product_id']) or brief and not brief['active']:
            raise ValueError('O produto e os materiais precisam estar autorizados e atuais.')
        if not quality.inspect(jid,verify_media=True)['allowed']:raise ValueError('Resolva as verificações e a revisão do vídeo antes de publicar.')
        previous=c.execute('SELECT * FROM immediate_publications WHERE job_id=?',(jid,)).fetchone()
        remote=c.execute('SELECT * FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
        if previous:
            current=(previous['channel_id']==config['channel_id'] and previous['content_hash']==quality.content_hash(dict(job)) and not expired(previous))
            if current:return {'requested':True,'already_requested':True}
            untouched=(not remote or remote['stage'] in ('failed','held_local') and not remote['video_id']) and not yt.secret_path('session-'+jid).exists()
            if not untouched:raise ValueError('Confira e vincule o vídeo privado existente no YouTube Studio antes de renovar o pedido.')
            c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(jid,))
            c.execute('DELETE FROM immediate_publications WHERE job_id=?',(jid,))
            remote=None
        if remote and remote['stage'] not in ('uploading','processing'):
            raise ValueError('Este vídeo já tem uma entrega definida ou exige conferência no YouTube Studio.')
        c.execute('INSERT INTO immediate_publications VALUES (?,?,?,?)',(jid,config['channel_id'],core.stamp(),quality.content_hash(dict(job))))
    autopilot.event('youtube','Publicação imediata solicitada para este vídeo. Aguardando processamento e confirmação pública.',jid)
    return {'requested':True,'already_requested':False}


def state():
    with core.db() as c:rows=c.execute('SELECT job_id,requested_at FROM immediate_publications').fetchall()
    return [dict(row) for row in rows]
