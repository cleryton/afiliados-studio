"""Original silent action samples, kept outside episode and publishing queues."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4
import core

TITLES={'arrival':'A chegada ao apartamento','handoff':'A entrega da chave','reveal':'A revelação do desenho'}


def state():
    from story_library import read_json
    catalog=read_json(core.DATA/'animation-demos'/'catalog.json',65536)
    rows=catalog.get('clips',[]) if catalog else []
    if not isinstance(rows,list):return []
    result=[];seen=set();root=(core.DATA/'stories').resolve()
    for row in rows[:12]:
        if not isinstance(row,dict):continue
        identifier=row.get('id');action=row.get('action')
        if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier) or identifier in seen:continue
        if not isinstance(action,str) or action not in TITLES:continue
        folder=root/identifier
        if folder.is_symlink() or folder.resolve().parent!=root:continue
        meta=read_json(folder/'roteiro.json',8192)
        if not meta or meta.get('animation_type')!='motion_demo_3d' or 'episode' in meta or meta.get('action')!=action:continue
        if any(not (folder/name).is_file() or (folder/name).is_symlink() or (folder/name).resolve().parent!=folder for name in ('video.mp4','poster.png')):continue
        duration=meta.get('duration');fps=meta.get('fps');digest=meta.get('sha256')
        if type(duration) not in (float,int) or not 0<duration<=30:continue
        if type(fps) is not int or not 1<=fps<=60 or not isinstance(digest,str) or not re.fullmatch('[a-f0-9]{64}',digest):continue
        seen.add(identifier)
        result.append({'id':identifier,'title':TITLES[action],'action':action,'duration':duration,'fps':fps,
                       'video_url':f'/stories/{identifier}/video.mp4?v={digest}','poster_url':f'/stories/{identifier}/poster.png'})
    return result


def render():
    """Explicit local command; does not register episodes or send media anywhere."""
    import animation3d
    import imageio_ffmpeg
    package=core.DATA/'animation-demos'/uuid4().hex;package.mkdir(parents=True)
    jobs=[{'action':action,'duration':6,'fps':18,'width':540,'height':960,'samples':12,
           'engine':'BLENDER_EEVEE_NEXT','assets':str(core.ROOT/'assets'/'story-pilot'),
           'output':str(package/action)} for action in TITLES]
    config=package/'render-config.json';config.write_text(json.dumps({'jobs':jobs}),encoding='utf-8')
    print('Rendering three original 3D actions locally.',flush=True)
    with (package/'blender.log').open('wb') as log:
        result=subprocess.run([str(animation3d.find_blender()),'--background','--factory-startup','--python-exit-code','1',
                               '--python',str(core.ROOT/'animation3d_actions.py'),'--',str(config)],
                              stdout=log,stderr=subprocess.STDOUT,timeout=3600,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Blender did not complete the action clips. Check its local log.')
    clips=[];ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    for job in jobs:
        folder=Path(job['output']);frames=sorted(folder.glob('frame-*.png'))
        report=json.loads((folder/'motion-state.json').read_text(encoding='utf-8'))
        if len(frames)!=108 or report['frames']!=108 or report['fps']!=18:raise ValueError('Incomplete action render.')
        identifier=uuid4().hex;destination=core.DATA/'stories'/identifier;destination.mkdir(parents=True)
        video=destination/'video.mp4'
        animation3d.run([ffmpeg,'-y','-v','error','-framerate','18','-start_number','1','-i',folder/'frame-%04d.png',
                         '-vf','hqdn3d=1.5:1.5:3:3','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',
                         '-movflags','+faststart',video])
        # Decode the completed MP4 before advertising it in the gallery.
        animation3d.run([ffmpeg,'-v','error','-xerror','-i',video,'-f','null','-'])
        shutil.copy2(folder/'frame-0054.png',destination/'poster.png')
        meta={'animation_type':'motion_demo_3d','action':job['action'],'duration':6,'fps':18,'voice':False,
              'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'source':'Original locally modeled Blender characters and scenery.',
              'native_project':str(folder/'scene.blend'),'motion_checks':{k:report[k] for k in (
                  'maximum_hand_target_error','maximum_planted_foot_height_error','maximum_planted_foot_slide_per_frame')}}
        (destination/'roteiro.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        clips.append({'id':identifier,'action':job['action']})
    catalog=core.DATA/'animation-demos'/'catalog.json';temporary=catalog.with_suffix('.tmp')
    temporary.write_text(json.dumps({'clips':clips},indent=2),encoding='utf-8');temporary.replace(catalog)
    print(json.dumps({'ready':state()},ensure_ascii=False),flush=True)
    return clips


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Create three silent 3D motion demonstrations locally. No publishing.')
    parser.add_argument('command',choices=['render','state']);args=parser.parse_args()
    if args.command=='render':render()
    else:print(json.dumps(state(),ensure_ascii=False))
