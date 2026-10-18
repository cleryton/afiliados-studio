"""Vertical video with extractive product facts, motion, speech and subtitles."""
import json
import math
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import core

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


def text_block(draw, value, top, max_height, color='#f6f7f8', maximum=52):
    for size in range(maximum, 19, -2):
        face = font(size, True)
        lines = wrap(draw, value, face, 570)
        line_height = size + 13
        if len(lines) * line_height <= max_height:
            break
    if len(lines) * line_height > max_height:
        raise ValueError('Uma cena contém texto demais. Reduza o roteiro para caber no vídeo.')
    for index, line in enumerate(lines):
        draw.text((70, top + index * line_height), line, font=face, fill=color)


def frame(product, text, index, destination, total=4, palette=0):
    themes=[('#121d22','#1c2d34','#a7dfc6','#36564d'),('#282019','#3a2d24','#f2d3a2','#66533b'),('#142330','#203448','#b5dcef','#34566d')]
    background,panel,accent,shape=themes[palette%len(themes)]
    canvas = Image.new('RGB', (W, H), background)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((46, 76, 674, 1140), radius=35, fill=panel)
    heading='ANTES DE ESCOLHER' if index==0 else ('O PRODUTO' if index==1 else ('SAIBA MAIS' if index==total-1 else f'DETALHE {index-1:02d}'))
    draw.text((72, 110),heading, font=font(22, True), fill=accent)
    draw.text((575,110),f'{index+1:02d}/{total:02d}',font=font(19),fill=accent)
    image_path = core.DATA / 'media' / product['image'] if product['image'] else None
    if image_path and image_path.exists():
        with Image.open(image_path) as original:
            image = ImageOps.contain(original.convert('RGB'), (570, 470))
            canvas.paste(image, ((W - image.width) // 2, 180 + (470 - image.height) // 2))
        top, height = 695, 350
    else:
        draw.ellipse((480, 195, 630, 345), fill=shape)
        draw.rounded_rectangle((80, 250, 180, 350), radius=24, fill=accent)
        draw.text((107, 260), '↗', font=font(54), fill='#182a26')
        top, height = 440, 590
    text_block(draw, text, top, height, maximum=56 if len(text) < 100 else 40)
    bar_width=576/total
    for step in range(total):
        draw.rounded_rectangle((72 + step * bar_width,1094,72+(step+1)*bar_width-13,1099),radius=2,fill=accent if step<=index else shape)
    # No affiliate URL is burned into the video. Link placement depends on the account.
    canvas.save(destination)


def landscape_frame(product,text,index,destination,total=4,palette=0):
    themes=[('#121d22','#1c2d34','#a7dfc6'),('#282019','#3a2d24','#f2d3a2'),('#142330','#203448','#b5dcef')]
    background,panel,accent=themes[palette%3]
    canvas=Image.new('RGB',(1280,720),background);draw=ImageDraw.Draw(canvas)
    draw.rounded_rectangle((35,35,1245,685),radius=28,fill=panel)
    draw.text((70,65),'PUBLICIDADE · CONHEÇA O PRODUTO',font=font(19,True),fill=accent)
    draw.text((1110,65),f'{index+1:02d}/{total:02d}',font=font(20),fill=accent)
    text_block(draw,text,180,380,maximum=48)
    image_path=core.DATA/'media'/product['image'] if product['image'] else None
    if image_path and image_path.is_file():
        with Image.open(image_path) as original:
            picture=ImageOps.contain(original.convert('RGB'),(465,420))
            canvas.paste(picture,(735+(465-picture.width)//2,155+(420-picture.height)//2))
    else:
        draw.rounded_rectangle((770,205,1160,490),radius=30,fill=background)
        draw.text((898,260),'↗',font=font(100),fill=accent)
        draw.text((805,510),'DETALHES NA DESCRIÇÃO',font=font(20,True),fill=accent)
    for step in range(total):
        left=70+step*1140/total
        draw.rounded_rectangle((left,635,left+1140/total-10,640),radius=2,fill=accent if step<=index else background)
    canvas.save(destination)


def render(job, product):
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
        (landscape_frame if landscape else frame)(product, scene, index, image_path,len(scenes),metadata.get('palette',0))
        speech_input = directory / f'speech-{index}.json'
        speech_output = directory / f'speech-{index}.wav'
        speech_input.write_text(json.dumps({'text': scene}, ensure_ascii=False), encoding='utf-8')
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
    for index, duration in enumerate(durations):
        segment = directory / f'clip-{index}.mp4'
        command = [exe, '-y', '-hide_banner', '-loglevel', 'error', '-loop', '1', '-framerate', '24', '-i', str(directory / f'scene-{index}.png')]
        if voices[index]:
            command += ['-i', str(directory / f'speech-{index}.wav')]
        else:
            command += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono']
        motion="zoompan=z='min(max(zoom,pzoom)+0.00012,1.025)':d=1:s="+dimensions+":fps=24,fade=t=in:d=0.18"
        command += ['-t', f'{duration:.3f}', '-vf',motion,'-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100', '-ac', '1', '-af', 'apad', '-movflags', '+faststart', str(segment)]
        subprocess.run(command, check=True, timeout=180, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        segments.append(segment)
    concat = directory / 'segments.txt'
    concat.write_text('\n'.join(f"file 'clip-{i}.mp4'" for i in range(len(scenes))), encoding='utf-8')
    temporary = directory / 'building.mp4'
    subprocess.run([exe, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '1', '-i', str(concat), '-c', 'copy', '-movflags', '+faststart', str(temporary)], check=True, timeout=90, capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    temporary.replace(directory / 'video.mp4')
    (directory / 'legenda.txt').write_text(job['caption'], encoding='utf-8')
    def timestamp(seconds):
        value=round(seconds*1000);hours,remaining=divmod(value,3600000);minutes,remaining=divmod(remaining,60000);seconds,milliseconds=divmod(remaining,1000)
        return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'
    subtitles=[];elapsed=0
    for index,(scene,duration) in enumerate(zip(scenes,durations)):
        subtitles.append(f'{index+1}\n{timestamp(elapsed)} --> {timestamp(elapsed+duration)}\n{scene}\n');elapsed+=duration
    (directory/'legendas.srt').write_text('\n'.join(subtitles),encoding='utf-8')
    (directory/'conteudo.json').write_text(json.dumps({**metadata,'scenes':scenes,'caption':job['caption'],'durations':durations,'voice':all(voices)},ensure_ascii=False,indent=2),encoding='utf-8')
    import quality
    quality.validate_media(job['id'])
    for index in range(len(scenes)):
        for name in (f'speech-{index}.json', f'speech-{index}.wav', f'clip-{index}.mp4'):
            (directory / name).unlink(missing_ok=True)
    concat.unlink(missing_ok=True)
    return all(voices), warnings[0] if warnings else ''
