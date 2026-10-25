"""Optional factual affiliate offer, distinct from fictional events and actors."""
import json
import core
import content_engine


def init():
    with core.db() as c:c.execute('''CREATE TABLE IF NOT EXISTS story_offers (
        series_id TEXT PRIMARY KEY REFERENCES story_series(id),
        product_id TEXT NOT NULL REFERENCES products(id), snapshot TEXT NOT NULL, updated_at TEXT NOT NULL
    )''')


def current(offer):
    import catalog
    if not offer:return True
    with core.db() as c:
        product=c.execute('SELECT * FROM products WHERE id=?',(offer['product_id'],)).fetchone()
        allowed=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(offer['product_id'],)).fetchone() if c.execute("SELECT 1 FROM sqlite_master WHERE name='auto_products'").fetchone() else None
    return bool(product and allowed and allowed['active'] and allowed['approved'] and catalog.eligible(offer['product_id'])
                and content_engine.product_fingerprint(dict(product))==offer['product_hash'])


def for_series(sid):
    with core.db() as c:row=c.execute('SELECT snapshot FROM story_offers WHERE series_id=?',(sid,)).fetchone()
    return json.loads(row['snapshot']) if row else None


def attach(payload):
    sid=payload.get('series_id');pid=payload.get('product_id')
    if payload.get('approved') is not True:raise ValueError('Confirme a oferta de afiliado e as características verificadas.')
    import catalog
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute('SELECT 1 FROM story_series WHERE id=?',(sid,)).fetchone():raise ValueError('Minissérie não encontrada.')
        if c.execute("SELECT 1 FROM story_episodes WHERE series_id=? AND status='rendering'",(sid,)).fetchone():raise ValueError('Aguarde a geração atual antes de alterar a oferta.')
        row=c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone()
        allowed=c.execute('SELECT active,approved FROM auto_products WHERE product_id=?',(pid,)).fetchone() if c.execute("SELECT 1 FROM sqlite_master WHERE name='auto_products'").fetchone() else None
        if not row or not allowed or not allowed['active'] or not allowed['approved'] or not catalog.eligible(pid):
            raise ValueError('Escolha um produto ativo com afiliação e materiais já autorizados.')
        product=dict(row);facts=content_engine.facts_from(product['description'])
        if not facts or len(product['description'].strip())<30:raise ValueError('Faltam características verificadas do produto.')
        offer={'product_id':pid,'name':product['name'],'url':core.public_url(product['url']),
               'facts':facts,'product_hash':content_engine.product_fingerprint(product)}
        prior=c.execute('SELECT snapshot FROM story_offers WHERE series_id=?',(sid,)).fetchone()
        if prior and json.loads(prior['snapshot'])==offer:return {'ok':True,'existing':True}
        c.execute('INSERT INTO story_offers VALUES (?,?,?,?) ON CONFLICT(series_id) DO UPDATE SET product_id=excluded.product_id,snapshot=excluded.snapshot,updated_at=excluded.updated_at',
                  (sid,pid,json.dumps(offer,ensure_ascii=False),core.stamp()))
        c.execute("UPDATE story_episodes SET status='queued',error='',voice=0,duration=NULL,updated_at=? WHERE series_id=? AND status!='archived'",(core.stamp(),sid))
    return {'ok':True,'existing':False}


def scenes(offer,brief=False):
    if not offer:return []
    if brief:
        return [{'visual':'offer','text':f"Publicidade. Conheça {offer['name']}. Link de afiliado na descrição. Posso receber comissão por compras elegíveis."}]
    facts=' '.join(offer['facts'][:2])
    return [{'visual':'offer','text':f"Publicidade. Conheça {offer['name']}. {facts}"},
            {'visual':'offer','text':'O link de afiliado está na descrição para copiar e abrir no navegador. Posso receber comissão por compras elegíveis. Confira as condições antes de comprar.'}]


def caption(offer):
    if not offer:return ''
    return '\n\nPUBLICIDADE · Oferta de afiliado, separada da ficção.\n'+offer['name']+'\n'+'\n'.join(offer['facts'])+'\n\nPosso receber comissão por compras elegíveis. Os personagens não são clientes nem depoimentos.\nLink do produto: '+offer['url']+'\nSe o endereço não estiver clicável, copie e abra no navegador.\n#publicidade'
