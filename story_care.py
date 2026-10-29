"""Local care for prepared stories. No account login, upload, or publication."""
from datetime import datetime,timedelta
import json
import re
import shutil
import core
import story_delivery
import story_library
from instance_lock import InstanceLock


def init():
    with core.db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS story_week_care(
            week_id TEXT PRIMARY KEY REFERENCES story_weeks(id),checked_at TEXT NOT NULL,
            next_check TEXT NOT NULL,code TEXT NOT NULL,checked INTEGER NOT NULL,
            repaired INTEGER NOT NULL,total_repairs INTEGER NOT NULL,freed_bytes INTEGER NOT NULL,
            repair_failures INTEGER NOT NULL DEFAULT 0)''')
        if 'repair_failures' not in {r['name'] for r in c.execute('PRAGMA table_info(story_week_care)')}:
            c.execute('ALTER TABLE story_week_care ADD COLUMN repair_failures INTEGER NOT NULL DEFAULT 0')


def save(week_id,code,checked=0,repaired=0,freed=0,minutes=15):
    with core.db() as c:
        c.execute('''INSERT INTO story_week_care(week_id,checked_at,next_check,code,checked,repaired,total_repairs,freed_bytes,repair_failures) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(week_id) DO UPDATE SET checked_at=excluded.checked_at,next_check=excluded.next_check,
            code=excluded.code,checked=excluded.checked,repaired=excluded.repaired,
            total_repairs=story_week_care.total_repairs+excluded.repaired,
            freed_bytes=story_week_care.freed_bytes+excluded.freed_bytes,
            repair_failures=CASE WHEN excluded.code IN ('repair_wait','repair_review') THEN story_week_care.repair_failures+1
            WHEN excluded.code='storage' THEN story_week_care.repair_failures ELSE 0 END''',
            (week_id,core.stamp(),(core.now()+timedelta(minutes=minutes)).isoformat(),code,checked,repaired,repaired,freed,
             1 if code in ('repair_wait','repair_review') else 0))


def primary_clip(item):
    """Read already existing source banks only. Maintenance never renders Blender."""
    identifier=item.get('project','');expected=item.get('sha256')
    if not isinstance(identifier,str) or not story_library.ID.fullmatch(identifier):return None
    if item.get('kind')=='drawing':
        candidates=[core.DATA/'story-bank'/identifier/'drawing.mp4']
    else:
        root=core.DATA/'story-3d'/identifier/'workspace'/'story-clips'
        manifest=story_library.read_json(root/'manifest.json') or {}
        candidates=[root/e['file'] for e in manifest.values() if isinstance(e,dict) and e.get('approved') is True and
                    e.get('sha256')==expected and re.fullmatch(r'episode-[1-3]-scene-[1-6]\.mp4',str(e.get('file','')))]
    for p in candidates:
        if not p.is_symlink() and p.is_file() and p.resolve().is_relative_to(core.DATA.resolve()) and story_delivery.file_hash(p)==expected:return p
    return None


def cleanup_copies(slots):
    """Only completed-job duplicates with an identical preserved primary file."""
    removed=0;freed=0
    for slot in slots:
        identifier=slot['media_id']
        if slot['status']!='ready' or not story_library.ID.fullmatch(identifier):continue
        master=core.DATA/'stories'/identifier
        workspace=core.DATA/'story-week'/'renders'/identifier
        if workspace.is_symlink() or not workspace.resolve().is_relative_to(core.DATA.resolve()):continue
        meta=story_library.read_json(master/'roteiro.json')
        if not meta or not (master/'video.mp4').is_file() or (master/'video.mp4').is_symlink():continue
        if story_delivery.file_hash(master/'video.mp4')!=meta.get('sha256'):continue
        pairs=[(workspace/'stories'/identifier/name,master/name) for name in story_delivery.FILES]
        clips=workspace/'story-clips'
        for index,item in enumerate(meta.get('animation_sources',[]),1):
            if not isinstance(item,dict):continue
            primary=primary_clip(item)
            if primary:pairs.append((clips/f"episode-{slot['number']}-scene-{index}.mp4",primary))
        for duplicate,primary in pairs:
            if removed>=20:return freed
            if (duplicate.is_symlink() or not duplicate.is_file() or not duplicate.resolve().is_relative_to(workspace.resolve()) or
                    not primary.is_file() or primary.is_symlink() or not primary.resolve().is_relative_to(core.DATA.resolve())):continue
            if not 0<duplicate.stat().st_size<=128*1024**2 or duplicate.stat().st_size!=primary.stat().st_size:continue
            if story_delivery.file_hash(duplicate)!=story_delivery.file_hash(primary):continue
            size=duplicate.stat().st_size;duplicate.unlink();freed+=size;removed+=1
    return freed


def tick(force=False):
    if core.TESTER:return {'status':'tester'}
    with core.db() as c:
        week=c.execute('SELECT * FROM story_weeks ORDER BY created_at DESC LIMIT 1').fetchone()
        if not week:return {'status':'no_plan'}
        if week['paused']:return {'status':'paused'}
        saved=c.execute('SELECT * FROM story_week_care WHERE week_id=?',(week['id'],)).fetchone()
        if saved and saved['code']=='repair_review' and not force:return {'status':'review'}
        if saved and not force and saved['next_check']>core.stamp():return {'status':'not_due'}
        slots=[dict(r) for r in c.execute('SELECT * FROM story_week_slots WHERE week_id=? ORDER BY due_at',(week['id'],))]
    lock=InstanceLock(core.DATA/'story-week'/'worker')
    try:lock.__enter__()
    except ValueError:
        # An active producer owns this directory. Try again next cycle.
        return {'status':'busy'}
    try:
        if force:
            with core.db() as c:c.execute('UPDATE story_week_care SET repair_failures=0 WHERE week_id=?',(week['id'],))
        audit(week,slots)
        return {'status':'checked'}
    finally:lock.__exit__(None,None,None)


def audit(week,slots):
    import story_offers
    import story_week
    if story_delivery.target()!=week['handle'] or not story_offers.current(json.loads(week['offer'])):
        save(week['id'],'account')
        return
    checked=0;repaired=0;code='ready'
    for slot in slots:
        if slot['status']=='error':code='review';continue
        if slot['status']!='ready':
            if code!='review':code='working'
            continue
        if story_library.receipt(slot['media_id']):continue
        try:
            snapshot=story_delivery.snapshot(slot['media_id'])
        except (ValueError,OSError):
            with core.db() as c:story_week.hold(c,slot,'integrity','Um arquivo, a oferta ou a legenda mudou. Confira antes de liberar o vídeo; ele não será recriado nem enviado sozinho.')
            code='review';continue
        checked+=1
        try:story_delivery.download(slot['media_id'])
        except (ValueError,OSError):
            # A valid master can safely rebuild a delivery ZIP. Re-rendering an
            # episode or changing captions is deliberately outside this repair.
            size=snapshot['stats']['video.mp4'][0]
            if shutil.disk_usage(core.DATA).free<128*1024**2+size:
                save(week['id'],'storage',checked,repaired,minutes=5)
                return
            with core.db() as c:
                if c.execute('SELECT paused FROM story_weeks WHERE id=?',(week['id'],)).fetchone()['paused']:return
            try:story_delivery.prepare(slot['media_id'])
            except (ValueError,OSError):
                with core.db() as c:
                    saved=c.execute('SELECT repair_failures FROM story_week_care WHERE week_id=?',(week['id'],)).fetchone()
                exhausted=saved and saved['repair_failures']>=2
                save(week['id'],'repair_review' if exhausted else 'repair_wait',checked,repaired,minutes=15)
                return
            repaired+=1
    freed=cleanup_copies(slots)
    save(week['id'],code,checked,repaired,freed)


def state():
    import story_offers
    with core.db() as c:
        week=c.execute('SELECT * FROM story_weeks ORDER BY created_at DESC LIMIT 1').fetchone()
        if not week:return None
        saved=c.execute('SELECT * FROM story_week_care WHERE week_id=?',(week['id'],)).fetchone()
        slots=[dict(r) for r in c.execute('SELECT * FROM story_week_slots WHERE week_id=? ORDER BY due_at',(week['id'],))]
    code='paused' if week['paused'] else saved['code'] if saved else 'pending'
    if code!='paused' and (story_delivery.target()!=week['handle'] or not story_offers.current(json.loads(week['offer']))):code='account'
    messages={'ready':'Arquivos conferidos. Novos envios ao TikTok continuam pendentes.',
              'working':'Acompanhando a criação e as esperas automáticas.',
              'review':'Há um item que precisa de revisão. A rotina não irá reenviá-lo ou inventar uma correção.',
              'storage':'Aguardando espaço para reparar o pacote; nova conferência em cinco minutos.',
              'repair_wait':'Não foi possível concluir o reparo local. Aguardando a próxima conferência.',
              'repair_review':'Três reparos do pacote falharam. Confira a causa e use Conferir agora para tentar novamente.',
              'account':'Perfil ou oferta alterados. Confira os dados antes de continuar.',
              'paused':'Cuidado e novas montagens pausados por você. Uma montagem já iniciada pode terminar.',
              'pending':'A primeira conferência automática será feita em breve.'}
    next_slot=next((r for r in slots if not story_library.receipt(r['media_id'])),None)
    if not next_slot and code=='ready':
        messages['ready']='Todos os capítulos têm registro nativo. A publicação efetiva continua dependendo da confirmação no TikTok.'
    next_item=None
    if next_slot:
        from story_week_catalog import STORIES
        next_item={'number':next_slot['number'],'title':STORIES.get(next_slot['number'],{}).get('title','Capítulo'),
                   'due_at':next_slot['due_at'],'status':next_slot['status'],'media_id':next_slot['media_id'],
                   'overdue':datetime.fromisoformat(next_slot['due_at'])<core.now()}
        if code!='account' and next_slot['status']=='ready' and story_library.ID.fullmatch(next_slot['media_id']):
            next_item['video_url']=f"/stories/{next_slot['media_id']}/video.mp4"
            next_item['caption_url']=f"/stories/{next_slot['media_id']}/legenda.txt"
            next_item['package']=story_delivery.info(next_slot['media_id']) if code not in ('repair_wait','repair_review') else None
    return {'code':code,'message':messages[code],'checked_at':saved['checked_at'] if saved else None,
            'next_check':saved['next_check'] if saved else None,'checked_files':saved['checked'] if saved else 0,
            'total_repairs':saved['total_repairs'] if saved else 0,'freed_bytes':saved['freed_bytes'] if saved else 0,
            'next_item':next_item,'posting_automatic':False,'tester':core.TESTER}
