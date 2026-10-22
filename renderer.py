"""Vertical video with extractive product facts, motion, speech and subtitles."""
import json
import math
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import core
import creative

W, H = 720, 1280


def font(size, bold=False):
    candidates = [Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf'), Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def wrap(draw, value, face, width):
    lines = []
    for paragraph in value.splitlines() or ['']:
        current = ''
        for word in paragraph.split():
            # Split long URLs/tokens as well as natural words.
            pieces = []
            token = ''
            for char in word:
                if token and draw.textlength(token + char, font=face) > width:
                    pieces.append(token)
                    token = ''
                token += char
            if token:
                pieces.append(token)
            for piece in pieces:
                if current and draw.textlength(current + ' ' + piece, font=face) > width:
                    lines.append(current)
                    current = piece
                else:
                    current = (current + ' ' + piece).strip()
        lines.append(current)
    return lines


def text_block(draw, value, top, max_height, color='#f6f7f8', maximum=52, width=570, left=70):
    for size in range(maximum, 19, -2):
        face = font(size, True)
        lines = wrap(draw, value, face, width)
        line_height = size + 13
        if len(lines) * line_height <= max_height:
            break
    if len(lines) * line_height > max_height:
        raise ValueError('Uma cena contém texto demais. Reduza o roteiro para caber no vídeo.')
    for index, line in enumerate(lines):
        draw.text((left, top + index * line_height), line, font=face, fill=color)


def frame(product, text, index, destination, total=4, palette=0, angle='O que observar'):
    themes=[('#121d22','#1c2d34','#a7dfc6','#36564d'),('#282019','#3a2d24','#f2d3a2','#66533b'),('#142330','#203448','#b5dcef','#34566d')]
    background,panel,accent,shape=themes[palette%len(themes)]
    canvas = Image.new('RGB', (W, H), background)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((46, 76, 674, 1140), radius=35, fill=panel)
    heading=creative.role(index,total,angle)
    draw.text((72, 110),heading, font=font(21, True), fill=accent)
    draw.text((575,110),f'{index+1:02d}/{total:02d}',font=font(19),fill=accent)
    draw.text((72,151),'PUBLICIDADE · DETALHES DO PRODUTO',font=font(15),fill=accent)
    image_path = core.DATA / 'media' / product['image'] if product['image'] else None
    if image_path and image_path.exists():
        with Image.open(image_path) as original:
            image = ImageOps.contain(original.convert('RGB'), (536, 390))
            draw.rounded_rectangle((72,197,648,635),radius=22,fill='#f4f5f0')
            canvas.paste(image, ((W - image.width) // 2, 215 + (390 - image.height) // 2))
        top, height = 672, 325
    else:
        draw.text((72,220),f'{index+1:02d}',font=font(110,True),fill=shape)
        draw.rounded_rectangle((540,242,622,324),radius=20,fill=accent)
        draw.text((562,249),'↗',font=font(44),fill=background)
        top, height = 385, 610
    text_block(draw, text, top, height, maximum=56 if len(text) < 100 else 40)
    if index==total-1:
        draw.rounded_rectangle((72,1023,648,1073),radius=12,fill=accent)
        draw.text((96,1037),'CONFIRA AS CONDIÇÕES NA LEGENDA',font=font(19,True),fill=background)
    else:
        draw.text((72,1047),'Um detalhe por vez. Confira a ficha completa.',font=font(17),fill=accent)
    bar_width=576/total
    for step in range(total):
        draw.rounded_rectangle((72 + step * bar_width,1094,72+(step+1)*bar_width-13,1099),radius=2,fill=accent if step<=index else shape)
    # No affiliate URL is burned into the video. Link placement depends on the account.
    canvas.save(destination)


def landscape_frame(product,text,index,destination,total=4,palette=0,angle='O que observar'):
    themes=[('#121d22','#1c2d34','#a7dfc6'),('#282019','#3a2d24','#f2d3a2'),('#142330','#203448','#b5dcef')]
    background,panel,accent=themes[palette%3]
    canvas=Image.new('RGB',(1280,720),background);draw=ImageDraw.Draw(canvas)
    draw.rounded_rectangle((35,35,1245,685),radius=28,fill=panel)
    draw.text((70,62),'PUBLICIDADE · DETALHES DO PRODUTO',font=font(16),fill=accent)
    draw.text((70,108),creative.role(index,total,angle),font=font(22,True),fill=accent)
    draw.text((1110,65),f'{index+1:02d}/{total:02d}',font=font(20),fill=accent)
    text_block(draw,text,186,370,maximum=49 if len(text)<130 else 42,width=600)
    image_path=core.DATA/'media'/product['image'] if product['image'] else None
    if image_path and image_path.is_file():
        with Image.open(image_path) as original:
            picture=ImageOps.contain(original.convert('RGB'),(420,390))
            draw.rounded_rectangle((750,147,1205,587),radius=24,fill='#f4f5f0')
            canvas.paste(picture,(768+(420-picture.width)//2,172+(390-picture.height)//2))
    else:
        draw.rounded_rectangle((750,147,1205,587),radius=24,fill=background)
        draw.text((790,200),f'{index+1:02d}',font=font(130,True),fill=accent)
        draw.text((795,381),creative.role(index,total),font=font(17,True),fill=accent)
        text_block(draw,creative.shorten(product['name'],72),430,120,maximum=26,width=350,left=795)
    if index==total-1:
        draw.rounded_rectangle((70,578,670,612),radius=8,fill=accent)
        draw.text((88,585),'CONFIRA AS CONDIÇÕES NA DESCRIÇÃO',font=font(17,True),fill=background)
    for step in range(total):
        left=70+step*1140/total
        draw.rounded_rectangle((left,635,left+1140/total-10,640),radius=2,fill=accent if step<=index else background)
    canvas.save(destination)


def render(job, product):
    try:
        return _render(job,product)
    finally:
        directory=core.DATA/'media'/job['id']
        names=['segments.txt','building.mp4']
        for index in range(7):names.extend([f'speech-{index}.json',f'speech-{index}.wav',f'clip-{index}.mp4',f'cards-{index}.txt'])
        for name in names:
            try:(directory/name).unlink(missing_ok=True)
            except OSError:pass


def _render(job, product):
    import imageio_ffmpeg
    directory = core.DATA / 'media' / job['id']
    directory.mkdir(exist_ok=True)
    scenes = json.loads(job['scenes'])
    with core.db() as c:
        row=c.execute('SELECT payload FROM content_meta WHERE job_id=?',(job['id'],)).fetchone()
    metadata=json.loads(row['payload']) if row else {}
    landscape=metadata.get('format')=='landscape'
    dimensions='1280x720' if landscape else '720x1280'
    durations = []
    voices = []
    warnings = []
    for index, scene in enumerate(scenes):
        image_path = directory / f'scene-{index}.png'
        (landscape_frame if landscape else frame)(product, scene, index, image_path,len(scenes),metadata.get('palette',0),metadata.get('angle','O que observar'))
        speech_input = directory / f'speech-{index}.json'
        speech_output = directory / f'speech-{index}.wav'
        speech_input.write_text(json.dumps({'text': scene,'rate':1 if metadata.get('pace')=='agil' else 0}, ensure_ascii=False), encoding='utf-8')
        voiced = False
        try:
            subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File', str(core.ROOT / 'speech.ps1'), str(speech_input), str(speech_output)], capture_output=True, check=True, timeout=60, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with wave.open(str(speech_output)) as audio:
                duration = audio.getnframes() / audio.getframerate()
            if duration <= 0:
                raise ValueError('Áudio vazio.')
            voiced = True
        except (OSError, subprocess.SubprocessError, wave.Error, ValueError):
            duration = max(4.5, len(scene.split()) / 2.3)
            warnings.append('Sem voz pt-BR disponível: vídeo com texto, sem narração. Instale uma voz portuguesa nas configurações de fala do Windows e gere novamente para narrar.')
        durations.append(math.ceil(max(4.5,duration+.6)*24)/24)
        voices.append(voiced)
    if sum(durations) > 180:
        raise ValueError('O roteiro ficou longo demais. Reduza o texto e gere novamente.')
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    segments = []
    subtitles=creative.subtitle_segments(scenes,durations)
    phrases=metadata.get('presentation','scene')=='phrases'
    for index, duration in enumerate(durations):
        segment = directory / f'clip-{index}.mp4'
        command = [exe, '-y', '-hide_banner', '-loglevel', 'error']
        if phrases:
            cards=[s for s in subtitles if s['scene']==index]
            listing=[]
            for card_index,card in enumerate(cards):
                name=f'card-{index}-{card_index}.png'
                (landscape_frame if landscape else frame)(product,card['text'],index,directory/name,len(scenes),metadata.get('palette',0),metadata.get('angle','O que observar'))
                listing.extend([f"file '{name}'",f"duration {card['end']-card['start']:.9f}"])
            listing.append(f"file 'card-{index}-{len(cards)-1}.png'")
            manifest=directory/f'cards-{index}.txt'
            manifest.write_text('\n'.join(listing)+'\n',encoding='utf-8')
            command += ['-f','concat','-safe','1','-i',str(manifest)]
            # The poster matches the first visible phrase in this scene.
            (directory/f'scene-{index}.png').write_bytes((directory/f'card-{index}-0.png').read_bytes())
        else:
            command += ['-loop', '1', '-framerate', '24', '-i', str(directory / f'scene-{index}.png')]
        if voices[index]:
            command += ['-i', str(directory / f'speech-{index}.wav')]
        else:
            command += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono']
        motion="fps=24,zoompan=z='min(max(zoom,pzoom)+0.00012,1.025)':d=1:s="+dimensions+":fps=24,fade=t=in:d=0.18"
        command += ['-t', f'{duration:.3f}', '-vf',motion,'-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100', '-ac', '1', '-af', 'apad', '-movflags', '+faststart', str(segment)]
        subprocess.run(command, check=True, timeout=180, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        segments.append(segment)
    concat = directory / 'segments.txt'
    concat.write_text('\n'.join(f"file 'clip-{i}.mp4'" for i in range(len(scenes))), encoding='utf-8')
    temporary = directory / 'building.mp4'
    subprocess.run([exe, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '1', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(temporary)], check=True, timeout=90, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    temporary.replace(directory / 'video.mp4')
    (directory / 'legenda.txt').write_text(job['caption'], encoding='utf-8')
    (directory/'legendas.srt').write_text(creative.srt(subtitles),encoding='utf-8')
    (directory/'conteudo.json').write_text(json.dumps({**metadata,'scenes':scenes,'caption':job['caption'],'durations':durations,'voice':all(voices),
        'subtitle_count':len(subtitles),'subtitle_timing':'estimated_by_text','presentation_segments':subtitles if phrases else []},ensure_ascii=False,indent=2),encoding='utf-8')
    import quality
    quality.validate_media(job['id'])
    return all(voices), warnings[0] if warnings else ''
