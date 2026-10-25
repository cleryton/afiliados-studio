"""Local storage, product import and observable scheduling. No social posting."""
import base64
from contextlib import contextmanager
import html
import http.client
import io
import ipaddress
import json
import math
import os
from pathlib import Path
import socket
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler, HTTPHandler, HTTPSHandler
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
TESTER = False
DATA = Path(os.environ.get('AFILIADOS_DATA', ROOT / 'data')).resolve()
TZ = timezone(timedelta(hours=-3))


def now():
    return datetime.now(TZ)


def stamp():
    return now().isoformat()


@contextmanager
def db():
    conn = sqlite3.connect(DATA / 'studio.sqlite', timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / 'media').mkdir(exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
            kind TEXT NOT NULL, platform TEXT NOT NULL, category TEXT NOT NULL,
            description TEXT NOT NULL, price REAL, commission REAL,
            image TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id),
            status TEXT NOT NULL, scenes TEXT NOT NULL, caption TEXT NOT NULL,
            due_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            error TEXT NOT NULL DEFAULT '', voice INTEGER NOT NULL DEFAULT 0,
            published_at TEXT, tiktok_url TEXT NOT NULL DEFAULT '',
            views INTEGER NOT NULL DEFAULT 0, clicks INTEGER NOT NULL DEFAULT 0,
            revenue REAL NOT NULL DEFAULT 0, rights INTEGER NOT NULL DEFAULT 0
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_unpublished_per_product
        ON jobs(product_id) WHERE status != 'published';
        CREATE TABLE IF NOT EXISTS content_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS content_meta (job_id TEXT PRIMARY KEY REFERENCES jobs(id), payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS render_state (
            job_id TEXT PRIMARY KEY REFERENCES jobs(id), interrupted INTEGER NOT NULL DEFAULT 0,
            started_at TEXT, block_code TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT ''
        );
        ''')
        columns={r['name'] for r in c.execute('PRAGMA table_info(jobs)')}
        if 'results_recorded_at' not in columns:
            c.execute('ALTER TABLE jobs ADD COLUMN results_recorded_at TEXT')
            has_youtube=c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone()
            has_auto=c.execute("SELECT 1 FROM sqlite_master WHERE name='auto_jobs'").fetchone()
            sources=(['SELECT job_id FROM youtube_jobs'] if has_youtube else [])+(["SELECT job_id FROM auto_jobs WHERE delivery='sent'"] if has_auto else [])
            recorded=" AND (clicks>0 OR revenue>0 OR id NOT IN ("+' UNION '.join(sources)+"))" if sources else ''
            c.execute("UPDATE jobs SET results_recorded_at=updated_at WHERE status='published'"+recorded)
        c.execute("INSERT INTO render_state(job_id,interrupted) SELECT id,1 FROM jobs WHERE status='rendering' ON CONFLICT(job_id) DO UPDATE SET interrupted=1")
        c.execute("UPDATE jobs SET status='error', error='A geração foi interrompida. A rotina pode retomar trabalhos locais autorizados; vídeos manuais exigem sua retomada.', updated_at=? WHERE status='rendering'", (stamp(),))
    import campaigns,quality,stories
    campaigns.init();quality.init();stories.init()


def clean(value, maximum=300, required=False):
    if not isinstance(value, str):
        raise ValueError('Preencha os campos de texto com valores válidos.')
    value = ''.join(ch for ch in value.strip() if ch >= ' ' or ch == '\n')
    if required and not value:
        raise ValueError('Preencha os campos obrigatórios.')
    if len(value) > maximum:
        raise ValueError(f'O texto deve ter até {maximum} caracteres.')
    return value


def numeric(value, maximum, integer=False, optional=False):
    if optional and (value is None or value == ''):
        return None
    if isinstance(value, bool):
        raise ValueError('Número inválido.')
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError('Número inválido.') from None
    if not math.isfinite(number) or number < 0 or number > maximum or (integer and not number.is_integer()):
        raise ValueError('Número fora do intervalo permitido.')
    return int(number) if integer else number


def public_url(value, resolve=False):
    value = clean(value, 3000, True)
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        raise ValueError('Link inválido.') from None
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Informe um link público http ou https, sem usuário e senha.')
    host = parsed.hostname.lower().rstrip('.')
    if host == 'localhost' or '.' not in host or host.endswith(('.local', '.localhost', '.internal')) or port not in (None, 80, 443):
        raise ValueError('Use um endereço público de produto.')
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        addr = None
    if addr and not addr.is_global:
        raise ValueError('Endereços de rede privada não são permitidos.')
    if resolve:
        try:
            addresses = socket.getaddrinfo(host, port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        except socket.gaierror:
            raise ValueError('Não foi possível localizar o site. Preencha o produto manualmente.') from None
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('O site não aponta exclusivamente para endereços públicos.')
    return value


def platform_for(url):
    host = urlparse(url).hostname.lower()
    for domain, label in [('amazon.com.br', 'Amazon'), ('amazon.com', 'Amazon'), ('amzn.to', 'Amazon'), ('mercadolivre.com.br', 'Mercado Livre'), ('mercadolivre.com', 'Mercado Livre'), ('mercadolibre.com', 'Mercado Livre'), ('meli.la', 'Mercado Livre'), ('shopee.com.br', 'Shopee'), ('shope.ee', 'Shopee'), ('hotmart.com', 'Hotmart'), ('kiwify.com.br', 'Kiwify'), ('kiwify.com', 'Kiwify'), ('eduzz.com', 'Eduzz'), ('aliexpress.com', 'AliExpress')]:
        if host == domain or host.endswith('.' + domain):
            return label
    return 'Outra plataforma'


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.in_title = False
        self.title = ''
        self.json_blocks = []
        self.json_buffer = None

    def handle_starttag(self, tag, attrs):
        attrs = {key: value or '' for key, value in attrs}
        if tag == 'script' and attrs.get('type', '').split(';')[0].strip().lower() == 'application/ld+json':
            self.json_buffer = '' if len(self.json_blocks) < 20 else None
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            key = attrs.get('property', attrs.get('name', '')).lower()
            self.meta.setdefault(key, attrs.get('content', ''))

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        if tag == 'script' and self.json_buffer is not None:
            self.json_blocks.append(self.json_buffer)
            self.json_buffer = None

    def handle_data(self, value):
        if self.in_title:
            self.title += value
        if self.json_buffer is not None:
            self.json_buffer = (self.json_buffer + value)[:64_000]


class PublicRedirect(HTTPRedirectHandler):
    max_redirections = 4

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl, resolve=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def public_connection(address, timeout=10, source_address=None):
    """Pin the actual socket to validated addresses to prevent DNS rebinding."""
    host, port = address
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('A conexão foi bloqueada: o site aponta para uma rede privada.')
    last_error = None
    for item in addresses:
        try:
            return socket.create_connection((item[4][0], port), timeout, source_address)
        except OSError as exc:
            last_error = exc
    raise last_error or OSError('Não foi possível conectar.')


class PublicHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = public_connection


class PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = public_connection


class PublicHTTPHandler(HTTPHandler):
    def http_open(self, req):
        return self.do_open(PublicHTTPConnection, req)


class PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PublicHTTPSConnection, req, context=self._context)


def import_product(url):
    url = public_url(url, resolve=True)
    opener = build_opener(ProxyHandler({}), PublicHTTPHandler(), PublicHTTPSHandler(), PublicRedirect())
    req = Request(url, headers={'User-Agent': 'AfiliadosLocalStudio/1.0', 'Accept': 'text/html'})
    try:
        with opener.open(req, timeout=10) as response:
            if response.headers.get_content_type() not in ('text/html', 'application/xhtml+xml'):
                raise ValueError('Esse link não oferece uma página de produto. Preencha os dados manualmente.')
            raw = response.read(750_001)
            if len(raw) > 750_000:
                raw = raw[:750_000]
            content = raw.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
    except (OSError, TimeoutError) as exc:
        raise ValueError('O site bloqueou ou não respondeu à leitura. Seu link foi mantido; preencha os dados manualmente.') from exc
    parser = MetadataParser()
    parser.feed(content)
    import product_source
    structured = product_source.single_product(parser.json_blocks)
    title = structured.get('name') or product_source.text(html.unescape(parser.meta.get('og:title') or parser.title))[:140]
    description = structured.get('description') or product_source.text(html.unescape(parser.meta.get('og:description') or parser.meta.get('description', '')))[:650]
    if not title or any(t in title.lower() for t in ('captcha', 'robot check', 'access denied', 'just a moment')):
        raise ValueError('Não foi possível identificar o produto. Preencha os dados manualmente.')
    source = 'schema.org/Product' if structured else 'metadados HTML'
    return {'name': title, 'description': description, 'platform': platform_for(url), 'source': source,
            'notice': f'Dados públicos sugeridos de {source}. Confira as características antes de salvar. Preço, comissão e autorização dos materiais precisam ser confirmados por você.'}


def save_product(payload):
    name = clean(payload.get('name'), 140, True)
    url = public_url(payload.get('url'))
    kind = payload.get('kind')
    if kind not in ('physical', 'digital'):
        raise ValueError('Escolha produto físico ou digital.')
    description = clean(payload.get('description', ''), 650)
    category = clean(payload.get('category', 'Geral'), 50, True)
    price = numeric(payload.get('price'), 10_000_000, optional=True)
    commission = numeric(payload.get('commission'), 100, optional=True)
    pid = uuid4().hex
    image = ''
    if payload.get('image'):
        from PIL import Image, ImageOps
        try:
            blob = base64.b64decode(payload['image'].split(',', 1)[-1], validate=True)
            if len(blob) > 8_000_000:
                raise ValueError('A imagem deve ter até 8 MB.')
            with Image.open(io.BytesIO(blob)) as original:
                if original.width * original.height > 25_000_000:
                    raise ValueError('A imagem tem resolução muito grande.')
                converted = ImageOps.exif_transpose(original).convert('RGB')
                converted.thumbnail((1600, 1600))
                image = pid + '.jpg'
                converted.save(DATA / 'media' / image, quality=90)
        except (OSError, IndexError, base64.binascii.Error):
            raise ValueError('Use uma imagem JPG, PNG ou WebP válida.') from None
    with db() as c:
        c.execute('INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?)', (pid, name, url, kind, platform_for(url), category, description, price, commission, image, stamp()))
    return pid


def make_script(product):
    subject = 'Uma opção para conhecer'
    detail = product['description'] or 'Confira as características e condições na página do produto antes de escolher.'
    # Only reuse supplied facts; no invented product tests, discounts or outcomes.
    scenes = [subject, product['name'], detail[:400], 'Compare as opções e confira os detalhes antes de comprar.']
    caption = f"{product['name']}\n\n{detail}\n\nPublicidade · Posso receber uma comissão por compras elegíveis.\n\n#achadinhos #produtos #publicidade"
    linked = caption + '\n\nLink do produto: ' + product['url']
    if len(linked) <= 2200:
        caption = linked
    return scenes, caption


def suggestion():
    with db() as c:
        rows = c.execute("SELECT published_at, clicks FROM jobs WHERE status='published' AND results_recorded_at IS NOT NULL").fetchall()
    buckets = {}
    for row in rows:
        hour = datetime.fromisoformat(row['published_at']).astimezone(TZ).hour
        buckets.setdefault(hour, []).append(row['clicks'])
    eligible = {h: values for h, values in buckets.items() if len(values) >= 3}
    if len(eligible) >= 2:
        ranked = sorted(eligible, key=lambda h: (-statistics.median(eligible[h]), h))
        return {'hours': ranked[:3], 'learned': True, 'label': 'Sugestão pelo histórico manual', 'detail': 'Mediana de cliques por horário, com pelo menos 3 registros em cada um de 2 horários. É um indício; produto e público também influenciam.'}
    return {'hours': [12, 18, 20], 'learned': False, 'label': 'Horários para experimentar', 'detail': '12h, 18h e 20h são pontos de partida, não melhores horários comprovados. Registre resultados em horários diferentes para comparar.'}


def next_slot():
    hours = sorted(suggestion()['hours'])
    current = now()
    with db() as c:
        used = {r[0][:16] for r in c.execute("SELECT due_at FROM jobs WHERE status != 'published'")}
    for day in range(365):
        for hour in hours:
            slot = (current + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot > current + timedelta(minutes=5) and slot.isoformat()[:16] not in used:
                return slot.isoformat()
    raise ValueError('Não há horários livres no próximo ano.')


def create_job(payload):
    import content_engine
    # Model requests happen before acquiring the SQLite write transaction.
    with db() as reader:
        product=reader.execute('SELECT * FROM products WHERE id=?',(payload.get('product_id'),)).fetchone()
        existing=reader.execute("SELECT 1 FROM jobs WHERE product_id=? AND status!='published'",(payload.get('product_id'),)).fetchone()
    if not product:raise ValueError('Produto não encontrado.')
    if existing:raise ValueError('Este produto já tem um vídeo em preparação. Abra o roteiro existente.')
    scenes,caption,meta=content_engine.generate(dict(product))
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        p = c.execute('SELECT * FROM products WHERE id=?', (payload.get('product_id'),)).fetchone()
        if not p:
            raise ValueError('Produto não encontrado.')
        existing = c.execute("SELECT id FROM jobs WHERE product_id=? AND status != 'published'", (p['id'],)).fetchone()
        if existing:
            raise ValueError('Este produto já tem um vídeo em preparação. Abra o roteiro existente.')
        jid = uuid4().hex
        timestamp = stamp()
        c.execute('INSERT INTO jobs (id,product_id,status,scenes,caption,due_at,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', (jid, p['id'], 'draft', json.dumps(scenes, ensure_ascii=False), caption, next_slot(), timestamp, timestamp))
        c.execute('INSERT INTO content_meta VALUES (?,?)',(jid,json.dumps(meta,ensure_ascii=False)))
    return jid


def get_job(jid):
    with db() as c:
        row = c.execute('SELECT * FROM jobs WHERE id=?', (jid,)).fetchone()
    if not row:
        raise ValueError('Vídeo não encontrado.')
    return dict(row)


def ensure_no_buffer_send(c,jid):
    if c.execute("SELECT 1 FROM sqlite_master WHERE name='auto_jobs'").fetchone():
        sent=c.execute("SELECT 1 FROM auto_jobs WHERE job_id=? AND (delivery!='local' OR buffer_id!='')",(jid,)).fetchone()
        if sent:raise ValueError('Este vídeo possui tentativa de envio ao Buffer. Confira o destino antes de alterar o conteúdo.')


def edit_job(jid, payload):
    scenes = payload.get('scenes')
    if not isinstance(scenes, list) or not 4<=len(scenes)<=7:
        raise ValueError('O roteiro deve ter de 4 a 7 cenas.')
    scenes = [clean(s, 400, True) for s in scenes]
    caption = clean(payload.get('caption', ''), 2200, True)
    due = clean(payload.get('due_at', ''), 60, True)
    try:
        date = datetime.fromisoformat(due)
        if date.tzinfo is None:
            date = date.replace(tzinfo=TZ)
        date = date.astimezone(TZ)
    except ValueError:
        raise ValueError('Informe uma data e hora válidas.') from None
    action = payload.get('action', 'save')
    if action not in ('save', 'render', 'schedule'):
        raise ValueError('Ação inválida.')
    rights = payload.get('rights') is True
    if action in ('render', 'schedule') and not rights:
        raise ValueError('Confirme que revisou os dados e tem autorização para usar os materiais.')
    if action == 'schedule' and date <= now():
        raise ValueError('Escolha um horário futuro para preparar o vídeo.')
    status = {'save': 'draft', 'render': 'queued', 'schedule': 'scheduled'}[action]
    with db() as c:
        old = c.execute('SELECT status,scenes,caption FROM jobs WHERE id=?', (jid,)).fetchone()
        if not old:
            raise ValueError('Vídeo não encontrado.')
        if old['status'] in ('rendering', 'queued', 'published'):
            raise ValueError('Este vídeo está em processamento ou já foi publicado.')
        ensure_no_buffer_send(c,jid)
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone():
            remote=c.execute('SELECT stage,video_id FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
            if remote and (remote['video_id'] or remote['stage'] not in ('failed','held_local')):
                raise ValueError('Este vídeo já possui envio no YouTube. Gerencie a publicação pelo YouTube Studio.')
            if remote:c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(jid,))
        c.execute('UPDATE jobs SET scenes=?,caption=?,due_at=?,status=?,rights=?,error=?,updated_at=? WHERE id=?', (json.dumps(scenes, ensure_ascii=False), caption, date.isoformat(), status, int(rights), '', stamp(), jid))
        c.execute('DELETE FROM editorial_reviews WHERE job_id=?',(jid,))
        if json.loads(old['scenes'])!=scenes or old['caption']!=caption:
            meta_row=c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()
            if meta_row:
                import creative
                meta=json.loads(meta_row['payload']);meta['edited']=True;meta['note']='Conteúdo editado por você após a criação inicial.'
                meta['scene_count']=len(scenes);meta['reading']=creative.reading(scenes,meta.get('pace','normal'))
                c.execute('UPDATE content_meta SET payload=? WHERE job_id=?',(json.dumps(meta,ensure_ascii=False),jid))
    return status


def record_results(jid, payload):
    url = public_url(payload.get('tiktok_url', ''))
    host = urlparse(url).hostname.lower()
    if host not in ('youtube.com','www.youtube.com','youtu.be','m.youtube.com') and host!='tiktok.com' and not host.endswith('.tiktok.com'):
        raise ValueError('Informe o link do vídeo publicado no YouTube ou TikTok.')
    try:
        published = datetime.fromisoformat(payload.get('published_at', ''))
        if published.tzinfo is None:
            published = published.replace(tzinfo=TZ)
        published = published.astimezone(TZ)
        if published > now() + timedelta(minutes=5):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Informe uma data de publicação válida, até o momento atual.') from None
    views = numeric(payload.get('views', 0), 10**12, integer=True)
    clicks = numeric(payload.get('clicks', 0), 10**12, integer=True)
    revenue = numeric(payload.get('revenue', 0), 10**9)
    with db() as c:
        row = c.execute('SELECT status FROM jobs WHERE id=?', (jid,)).fetchone()
        if not row or row['status'] not in ('ready', 'published'):
            raise ValueError('Gere o vídeo antes de registrar sua publicação.')
        c.execute("UPDATE jobs SET status='published',published_at=?,tiktok_url=?,views=?,clicks=?,revenue=?,updated_at=?,results_recorded_at=? WHERE id=?", (published.isoformat(), url, views, clicks, revenue, stamp(),stamp(), jid))


def regenerate_job(jid):
    """Explicitly replace an editable script with current product/campaign data."""
    import content_engine
    old=get_job(jid)
    if old['status'] not in ('draft','ready','error','scheduled'):raise ValueError('Aguarde o processamento antes de recriar o roteiro.')
    with db() as c:product=dict(c.execute('SELECT * FROM products WHERE id=?',(old['product_id'],)).fetchone())
    scenes,caption,meta=content_engine.generate(product)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        current=c.execute('SELECT updated_at,status FROM jobs WHERE id=?',(jid,)).fetchone()
        if current['updated_at']!=old['updated_at'] or current['status']!=old['status']:raise ValueError('O vídeo mudou. Atualize a página antes de recriar.')
        ensure_no_buffer_send(c,jid)
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='youtube_jobs'").fetchone():
            remote=c.execute('SELECT stage,video_id FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
            if remote and (remote['video_id'] or remote['stage'] not in ('failed','held_local')):raise ValueError('Este vídeo possui envio externo. Gerencie pelo YouTube Studio.')
            c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(jid,))
        c.execute("UPDATE jobs SET scenes=?,caption=?,status='draft',rights=0,voice=0,error='',updated_at=? WHERE id=?",(json.dumps(scenes,ensure_ascii=False),caption,stamp(),jid))
        c.execute('INSERT INTO content_meta VALUES (?,?) ON CONFLICT(job_id) DO UPDATE SET payload=excluded.payload',(jid,json.dumps(meta,ensure_ascii=False)))
        c.execute('DELETE FROM media_validations WHERE job_id=?',(jid,))
        c.execute('DELETE FROM editorial_reviews WHERE job_id=?',(jid,))


def state():
    with db() as c:
        products = [dict(r) for r in c.execute('SELECT * FROM products ORDER BY created_at DESC')]
        jobs = [dict(r) for r in c.execute('SELECT jobs.*, products.name, products.platform, products.image, products.kind FROM jobs JOIN products ON products.id=jobs.product_id ORDER BY jobs.created_at DESC')]
        meta={r['job_id']:json.loads(r['payload']) for r in c.execute('SELECT * FROM content_meta')}
    for j in jobs:
        j['scenes'] = json.loads(j['scenes'])
        j['content']=meta.get(j['id'])
        j['video_url'] = f"/media/{j['id']}/video.mp4?v={j['updated_at']}" if j['status'] in ('ready', 'published') else None
        import quality
        j['quality']=quality.inspect(j['id'])
    return {'products': products, 'jobs': jobs, 'suggestion': suggestion(), 'next_slot': next_slot(), 'timezone': 'America/Sao_Paulo', 'posting': {'connected': False, 'mode': 'manual', 'reason': 'A API direta do TikTok não aceita ferramentas de uso pessoal restrito. Exporte o MP4 e publique pelo TikTok.'}}
