"""Edit vertical fiction with short shots, prop animation and local narration."""
import hashlib
import json
import math
import re
import subprocess
import wave
from PIL import Image, ImageDraw
import core
import creative
import story_motion
from renderer import font, wrap

ASSETS={'key':'discovery.png','letter':'sisters.png','building':'corridor.png',
        'door':'corridor.png','portrait':'sisters.png','photo':'sisters.png','room':'sisters.png','drawing':'sisters.png'}


def asset_path(name):
    if name not in set(ASSETS.values()):raise ValueError('Imagem de cena inválida.')
    local=core.DATA/'story-assets'/name
    return local if local.is_file() else core.ROOT/'assets'/'story-pilot'/name


def asset_for(episode,index,scene):
    if scene['visual']=='offer':return None
    name='discovery.png' if episode['number']==1 and index<2 else ASSETS[scene['visual']]
    path=asset_path(name)
    if not path.is_file():
        raise ValueError('Adicione as imagens do piloto em data/story-assets antes de gerar.')
    return path


def overlay(episode,text,path,commercial=False):
    canvas=Image.new('RGBA',(720,1280),(0,0,0,0));draw=ImageDraw.Draw(canvas)
    draw.rounded_rectangle((30,72,610,164),radius=18,fill=(10,15,20,200))
    draw.text((48,85),f"A CHAVE DO 12 · EP. {episode['number']}",font=font(25,True),fill='#f2d9a8')
    label='PUBLICIDADE · OFERTA DE AFILIADO' if commercial else 'FICÇÃO · IA · CONTÉM PUBLICIDADE' if episode.get('offer') else 'FICÇÃO · IMAGENS IA · VOZ SINTÉTICA'
    draw.text((48,124),label,font=font(16,True),fill='white')
    if commercial:
        draw.text((52,260),'OFERTA DE AFILIADO',font=font(29,True),fill='#f2d9a8')
        name=(episode.get('offer') or {}).get('name','Produto')
        for i,line in enumerate(wrap(draw,name,font(32,True),530)):
            draw.text((52,320+i*43),line,font=font(32,True),fill='white')
        draw.text((52,570),'Informações do produtor.',font=font(24),fill='#dfdfdf')
        draw.text((52,612),'Sem depoimento dos personagens.',font=font(23),fill='#dfdfdf')
    for size in (36,34,32,30,28,26):
        face=font(size,True);lines=wrap(draw,text,face,532)
        if len(lines)*(size+10)<=194:break
    else:raise ValueError('Trecho de legenda longo demais.')
    height=len(lines)*(size+10)+34;top=1045-height
    draw.rounded_rectangle((34,top,602,1055),radius=17,fill=(6,11,18,225))
    for i,line in enumerate(lines):draw.text((52,top+18+i*(size+10)),line,font=face,fill='white')
    canvas.save(path)


def validate(path,expected_duration):
    import imageio_ffmpeg
    r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(path),'-f','null','-'],
                     capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,
                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    clock=re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)',r.stderr)
    if r.returncode or not clock or not re.search(r'Video:.*?\b720x1280\b',r.stderr) or 'Audio:' not in r.stderr:
        raise ValueError('O episódio não passou na decodificação.')
    duration=int(clock[1])*3600+int(clock[2])*60+float(clock[3])
    if not 0<duration<=180 or abs(duration-expected_duration)>.8:raise ValueError('Duração inesperada.')
    return duration


def render(episode):
    import imageio_ffmpeg
    import story_offers
    offer=episode.get('offer')
    scenes=json.loads(episode['scenes'])+story_offers.scenes(offer,brief=episode.get('offer_style')=='brief');directory=core.DATA/'stories'/episode['id'];directory.mkdir(parents=True,exist_ok=True)
    exe=imageio_ffmpeg.get_ffmpeg_exe();durations=[];voice=[];segments=[]
    run_options={'check':True,'capture_output':True,'timeout':180,'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0)}
    try:
        # Check the entire source set before spending time on narration.
        assets=[asset_for(episode,i,s) for i,s in enumerate(scenes)]
        clips=[story_motion.authorized_clip(episode,i) if s['visual']!='offer' else None for i,s in enumerate(scenes)]
        for index,scene in enumerate(scenes):
            speech=directory/f'speech-{index}.json';audio=directory/f'speech-{index}.wav'
            speech.write_text(json.dumps({'text':scene['text'],'rate':0},ensure_ascii=False),encoding='utf-8')
            voiced=False
            try:
                subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-File',str(core.ROOT/'speech.ps1'),str(speech),str(audio)],**{**run_options,'timeout':60})
                with wave.open(str(audio)) as stream:duration=stream.getnframes()/stream.getframerate()
                if duration<=0:raise ValueError('Áudio vazio.')
                voiced=True
            except (OSError,subprocess.SubprocessError,wave.Error,ValueError):duration=len(scene['text'].split())/2.5
            durations.append(math.ceil(max(4.5,duration+.35)*24)/24);voice.append(voiced)
        if sum(durations)>180:raise ValueError('Episódio longo demais.')
        cards=creative.subtitle_segments([s['text'] for s in scenes],durations)
        backgrounds=[story_motion.render_background(exe,episode,i,s,durations[i],assets[i],directory,clips[i]) for i,s in enumerate(scenes)]
        part=0
        for index,scene in enumerate(scenes):
            scene_cards=[c for c in cards if c['scene']==index];base=scene_cards[0]['start']
            for card in scene_cards:
                commercial=scene['visual']=='offer'
                caption=directory/f'overlay-{part}.png';overlay(episode,card['text'],caption,commercial)
                segment=directory/f'clip-{part}.mp4';length=card['end']-card['start']
                command=[exe,'-y','-hide_banner','-loglevel','error']
                command+=['-ss',f"{max(0,card['start']-base):.6f}",'-i',str(backgrounds[index])]
                command+=['-loop','1','-framerate','24','-i',str(caption)]
                if voice[index]:command+=['-ss',str(max(0,card['start']-base)),'-i',str(directory/f'speech-{index}.wav')]
                else:command+=['-f','lavfi','-i','anullsrc=r=44100:cl=mono']
                # The scene timeline continues across caption cards without resets.
                graph='[0:v][1:v]overlay=0:0,setsar=1,format=yuv420p[v]'
                command+=['-filter_complex',graph,'-map','[v]','-map','2:a','-t',f'{length:.6f}',
                          '-c:v','libx264','-preset','ultrafast','-crf','24','-c:a','aac','-ar','44100','-ac','1','-af','apad','-movflags','+faststart',str(segment)]
                subprocess.run(command,**run_options);segments.append(segment);part+=1
        listing=directory/'segments.txt';listing.write_text('\n'.join(f"file '{p.name}'" for p in segments),encoding='utf-8')
        assembled=directory/'assembled.mp4';building=directory/'building.mp4'
        subprocess.run([exe,'-y','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(listing),'-c','copy',str(assembled)],**run_options)
        sound=directory/'ambience.wav';story_motion.sound_design(sound,scenes,durations)
        subprocess.run([exe,'-y','-hide_banner','-loglevel','error','-i',str(assembled),'-i',str(sound),
            '-filter_complex','[0:a]loudnorm=I=-18:TP=-2:LRA=11[voice];[voice][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0[a]',
            '-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-ar','44100','-ac','1','-movflags','+faststart',str(building)],**run_options)
        duration=validate(building,sum(durations))
        building.replace(directory/'video.mp4')
        subprocess.run([exe,'-y','-v','error','-ss','1','-i',str(directory/'video.mp4'),'-frames:v','1',str(directory/'poster.png')],**run_options)
        caption=f"{episode['series_title']} | Episódio {episode['number']} — {episode['title']}\n\nFicção original. Personagens e imagens gerados por IA. Narração sintética."
        caption+='\nFinal da minissérie.' if episode['number']==3 else f"\nContinua no episódio {episode['number']+1}."
        caption+='\n\n#historias #minisserie #ficcao #conteudogeradoporia'
        caption+=story_offers.caption(offer)
        (directory/'legenda.txt').write_text(caption,encoding='utf-8')
        (directory/'legendas.srt').write_text(creative.srt(cards),encoding='utf-8')
        (directory/'roteiro.json').write_text(json.dumps({'title':episode['series_title'],'episode':episode['number'],'scenes':scenes,
            'duration':duration,'voice':all(voice),'ai_images':True,'offer':offer,'offer_style':episode.get('offer_style','full'),'image_generation':'Prepared separately; no automatic image service connected.',
            'subtitle_timing':'estimated_by_text','editing_style':story_motion.STYLE,
            'character_animation':False,'sound_design':'original_local_synthesis',
            'shot_timeline':[{'scene':i,'source':'authorized_video' if clips[i] else 'local_composite',
                'shots':[] if clips[i] else story_motion.shots(s,durations[i]),
                'clip':{k:v for k,v in clips[i].items() if k!='path'} if clips[i] else None} for i,s in enumerate(scenes)],
            'sha256':hashlib.sha256((directory/'video.mp4').read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
        return {'voice':all(voice),'duration':duration,'warning':'' if all(voice) else 'Sem voz pt-BR disponível; episódio com texto. Instale uma voz portuguesa e gere novamente.'}
    finally:
        for pattern in ('speech-*.json','speech-*.wav','clip-*.mp4','overlay-*.png','motion-*.mp4','motion-error.txt','ambience.wav','assembled.mp4','segments.txt','building.mp4'):
            for file in directory.glob(pattern):file.unlink(missing_ok=True)
