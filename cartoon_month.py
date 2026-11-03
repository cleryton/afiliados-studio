"""Finite monthly cartoon production and native Studio checkpoints, without uploads."""
import argparse
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

import core
from instance_lock import InstanceLock

HOURS=(12,15,18,21)


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS cartoon_months (
            id TEXT PRIMARY KEY,handle TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,
            production_enabled INTEGER NOT NULL,paused INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,
            UNIQUE(handle,start_date,end_date));
          CREATE TABLE IF NOT EXISTS cartoon_slots (
            id TEXT PRIMARY KEY,plan_id TEXT NOT NULL REFERENCES cartoon_months(id),position INTEGER NOT NULL,
            due_at TEXT NOT NULL,story TEXT NOT NULL,script_hash TEXT NOT NULL,media_id TEXT NOT NULL,
            status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,
            UNIQUE(plan_id,position),UNIQUE(plan_id,due_at));''')
        if 'reviewed_retry' not in {r['name'] for r in c.execute('PRAGMA table_info(cartoon_slots)')}:
            c.execute('ALTER TABLE cartoon_slots ADD COLUMN reviewed_retry INTEGER NOT NULL DEFAULT 0')


def script_hash(story):
    return hashlib.sha256(json.dumps(story,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def exists():
    with core.db() as c:
        return bool(c.execute("SELECT 1 FROM sqlite_master WHERE name='cartoon_months'").fetchone())


def prepare(start_date='2026-11-09',end_date='2026-12-02'):
    """Explicit finite expansion, preserving every existing file and native receipt."""
    import cartoon2d
    from cartoon_month_catalog import ALL_STORIES
    import story_delivery
    if core.TESTER:raise ValueError('Use o aplicativo normal para preparar a operação real.')
    start,end=date.fromisoformat(start_date),date.fromisoformat(end_date)
    if (end-start).days!=23:raise ValueError('Esta coleção cobre 24 dias com quatro histórias por dia.')
    if start<=core.now().date():raise ValueError('Escolha datas futuras; não compensar horários vencidos.')
    handle=story_delivery.target()
    if handle!='novelitas0213':raise ValueError('A coleção é autorizada somente para @novelitas0213.')
    ready=cartoon2d.state()
    if len(ready)!=4:raise ValueError('Confira os quatro pilotos completos antes de preparar o mês.')
    init()
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT id FROM cartoon_months WHERE handle=? AND start_date=? AND end_date=?',(handle,start_date,end_date)).fetchone()
        if prior:return {'id':prior['id'],'existing':True}
        if c.execute('SELECT 1 FROM cartoon_months WHERE handle=?',(handle,)).fetchone():raise ValueError('Revise a coleção existente antes de criar outra.')
        identifier=uuid4().hex
        proposals=[]
        for i,story in enumerate(ALL_STORIES):
            day=start+timedelta(days=i//4)
            due=datetime.combine(day,datetime.min.time(),core.TZ).replace(hour=HOURS[i%4]).isoformat()
            if c.execute('SELECT 1 FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id WHERE lower(w.handle)=lower(?) AND s.due_at=?',(handle,due)).fetchone():
                raise ValueError('O horário já pertence à coleção 3D. Nenhum registro foi alterado.')
            if c.execute("SELECT 1 FROM story_native_attempts WHERE lower(handle)=lower(?) AND due_at=?",(handle,due)).fetchone():
                raise ValueError('Já existe uma tentativa neste horário. Confira o destino antes de continuar.')
            proposals.append((uuid4().hex,identifier,i+1,due,json.dumps(story,ensure_ascii=False),script_hash(story),
                              ready[i]['id'] if i<4 else uuid4().hex,'ready' if i<4 else 'queued',core.stamp()))
        c.execute('INSERT INTO cartoon_months VALUES (?,?,?,?,?,?,?)',(identifier,handle,start_date,end_date,1,0,core.stamp()))
        c.executemany('INSERT INTO cartoon_slots(id,plan_id,position,due_at,story,script_hash,media_id,status,updated_at) VALUES (?,?,?,?,?,?,?,?,?)',proposals)
    export_calendar()
    return {'id':identifier,'existing':False,'slots':96,'ready':4}


def _rows():
    if not exists():return None,[]
    with core.db() as c:
        plan=c.execute('SELECT * FROM cartoon_months ORDER BY created_at DESC LIMIT 1').fetchone()
        rows=[dict(r) for r in c.execute('SELECT * FROM cartoon_slots WHERE plan_id=? ORDER BY position',(plan['id'],))] if plan else []
    return dict(plan) if plan else None,rows


def owns(media):
    if not isinstance(media,str) or not re.fullmatch('[a-f0-9]{32}',media) or not exists():return False
    with core.db() as c:return bool(c.execute('SELECT 1 FROM cartoon_slots WHERE media_id=?',(media,)).fetchone())


def _source(slot):
    from story_library import read_json
    from cartoon_catalog import caption as expected_caption
    root=(core.DATA/'stories').resolve();folder=root/slot['media_id']
    if folder.is_symlink() or folder.resolve().parent!=root:raise ValueError('Arquivo fora da pasta autorizada.')
    meta=read_json(folder/'roteiro.json',65536);story=json.loads(slot['story'])
    if (not meta or meta.get('animation_type')!='original_procedural_2d' or meta.get('voice') is not True or
            meta.get('validation',{}).get('decoded') is not True or meta.get('scenes')!=story['scenes'] or
            meta.get('title')!=story['title'] or meta.get('offer') or script_hash(story)!=slot['script_hash']):
        raise ValueError('A história, a voz ou o arquivo concluído precisam de revisão.')
    hashes={};stats={}
    import story_delivery
    for name in ('video.mp4','poster.png','legenda.txt','legendas.srt'):
        path=folder/name
        if path.is_symlink() or not path.is_file() or path.resolve().parent!=folder:raise ValueError('Falta um arquivo original válido.')
        stat=path.stat()
        if not 0<stat.st_size<128*1024**2:raise ValueError('Arquivo vazio ou grande demais.')
        hashes[name]=story_delivery.file_hash(path);stats[name]=[stat.st_size,stat.st_mtime_ns]
    if hashes['video.mp4']!=meta.get('sha256'):raise ValueError('O vídeo foi alterado depois da validação.')
    text=(folder/'legenda.txt').read_text(encoding='utf-8')
    if not 0<len(' '.join(text.split()))<=2200 or ' '.join(text.split())!=' '.join(expected_caption(story).split()):
        raise ValueError('A legenda não corresponde à história completa.')
    if len(meta['scenes'])!=6:raise ValueError('História incompleta.')
    return meta,hashes,stats


def snapshot(media):
    import story_delivery
    if not owns(media):raise ValueError('História fora da coleção mensal.')
    with core.db() as c:
        slot=dict(c.execute('SELECT * FROM cartoon_slots WHERE media_id=?',(media,)).fetchone())
        plan=dict(c.execute('SELECT * FROM cartoon_months WHERE id=?',(slot['plan_id'],)).fetchone())
    if plan['paused'] or plan['handle']!=story_delivery.target() or slot['status']!='ready':raise ValueError('Confira o perfil, a pausa e o vídeo pronto.')
    meta,hashes,stats=_source(slot)
    proof={'id':media,'chapter':slot['position'],'handle':plan['handle'],'content_key':'2d:month:'+slot['script_hash'],
           'duration':meta['duration'],'files':hashes,'offer_hash':None,'ai_label_required':True,
           'third_party_commercial_label_required':False,'slot_id':slot['id'],'due_at':slot['due_at'],
           'script_sha256':slot['script_hash']}
    fingerprint=hashlib.sha256(json.dumps(proof,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {'proof':proof,'fingerprint':fingerprint,'stats':stats}


def begin(payload):
    import story_delivery
    if core.TESTER:raise ValueError('O modo tester bloqueia tentativas externas.')
    handle=story_delivery.target();media=payload.get('media_id')
    if handle!='novelitas0213' or payload.get('observed_handle')!=handle:raise ValueError('Confira o @novelitas0213 no próprio TikTok.')
    plan,rows=_rows()
    if not plan or plan['paused'] or plan['handle']!=handle:raise ValueError('Coleção pausada ou perfil alterado.')
    with core.db() as c:
        confirmed={r['content_key'] for r in c.execute("SELECT content_key FROM story_native_attempts WHERE lower(handle)=lower(?) AND stage='confirmed'",(handle,))}
    first=next((r for r in rows if '2d:month:'+r['script_hash'] not in confirmed),None)
    if not first or first['media_id']!=media or first['status']!='ready':raise ValueError('Comece pelo primeiro horário pronto e sem confirmação da coleção mensal.')
    if datetime.fromisoformat(first['due_at'])<=core.now():raise ValueError('A data proposta venceu. Retenha para revisão, sem publicar imediatamente.')
    proof=snapshot(media);caption=' '.join((core.DATA/'stories'/media/'legenda.txt').read_text(encoding='utf-8').split())
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        latest=c.execute('SELECT paused,handle FROM cartoon_months WHERE id=?',(plan['id'],)).fetchone()
        if latest['paused'] or latest['handle']!=handle:raise ValueError('A coleção mudou durante a preparação.')
        prior=c.execute('SELECT * FROM story_native_attempts WHERE lower(handle)=lower(?) AND content_key=?',(handle,proof['proof']['content_key'])).fetchone()
        if prior:return {'id':prior['id'],'existing':True,'may_upload':False,'stage':prior['stage']}
        if c.execute("SELECT 1 FROM story_publications WHERE content_key=? AND status!='cancelled'",(proof['proof']['content_key'],)).fetchone():raise ValueError('Há outra fila para esta história.')
        if c.execute('SELECT 1 FROM story_native_attempts WHERE lower(handle)=lower(?) AND due_at=?',(handle,first['due_at'])).fetchone():raise ValueError('Há outra tentativa neste horário.')
        identifier=uuid4().hex
        c.execute('INSERT INTO story_native_attempts(id,media_id,content_key,handle,due_at,fingerprint,source_sha256,caption_hash,stage,created_at,updated_at,commercial) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)',
                  (identifier,media,proof['proof']['content_key'],handle,first['due_at'],proof['fingerprint'],proof['proof']['files']['video.mp4'],hashlib.sha256(caption.encode()).hexdigest(),'reserved',core.stamp(),core.stamp()))
    return {'id':identifier,'existing':False,'may_upload':True,'stage':'reserved','due_at':first['due_at']}


def state():
    from story_library import receipt
    from story_local_archive import archived
    plan,rows=_rows()
    if not plan:return None
    with core.db() as c:
        observed={r['media_id']:json.loads(r['receipt']) for r in c.execute("SELECT media_id,receipt FROM story_native_attempts WHERE handle=? AND stage='confirmed' AND receipt IS NOT NULL",(plan['handle'],))}
    items=[]
    for r in rows:
        story=json.loads(r['story']);saved=observed.get(r['media_id']) or (receipt(r['media_id']) if r['status']=='ready' else None)
        present=(core.DATA/'stories'/r['media_id']/'video.mp4').is_file()
        retired=bool(saved and archived(r['media_id']))
        items.append({'local_archived':retired,'id':r['id'],'position':r['position'],'due_at':r['due_at'],'media_id':r['media_id'],
                      'title':story['title'],'status':r['status'],'error':r['error'],'receipt':saved,
                      'video_url':f"/stories/{r['media_id']}/video.mp4" if r['status']=='ready' and present else None,
                      'poster_url':f"/stories/{r['media_id']}/poster.png" if r['status']=='ready' else None})
    confirmed=sum(bool(i['receipt'] and i['receipt']['handle']==plan['handle']) for i in items)
    ready=sum(i['status']=='ready' and bool(i['video_url']) for i in items)
    produced=sum(i['status']=='ready' for i in items)
    retired=sum(i['local_archived'] for i in items)
    pending=next((i for i in items if not i['receipt']),None)
    return {**plan,'total':len(items),'ready':ready,'confirmed':confirmed,'pending':len(items)-confirmed,
            'per_day':4,'hours':list(HOURS),'next_item':pending,'slots':items,'produced':produced,'archived':retired,
            'publication_requires_browser':True,'publishes_automatically_without_operator':False}


def export_calendar():
    value=state()
    if not value:return
    root=core.DATA/'cartoon-month';root.mkdir(exist_ok=True)
    lines=['# Reserva de histórias 2D — @novelitas0213','',
           'Quatro por dia. Propostas locais não são agendamentos do TikTok. Horários de São Paulo.','',
           '| Data | Hora | História | Estado |','|---|---|---|---|']
    for row in value['slots']:
        label='Agendamento confirmado' if row['receipt'] else 'Vídeo pronto; envio pendente' if row['status']=='ready' else 'Produção '+row['status']
        lines.append(f"| {row['due_at'][:10]} | {row['due_at'][11:16]} | {row['title']} | {label} |")
    tmp=root/'calendar.new';tmp.write_text('\n'.join(lines)+'\n',encoding='utf-8');tmp.replace(root/'CALENDARIO.md')


def pause(payload):
    if not isinstance(payload.get('paused'),bool):raise ValueError('Informe se deseja pausar ou retomar.')
    plan,_=_rows()
    if not plan or payload.get('id')!=plan['id']:raise ValueError('Coleção mensal não encontrada.')
    with core.db() as c:
        c.execute('UPDATE cartoon_months SET paused=?,production_enabled=? WHERE id=?',(int(payload['paused']),int(not payload['paused']),plan['id']))
    return {'ok':True,'paused':payload['paused']}


def retry_reviewed(payload):
    """One extra local attempt after an operator fixes the cause; keep its history."""
    if payload.get('cause_reviewed') is not True:raise ValueError('Confira e corrija a causa antes de retomar.')
    plan,_=_rows()
    if not plan:raise ValueError('Coleção não encontrada.')
    with InstanceLock(core.DATA/'cartoon-month'/'worker'):
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM cartoon_slots WHERE id=? AND plan_id=?',(payload.get('id'),plan['id'])).fetchone()
            if not row or row['status']!='error' or row['reviewed_retry'] or row['attempts']>=3:
                raise ValueError('Não há uma retomada revisada disponível para este item.')
            c.execute("UPDATE cartoon_slots SET status='queued',error='',reviewed_retry=1,updated_at=? WHERE id=?",(core.stamp(),row['id']))
            c.execute('UPDATE cartoon_months SET production_enabled=? WHERE id=?',(int(not plan['paused']),plan['id']))
    return {'ok':True}


def tick():
    if core.TESTER or not exists():return
    with core.db() as c:
        pending=c.execute("SELECT 1 FROM cartoon_slots s JOIN cartoon_months p ON p.id=s.plan_id WHERE p.production_enabled=1 AND p.paused=0 AND s.status IN ('queued','rendering') LIMIT 1").fetchone()
    if not pending:return
    directory=core.DATA/'cartoon-month'/'worker'
    try:
        with InstanceLock(directory):pass
    except ValueError:return
    with (directory/'worker.log').open('ab') as log:
        subprocess.Popen([sys.executable,str(core.ROOT/'cartoon_month.py'),'worker'],cwd=core.ROOT,stdout=log,stderr=subprocess.STDOUT,
                         env={**os.environ,'AFILIADOS_DATA':str(core.DATA),'PYTHONUTF8':'1'},creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def run_worker():
    import cartoon2d
    init();directory=core.DATA/'cartoon-month'/'worker'
    with InstanceLock(directory):
        with core.db() as c:c.execute("UPDATE cartoon_slots SET status='queued' WHERE status='rendering'")
        while True:
            with core.db() as c:
                c.execute('BEGIN IMMEDIATE')
                row=c.execute("SELECT s.* FROM cartoon_slots s JOIN cartoon_months p ON p.id=s.plan_id WHERE p.production_enabled=1 AND p.paused=0 AND s.status='queued' ORDER BY s.due_at LIMIT 1").fetchone()
                if not row:break
                job=dict(row)
                if shutil.disk_usage(core.DATA).free<350*1024**2:
                    c.execute("UPDATE cartoon_slots SET error='Aguardando pelo menos 350 MB livres.' WHERE id=?",(job['id'],));break
                # Recover the exact completed master after a process interruption.
                try:_source(job)
                except (OSError,ValueError,KeyError,TypeError):pass
                else:
                    c.execute("UPDATE cartoon_slots SET status='ready',error='',updated_at=? WHERE id=?",(core.stamp(),job['id']));continue
                if job['attempts']>=2+job['reviewed_retry']:
                    c.execute("UPDATE cartoon_slots SET status='error',error='Limite de tentativas locais atingido; confira o registro.',updated_at=? WHERE id=?",(core.stamp(),job['id']))
                    c.execute('UPDATE cartoon_months SET production_enabled=0 WHERE id=?',(job['plan_id'],));break
                c.execute("UPDATE cartoon_slots SET status='rendering',attempts=attempts+1,error='',updated_at=? WHERE id=?",(core.stamp(),job['id']))
            try:
                story=json.loads(job['story']);project=core.DATA/'cartoon-month'/'projects'/job['id'];project.mkdir(parents=True,exist_ok=True)
                (project/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2),encoding='utf-8')
                for name in ('cartoon2d.py','cartoon_worlds.py','cartoon_catalog.py'):(project/name).write_bytes((core.ROOT/name).read_bytes())
                cartoon2d.render_story(story,job['media_id'],project,resume_incomplete=True)
                _source(job)
                with core.db() as c:c.execute("UPDATE cartoon_slots SET status='ready',error='',updated_at=? WHERE id=?",(core.stamp(),job['id']))
                export_calendar()
                # Only these newly generated intermediates are disposable; masters,
                # source projects, subtitles and all previous episodes are kept.
                root=(core.DATA/'stories'/job['media_id']).resolve()
                if root.parent==(core.DATA/'stories').resolve():
                    for path in root.iterdir():
                        if path.is_symlink() or path.resolve().parent!=root:continue
                        if path.name in ('narration.wav','soundtrack.wav') or re.fullmatch(r'(speech-\d+\.(wav|json)|timing-\d+\.json)',path.name):path.unlink()
            except Exception:
                import traceback
                traceback.print_exc()
                with core.db() as c:
                    c.execute("UPDATE cartoon_slots SET status='error',error='A produção foi interrompida. Consulte o registro local antes de retomar.',updated_at=? WHERE id=?",(core.stamp(),job['id']))
                    c.execute('UPDATE cartoon_months SET production_enabled=0 WHERE id=?',(job['plan_id'],))
                break


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','state','worker','calendar']);args=parser.parse_args()
    if args.command=='prepare':print(json.dumps(prepare(),ensure_ascii=False))
    elif args.command=='worker':run_worker()
    elif args.command=='calendar':export_calendar()
    else:
        value=state()
        print(json.dumps({k:v for k,v in value.items() if k!='slots'} if value else None,ensure_ascii=False))
