"""Scheduled import of authorized affiliate catalogs. Never creates tracking IDs."""
import json
import sqlite3
from datetime import datetime,timedelta
from urllib.request import Request,build_opener,ProxyHandler
from uuid import uuid4
import core

DEFAULTS={'url':'','enabled':False,'authorized':False,'interval_hours':4,'next_check':None,'last_success':None,'message':'Conecte um catálogo com seus links de afiliado.'}


def init():
    with core.db() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS catalog_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS catalog_items(source_id TEXT PRIMARY KEY,product_id TEXT NOT NULL REFERENCES products(id),active INTEGER NOT NULL,last_seen TEXT NOT NULL);''')


def settings():
    with core.db() as c:rows=c.execute('SELECT * FROM catalog_settings').fetchall()
    return {**DEFAULTS,**{r['key']:json.loads(r['value']) for r in rows}}


def put(values):
    with core.db() as c:
        for key,value in values.items():
            c.execute('INSERT INTO catalog_settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,ensure_ascii=False)))


def configure(payload):
    enabled=payload.get('enabled') is True
    authorized=payload.get('authorized') is True
    url=core.clean(payload.get('url',''),3000)
    if url:core.public_url(url)
    if enabled and (not authorized or not url):
        raise ValueError('Informe o catálogo e confirme sua afiliação e autorização de uso.')
    put({'url':url,'enabled':enabled,'authorized':authorized,'next_check':None,
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
    except (OSError,UnicodeError,json.JSONDecodeError):
        raise ValueError('Não foi possível ler o catálogo JSON. Confira o endereço e a disponibilidade da fonte.') from None


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


def ingest(document,authorized=False):
    if not authorized:raise ValueError('Confirme sua afiliação e a autorização dos dados antes de importar.')
    rows=validate(document)  # Validate every item before changing stored data.
    import autopilot
    added=0;updated=0;now=core.stamp()
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        previous=[r['product_id'] for r in c.execute('SELECT product_id FROM catalog_items WHERE active=1')]
        c.execute('UPDATE catalog_items SET active=0')
        for pid in previous:c.execute('UPDATE auto_products SET active=0 WHERE product_id=?',(pid,))
        for row in rows:
            existing=c.execute('SELECT product_id FROM catalog_items WHERE source_id=?',(row['source_id'],)).fetchone()
            if existing:
                pid=existing['product_id'];updated+=1
                c.execute('UPDATE products SET name=?,url=?,kind=?,platform=?,category=?,description=?,price=?,commission=? WHERE id=?',(row['name'],row['url'],row['kind'],core.platform_for(row['url']),row['category'],row['description'],row['price'],row['commission'],pid))
            else:
                # Reuse an identical existing link rather than duplicating a manual product.
                match=c.execute('SELECT id FROM products WHERE url=?',(row['url'],)).fetchone()
                if match:pid=match['id'];updated+=1
                else:
                    pid=uuid4().hex;added+=1
                    c.execute('INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pid,row['name'],row['url'],row['kind'],core.platform_for(row['url']),row['category'],row['description'],row['price'],row['commission'],'',now))
            c.execute('INSERT INTO catalog_items VALUES (?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET active=excluded.active,last_seen=excluded.last_seen',(row['source_id'],pid,int(row['active']),now))
            c.execute('INSERT INTO auto_products VALUES (?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET active=excluded.active,approved=excluded.approved,updated_at=excluded.updated_at',(pid,1,int(row['active']),4,now))
    put({'last_success':now,'message':f'Catálogo atualizado: {added} novos, {updated} atualizados, {sum(r["active"] for r in rows)} ativos.'})
    autopilot.event('catalog',f'Catálogo recebido: {added} novos produtos e {updated} atualizados.')
    return {'added':added,'updated':updated,'active':sum(r['active'] for r in rows)}


def tick():
    config=settings()
    if not config['enabled']:return
    if config['next_check'] and datetime.fromisoformat(config['next_check'])>core.now():return
    put({'next_check':(core.now()+timedelta(hours=config['interval_hours'])).isoformat(),'message':'Consultando catálogo autorizado…'})
    try:ingest(fetch(config['url']),config['authorized'])
    except Exception as error:put({'message':str(error)[:500]})


def eligible(pid):
    with core.db() as c:row=c.execute('SELECT active,last_seen FROM catalog_items WHERE product_id=?',(pid,)).fetchone()
    if not row:return True  # Manually authorized products retain their existing workflow.
    return bool(row['active']) and datetime.fromisoformat(row['last_seen'])>core.now()-timedelta(hours=24)


def state():
    config=settings()
    with core.db() as c:count=c.execute('SELECT COUNT(*) FROM catalog_items WHERE active=1').fetchone()[0]
    return {'settings':config,'active_products':count,'notice':'A fonte deve fornecer seus links de afiliado já emitidos. Esta conexão não cria conta nem garante comissão.'}
