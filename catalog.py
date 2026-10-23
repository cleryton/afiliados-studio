"""Scheduled import of authorized affiliate catalogs. Never creates tracking IDs."""
import json
import sqlite3
import threading
from datetime import datetime,timedelta
from urllib.error import HTTPError
from urllib.request import Request,build_opener,ProxyHandler
from uuid import uuid4
import core

DEFAULTS={'url':'','enabled':False,'authorized':False,'interval_hours':4,'next_check':None,'last_success':None,
          'last_attempt':None,'failures':0,'last_error':'','revision':'',
          'message':'Conecte um catálogo com seus links de afiliado.'}
_tick_lock=threading.Lock()


class FetchError(ValueError):
    def __init__(self,message,transient=False):
        super().__init__(message)
        self.transient=transient


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS catalog_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS catalog_items(source_id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(id),active INTEGER NOT NULL,last_seen TEXT NOT NULL);''')


def settings():
    with core.db() as c:rows=c.execute('SELECT * FROM catalog_settings').fetchall()
    return {**DEFAULTS,**{r['key']:json.loads(r['value']) for r in rows}}


def _put(c,values):
    for key,value in values.items():
        c.execute('INSERT INTO catalog_settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))


def put(values):
    with core.db() as c:_put(c,values)


def configure(payload):
    enabled=payload.get('enabled') is True
    authorized=payload.get('authorized') is True
    url=core.clean(payload.get('url',''),3000)
    if url:core.public_url(url)
    if enabled and (not authorized or not url):
        raise ValueError('Informe o catálogo e confirme sua afiliação e autorização de uso.')
    put({'url':url,'enabled':enabled,'authorized':authorized,'next_check':None,
         'revision':uuid4().hex,'failures':0,'last_error':'',
         'message':'Catálogo configurado. A primeira consulta acontece em até um minuto.' if enabled else 'Consulta automática de catálogo pausada.'})


def fetch(url):
    core.public_url(url,resolve=True)
    opener=build_opener(ProxyHandler({}),core.PublicHTTPHandler(),core.PublicHTTPSHandler(),core.PublicRedirect())
    request=Request(url,headers={'Accept':'application/json','User-Agent':'AfiliadosStudioCatalog/1.0'})
    try:
        with opener.open(request,timeout=12) as response:
            raw=response.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('Catálogo maior que 1 MB.')
        return json.loads(raw.decode('utf-8-sig'))
    except HTTPError as error:
        transient=error.code in (408,425,429) or error.code>=500
        raise FetchError('A fonte do catálogo está temporariamente indisponível.' if transient else 'A fonte recusou a consulta. Confira o endereço e a autorização.',transient) from None
    except OSError:
        raise FetchError('Sem resposta da fonte do catálogo. Confira a conexão com a internet.',True) from None
    except (UnicodeError,json.JSONDecodeError):
        raise FetchError('A fonte não retornou um catálogo JSON válido. Confira o arquivo.') from None


def validate(document):
    rows=document.get('products') if isinstance(document,dict) else document
    if not isinstance(rows,list) or len(rows)>100:
        raise ValueError('O catálogo deve conter uma lista de até 100 produtos.')
    output=[];identifiers=set();urls=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Produto inválido no catálogo.')
        sid=core.clean(row.get('id'),150,True)
        name=core.clean(row.get('name'),140,True)
        description=core.clean(row.get('description'),650,True)
        url=core.public_url(row.get('affiliate_url'))
        if len(url)>1500:raise ValueError('Use links oficiais curtos de afiliado no catálogo (até 1500 caracteres).')
        kind=row.get('kind')
        if kind not in ('physical','digital'):raise ValueError('O tipo deve ser physical ou digital.')
        if len(description)<30:raise ValueError('Cada produto precisa de pelo menos 30 caracteres de características verificadas.')
        if sid in identifiers or url in urls:raise ValueError('Há identificadores ou links duplicados no catálogo.')
        identifiers.add(sid);urls.add(url)
        output.append({'source_id':sid,'name':name,'description':description,'url':url,'kind':kind,
          'category':core.clean(row.get('category','Geral'),50,True),
          'price':core.numeric(row.get('price'),10**7,optional=True),
          'commission':core.numeric(row.get('commission_percent'),100,optional=True),
          'active':row.get('active',True) is True})
    return output


def ingest(document,authorized=False,expected_revision=None):
    if not authorized:raise ValueError('Confirme sua afiliação e a autorização dos dados antes de importar.')
    rows=validate(document)  # Validate every item before changing stored data.
    import autopilot
    added=0;updated=0;now=core.stamp()
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if expected_revision is not None:
            config=settings()
            if not config['enabled'] or not config['authorized'] or config['revision']!=expected_revision:return None
        c.execute('UPDATE catalog_items SET active=0')
        for row in rows:
            existing=c.execute('SELECT product_id FROM catalog_items WHERE source_id=?',(row['source_id'],)).fetchone()
            if existing:
                pid=existing['product_id'];updated+=1
                c.execute('UPDATE products SET name=?,url=?,kind=?,platform=?,category=?,description=?,price=?,commission=? WHERE id=?',(row['name'],row['url'],row['kind'],core.platform_for(row['url']),row['category'],row['description'],row['price'],row['commission'],pid))
            else:
                # Reuse an identical existing link rather than duplicating a manual product.
                match=c.execute('SELECT id FROM products WHERE url=?',(row['url'],)).fetchone()
                if match:
                    pid=match['id'];updated+=1
                    c.execute('UPDATE products SET name=?,url=?,kind=?,platform=?,category=?,description=?,price=?,commission=? WHERE id=?',(row['name'],row['url'],row['kind'],core.platform_for(row['url']),row['category'],row['description'],row['price'],row['commission'],pid))
                else:
                    pid=uuid4().hex;added+=1
                    c.execute('INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pid,row['name'],row['url'],row['kind'],core.platform_for(row['url']),row['category'],row['description'],row['price'],row['commission'],'',now))
            c.execute('INSERT INTO catalog_items VALUES (?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET active=excluded.active,last_seen=excluded.last_seen',(row['source_id'],pid,int(row['active']),now))
            # Source availability is enforced by eligible(). Keep the operator's
            # pause, authorization and variant limit across catalog refreshes.
            c.execute('INSERT INTO auto_products VALUES (?,?,?,?,?) ON CONFLICT(product_id) DO NOTHING',(pid,1,1,4,now))
        _put(c,{'last_success':now,'failures':0,'last_error':'',
                'revision':uuid4().hex if expected_revision is None else expected_revision,
                'next_check':(core.now()+timedelta(hours=settings()['interval_hours'])).isoformat(),
                'message':f'Catálogo atualizado: {added} novos, {updated} atualizados, {sum(r["active"] for r in rows)} ativos.'})
    autopilot.event('catalog',f'Catálogo recebido: {added} novos produtos e {updated} atualizados.')
    return {'added':added,'updated':updated,'active':sum(r['active'] for r in rows)}


def tick():
    if not _tick_lock.acquire(blocking=False):return
    try:
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            config=settings()
            if not config['enabled'] or not config['authorized']:return
            if config['next_check'] and datetime.fromisoformat(config['next_check'])>core.now():return
            # Persist a short lease before I/O so a restart cannot spin on a failing source.
            _put(c,{'last_attempt':core.stamp(),'next_check':(core.now()+timedelta(minutes=5)).isoformat(),'message':'Consultando catálogo autorizado…'})
        try:ingest(fetch(config['url']),config['authorized'],expected_revision=config['revision'])
        except Exception as error:
            with core.db() as c:
                c.execute('BEGIN IMMEDIATE')
                latest=settings()
                if latest['revision']!=config['revision'] or not latest['enabled']:return
                failures=latest['failures']+1
                transient=isinstance(error,FetchError) and error.transient
                minutes=(5,15,30,60,120,240)[min(failures-1,5)] if transient else 240
                detail=str(error)[:350] if isinstance(error,ValueError) else 'Falha ao consultar o catálogo. Confira a fonte e a conexão.'
                _put(c,{'failures':failures,'last_error':detail,
                        'next_check':(core.now()+timedelta(minutes=minutes)).isoformat(),
                        'message':detail+f' Nova consulta em {minutes} minutos. Os dados anteriores foram preservados.'})
    finally:_tick_lock.release()


def eligible(pid):
    with core.db() as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='catalog_items'").fetchone():return True
        row=c.execute('SELECT active,last_seen FROM catalog_items WHERE product_id=? ORDER BY active DESC,last_seen DESC LIMIT 1',(pid,)).fetchone()
    if not row:return True  # Manually authorized products retain their existing workflow.
    return bool(row['active']) and datetime.fromisoformat(row['last_seen'])>core.now()-timedelta(hours=24)


def state():
    config=settings()
    with core.db() as c:count=c.execute('SELECT COUNT(*) FROM catalog_items WHERE active=1').fetchone()[0]
    return {'settings':config,'active_products':count,'notice':'A fonte deve fornecer seus links de afiliado já emitidos. Esta conexão não cria conta nem garante comissão.'}
