"""Claim local work atomically and recover interrupted, authorized renders only."""
import json
from datetime import datetime
import core
import autopilot
import campaigns
import catalog
import content_engine


def block_reason(c, job, claimed_buffer=False):
    if not job['rights']:
        return ('rights', 'Autorize os materiais antes de gerar este vídeo.')
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone():
        if c.execute('SELECT 1 FROM youtube_jobs WHERE job_id=?',(job['id'],)).fetchone():
            return ('external', 'Existe registro de envio ao YouTube. Confira o destino antes de alterar o vídeo.')
    auto=c.execute('SELECT * FROM auto_jobs WHERE job_id=?',(job['id'],)).fetchone()
    if not auto:return None
    if auto['delivery'] not in (('local','sending') if claimed_buffer else ('local',)) or auto['buffer_id']:
        return ('external', 'Existe tentativa de envio ao Buffer. Confira o destino antes de gerar novamente.')
    if not autopilot.settings()['enabled']:
        return ('routine', 'Produção automática pausada. Retome a operação para continuar.')
    rule=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(job['product_id'],)).fetchone()
    if not rule or not rule['active'] or not rule['approved']:
        return ('product', 'Produto pausado ou sem autorização na rotina.')
    if not catalog.eligible(job['product_id']):
        return ('catalog', 'Produto indisponível ou catálogo desatualizado. Aguardando a fonte autorizada.')
    brief=campaigns.for_product(job['product_id'])
    if brief and not brief['active']:
        return ('campaign', 'Campanha pausada. A produção aguarda sua reativação.')
    return None


def recover_interrupted():
    with core.db() as c:
        ids=[r[0] for r in c.execute("SELECT jobs.id FROM jobs JOIN render_state ON render_state.job_id=jobs.id JOIN auto_jobs ON auto_jobs.job_id=jobs.id WHERE interrupted=1 AND jobs.status='error'")]
    for jid in ids:
        autopilot.render_failed(jid,only_interrupted=True)


def changed(product, meta):
    brief=campaigns.for_product(product['id'])
    return (meta.get('product_hash')!=content_engine.product_fingerprint(product) or
            (meta.get('campaign') or {}).get('revision')!=(brief or {}).get('revision'))


def claim_next():
    """A writer transaction prevents two workers from claiming the same job."""
    recover_interrupted()
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute("UPDATE jobs SET status='queued',updated_at=? WHERE status='scheduled' AND due_at<=?",(core.stamp(),core.stamp()))
        rows=c.execute("SELECT jobs.* FROM jobs LEFT JOIN auto_jobs ON auto_jobs.job_id=jobs.id WHERE jobs.status='queued' AND (auto_jobs.retry_at IS NULL OR auto_jobs.retry_at<=?) ORDER BY jobs.created_at,jobs.id",(core.stamp(),)).fetchall()
        for row in rows:
            reason=block_reason(c,row)
            if reason:
                c.execute('INSERT INTO render_state(job_id,block_code,detail) VALUES (?,?,?) ON CONFLICT(job_id) DO UPDATE SET block_code=excluded.block_code,detail=excluded.detail',(row['id'],*reason))
                continue
            c.execute("UPDATE jobs SET status='rendering',updated_at=? WHERE id=? AND status='queued'",(core.stamp(),row['id']))
            c.execute("INSERT INTO render_state(job_id,started_at) VALUES (?,?) ON CONFLICT(job_id) DO UPDATE SET started_at=excluded.started_at,interrupted=0,block_code='',detail=''",(row['id'],core.stamp()))
            job=dict(row);job['status']='rendering'
            product=dict(c.execute('SELECT * FROM products WHERE id=?',(row['product_id'],)).fetchone())
            return job,product
    return None


def prepare(job, product):
    """Refresh automatic source changes without holding SQLite during local AI."""
    jid=job['id']
    with core.db() as c:
        row=c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()
        auto=c.execute('SELECT variant FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
    meta=json.loads(row['payload']) if row else {}
    stale=changed(product,meta)
    if stale and (not auto or meta.get('edited')):
        with core.db() as c:
            c.execute("UPDATE jobs SET status='draft',error=?,updated_at=? WHERE id=? AND status='rendering'",('Dados ou campanha alterados. Recrie o roteiro com a campanha atual antes de gerar.',core.stamp(),jid))
        return None
    if stale:
        scenes,caption,meta=content_engine.generate(product,auto['variant'])
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        current=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        latest=dict(c.execute('SELECT * FROM products WHERE id=?',(product['id'],)).fetchone())
        if not current or current['status']!='rendering':return None
        reason=block_reason(c,current)
        if reason or changed(latest,meta):
            c.execute("UPDATE jobs SET status='queued',updated_at=? WHERE id=?",(core.stamp(),jid))
            return None
        if stale:
            c.execute('UPDATE jobs SET scenes=?,caption=?,error=?,updated_at=? WHERE id=?',(json.dumps(scenes,ensure_ascii=False),caption,'',core.stamp(),jid))
            c.execute('INSERT INTO content_meta VALUES (?,?) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload',(jid,json.dumps(meta,ensure_ascii=False)))
            c.execute('DELETE FROM editorial_reviews WHERE job_id=?',(jid,))
            c.execute('DELETE FROM media_validations WHERE job_id=?',(jid,))
        result=dict(c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())
    if stale:autopilot.event('production','Dados atualizados: roteiro automático refeito antes de renderizar.',jid)
    return result,latest


def queue():
    with core.db() as c:
        rows=c.execute("SELECT jobs.*,products.name,auto_jobs.retry_at FROM jobs JOIN products ON products.id=jobs.product_id LEFT JOIN auto_jobs ON auto_jobs.job_id=jobs.id WHERE jobs.status IN ('queued','scheduled','rendering') ORDER BY jobs.created_at,jobs.id").fetchall()
        result=[]
        for row in rows:
            reason=block_reason(c,row) if row['status']!='rendering' else None
            state='blocked' if reason else row['status']
            detail=reason[1] if reason else {'queued':'Aguardando o próximo ciclo local.','scheduled':'Preparação programada para '+row['due_at'],'rendering':'Gerando imagens, voz e MP4 neste computador.'}[row['status']]
            if not reason and row['status']=='queued' and row['retry_at'] and datetime.fromisoformat(row['retry_at'])>core.now():
                state='retry';detail='Nova tentativa local a partir de '+row['retry_at']
            result.append({'id':row['id'],'name':row['name'],'state':state,'detail':detail,'due_at':row['due_at'],'retry_at':row['retry_at']})
    return result
