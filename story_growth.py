"""Original editorial experiments and owner-entered TikTok measurements."""
from datetime import datetime
import json
import math
import re
from urllib.parse import urlsplit
from uuid import uuid4
import core


# Hypotheses for this finite story, never presented as proven winning hooks.
EPISODES = {
    2: {
        'title': 'A filha na fotografia',
        'hook': 'Duas filhas. A mesma carta. Quem escondeu Eva?',
        'question': 'A mãe tentou contar a verdade ou esperou tempo demais?',
        'scenes': [
            {'visual': 'letter', 'text': 'Duas filhas. A mesma carta. Quem escondeu Eva?'},
            {'visual': 'photo', 'text': 'Lia reconheceu a mãe na foto. Eva era a irmã que ninguém mencionava.'},
            {'visual': 'room', 'text': 'Não quero a herança, disse Eva. Quero saber por que fui escondida.'},
            {'visual': 'building', 'text': 'O porteiro trouxe uma caixa. Lá dentro, cartas para Eva. Todas devolvidas.'},
            {'visual': 'letter', 'text': 'No primeiro envelope, Lia reconheceu a letra da avó.'},
            {'visual': 'letter', 'text': 'Não procure mais essa criança. Quem impediu o reencontro? A resposta está no capítulo três.'},
        ],
    },
    3: {
        'title': 'O que a caixa guardava',
        'hook': 'A avó devolveu as cartas. A mãe guardou o silêncio.',
        'question': 'Você voltaria ao apartamento no sábado?',
        'scenes': [
            {'visual': 'letter', 'text': 'A avó devolveu as cartas. A mãe guardou o silêncio.'},
            {'visual': 'room', 'text': 'Na última carta, a mãe escreveu: tive medo. Depois, vergonha.'},
            {'visual': 'photo', 'text': 'Eva chorou. Trinta e cinco anos não cabiam numa explicação.'},
            {'visual': 'door', 'text': 'Posso voltar no sábado? Lia perguntou. Eva respondeu: só não traga respostas prontas.'},
            {'visual': 'room', 'text': 'No sábado, fizeram café. Pela primeira vez, conversaram como irmãs.'},
            {'visual': 'key', 'text': 'Eva devolveu a chave. Fica com ela. Agora você sabe qual porta pode abrir. Fim.'},
        ],
    },
}

COUNTS = ('views', 'likes', 'comments', 'shares', 'followers')
DECIMALS = ('duration', 'average_watch', 'completion')


def init():
    with core.db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS story_growth_observations(
            id TEXT PRIMARY KEY, handle TEXT NOT NULL, url TEXT NOT NULL,
            published_at TEXT NOT NULL, observed_at TEXT NOT NULL, metrics TEXT NOT NULL,
            UNIQUE(handle,url,observed_at))''')


def target():
    with core.db() as c:
        row = c.execute("SELECT value FROM story_settings WHERE key='target_handle'").fetchone()
    return row['value'] if row else ''


def record(payload):
    handle = target()
    if not handle:
        raise ValueError('Indique primeiro o perfil exclusivo do projeto.')
    url = payload.get('url', '')
    if not isinstance(url, str) or len(url) > 200:
        raise ValueError('Informe o link completo do vídeo no perfil do projeto.')
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.netloc != 'www.tiktok.com' or parts.query or parts.fragment or
            not re.fullmatch(r'/@' + re.escape(handle) + r'/video/[0-9]{15,24}', parts.path, re.I)):
        raise ValueError('Use um link https://www.tiktok.com/@seu_perfil/video/ID, do perfil indicado.')
    try:
        published = datetime.fromisoformat(payload['published_at'])
        if published.tzinfo is None or published > core.now():
            raise ValueError()
    except (KeyError, ValueError, TypeError):
        raise ValueError('Informe a data real de uma publicação já realizada, com fuso horário.') from None
    metrics = {}
    for key in COUNTS + DECIMALS:
        value = payload.get(key)
        if value is None or value == '':
            metrics[key] = None
            continue
        if isinstance(value, bool):
            raise ValueError('Use números válidos nas métricas; deixe em branco o que não aparece no TikTok.')
        if key in COUNTS:
            if not re.fullmatch(r'[0-9]{1,12}', str(value)):
                raise ValueError('As contagens devem ser números inteiros a partir de zero.')
            metrics[key] = int(value)
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError('Use valores numéricos nas durações e porcentagens.') from None
            limit = 100 if key == 'completion' else 86400
            if not math.isfinite(number) or not 0 <= number <= limit or (key == 'duration' and number == 0):
                raise ValueError('Confira a duração e os valores das métricas.')
            metrics[key] = number
    if metrics['duration'] is None:
        raise ValueError('Informe a duração real do vídeo em segundos.')
    if all(metrics[k] is None for k in COUNTS + ('average_watch', 'completion')):
        raise ValueError('Registre pelo menos uma métrica que já aparece no TikTok.')
    identifier = uuid4().hex
    with core.db() as c:
        c.execute('INSERT INTO story_growth_observations VALUES (?,?,?,?,?,?)',
                  (identifier, handle, url, published.isoformat(), core.stamp(), json.dumps(metrics)))
    return {'ok': True, 'id': identifier}


def editorial(number, offer=None):
    import story_offers
    episode = EPISODES[number]
    caption = (f"{episode['hook']}\nA chave do 12 · Capítulo {number}: {episode['title']}.\n"
               'Ficção original em animação 3D, com fotografia de IA e narração sintética.\n' +
               ('Desfecho no capítulo 3.\n' if number == 2 else 'Final da minissérie.\n') +
               episode['question'] + '\n#historias #animacao3d #suspense #conteudogeradoporia' + story_offers.caption(offer))
    return {'number': number, **episode, 'caption': caption, 'status': 'hypothesis'}


def state(offer=None):
    handle = target()
    with core.db() as c:
        rows = [dict(r) for r in c.execute('SELECT * FROM story_growth_observations WHERE handle=? ORDER BY observed_at DESC LIMIT 200', (handle,))]
    latest = {}
    for row in rows:
        if row['url'] in latest:
            continue
        metrics = json.loads(row.pop('metrics'))
        row.update(metrics)
        views = metrics['views']
        row['interaction_rate'] = (round(100 * sum(metrics[k] for k in ('likes', 'comments', 'shares')) / views, 2)
                                   if views and all(metrics[k] is not None for k in ('likes', 'comments', 'shares')) else None)
        row['watch_ratio'] = round(100 * metrics['average_watch'] / metrics['duration'], 1) if metrics['average_watch'] is not None else None
        row['source'] = 'Registro local do TikTok Studio; sem sincronização automática.'
        latest[row['url']] = row
    posts = list(latest.values())
    measured = [p for p in posts if p['views'] and p['average_watch'] is not None]
    import story_director
    return {'posts': posts, 'observations': len(rows), 'director_policy':story_director.policy(posts,core.now()),
            'diagnosis': ('Registre tempo médio e conclusão após 24 h e 72 h para comparar capítulos. '
                          'As diferenças ainda não comprovam que uma abertura ou horário causou mais alcance.' if measured else
                          'Ainda faltam visualizações e tempo assistido para avaliar retenção. Não há abertura vencedora nem melhor horário comprovados.'),
            'experiments': [editorial(n, offer) for n in EPISODES],
            'cadence': 'Teste um capítulo novo por dia, em ordem. Compare após 24 h e 72 h. O horário inicial é uma hipótese.',
            'method': 'Mude uma coisa por vez nos próximos capítulos. Não republique o mesmo capítulo para simular um teste A/B.'}
