"""Tester fixtures and a deliberately minimal, credential-free support report."""
import json
import platform
import threading
import core
from version import VERSION

_demo_lock=threading.Lock()
DEMO_URL='https://example.com/afiliados-studio-teste'


def create_demo():
    if not core.TESTER:raise ValueError('Abra iniciar_tester.bat para criar a demonstração em uma pasta separada.')
    import content_engine
    with _demo_lock:
        content_engine.configure({'mode':'rules','format':'landscape'})
        with core.db() as c:row=c.execute('SELECT id FROM products WHERE url=?',(DEMO_URL,)).fetchone()
        pid=row['id'] if row else core.save_product({'name':'Demonstração local · sem comissão','url':DEMO_URL,'kind':'digital','category':'Teste local',
          'description':'Este cadastro verifica a criação de roteiro e vídeo no notebook. O conteúdo é demonstrativo. Não corresponde a uma oferta comercial e não gera comissão.'})
        with core.db() as c:job=c.execute("SELECT * FROM jobs WHERE product_id=? AND status!='published'",(pid,)).fetchone()
        jid=job['id'] if job else core.create_job({'product_id':pid})
        current=core.get_job(jid)
        if current['status'] in ('draft','error'):
            core.edit_job(jid,{'scenes':json.loads(current['scenes']),'caption':current['caption'],'due_at':current['due_at'],'rights':True,'action':'render'})
        return {'id':jid,'notice':'Demonstração local, sem oferta comercial, comissão ou publicação externa.'}


def report():
    import diagnostics
    with core.db() as c:
        jobs={r['status']:r['count'] for r in c.execute('SELECT status,COUNT(*) AS count FROM jobs GROUP BY status')}
        deliveries={r['stage']:r['count'] for r in c.execute('SELECT stage,COUNT(*) AS count FROM youtube_jobs GROUP BY stage')}
        products=c.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    test=diagnostics.report();runtime=diagnostics.runtime()
    # Do not add products, URLs, captions, raw errors, events, paths or secrets.
    return {'schema_version':1,'app_version':VERSION,'generated_at':core.stamp(),'mode':'tester' if core.TESTER else 'normal',
            'system':{'os':platform.system(),'os_release':platform.release(),'python':platform.python_version()},
            'runtime':runtime,'counts':{'products':products,'jobs_by_status':jobs,'youtube_by_stage':deliveries},
            'local_test':{'status':test['status'],'voice':test.get('voice'),'checked_at':test.get('checked_at')},
            'privacy':'Este relatório não inclui credenciais, conta, links de afiliado, nomes de produtos, roteiros, mensagens de erro ou caminhos do computador.'}
