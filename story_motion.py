"""Local shot editing, independently animated props and optional authorized footage.

This is compositing, not an image-to-video model or character animation.
"""
from array import array
import hashlib
import json
import math
import random
import subprocess
import sys
import wave
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import core
from renderer import font

FPS = 24
STYLE = 'cinematic-local-v1'
SIZE = (720, 1280)


def clip_shots(scene,duration,episode):
    frames=round(duration*FPS)
    maximum=episode.get('director',{}).get('policy',{}).get('shot_seconds',3.25)
    if type(maximum) not in (float,int) or not 2<=maximum<=4:raise ValueError('Duração de plano inválida.')
    count=max(1,math.ceil(frames/(maximum*FPS)))
    # Centered, small reframings preserve faces/props in this source bank.
    zooms=(1.0,1.16,1.06) if scene['visual'] in ('key','drawing') else (1.0,1.10,1.0)
    return [{'start_frame':round(i*frames/count),'end_frame':round((i+1)*frames/count),
             'mode':'original_3d_reframe','zoom':zooms[i%len(zooms)]} for i in range(count)]


def shots(scene, duration):
    frames = round(duration * FPS)
    count = 1 if scene['visual'] == 'offer' else max(2, math.ceil(frames / (4 * FPS)))
    modes = ('wide', 'insert', 'reaction', 'detail')
    if scene['visual'] == 'building':modes = ('wide', 'reaction', 'detail')
    return [{'start_frame': round(i * frames / count), 'end_frame': round((i + 1) * frames / count),
             'mode': modes[i % len(modes)]} for i in range(count)]


def authorized_clip(episode, index):
    """Only explicitly approved, content-hashed local footage; no remote downloads."""
    directory = core.DATA / 'story-clips'
    manifest = directory / 'manifest.json'
    if not manifest.is_file():return None
    try:
        if manifest.stat().st_size > 65536:raise ValueError('Manifesto de clipes muito grande.')
        entry = json.loads(manifest.read_text(encoding='utf-8')).get(f"{episode['number']}:{index + 1}")
        if entry is None:return None
        name = f"episode-{episode['number']}-scene-{index + 1}.mp4"
        if (entry.get('approved') is not True or entry.get('file') != name or
                not isinstance(entry.get('source'), str) or not entry['source'].strip()):
            raise ValueError('Clipe sem autorização e origem registradas.')
        path = directory / name
        if not path.is_file() or path.resolve().parent != directory.resolve() or path.stat().st_size > 200 * 1024**2:
            raise ValueError('Clipe local ausente ou inválido.')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry.get('sha256'):raise ValueError('Clipe alterado; revise a autorização.')
        return {'path': path, 'sha256': digest, 'source': entry['source'][:500]}
    except (OSError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError('Confira o manifesto dos clipes locais.') from error


def ease(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


class SceneFrames:
    def __init__(self, source, scene, episode, duration):
        self.scene = scene;self.episode = episode;self.timeline = shots(scene, duration)
        self.source = ImageOps.fit(Image.open(source).convert('RGB'), SIZE, method=Image.Resampling.LANCZOS) if source else Image.new('RGB', SIZE, '#142725')
        self.blur = ImageEnhance.Brightness(self.source.filter(ImageFilter.GaussianBlur(22))).enhance(.40)
        self.props = {}
        for key, name in [('key', 'key-prop.png'), ('letter', 'envelope-prop.png'), ('photo', 'photo-prop.png')]:
            path = core.ROOT / 'assets' / 'story-pilot' / name
            with Image.open(path) as image:
                rgba = image.convert('RGBA');box = rgba.getchannel('A').getbbox()
                self.props[key] = rgba.crop(box)
        self.props['key'].thumbnail((260, 580), Image.Resampling.LANCZOS)
        self.props['letter'].thumbnail((570, 570), Image.Resampling.LANCZOS)
        self.props['photo'].thumbnail((570, 430), Image.Resampling.LANCZOS)
        self.paper = Image.new('RGBA', (460, 440), '#e9dcc0')
        draw = ImageDraw.Draw(self.paper)
        if scene['visual'] == 'letter' and episode['number'] == 1:
            draw.text((36, 45), 'Lia,', font=font(34), fill='#4c4235')
            draw.text((36, 120), 'Vá sozinha.', font=font(34), fill='#4c4235')
        else:
            for y in range(125, 365, 36):draw.line((36, y, 390 - (y % 54), y), fill='#ab9c80', width=2)
        self.door = self.source.crop((568, 105, 720, 1170)).resize((510, 1065), Image.Resampling.LANCZOS)

    def camera(self, progress, mode, shot_index):
        # Alternate shot size and viewpoint, while preserving aspect ratio.
        if mode == 'wide':zoom = 1.02 + .09 * ease(progress);focus = (.5, .42)
        elif mode == 'reaction':
            zoom = 1.65 - .10 * ease(progress)
            focus = (.30, .23) if self.scene['visual'] in ('portrait', 'photo', 'room', 'letter') else (.58, .25)
        else:
            zoom = 1.28 + .12 * ease(progress)
            focus = (.72, .25) if self.scene['visual'] in ('portrait', 'photo', 'room') else (.42, .44)
        width, height = 720 / zoom, 1280 / zoom
        x = min(720 - width, max(0, focus[0] * 720 - width / 2 + (progress - .5) * 16 * (-1 if shot_index % 2 else 1)))
        y = min(1280 - height, max(0, focus[1] * 1280 - height / 2))
        return self.source.crop((round(x), round(y), round(x + width), round(y + height))).resize(SIZE, Image.Resampling.BILINEAR)

    def frame(self, number):
        shot_index = next(i for i, s in enumerate(self.timeline) if s['start_frame'] <= number < s['end_frame'])
        shot = self.timeline[shot_index];p = (number - shot['start_frame']) / max(1, shot['end_frame'] - shot['start_frame'] - 1)
        visual = self.scene['visual'];insert = shot['mode'] == 'insert'
        if visual == 'offer':return self.source.copy()
        result = self.camera(p, shot['mode'], shot_index).convert('RGBA')
        if insert and visual in ('key', 'letter', 'door', 'photo', 'portrait'):
            result = self.blur.copy().convert('RGBA')
            if visual == 'key':
                prop = self.props['key'].rotate(12 * math.sin(p * math.pi * 1.2) - 7, resample=Image.Resampling.BICUBIC, expand=True)
                x, y = 360 - prop.width // 2, round(290 + 24 * math.sin(p * math.pi))
                result.alpha_composite(prop, (x, y))
            elif visual == 'letter':
                envelope = self.props['letter'];x = (720 - envelope.width) // 2;y = 430
                result.alpha_composite(envelope, (x, y))
                # Letter moves independently, tucked behind the lower pocket.
                result.alpha_composite(self.paper, (130, round(610 - 310 * ease(p))))
                pocket = envelope.crop((0, round(envelope.height * .48), envelope.width, envelope.height))
                result.alpha_composite(pocket, (x, y + round(envelope.height * .48)))
            elif visual in ('photo', 'portrait'):
                prop = self.props['photo'].rotate(-9 + 15 * ease(p), resample=Image.Resampling.BICUBIC, expand=True)
                result.alpha_composite(prop, ((720 - prop.width) // 2, round(610 - 250 * ease(p))))
            else:
                # A hinged door reveal. This moves the door, never a person's face.
                width = round(510 * (1 - .78 * ease(p)))
                door = self.door.resize((max(1, width), 1065), Image.Resampling.BILINEAR).convert('RGBA')
                result.alpha_composite(door, (650 - width, 105))
        # Fine dust moves independently from the camera; deterministic, no flashes.
        draw = ImageDraw.Draw(result, 'RGBA');time = number / FPS
        for i in range(16):
            x = (i * 137 + time * (3 + i % 4)) % 720;y = (i * 181 - time * (5 + i % 3)) % 1280
            draw.ellipse((x, y, x + 2, y + 2), fill=(255, 221, 169, 34))
        # Short fade only on scene entry/exit, never on every subtitle change.
        total = self.timeline[-1]['end_frame'];level = min(1, (number + 1) / 5, (total - number) / 5)
        return ImageEnhance.Brightness(result.convert('RGB')).enhance(level)


def render_background(exe, episode, index, scene, duration, source, directory, clip=None):
    output = directory / f'motion-{index}.mp4'
    options = {'check': True, 'capture_output': True, 'timeout': 180,
               'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)}
    command = [exe, '-y', '-hide_banner', '-loglevel', 'error']
    encoding = ['-t', str(duration), '-an', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '20', '-pix_fmt', 'yuv420p', str(output)]
    if clip:
        # Loop short footage instead of freezing its final frame. Original sound
        # is omitted: the story retains local narration and original effects.
        if episode.get('director'):
            timeline=clip_shots(scene,duration,episode)
            # Cut between bounded crops of the actual 3D footage. Source motion
            # continues across cuts and caption changes; no still-frame inserts.
            zoom='1'
            for shot in reversed(timeline):
                zoom=f"if(between(on,{shot['start_frame']},{shot['end_frame']-1}),{shot['zoom']},{zoom})"
            graph=("scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24,"
                   f"zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=720x1280:fps=24,setsar=1")
            subprocess.run(command+['-stream_loop','-1','-i',str(clip['path']),'-vf',graph]+encoding,**options)
        else:
            subprocess.run(command + ['-stream_loop', '-1', '-i', str(clip['path']), '-vf',
                'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24'] + encoding, **options)
    else:
        painter = SceneFrames(source, scene, episode, duration)
        command += ['-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', '720x1280', '-framerate', '24', '-i', 'pipe:0'] + encoding
        # Stderr goes to a file to avoid filling a pipe while frames stream.
        with (directory / 'motion-error.txt').open('wb') as errors:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                for number in range(round(duration * FPS)):process.stdin.write(painter.frame(number).tobytes())
                process.stdin.close()
                if process.wait(timeout=180):raise ValueError('Falha na montagem das cenas em movimento.')
            finally:
                if process.poll() is None:process.kill();process.wait(timeout=10)
    return output


def sound_design(path, scenes, durations):
    """Quiet, synthesized original ambience and prop cues. No downloaded music."""
    rate = 22050;events = [];base = 0
    for scene, duration in zip(scenes, durations):
        if scene['visual'] != 'offer':
            for shot in shots(scene, duration):
                if shot['mode'] == 'insert':events.append((base + shot['start_frame'] / FPS, scene['visual']))
        base += duration
    rng = random.Random(12);samples = array('h');cursor = 0;active = []
    for n in range(round(base * rate)):
        time = n / rate
        while cursor < len(events) and events[cursor][0] <= time:active.append(events[cursor]);cursor += 1
        active = [e for e in active if time - e[0] < .8]
        # Barely audible room tone, faded globally. End cards have no cue events.
        value = .0018 * math.sin(2 * math.pi * 83 * time)
        for start, kind in active:
            t = time - start
            if kind == 'key':value += .035 * math.exp(-t * 14) * (math.sin(2 * math.pi * 1800 * t) + .4 * math.sin(2 * math.pi * 2710 * t))
            elif kind == 'letter':value += .014 * rng.uniform(-1, 1) * math.exp(-t * 5)
            elif kind in ('door', 'building'):value += .055 * math.exp(-t * 25) * math.sin(2 * math.pi * 140 * t)
        value *= min(1, time / .4, max(0, (base - time) / .5))
        samples.append(round(max(-.1, min(.1, value)) * 32767))
    if sys.byteorder != 'little':samples.byteswap()
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(samples.tobytes())
