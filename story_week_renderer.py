"""New weekly stories with verified original 3D motion and fresh narration."""
import hashlib
import json
import shutil
import subprocess
from uuid import uuid4
import core
import animation3d
import story_library
import story_renderer
from story_week_catalog import STORIES,caption


def drawing_clip():
    import imageio_ffmpeg
    base=core.DATA/'story-bank';base.mkdir(exist_ok=True)
    if not base.resolve().is_relative_to(core.DATA.resolve()):raise ValueError('Pasta de cenas fora dos dados locais.')
    pointer=story_library.read_json(base/'drawing.json')
    if pointer and isinstance(pointer.get('id'),str) and story_library.ID.fullmatch(pointer['id']):
        folder=base/pointer['id'];clip=folder/'drawing.mp4'
        if clip.is_file() and not clip.is_symlink() and clip.resolve().is_relative_to(core.DATA.resolve()) and hashlib.sha256(clip.read_bytes()).hexdigest()==pointer.get('sha256'):
            return {'path':clip,'sha256':pointer['sha256'],'kind':'drawing','project':folder.name}
    identifier=uuid4().hex;folder=base/identifier;folder.mkdir()
    config={'kind':'drawing','episode':4,'duration':8,'width':540,'height':960,'samples':12,
            'engine':'BLENDER_EEVEE_NEXT','fps':12,'assets':str(core.ROOT/'assets'/'story-pilot'),'output':str(folder)}
    task=folder/'render.json';task.write_text(json.dumps({'jobs':[config]}),encoding='utf-8')
    with (folder/'blender.log').open('wb') as log:
        subprocess.run([str(animation3d.find_blender()),'--background','--factory-startup','--python-exit-code','1','--python',
                        str(core.ROOT/'animation3d_scene.py'),'--',str(task)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    state=story_library.read_json(folder/'motion-state.json')
    if not state or state['kind']!='drawing' or state['frames']!=96 or not (folder/'scene.blend').is_file():
        raise ValueError('O trecho 3D do desenho não foi concluído.')
    clip=folder/'drawing.mp4'
    animation3d.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-framerate','12','-i',folder/'frame-%04d.png',
                     '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',clip])
    proof={'id':identifier,'sha256':hashlib.sha256(clip.read_bytes()).hexdigest(),'original_procedural_3d':True}
    note=base/'drawing.new';note.write_text(json.dumps(proof),encoding='utf-8');note.replace(base/'drawing.json')
    for image in folder.glob('frame-*.png'):image.unlink()
    return {'path':clip,'sha256':proof['sha256'],'kind':'drawing','project':identifier}


def scene_bank():
    bank={'drawing':drawing_clip()}
    for row in sorted(story_library.entries(),key=lambda r:r['updated'],reverse=True):
        if row['meta'].get('animation_type')!='original_procedural_3d' or row['meta']['episode']>3:continue
        root=core.DATA/'story-3d'/row['id'];config=story_library.read_json(root/'render-config.json')
        manifest=story_library.read_json(root/'workspace'/'story-clips'/'manifest.json')
        if not config or not manifest:continue
        for index,job in enumerate(config['jobs'],1):
            kind=job['kind']
            if kind not in ('room','building','key','door') or kind in bank:continue
            if kind=='building' and job['episode']==1:continue
            native=root/f'scene-{index}'
            motion=story_library.read_json(native/'motion-state.json')
            if (not motion or motion.get('kind')!=kind or motion.get('world_up')!='Z' or
                    motion.get('fps')!=12 or motion.get('frames',0)<2 or not (native/'scene.blend').is_file()):continue
            poses=[[(a['name'],a['head_rotation'],a['upper_arm']) for a in sample.get('actors',[])] for sample in motion.get('samples',[])]
            if len(poses)<2 or all(p==poses[0] for p in poses[1:]):continue
            name=f"episode-{job['episode']}-scene-{index}.mp4"
            clip=root/'workspace'/'story-clips'/name;entry=manifest.get(f"{job['episode']}:{index}",{})
            if (not clip.is_file() or clip.is_symlink() or not clip.resolve().is_relative_to(core.DATA.resolve()) or
                    entry.get('approved') is not True or entry.get('file')!=name or
                    hashlib.sha256(clip.read_bytes()).hexdigest()!=entry.get('sha256')):continue
            bank[kind]={'path':clip,'sha256':entry['sha256'],'kind':kind,'project':row['id']}
    if set(bank)!=set(('drawing','room','building','key','door')):raise ValueError('Faltam cenas 3D originais verificadas para produzir a semana.')
    return bank


def render(number,offer,slot_id,directed=None):
    import story_offers
    if number not in STORIES or not story_offers.current(offer):raise ValueError('Roteiro ou oferta indisponível.')
    if shutil.disk_usage(core.DATA).free<256*1024**2:raise ValueError('Libere pelo menos 256 MB para a próxima montagem.')
    original=core.DATA;identifier=uuid4().hex;story=STORIES[number]
    if number>=9:
        import story_director
        if not directed or not directed.get('report'):raise ValueError('Falta o plano editorial deste episódio.')
        story,report=story_director.plan(STORIES[number],directed['report']['policy'])
        if story!=directed['story'] or report!=directed['report']:raise ValueError('O plano editorial mudou; confira a preparação.')
    bank=scene_bank();workspace=original/'story-week'/'renders'/identifier;clips=workspace/'story-clips';clips.mkdir(parents=True)
    manifest={};sources=[]
    for index,scene in enumerate(story['scenes'],1):
        item=bank[scene['visual']];name=f'episode-{number}-scene-{index}.mp4'
        shutil.copy2(item['path'],clips/name)
        manifest[f'{number}:{index}']={'approved':True,'source':'Original local Blender animation; reused articulated 3D scene with fresh script and narration.',
                                      'sha256':item['sha256'],'file':name}
        sources.append({k:v for k,v in item.items() if k!='path'})
    (clips/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    episode={'id':identifier,'number':number,'title':story['title'],'series_title':story.get('arc','A chave do 12 · O último desenho'),
             'scenes':json.dumps(story['scenes'],ensure_ascii=False),'offer':offer,'offer_style':'brief'}
    if directed:
        episode.update(director=directed['report'],overlay_title='SEGREDOS DO 12',display_number=story['arc_number'])
    try:
        core.DATA=workspace;result=story_renderer.render(episode)
    finally:core.DATA=original
    if not result['voice'] or not story_offers.current(offer):raise ValueError('A geração ficou sem voz ou a oferta mudou.')
    source=workspace/'stories'/identifier;target=original/'stories'/identifier;target.mkdir(parents=True)
    for name in ('video.mp4','poster.png','legenda.txt','legendas.srt','roteiro.json'):shutil.copy2(source/name,target/name)
    meta=json.loads((target/'roteiro.json').read_text(encoding='utf-8'))
    meta.update({'animation_type':'original_procedural_3d','character_animation':True,'week_slot':slot_id,
                 'animation_reuse':True,'native_animation_fps':12,'rendered_size':[540,960],
                 'mouth_alignment':'reused_procedural_gestures_not_speech_aligned','animation_sources':sources,
                 'ai_images':False,'image_generation':'No raster imagery is visible in the reused 3D scenes.'})
    (target/'roteiro.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (target/'legenda.txt').write_text(caption(number,offer,story),encoding='utf-8')
    if not story_offers.current(offer):raise ValueError('A oferta mudou. O arquivo não foi liberado.')
    pointer={'id':identifier,'ready':True,'sha256':meta['sha256']}
    note=original/'story-3d'/'preview.new';note.write_text(json.dumps(pointer),encoding='utf-8');note.replace(original/'story-3d'/'preview.json')
    # Discard only our duplicate render outputs after the complete master exists.
    # Verified Blender source footage and native projects remain in their banks.
    if (workspace.resolve().parent==(original/'story-week'/'renders').resolve() and
            not workspace.is_symlink() and source.resolve().is_relative_to(workspace.resolve())):
        for name in ('video.mp4','poster.png','legenda.txt','legendas.srt'):
            duplicate=source/name
            if (not duplicate.is_symlink() and duplicate.resolve().parent==source.resolve() and
                    hashlib.sha256(duplicate.read_bytes()).hexdigest()==hashlib.sha256((target/name).read_bytes()).hexdigest()):
                duplicate.unlink()
        for index,item in enumerate(sources,1):
            duplicate=clips/f'episode-{number}-scene-{index}.mp4'
            if (not duplicate.is_symlink() and duplicate.resolve().parent==clips.resolve() and
                    hashlib.sha256(duplicate.read_bytes()).hexdigest()==item['sha256']):duplicate.unlink()
    return identifier
