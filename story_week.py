"""Seven local preparation slots. Never claims a TikTok schedule or sends media."""
import argparse
from datetime import date,datetime,timedelta
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from uuid import uuid4
import core
import story_library
import story_delivery
from story_week_catalog import WEEK_NUMBERS,NEXT_NUMBERS,STORIES
from instance_lock import InstanceLock


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS story_weeks(
            id TEXT PRIMARY KEY,handle TEXT NOT NULL,start_date TEXT NOT NULL,offer TEXT NOT NULL,
            enabled INTEGER NOT NULL,created_at TEXT NOT NULL,UNIQUE(handle,start_date));
            CREATE TABLE IF NOT EXISTS story_week_slots(
            id TEXT PRIMARY KEY,week_id TEXT NOT NULL REFERENCES story_weeks(id),number INTEGER NOT NULL,
            due_at TEXT NOT NULL,status TEXT NOT NULL,media_id TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,UNIQUE(week_id,number),UNIQUE(week_id,due_at));''')
        if 'creative_plan' not in {r['name'] for r in c.execute('PRAGMA table_info(story_week_slots)')}:
            c.execute("ALTER TABLE story_week_slots ADD COLUMN creative_plan TEXT NOT NULL DEFAULT '{}'")


def prepare(payload):
    import story_offers
    handle=story_delivery.target()
    collection=payload.get('collection','first')
    if collection not in ('first','standalone'):raise ValueError('Coleção de histórias indisponível.')
    numbers=NEXT_NUMBERS if collection=='standalone' else WEEK_NUMBERS
    try:
        start=date.fromisoformat(payload['start_date']);hour=payload.get('hour',18)
        if type(hour) is not int or not 0<=hour<=23 or start<core.now().date() or start>core.now().date()+timedelta(days=30):raise ValueError()
    except (KeyError,TypeError,ValueError):raise ValueError('Escolha uma data inicial válida e um horário entre 0 e 23.') from None
    with core.db() as c:
        prior=c.execute('SELECT id FROM story_weeks WHERE handle=? AND start_date=?',(handle,start.isoformat())).fetchone()
        if prior:
            saved=tuple(r['number'] for r in c.execute('SELECT number FROM story_week_slots WHERE week_id=? ORDER BY number',(prior['id'],)))
            if saved!=numbers:raise ValueError('Já existe outra coleção para esta data. Escolha uma data livre.')
            return {'id':prior['id'],'existing':True}
        series=c.execute('SELECT id FROM story_series ORDER BY created_at LIMIT 1').fetchone()
    offer=story_offers.for_series(series['id']) if series else None
    if not offer or not story_offers.current(offer):raise ValueError('Vincule primeiro uma oferta ativa e autorizada à história.')
    if any(story_library.native_post_exists(f'3d:a-chave-do-12:{n}',handle) for n in numbers):
        raise ValueError('Um destes capítulos já tem registro no TikTok. Uma nova semana exige conteúdos novos.')
    creative_plans={}
    if collection=='standalone':
        import story_director
        import story_growth
        feedback=story_director.policy(story_growth.state()['posts'],core.now())
        for n in numbers:
            story,report=story_director.plan(STORIES[n],feedback)
            creative_plans[n]={'story':story,'report':report}
    ready={n:r for n,r in story_library.latest_3d(story_library.entries()).items() if r['meta'].get('offer')==offer}
    identifier=uuid4().hex
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT id FROM story_weeks WHERE handle=? AND start_date=?',(handle,start.isoformat())).fetchone()
        if prior:
            saved=tuple(r['number'] for r in c.execute('SELECT number FROM story_week_slots WHERE week_id=? ORDER BY number',(prior['id'],)))
            if saved!=numbers:raise ValueError('Já existe outra coleção para esta data. Escolha uma data livre.')
            return {'id':prior['id'],'existing':True}
        if c.execute('SELECT 1 FROM story_weeks WHERE enabled=1').fetchone():raise ValueError('Aguarde a semana em produção antes de preparar outra.')
        if collection=='standalone' and c.execute('SELECT 1 FROM story_weeks w JOIN story_week_slots s ON s.week_id=w.id WHERE w.handle=? AND s.number=9',(handle,)).fetchone():
            raise ValueError('Esta coleção já foi preparada. Use o calendário existente; não haverá outra cópia na fila.')
        c.execute('INSERT INTO story_weeks VALUES (?,?,?,?,?,?)',(identifier,handle,start.isoformat(),json.dumps(offer),1,core.stamp()))
        for offset,number in enumerate(numbers):
            due=datetime.combine(start+timedelta(days=offset),datetime.min.time(),core.TZ).replace(hour=hour)
            media=ready.get(number);media_id=media['id'] if media else ''
            # New editorial versions must be rendered from the pinned plan,
            # never adopted from an unrelated ready clip of the same number.
            if number in creative_plans:media_id='';media=None
            c.execute('INSERT INTO story_week_slots(id,week_id,number,due_at,status,media_id,error,updated_at,creative_plan) VALUES (?,?,?,?,?,?,?,?,?)',
                      (uuid4().hex,identifier,number,due.isoformat(),'ready' if media else 'queued',media_id,'',core.stamp(),json.dumps(creative_plans.get(number,{}),ensure_ascii=False)))
    for number in (2,3):
        if number in ready and not story_library.native_post_exists(f'3d:a-chave-do-12:{number}',handle):
            if number in numbers:story_delivery.prepare(ready[number]['id'])
    return {'id':identifier,'existing':False}


def state():
    import story_offers
    with core.db() as c:
        plan=c.execute('SELECT * FROM story_weeks ORDER BY created_at DESC LIMIT 1').fetchone()
        if not plan:return None
        slots=[dict(r) for r in c.execute('SELECT * FROM story_week_slots WHERE week_id=? ORDER BY due_at',(plan['id'],))]
    for row in slots:
        row['creative_plan']=json.loads(row['creative_plan'])
        meta=story_library.read_json(core.DATA/'stories'/row['media_id']/'roteiro.json') if row['media_id'] else None
        row['review']=meta.get('director') if meta else None
        row['title']=STORIES[row['number']]['title'] if row['number'] in STORIES else ('A filha na fotografia' if row['number']==2 else 'O que a caixa guardava')
        row['receipt']=story_library.receipt(row['media_id']) if row['media_id'] else None
        row['package']=story_delivery.info(row['media_id']) if row['media_id'] and not row['receipt'] else None
        if row['status']=='ready' and not (core.DATA/'stories'/row['media_id']/'video.mp4').is_file():
            row['status']='error';row['error']='Arquivo indisponível. A data continua sendo apenas um plano local.'
        if row['status']=='ready' and (story_delivery.target()!=plan['handle'] or not story_offers.current(json.loads(plan['offer']))):
            row['status']='error';row['error']='O perfil ou a oferta mudou. Confira os dados antes de retomar.';row['package']=None
    native=sum(bool(r['receipt']) for r in slots)
    return {'id':plan['id'],'handle':plan['handle'],'start_date':plan['start_date'],'preparing':bool(plan['enabled']),
            'slots':slots,'ready':sum(r['status']=='ready' for r in slots),'total':7,
            'native_registered':native,
            'collection':'standalone' if slots[0]['number'] in NEXT_NUMBERS else 'first',
            'notice':f'{native} de 7 capítulos com registro nativo. Os demais horários são propostas locais; a data passar não comprova publicação.'}


def resume(payload):
    import story_offers
    identifier=payload.get('id','')
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):raise ValueError('Semana inválida.')
    if shutil.disk_usage(core.DATA).free<256*1024**2:raise ValueError('Libere pelo menos 256 MB no disco para retomar.')
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM story_weeks WHERE id=?',(identifier,)).fetchone()
        if not row or story_delivery.target()!=row['handle'] or not story_offers.current(json.loads(row['offer'])):
            raise ValueError('Confira o perfil e a oferta antes de retomar.')
        if row['enabled']:return {'ok':True,'existing':True}
        if c.execute('SELECT 1 FROM story_weeks WHERE enabled=1').fetchone():raise ValueError('Outra semana já está em produção.')
        pending=c.execute("SELECT number FROM story_week_slots WHERE week_id=? AND status IN ('queued','error','rendering')",(identifier,)).fetchall()
        if not pending:raise ValueError('Esta semana já terminou; não há montagem para repetir.')
        if any(story_library.native_post_exists(f"3d:a-chave-do-12:{r['number']}",row['handle']) for r in pending):
            raise ValueError('Um capítulo pendente já tem registro no TikTok; confira o destino.')
        c.execute("UPDATE story_week_slots SET status='queued',error='',updated_at=? WHERE week_id=? AND status='error'",(core.stamp(),identifier))
        c.execute('UPDATE story_weeks SET enabled=1 WHERE id=?',(identifier,))
    return {'ok':True,'existing':False}


def tick():
    if core.TESTER:return
    with core.db() as c:
        needed=c.execute("SELECT 1 FROM story_weeks w JOIN story_week_slots s ON s.week_id=w.id WHERE w.enabled=1 AND s.status IN ('queued','rendering')").fetchone()
    if not needed:return
    directory=core.DATA/'story-week'/'worker'
    try:
        with InstanceLock(directory):pass
    except ValueError:return
    log=directory/'worker.log'
    with log.open('ab') as output:
        subprocess.Popen([sys.executable,str(core.ROOT/'story_week.py'),'--worker'],cwd=core.ROOT,
                         stdout=output,stderr=subprocess.STDOUT,env={**os.environ,'AFILIADOS_DATA':str(core.DATA),'PYTHONUTF8':'1'},
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def run_worker():
    import story_offers
    import story_week_renderer
    init()
    with InstanceLock(core.DATA/'story-week'/'worker'):
        with core.db() as c:
            interrupted=[dict(r) for r in c.execute("SELECT s.*,w.handle,w.offer FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id WHERE s.status='rendering'")]
        for row in interrupted:
            pinned=json.loads(row['creative_plan'])
            expected=pinned.get('story',STORIES.get(row['number'],{})).get('scenes',[])
            found=next((r for r in story_library.latest_3d(story_library.entries()).values() if r['meta'].get('week_slot')==row['id'] and
                        r['meta'].get('offer')==json.loads(row['offer']) and r['meta'].get('scenes',[])[:len(expected)]==expected and
                        (not pinned or r['meta'].get('director',{}).get('policy')==pinned['report']['policy']) and
                        hashlib.sha256((core.DATA/'stories'/r['id']/'video.mp4').read_bytes()).hexdigest()==r['meta']['sha256']),None)
            if found and story_delivery.target()==row['handle']:
                try:story_delivery.prepare(found['id'])
                except Exception:
                    with core.db() as c:
                        c.execute("UPDATE story_week_slots SET status='error',error=?,updated_at=? WHERE id=?",('O pacote recuperado precisa de revisão antes de retomar.',core.stamp(),row['id']))
                        c.execute('UPDATE story_weeks SET enabled=0 WHERE id=?',(row['week_id'],))
                    continue
            elif found:found=None
            with core.db() as c:
                c.execute('UPDATE story_week_slots SET status=?,media_id=?,updated_at=? WHERE id=?',
                          ('ready' if found else 'queued',found['id'] if found else '',core.stamp(),row['id']))
        while True:
            with core.db() as c:
                c.execute('BEGIN IMMEDIATE')
                row=c.execute("""SELECT s.*,w.handle,w.offer FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id
                    WHERE w.enabled=1 AND s.status='queued' ORDER BY s.due_at LIMIT 1""").fetchone()
                if not row:
                    c.execute("UPDATE story_weeks SET enabled=0 WHERE NOT EXISTS(SELECT 1 FROM story_week_slots s WHERE s.week_id=story_weeks.id AND s.status IN ('queued','rendering'))")
                    break
                job=dict(row);c.execute("UPDATE story_week_slots SET status='rendering',updated_at=? WHERE id=?",(core.stamp(),job['id']))
            try:
                offer=json.loads(job['offer'])
                if story_delivery.target()!=job['handle'] or not story_offers.current(offer):raise ValueError('Destino ou oferta alterados.')
                if job['number'] in (2,3):
                    import animation3d
                    identifier=animation3d.render_pilot(offer=offer,number=job['number'])['id']
                elif job['number'] in NEXT_NUMBERS:
                    identifier=story_week_renderer.render(job['number'],offer,job['id'],json.loads(job['creative_plan']))
                else:identifier=story_week_renderer.render(job['number'],offer,job['id'])
                if story_delivery.target()!=job['handle']:raise ValueError('Perfil alterado durante a preparação.')
                story_delivery.prepare(identifier)
                with core.db() as c:c.execute("UPDATE story_week_slots SET status='ready',media_id=?,error='',updated_at=? WHERE id=?",(identifier,core.stamp(),job['id']))
                print(json.dumps({'stage':'ready_local','chapter':job['number'],'media_id':identifier}),flush=True)
            except Exception:
                # Private process log only; the API retains a short safe error.
                import traceback
                traceback.print_exc()
                with core.db() as c:
                    c.execute("UPDATE story_week_slots SET status='error',error=?,updated_at=? WHERE id=?",('A preparação parou. Confira o produto, as cenas e o registro local antes de retomar.',core.stamp(),job['id']))
                    c.execute('UPDATE story_weeks SET enabled=0 WHERE id=?',(job['week_id'],))
                print(json.dumps({'stage':'stopped','chapter':job['number']}),flush=True)
                break


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:run_worker()
