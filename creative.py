"""Source-based editorial openings and readable, approximately timed subtitles."""
import hashlib
import re
import textwrap
import unicodedata

OPENINGS = {
    'educativo': [
        '{name}: o que observar antes de escolher?',
        'Antes de escolher {name}, quais detalhes conferir?',
        'Como comparar as características de {name}?',
        '{name}: quais especificações merecem atenção?'],
    'direto': [
        'Já conferiu estes detalhes de {name}?',
        '{name}: o que você procura neste produto?',
        'O que verificar antes de escolher {name}?',
        '{name}: estas características fazem sentido para você?'],
    'comparativo': [
        'Na hora de comparar {name}, o que conferir?',
        'Qual detalhe pesa na sua escolha de {name}?',
        '{name}: quais características você precisa comparar?',
        'O que conferir na ficha de {name} antes de decidir?']}
AUDIENCE_OPENINGS = {
    'educativo': ['Para {audience}, o que conferir em {name}?',
                  '{name}: quais detalhes observar pensando em {audience}?',
                  'O que comparar em {name} para {audience}?',
                  'Pensando em {audience}, o que verificar antes de escolher {name}?'],
    'direto': ['Para {audience}: já conferiu estes detalhes de {name}?',
               '{name}: estas características atendem ao que {audience} procura?',
               'Pensando em {audience}, o que você procura em {name}?',
               '{name} para {audience}: quais detalhes conferir?'],
    'comparativo': ['Pensando em {audience}, quais detalhes comparar em {name}?',
                    '{name} para {audience}: o que conferir na ficha?',
                    'Para {audience}, o que pesa na escolha de {name}?',
                    'Quais especificações comparar em {name} para {audience}?']}


def shorten(value, maximum):
    value = ' '.join(value.split()).rstrip('.?!:;')
    if len(value) <= maximum:
        return value
    cut = value.rfind(' ', 0, maximum - 1)
    return value[:cut if cut > maximum // 2 else maximum - 1] + '…'


def opening(product, campaign, variant):
    tone = (campaign or {}).get('tone', 'educativo')
    audience = (campaign or {}).get('audience', '')
    templates = AUDIENCE_OPENINGS[tone] if audience else OPENINGS[tone]
    seed = int(hashlib.sha256(product['name'].encode()).hexdigest()[:8], 16)
    return templates[(seed + variant) % len(templates)].format(
        name=shorten(product['name'], 68), audience=shorten(audience, 65))


def hashtags(product):
    category = unicodedata.normalize('NFKD', product.get('category', ''))
    category = ''.join(c for c in category if not unicodedata.combining(c))
    category = re.sub(r'[^a-zA-Z0-9]', '', category).lower()[:30]
    tags = ['produtosdigitais' if product.get('kind') == 'digital' else 'produtos']
    if category and category not in ('geral', 'publicidade'):
        tags.append(category)
    tags.append('publicidade')
    return ' '.join('#' + tag for tag in dict.fromkeys(tags))


def reading(scenes, pace='normal'):
    speed = 180 if pace == 'agil' else 160
    counts = [len(scene.split()) for scene in scenes]
    return {'words': sum(counts), 'estimated_seconds': round(sum(max(4.5, n * 60 / speed + .6) for n in counts)),
            'pace': pace, 'estimated': True}


def role(index, total, angle='O que observar'):
    if index == 0:
        return angle.upper()
    if index == 1:
        return 'CONHEÇA O PRODUTO'
    if index == total - 1:
        return 'ANTES DE DECIDIR'
    return f'CARACTERÍSTICA {index - 1:02d}'


def subtitle_segments(scenes, durations):
    """Allocate phrase cards by text length, not speech recognition/word alignment."""
    if len(scenes) != len(durations):
        raise ValueError('Durações e cenas não correspondem.')
    result = []
    elapsed = 0
    for index, (scene, duration) in enumerate(zip(scenes, durations)):
        lines = textwrap.wrap(scene, width=42, break_long_words=True, break_on_hyphens=False)
        chunks = ['\n'.join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
        frames = round(duration * 24)
        if not chunks or frames < len(chunks):
            raise ValueError('Cena vazia ou curta demais para as legendas.')
        weights = [len(chunk.replace('\n', ' ')) for chunk in chunks]
        total = sum(weights)
        used = 0
        previous = 0
        for pos, (chunk, weight) in enumerate(zip(chunks, weights)):
            used += weight
            end = frames if pos == len(chunks) - 1 else min(frames - (len(chunks) - pos - 1), max(previous + 1, round(frames * used / total)))
            result.append({'text': chunk, 'start': (elapsed + previous) / 24, 'end': (elapsed + end) / 24, 'scene': index})
            previous = end
        elapsed += frames
    return result


def srt(segments):
    def stamp(seconds):
        value = round(seconds * 1000)
        hours, value = divmod(value, 3600000)
        minutes, value = divmod(value, 60000)
        seconds, milliseconds = divmod(value, 1000)
        return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'
    return '\n'.join(f"{i + 1}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text']}\n" for i, s in enumerate(segments))
