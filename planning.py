"""Local publication reservations. Never changes a remote schedule itself."""
from datetime import datetime, timedelta
import autopilot
import core


def reserve_late(jid,processing=False):
    """Move a missed slot atomically; a known private upload may reserve only
    while processing, before its first confirmed remote scheduling stage.
    """
    import campaigns,catalog,production
    changed=None
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        config=autopilot.settings()
        if not config['enabled']:return None
        job=c.execute('SELECT jobs.* FROM jobs JOIN auto_jobs ON job_id=jobs.id WHERE jobs.id=?',(jid,)).fetchone()
        if not job or job['status'] not in ('queued','ready'):return None
        remote=None
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone():
            remote=c.execute('SELECT * FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
        if processing:
            if not remote or remote['stage']!='processing' or not remote['video_id']:return None
            auto=c.execute('SELECT * FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
            rule=c.execute('SELECT * FROM auto_products WHERE product_id=?',(job['product_id'],)).fetchone()
            brief=campaigns.for_product(job['product_id'])
            if not job['rights'] or auto['delivery']!='local' or auto['buffer_id']:return None
            if not rule or not rule['active'] or not rule['approved'] or not catalog.eligible(job['product_id']):return None
            if brief and not brief['active']:return None
        elif production.block_reason(c,job,local_hold=True):return None
        current=core.now()
        previous=datetime.fromisoformat(job['due_at'])
        if previous>current+timedelta(minutes=5 if processing else 10):return previous
        slot=autopilot.next_slot(config,current,connection=c,exclude_job_id=jid)
        if slot is None:return None
        c.execute('UPDATE jobs SET due_at=?,updated_at=? WHERE id=?',(slot.isoformat(),core.stamp(),jid))
        c.execute('''INSERT INTO auto_schedule_changes(job_id,previous_due_at,updated_at) VALUES (?,?,?)
            ON CONFLICT(job_id) DO UPDATE SET previous_due_at=excluded.previous_due_at,
            updated_at=excluded.updated_at,changes=auto_schedule_changes.changes+1''',(jid,job['due_at'],core.stamp()))
        changed=(job['due_at'],slot)
    if changed:
        autopilot.event('schedule','Horário vencido: nova reserva local em '+changed[1].strftime('%d/%m às %H:%M')+'. O agendamento no destino ainda precisa ser confirmado.',jid)
    return changed[1]


def recover_overdue():
    with core.db() as c:
        rows=c.execute("""SELECT jobs.id,jobs.due_at FROM jobs JOIN auto_jobs ON job_id=jobs.id
            WHERE jobs.status IN ('queued','ready')""").fetchall()
    rows=sorted(rows,key=lambda row:(datetime.fromisoformat(row['due_at']),row['id']))
    return [row['id'] for row in rows if datetime.fromisoformat(row['due_at'])<=core.now()+timedelta(minutes=10) and reserve_late(row['id']) is not None]


def state():
    """Read-only calendar facts. A local reservation is never remote proof."""
    with core.db() as c:
        rows=c.execute("""SELECT jobs.id,jobs.status,jobs.due_at,auto_jobs.delivery,auto_jobs.buffer_id,
            youtube_jobs.stage,youtube_jobs.error AS remote_error,
            auto_schedule_changes.previous_due_at,auto_schedule_changes.updated_at AS revised_at
            FROM jobs LEFT JOIN auto_jobs ON auto_jobs.job_id=jobs.id
            LEFT JOIN youtube_jobs ON youtube_jobs.job_id=jobs.id
            LEFT JOIN auto_schedule_changes ON auto_schedule_changes.job_id=jobs.id
            WHERE jobs.status!='published' ORDER BY jobs.due_at,jobs.id""").fetchall()
    result=[]
    for row in rows:
        auto=row['delivery'] is not None
        stage=row['stage']
        if stage=='scheduled':
            label='Agendamento confirmado no YouTube';detail='O destino confirmou o agendamento. Confira alterações ou cancelamentos no YouTube Studio.';kind='remote'
        elif stage:
            label={'held_local':'Envio retido localmente','uncertain':'Envio sem confirmação','failed':'Envio exige atenção','uploaded':'Enviado com visibilidade restrita','held':'Publicação retida no YouTube'}.get(stage,'Envio em andamento no YouTube')
            detail=row['remote_error'] or 'Publicação pública ainda não confirmada.';kind='attention' if stage in ('held_local','held','uncertain','failed') else 'sending'
        elif row['buffer_id'] or auto and row['delivery']!='local':
            label='Acompanhamento pelo Buffer';detail='Confira o rascunho ou a publicação no destino. Esta data não confirma um agendamento remoto.';kind='attention'
        elif auto:
            label='Publicação planejada';detail='Reserva local da rotina. Depende de vídeo válido, autorizações, conexão e confirmação do destino.';kind='local'
        else:
            label='Preparação do vídeo';detail='Horário local de geração. Não é um agendamento de publicação.';kind='manual'
        destination='youtube' if stage else 'buffer' if row['buffer_id'] or auto and row['delivery']!='local' else None
        result.append({'id':row['id'],'automatic':auto,'kind':kind,'label':label,'detail':detail,'destination':destination,
                       'due_at':row['due_at'],'previous_due_at':row['previous_due_at'],'revised_at':row['revised_at']})
    return result
