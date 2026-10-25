"""Render an original 3D pilot locally with an explicitly selected Blender binary."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4
import wave
import core
import story_renderer

PILOT_3D = [
    {'visual':'key','text':'Lia encontrou uma chave entre as coisas da mãe. Na etiqueta, apenas um número: doze.'},
    {'visual':'letter','text':'Uma carta dizia: vá sozinha. Lia decidiu seguir o endereço.'},
    {'visual':'building','text':'No prédio, o porteiro reconheceu a chave. Você demorou, disse ele.'},
    {'visual':'door','text':'Lia tocou a porta do apartamento doze. Alguém se moveu lá dentro.'},
    {'visual':'portrait','text':'Uma mulher abriu. Nas mãos, uma fotografia da mãe de Lia com um bebê.'},
    {'visual':'photo','text':'Meu nome é Eva. Esse bebê sou eu. Lia percebeu que tinha uma irmã. Continua.'},
]


def preview_state():
    """Expose only a completed local render; no private paths or tool claims."""
    pointer=core.DATA/'story-3d'/'preview.json'
    try:
        if not pointer.is_file() or pointer.stat().st_size>8192:return None
        preview=json.loads(pointer.read_text(encoding='utf-8'))
        identifier=preview.get('id','')
        if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):return None
        folder=core.DATA/'stories'/identifier
        if preview.get('ready') is not True or not (folder/'video.mp4').is_file():return None
        metadata=folder/'roteiro.json'
        if not metadata.is_file() or metadata.stat().st_size>512*1024:return None
        meta=json.loads(metadata.read_text(encoding='utf-8'))
        if meta.get('animation_type')!='original_procedural_3d' or meta.get('character_animation') is not True:return None
        import story_offers
        if not story_offers.current(meta.get('offer')):return None
        duration=float(meta['duration'])
        if not 0<duration<=180:return None
        return {'id':identifier,'title':'A chave do 12 — piloto em animação 3D','duration':duration,
            'video_url':f"/stories/{identifier}/video.mp4?v={preview.get('sha256','')}",
            'poster_url':f'/stories/{identifier}/poster.png','mouth_alignment':'procedural_not_phoneme_aligned'}
    except (OSError,ValueError,TypeError,AttributeError,KeyError):return None


def find_blender(value=None):
    if value:
        path=Path(value).resolve()
        if not path.is_file():raise ValueError('Executável do Blender não encontrado.')
        return path
    found=shutil.which('blender')
    if found:return Path(found)
    candidates=list((core.ROOT/'artifacts'/'tools'/'blender').glob('blender-*/blender.exe'))
    if candidates:return sorted(candidates)[-1]
    raise ValueError('Instale o Blender oficial e informe seu executável com --blender.')


def run(command, timeout=180):
    return subprocess.run([str(v) for v in command],check=True,capture_output=True,timeout=timeout,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))


def narration(scenes, folder):
    durations=[]
    for index,scene in enumerate(scenes):
        payload=folder/f'narration-{index}.json';audio=folder/f'narration-{index}.wav'
        payload.write_text(json.dumps({'text':scene['text'],'rate':0},ensure_ascii=False),encoding='utf-8')
        run(['powershell.exe','-NoProfile','-NonInteractive','-File',core.ROOT/'speech.ps1',payload,audio],60)
        with wave.open(str(audio)) as stream:duration=stream.getnframes()/stream.getframerate()
        if duration<=0:raise ValueError('Narração vazia.')
        durations.append(math.ceil(max(4.5,duration+.35)*24)/24)
    return durations


def render_pilot(blender=None, offer=None, width=540, height=960, samples=12, engine='BLENDER_EEVEE_NEXT',fps=12):
    import imageio_ffmpeg
    blender=find_blender(blender);identifier=uuid4().hex
    original_data=core.DATA
    package=original_data/'story-3d'/identifier;package.mkdir(parents=True)
    durations=narration(PILOT_3D,package)
    configurations=[]
    for index,(scene,duration) in enumerate(zip(PILOT_3D,durations)):
        configurations.append({'kind':scene['visual'],'episode':1,'duration':duration,'width':width,'height':height,
            'assets':str(core.ROOT/'assets'/'story-pilot'),'output':str(package/f'scene-{index+1}'),'samples':samples,'engine':engine,'fps':fps})
    config=package/'render-config.json';config.write_text(json.dumps({'jobs':configurations},ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'stage':'rendering_3d','id':identifier,'scenes':6,'duration':sum(durations)}),flush=True)
    # Keep native render progress in a private local log. Nothing is uploaded.
    with (package/'blender.log').open('wb') as log:
        result=subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',
            str(core.ROOT/'animation3d_scene.py'),'--',str(config)],stdout=log,stderr=subprocess.STDOUT,timeout=3600,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('A renderização 3D falhou. Confira o registro local do Blender.')
    if offer:
        import story_offers
        if not story_offers.current(offer):raise ValueError('A oferta mudou durante a produção 3D. Revise antes de continuar.')
    workspace=package/'workspace';clips=workspace/'story-clips';clips.mkdir(parents=True)
    manifest={};states=[];exe=imageio_ffmpeg.get_ffmpeg_exe()
    for index,(scene,duration) in enumerate(zip(PILOT_3D,durations)):
        folder=package/f'scene-{index+1}';state=json.loads((folder/'motion-state.json').read_text(encoding='utf-8'));states.append(state)
        frames=list(folder.glob('frame-*.png'))
        if len(frames)!=round(duration*fps) or not (folder/'scene.blend').is_file():raise ValueError('Quadros 3D incompletos.')
        clip=clips/f'episode-1-scene-{index+1}.mp4'
        run([exe,'-y','-v','error','-framerate',fps,'-start_number','1','-i',folder/'frame-%04d.png',
            '-vf','hqdn3d=1.5:1.5:3:3','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',clip])
        manifest[f'1:{index+1}']={'file':clip.name,'approved':True,'source':'Original procedural 3D actors and apartment, modeled and animated locally in Blender.',
            'sha256':hashlib.sha256(clip.read_bytes()).hexdigest()}
        for frame in frames:frame.unlink()
    (clips/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    episode={'id':identifier,'number':1,'title':'A chave que não era de casa — animação 3D',
        'series_title':'A chave do 12 — piloto 3D','scenes':json.dumps(PILOT_3D,ensure_ascii=False),'offer':offer}
    try:
        core.DATA=workspace
        result=story_renderer.render(episode)
    finally:core.DATA=original_data
    source=workspace/'stories'/identifier
    target=original_data/'stories'/identifier;target.mkdir(parents=True)
    for name in ('video.mp4','poster.png','legenda.txt','legendas.srt','roteiro.json'):shutil.copy2(source/name,target/name)
    meta=json.loads((target/'roteiro.json').read_text(encoding='utf-8'))
    meta.update({'animation_type':'original_procedural_3d','character_animation':True,'native_project_format':'Blender',
        'mouth_alignment':'procedural_not_phoneme_aligned','rendered_size':[width,height],'native_animation_fps':fps,
        'motion_states':states,'image_generation':'The only raster AI asset is the fictional photograph held as a prop.'})
    (target/'roteiro.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    caption=(target/'legenda.txt').read_text(encoding='utf-8')
    caption=caption.replace('Personagens e imagens gerados por IA.','Animação 3D original, com personagens modelados e gestos procedurais.')
    (target/'legenda.txt').write_text(caption,encoding='utf-8')
    preview={'id':identifier,'title':'A chave do 12 — piloto em animação 3D','duration':result['duration'],
        'width':720,'height':1280,'native_render_size':[width,height],'character_animation':True,
        'mouth_alignment':'procedural_not_phoneme_aligned','sha256':meta['sha256'],'ready':True}
    if offer:
        import story_offers
        if not story_offers.current(offer):raise ValueError('A oferta perdeu autorização. A prévia anterior foi preservada.')
    pointer=original_data/'story-3d'/'preview.json';temporary=pointer.with_suffix('.new')
    temporary.write_text(json.dumps(preview,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(pointer)
    for file in package.glob('narration-*'):file.unlink()
    print(json.dumps({'stage':'ready',**preview,'video':str(target/'video.mp4'),'projects':str(package)},ensure_ascii=False),flush=True)
    return preview


def main():
    parser=argparse.ArgumentParser(description='Criar piloto original em animação 3D local, sem publicar.')
    parser.add_argument('--blender');parser.add_argument('--with-current-offer',action='store_true')
    parser.add_argument('--width',type=int,default=540);parser.add_argument('--height',type=int,default=960)
    parser.add_argument('--samples',type=int,default=12)
    parser.add_argument('--fps',type=int,choices=(12,24),default=12)
    parser.add_argument('--engine',choices=('BLENDER_EEVEE_NEXT','BLENDER_WORKBENCH'),default='BLENDER_EEVEE_NEXT')
    args=parser.parse_args();offer=None
    if args.with_current_offer:
        import story_offers
        with core.db() as c:row=c.execute('SELECT id FROM story_series ORDER BY created_at LIMIT 1').fetchone()
        if row:offer=story_offers.for_series(row['id'])
        if not offer or not story_offers.current(offer):raise ValueError('Uma oferta ativa e autorizada é necessária.')
    if (not 240<=args.width<=1080 or not 426<=args.height<=1920 or abs(args.width/args.height-9/16)>.005 or not 1<=args.samples<=64):
        raise ValueError('Use resolução vertical 9:16 e entre 1 e 64 amostras.')
    render_pilot(args.blender,offer,args.width,args.height,args.samples,args.engine,args.fps)


if __name__=='__main__':main()
