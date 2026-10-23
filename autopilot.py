"""Persistent, bounded local production loop and delivery tracking."""
import json
from datetime import datetime, timedelta
from uuid import uuid4
import core

DEFAULTS = {'enabled':False, 'daily_limit':1, 'hours':[18], 'cooldown_days':7,
            'backlog_limit':3, 'channel_id':'', 'send_drafts':False, 'channels':[],
            'buffer_checked_at':None, 'last_cycle':None, 'status':'Modo automático pausado.','timing_mode':'fixed'}


def init():
    with core.db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS automation_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS auto_products (
          product_id TEXT PRIMARY KEY REFERENCES products(id), approved INTEGER NOT NULL,
          active INTEGER NOT NULL, max_variants INTEGER NOT NULL DEFAULT 4, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS auto_jobs (
          job_id TEXT PRIMARY KEY REFERENCES jobs(id), variant INTEGER NOT NULL,
          delivery TEXT NOT NULL DEFAULT 'local', buffer_id TEXT NOT NULL DEFAULT '',
          delivery_error TEXT NOT NULL DEFAULT '', last_sync TEXT, metrics_sync TEXT,
          render_failures INTEGER NOT NULL DEFAULT 0, retry_at TEXT
        );
        CREATE TABLE IF NOT EXISTS operation_events (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL,
          message TEXT NOT NULL, job_id TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS expenses (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, description TEXT NOT NULL, amount REAL NOT NULL
        );
        ''')
        columns={row['name'] for row in c.execute('PRAGMA table_info(auto_jobs)')}
        if 'render_failures' not in columns:
            c.execute('ALTER TABLE auto_jobs ADD COLUMN render_failures INTEGER NOT NULL DEFAULT 0')
        if 'retry_at' not in columns:
            c.execute('ALTER TABLE auto_jobs ADD COLUMN retry_at TEXT')
        c.execute("UPDATE auto_jobs SET delivery='uncertain', delivery_error='O programa encerrou durante o envio. Confira os rascunhos no Buffer antes de reenviar.' WHERE delivery='sending'")


def settings():
    with core.db() as c:
        rows = c.execute('SELECT key,value FROM automation_settings').fetchall()
    return {**DEFAULTS, **{r['key']:json.loads(r['value']) for r in rows}}


def put_settings(values):
    with core.db() as c:
        for key,value in values.items():
            c.execute('INSERT INTO automation_settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))


def event(kind,message,job_id=''):
    with core.db() as c:
        c.execute('INSERT INTO operation_events VALUES (?,?,?,?,?)',(uuid4().hex,core.stamp(),kind,message[:900],job_id))
        c.execute('DELETE FROM operation_events WHERE id NOT IN (SELECT id FROM operation_events ORDER BY created_at DESC LIMIT 300)')


def configure(payload):
    previous=settings()
    limit=core.numeric(payload.get('daily_limit',previous['daily_limit']),3,integer=True)
    cooldown=core.numeric(payload.get('cooldown_days',previous['cooldown_days']),90,integer=True)
    if limit<1 or cooldown<1:
        raise ValueError('Use pelo menos 1 vídeo por dia e 1 dia de intervalo por produto.')
    hours=payload.get('hours',previous['hours'])
    if not isinstance(hours,list) or not hours or len(hours)>6:
        raise ValueError('Escolha de 1 a 6 horários.')
    hours=sorted(set(core.numeric(h,23,integer=True) for h in hours))
    timing_mode=payload.get('timing_mode',previous['timing_mode'])
    if timing_mode not in ('fixed','history'):raise ValueError('Selecione horários fixos ou aprendizado pelo histórico.')
    channel=core.clean(payload.get('channel_id',previous['channel_id']),200)
    if channel and channel not in {c['id'] for c in previous['channels']}:
        raise ValueError('Escolha um canal que foi confirmado pela conexão do Buffer.')
    enabled=payload.get('enabled') is True
    send=payload.get('send_drafts') is True
    if send and core.TESTER:raise ValueError('Envios externos estão bloqueados no modo tester.')
    if send and not channel:
        raise ValueError('Conecte o Buffer e selecione o TikTok antes de enviar rascunhos.')
    put_settings({'enabled':enabled,'daily_limit':limit,'cooldown_days':cooldown,'hours':hours,'timing_mode':timing_mode,'channel_id':channel,'send_drafts':send,
                  'status':'Aguardando o próximo ciclo de produção.' if enabled else 'Modo automático pausado.'})
    event('settings','Modo automático ativado.' if enabled else 'Modo automático pausado. Os arquivos já criados foram mantidos.')


def approve_product(pid,payload):
    with core.db() as c:
        product=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
        if not product:
            raise ValueError('Produto não encontrado.')
        active=payload.get('active') is True
        approved=payload.get('approved') is True
        if active and (not approved or len(product['description'].strip())<30):
            raise ValueError('Confirme os materiais e informe pelo menos 30 caracteres de características verificadas.')
        maximum=core.numeric(payload.get('max_variants',4),4,integer=True)
        if maximum<1:
            raise ValueError('Escolha de 1 a 4 variações por produto.')
        c.execute('INSERT INTO auto_products VALUES (?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET approved=excluded.approved,active=excluded.active,max_variants=excluded.max_variants,updated_at=excluded.updated_at',(pid,int(approved),int(active),maximum,core.stamp()))


def script(product,variant):
    import content_engine
    scenes,caption,_=content_engine.generate(product,variant)
    return scenes,caption


def timing(config=None):
    config=config or settings()
    suggestion=core.suggestion()
    learned=config.get('timing_mode')=='history' and suggestion['learned']
    return {'hours':suggestion['hours'] if learned else config['hours'],'learned':learned,
            'reason':suggestion['detail'] if learned else ('Ainda faltam resultados comparáveis. Usando os horários de partida.' if config.get('timing_mode')=='history' else 'Usando os horários configurados na rotina.')}


def next_slot(config,current,connection=None):
    hours=timing(config)['hours']
    def reserved(c):
        return [datetime.fromisoformat(r[0]).astimezone(core.TZ) for r in c.execute("SELECT due_at FROM jobs JOIN auto_jobs ON job_id=jobs.id WHERE jobs.status!='error'")]
    if connection is not None:slots=reserved(connection)
    else:
        with core.db() as c:slots=reserved(c)
    for day in range(8):
        for hour in hours:
            slot=(current+timedelta(days=day)).replace(hour=hour,minute=0,second=0,microsecond=0)
            if slot<=current+timedelta(minutes=10):
                continue
            on_day=[s for s in slots if s.date()==slot.date()]
            if len(on_day)<config['daily_limit'] and not any(s==slot for s in slots):
                return slot
    return None


def candidates(config,current):
    with core.db() as c:
        products=[dict(r) for r in c.execute('''SELECT products.*,auto_products.max_variants FROM products
        JOIN auto_products ON products.id=auto_products.product_id
        WHERE auto_products.active=1 AND auto_products.approved=1''')]
        jobs=[dict(r) for r in c.execute('SELECT jobs.*,auto_jobs.variant FROM jobs LEFT JOIN auto_jobs ON job_id=jobs.id')]
    eligible=[]
    for p in products:
        import catalog,campaigns
        campaign=campaigns.for_product(p['id'])
        if campaign and not campaign['active']:continue
        if not catalog.eligible(p['id']):continue
        history=[j for j in jobs if j['product_id']==p['id']]
        if any(j['status']!='published' for j in history):
            continue
        variants=[j['variant'] for j in history if j['variant'] is not None]
        if len(variants)>=p['max_variants']:
            continue
        latest=max((datetime.fromisoformat(j['published_at'] or j['created_at']).astimezone(core.TZ) for j in history),default=None)
        if latest and current-latest<timedelta(days=config['cooldown_days']):
            continue
        recorded=[j for j in history if j['results_recorded_at']]
        confirmed=sum(j['revenue'] for j in recorded)
        p['confirmed_per_post']=confirmed/len(recorded) if recorded else 0
        p['recorded_count']=len(recorded)
        p['sample_count']=len(history)
        p['variant']=max(variants,default=-1)+1
        eligible.append(p)
    # First explore products without evidence; afterwards compare confirmed returns.
    return sorted(eligible,key=lambda p:(p['sample_count']>0,-p['confirmed_per_post'],p['sample_count'],p['created_at']))


def cycle():
    config=settings()
    if not config['enabled']:
        return None
    current=core.now()
    with core.db() as c:
        backlog=c.execute("SELECT COUNT(*) FROM jobs JOIN auto_jobs ON job_id=jobs.id WHERE jobs.status!='published'").fetchone()[0]
    if backlog>=config['backlog_limit']:
        put_settings({'last_cycle':core.stamp(),'status':'Fila de 3 vídeos preenchida. Aguardando publicações ou atenção aos erros.'})
        return None
    options=candidates(config,current)
    if not options:
        put_settings({'last_cycle':core.stamp(),'status':'Sem produtos elegíveis. Ative produtos revisados ou aguarde o intervalo entre variações.'})
        return None
    slot=next_slot(config,current)
    if not slot:
        put_settings({'last_cycle':core.stamp(),'status':'Agenda dos próximos 7 dias preenchida.'})
        return None
    product=options[0]
    import content_engine
    scenes,caption,meta=content_engine.generate(product,product['variant'])
    jid=uuid4().hex
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        # Planning can take time. Recheck pause, limits and the source before
        # reserving a slot; another cycle may have committed in the meantime.
        import production
        latest_config=settings()
        if not latest_config['enabled']:return None
        if c.execute("SELECT COUNT(*) FROM jobs JOIN auto_jobs ON job_id=jobs.id WHERE jobs.status!='published'").fetchone()[0]>=latest_config['backlog_limit']:return None
        eligible=next((p for p in candidates(latest_config,core.now()) if p['id']==product['id']),None)
        if not eligible or eligible['variant']!=product['variant'] or production.changed(eligible,meta):return None
        slot=next_slot(latest_config,core.now(),connection=c)
        if not slot:return None
        # The unique active-product index also protects simultaneous manual requests.
        if c.execute("SELECT 1 FROM jobs WHERE product_id=? AND status!='published'",(product['id'],)).fetchone():
            return None
        c.execute('INSERT INTO jobs (id,product_id,status,scenes,caption,due_at,created_at,updated_at,rights) VALUES (?,?,?,?,?,?,?,?,1)',(jid,product['id'],'queued',json.dumps(scenes,ensure_ascii=False),caption,slot.isoformat(),core.stamp(),core.stamp()))
        c.execute('INSERT INTO auto_jobs (job_id,variant) VALUES (?,?)',(jid,product['variant']))
        c.execute('INSERT INTO content_meta VALUES (?,?)',(jid,json.dumps(meta,ensure_ascii=False)))
    event('production',f"Roteiro criado automaticamente: {product['name']}. Variação {product['variant']+1}.",jid)
    put_settings({'last_cycle':core.stamp(),'status':'Produção automática em andamento. Confira o acompanhamento de publicação na página Começar.'})
    return jid


def delivery_cycle(media_url):
    if core.TESTER:return
    import buffer_client
    config=settings()
    if not config['enabled'] or not config['send_drafts'] or not config['channel_id']:
        return
    with core.db() as c:
        rows=c.execute("SELECT jobs.* FROM jobs JOIN auto_jobs ON job_id=jobs.id WHERE jobs.status='ready' AND delivery='local' ORDER BY jobs.due_at,jobs.id").fetchall()
    for job in rows:
        import quality,production
        with core.db() as c:
            if production.block_reason(c,job):continue
        if not quality.inspect(job['id'],verify_media=True)['allowed']:continue
        # Build media access before claiming the external send. Failure here is safe to retry.
        url=media_url(job['id'])
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if production.block_reason(c,job):continue
            if not c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=? AND delivery='local'",(job['id'],)).rowcount:
                continue
        with core.db() as c:paused=production.block_reason(c,job,claimed_buffer=True)
        if paused or not quality.inspect(job['id'])['allowed']:
            with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='local' WHERE job_id=? AND delivery='sending'",(job['id'],))
            continue
        try:
            post=buffer_client.create_draft(config['channel_id'],job['caption'],url,bool(job['voice']))
        except Exception as exc:
            # A timeout may follow successful creation. Never blindly create again.
            with core.db() as c:
                c.execute("UPDATE auto_jobs SET delivery='uncertain',delivery_error=? WHERE job_id=?",(str(exc)[:700],job['id']))
            event('attention','Envio sem confirmação. Confira os rascunhos no Buffer antes de reenviar.',job['id'])
            return
        with core.db() as c:
            c.execute("UPDATE auto_jobs SET delivery='draft',buffer_id=?,last_sync=?,delivery_error='' WHERE job_id=?",(post['id'],core.stamp(),job['id']))
        event('buffer','Rascunho enviado ao Buffer. Falta a identificação comercial nativa antes de publicar.',job['id'])


def sync():
    if core.TESTER:return
    import buffer_client
    if not buffer_client.key_path().exists():
        return
    with core.db() as c:
        rows=c.execute("SELECT auto_jobs.*,jobs.status FROM auto_jobs JOIN jobs ON job_id=jobs.id WHERE buffer_id!='' AND (last_sync IS NULL OR last_sync<?) LIMIT 5",((core.now()-timedelta(minutes=15)).isoformat(),)).fetchall()
    for row in rows:
        with core.db() as c:
            c.execute('UPDATE auto_jobs SET last_sync=? WHERE job_id=?',(core.stamp(),row['job_id']))
        try:
            post=buffer_client.get_post(row['buffer_id'])
            if post.get('status')=='sent' and post.get('sentAt'):
                with core.db() as c:
                    c.execute("UPDATE jobs SET status='published',published_at=?,tiktok_url=?,updated_at=? WHERE id=?",(post['sentAt'],post.get('externalLink') or '',core.stamp(),row['job_id']))
                    c.execute("UPDATE auto_jobs SET delivery='sent',delivery_error='' WHERE job_id=?",(row['job_id'],))
                if row['status']!='published':
                    event('published','Publicação confirmada pelo Buffer.',row['job_id'])
            elif post.get('status')=='error':
                with core.db() as c:
                    c.execute("UPDATE auto_jobs SET delivery='error',delivery_error='O Buffer informou falha. Abra o painel do Buffer para corrigir.' WHERE job_id=?",(row['job_id'],))
            if post.get('status')=='sent' and (not row['metrics_sync'] or datetime.fromisoformat(row['metrics_sync'])<core.now()-timedelta(hours=24)):
                result=buffer_client.metrics(row['buffer_id'])
                views=next((m['value'] for m in result.get('metrics') or [] if m.get('type') in ('video_views','views')),None)
                with core.db() as c:
                    if views is not None:
                        c.execute('UPDATE jobs SET views=? WHERE id=?',(core.numeric(views,10**12,integer=True),row['job_id']))
                    c.execute('UPDATE auto_jobs SET metrics_sync=? WHERE job_id=?',(core.stamp(),row['job_id']))
        except Exception as exc:
            with core.db() as c:
                c.execute('UPDATE auto_jobs SET delivery_error=? WHERE job_id=?',(str(exc)[:700],row['job_id']))


def expense(payload):
    description=core.clean(payload.get('description'),120,True)
    amount=core.numeric(payload.get('amount'),10**8)
    if amount<=0:
        raise ValueError('Informe um custo maior que zero.')
    with core.db() as c:
        c.execute('INSERT INTO expenses VALUES (?,?,?,?)',(uuid4().hex,core.stamp(),description,amount))


def render_failed(jid, only_interrupted=False):
    """Only local rendering is retried. Never repeat an uncertain external send."""
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
        job=c.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone()
        if not row or not job or job['status']!='error':
            return
        import production
        reason=production.block_reason(c,job)
        if reason and (only_interrupted or reason[0] in ('external','rights')):return
        if only_interrupted:
            interrupted=c.execute('SELECT interrupted FROM render_state WHERE job_id=?',(jid,)).fetchone()
            if not interrupted or not interrupted['interrupted']:return
        c.execute('UPDATE render_state SET interrupted=0 WHERE job_id=?',(jid,))
        failures=row['render_failures']+1
        delay=2 if failures==1 else 10
        retry=(core.now()+timedelta(minutes=delay)).isoformat() if failures<3 else None
        c.execute('UPDATE auto_jobs SET render_failures=?,retry_at=? WHERE job_id=?',(failures,retry,jid))
        if retry:
            c.execute("UPDATE jobs SET status='queued',error=?,updated_at=? WHERE id=?",(f'A geração falhou. Nova tentativa local em {delay} minutos ({failures}/3).',core.stamp(),jid))
    event('attention',f'Falha na geração. {"Nova tentativa local programada." if retry else "Três falhas: verifique as dependências e o roteiro."}',jid)


def reconcile(jid,post_id):
    import buffer_client
    post_id=core.clean(post_id,200,True)
    config=settings()
    with core.db() as c:
        if not c.execute('SELECT 1 FROM auto_jobs WHERE job_id=?',(jid,)).fetchone():
            raise ValueError('Vídeo automático não encontrado.')
    post=buffer_client.get_post(post_id)
    if post.get('id')!=post_id or post.get('channelId')!=config['channel_id']:
        raise ValueError('O post não pertence ao TikTok selecionado na rotina.')
    with core.db() as c:
        c.execute("UPDATE auto_jobs SET buffer_id=?,delivery='draft',delivery_error='',last_sync=NULL WHERE job_id=?",(post_id,jid))
    event('buffer','Post existente vinculado ao vídeo. O sistema consultará a confirmação de publicação.',jid)


def state():
    import buffer_client
    with core.db() as c:
        approved=[dict(r) for r in c.execute('SELECT * FROM auto_products')]
        runs=[dict(r) for r in c.execute('SELECT * FROM auto_jobs')]
        events=[dict(r) for r in c.execute('SELECT * FROM operation_events ORDER BY created_at DESC LIMIT 25')]
        expenses=[dict(r) for r in c.execute('SELECT * FROM expenses ORDER BY created_at DESC')]
        gross=c.execute("SELECT COALESCE(SUM(revenue),0) FROM jobs WHERE status='published'").fetchone()[0]
    cost=sum(e['amount'] for e in expenses)
    return {'settings':settings(),'products':approved,'runs':runs,'events':events,'expenses':expenses,
            'profit':{'commissions':gross,'costs':cost,'net':gross-cost,'source':'Comissões e custos informados por você.'},
            'buffer':{'key_present':buffer_client.key_path().exists(),'automatic_commercial_posting':False,'notice':buffer_client.NOTICE}}
