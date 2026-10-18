"""Editorial briefs. One campaign per product avoids ambiguous instructions."""
import hashlib
import json
from uuid import uuid4
import core

TONES={'direto':'Direto','educativo':'Educativo','comparativo':'Comparativo'}
CTAS={'detalhes':'Ver detalhes','comparar':'Comparar características','conhecer':'Conhecer o produto'}


def init():
    with core.db() as c:c.executescript('''
    CREATE TABLE IF NOT EXISTS campaigns(id TEXT PRIMARY KEY,name TEXT NOT NULL,audience TEXT NOT NULL,tone TEXT NOT NULL,cta TEXT NOT NULL,review_mode TEXT NOT NULL,active INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS campaign_products(product_id TEXT PRIMARY KEY REFERENCES products(id),campaign_id TEXT NOT NULL REFERENCES campaigns(id));
    ''')


def snapshot(row):
    if not row:return None
    value={k:row[k] for k in ('id','name','audience','tone','cta','review_mode','active')}
    value['revision']=hashlib.sha256(json.dumps({**value,'updated_at':row['updated_at']},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return value


def for_product(pid):
    if not pid:return None
    with core.db() as c:row=c.execute('SELECT campaigns.* FROM campaigns JOIN campaign_products ON campaign_id=campaigns.id WHERE product_id=?',(pid,)).fetchone()
    return snapshot(row)


def save(payload,cid=None):
    name=core.clean(payload.get('name'),100,True);audience=core.clean(payload.get('audience',''),120)
    tone=payload.get('tone','educativo');cta=payload.get('cta','detalhes');mode=payload.get('review_mode','automatic')
    if tone not in TONES or cta not in CTAS or mode not in ('automatic','manual'):raise ValueError('Escolha estilo, encerramento e modo de revisão válidos.')
    ids=payload.get('product_ids',[])
    if not isinstance(ids,list) or len(ids)>100 or any(not isinstance(pid,str) for pid in ids):raise ValueError('Selecione até 100 produtos.')
    ids=list(dict.fromkeys(ids));active=payload.get('active',True) is True
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if cid and not c.execute('SELECT 1 FROM campaigns WHERE id=?',(cid,)).fetchone():raise ValueError('Campanha não encontrada.')
        for pid in ids:
            if not c.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone():raise ValueError('Produto não encontrado.')
            used=c.execute('SELECT campaign_id FROM campaign_products WHERE product_id=?',(pid,)).fetchone()
            if used and used['campaign_id']!=cid:raise ValueError('Um produto já pertence a outra campanha. Remova-o da campanha anterior para transferir.')
        cid=cid or uuid4().hex;now=core.stamp()
        c.execute('INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,audience=excluded.audience,tone=excluded.tone,cta=excluded.cta,review_mode=excluded.review_mode,active=excluded.active,updated_at=excluded.updated_at',(cid,name,audience,tone,cta,mode,int(active),now,now))
        c.execute('DELETE FROM campaign_products WHERE campaign_id=?',(cid,))
        for pid in ids:c.execute('INSERT INTO campaign_products VALUES (?,?)',(pid,cid))
    return cid


def state():
    with core.db() as c:
        rows=[dict(r) for r in c.execute('SELECT * FROM campaigns ORDER BY created_at DESC')]
        pairs=[dict(r) for r in c.execute('SELECT * FROM campaign_products')]
    for row in rows:row['product_ids']=[r['product_id'] for r in pairs if r['campaign_id']==row['id']]
    return rows
