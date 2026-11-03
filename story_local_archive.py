"""Owner-requested recycling of confirmed local masters; never alter TikTok."""
import argparse
import json
import os
import re
import subprocess
from uuid import uuid4

import core


def archived(identifier):
    import story_library as library
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):return False
    root=(core.DATA/'stories').resolve();folder=root/identifier
    if folder.is_symlink() or folder.resolve().parent!=root or (folder/'video.mp4').exists():return False
    marker=library.read_json(folder/'mp4-retirado.json',8192)
    meta=library.read_json(folder/'roteiro.json');receipt=library.receipt(identifier)
    return bool(marker and meta and receipt and marker.get('media_id')==identifier and
                marker.get('status') in ('recycle_requested','recycled') and
                marker.get('source_sha256')==meta.get('sha256') and marker.get('url')==receipt['url'])


def plan(handle='novelitas0213'):
    import story_delivery as delivery
    import story_library as library
    if handle!='novelitas0213' or delivery.target()!=handle:raise ValueError('Perfil fora do escopo autorizado.')
    with core.db() as c:
        ids={r['media_id'] for r in c.execute('SELECT s.media_id FROM story_week_slots s JOIN story_weeks w ON w.id=s.week_id WHERE w.handle=? AND w.id=(SELECT id FROM story_weeks WHERE handle=? ORDER BY created_at DESC LIMIT 1)',(handle,handle))}
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='cartoon_slots'").fetchone():
            ids.update(r['media_id'] for r in c.execute('SELECT s.media_id FROM cartoon_slots s JOIN cartoon_months m ON m.id=s.plan_id WHERE m.handle=? AND m.id=(SELECT id FROM cartoon_months WHERE handle=? ORDER BY created_at DESC LIMIT 1)',(handle,handle)))
        active={r['media_id'] for r in c.execute("SELECT media_id FROM story_native_attempts WHERE stage!='confirmed'")}
        active.update(r['media_id'] for r in c.execute("SELECT media_id FROM story_publications WHERE status NOT IN ('published','cancelled')"))
    root=(core.DATA/'stories').resolve();items=[]
    for identifier in sorted(ids-active):
        if not re.fullmatch('[a-f0-9]{32}',identifier):continue
        folder=root/identifier;path=folder/'video.mp4';receipt=library.receipt(identifier)
        if not receipt or receipt['handle']!=handle or receipt['status']!='scheduled_confirmed' or not path.exists():continue
        if folder.is_symlink() or folder.resolve().parent!=root or path.is_symlink() or path.resolve().parent!=folder or not path.is_file():
            raise ValueError('Caminho fora da pasta original; limpeza interrompida.')
        meta=library.read_json(folder/'roteiro.json')
        raw=library.read_json(folder/'agendamento-tiktok.json',65536)
        digest=delivery.file_hash(path)
        if not meta or not raw or digest!=meta.get('sha256') or digest!=raw.get('source_sha256'):
            raise ValueError('Vídeo ou recibo alterado; limpeza interrompida antes de remover arquivos.')
        items.append({'media_id':identifier,'path':str(path),'source_sha256':digest,'bytes':path.stat().st_size,
                      'url':receipt['url'],'scheduled_for':receipt['scheduled_for']})
    return {'handle':handle,'files':items,'count':len(items),'bytes':sum(i['bytes'] for i in items)}


def _recycle(path):
    if os.name!='nt':raise ValueError('Esta operação usa somente a Lixeira do Windows.')
    script="""$ErrorActionPreference='Stop'
[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName Microsoft.VisualBasic
$archivePath=[Console]::In.ReadToEnd().Trim()
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($archivePath,[Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs,[Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin,[Microsoft.VisualBasic.FileIO.UICancelOption]::ThrowException)
"""
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],input=str(path),
                   text=True,encoding='utf-8',errors='replace',capture_output=True,check=True,timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def execute(*,recycle=None):
    import story_delivery as delivery
    from instance_lock import InstanceLock
    if core.TESTER:raise ValueError('O modo tester bloqueia a limpeza real.')
    trash=recycle or _recycle
    directory=core.DATA/'story-local-archive'
    with InstanceLock(directory):
        value=plan();value.update(id=uuid4().hex,requested_at=core.stamp(),recycled=0)
        report=directory/(value['id']+'.json')
        report.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        for item in value['files']:
            # Revalidate the entire eligibility set and the exact master before every move.
            current={r['media_id']:r for r in plan()['files']}
            if current.get(item['media_id'])!=item:raise ValueError('A fila ou um arquivo mudou; limpeza interrompida.')
            path=core.DATA/'stories'/item['media_id']/'video.mp4'
            if delivery.file_hash(path)!=item['source_sha256']:raise ValueError('Arquivo alterado antes da retirada.')
            marker=path.parent/'mp4-retirado.json'
            record={**item,'status':'recycle_requested','requested_at':core.stamp()}
            marker.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            trash(path)
            if path.exists():raise ValueError('A Lixeira não confirmou a retirada; nenhum outro arquivo será removido.')
            record.update(status='recycled',recycled_at=core.stamp())
            marker.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
            value['recycled']+=1
            report.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        return {'recycled':value['recycled'],'bytes':value['bytes'],'report':str(report)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    print(json.dumps(execute() if args.execute else plan(),ensure_ascii=False))
