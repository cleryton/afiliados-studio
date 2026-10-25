"""Separate local fiction queue: never sends episodes to any social account."""
import json
import re
from pathlib import Path
from uuid import uuid4
import core
from story_catalog import PILOT


def init():
    with core.db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS story_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS story_series (
            id TEXT PRIMARY KEY, template_key TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
            premise TEXT NOT NULL, characters TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS story_episodes (
            id TEXT PRIMARY KEY, series_id TEXT NOT NULL REFERENCES story_series(id),
            number INTEGER NOT NULL, title TEXT NOT NULL, scenes TEXT NOT NULL,
            status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '', voice INTEGER NOT NULL DEFAULT 0,
            duration REAL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(series_id,number)
        );
        ''')
        c.execute("UPDATE story_episodes SET status='queued',error='',updated_at=? WHERE status='rendering'", (core.stamp(),))
    import story_offers
    story_offers.init()


def create_pilot():
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        prior=c.execute('SELECT id FROM story_series WHERE template_key=?',(PILOT['key'],)).fetchone()
        if prior:return {'id':prior['id'],'existing':True}
        sid=uuid4().hex;stamp=core.stamp()
        c.execute('INSERT INTO story_series VALUES (?,?,?,?,?,?)',(sid,PILOT['key'],PILOT['title'],PILOT['premise'],PILOT['characters'],stamp))
        for number,episode in enumerate(PILOT['episodes'],1):
            c.execute('INSERT INTO story_episodes(id,series_id,number,title,scenes,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                      (uuid4().hex,sid,number,episode['title'],json.dumps(episode['scenes'],ensure_ascii=False),'queued',stamp,stamp))
    return {'id':sid,'existing':False}


def state():
    import story_offers
    with core.db() as c:
        series=[dict(r) for r in c.execute('SELECT * FROM story_series ORDER BY created_at')]
        episodes=[dict(r) for r in c.execute('SELECT * FROM story_episodes ORDER BY series_id,number')]
        profile=c.execute("SELECT value FROM story_settings WHERE key='target_handle'").fetchone()
    for row in episodes:
        row['scenes']=json.loads(row['scenes'])
        offer=story_offers.for_series(row['series_id']);row['offer']=offer
        row['offer_current']=story_offers.current(offer)
        row['scenes']+=story_offers.scenes(offer)
        row['video_url']=f"/stories/{row['id']}/video.mp4?v={row['updated_at']}" if row['status']=='ready' and row['offer_current'] else None
    from story_renderer import asset_path
    assets_ready=all(asset_path(name).is_file() for name in ('discovery.png','corridor.png','sisters.png'))
    return {'series':series,'episodes':episodes,'publishing_connected':False,'target_handle':profile['value'] if profile else '', 'assets_ready':assets_ready,
            'destination':'TikTok','notice':'Criação local de ficção. Publicação no TikTok ainda não conectada; nenhum episódio será enviado ao YouTube ou a contas pessoais.'}


def set_profile(payload):
    handle=core.clean(payload.get('handle',''),25,True).lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.]{1,22}[A-Za-z0-9_]',handle):raise ValueError('Informe um @ válido do TikTok, sem senha nem endereço completo.')
    with core.db() as c:c.execute("INSERT INTO story_settings VALUES ('target_handle',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(handle,))
    return {'ok':True,'handle':handle,'publishing_connected':False}


def retry(eid):
    with core.db() as c:
        if not c.execute("UPDATE story_episodes SET status='queued',error='',updated_at=? WHERE id=? AND status='error'",(core.stamp(),eid)).rowcount:
            raise ValueError('Somente episódios com erro podem voltar à fila.')


def claim_next():
    with core.db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT 1 FROM story_episodes WHERE status='rendering'").fetchone():return None
        row=c.execute("""SELECT e.*,s.title AS series_title FROM story_episodes e JOIN story_series s ON s.id=e.series_id
            WHERE e.status='queued' ORDER BY e.created_at,e.series_id,e.number LIMIT 1""").fetchone()
        if not row:return None
        c.execute("UPDATE story_episodes SET status='rendering',updated_at=? WHERE id=?",(core.stamp(),row['id']))
    import story_offers
    result=dict(row);result['offer']=story_offers.for_series(row['series_id'])
    return result


def tick():
    episode=claim_next()
    if not episode:return
    try:
        import story_offers
        if not story_offers.current(episode.get('offer')):raise ValueError('A oferta mudou ou perdeu autorização.')
        from story_renderer import render
        result=render(episode)
        if not story_offers.current(episode.get('offer')):raise ValueError('A oferta mudou durante a geração.')
        with core.db() as c:
            c.execute("UPDATE story_episodes SET status='ready',voice=?,duration=?,error=?,updated_at=? WHERE id=?",
                      (int(result['voice']),result['duration'],result.get('warning',''),core.stamp(),episode['id']))
    except Exception:
        with core.db() as c:
            c.execute("UPDATE story_episodes SET status='error',error=?,updated_at=? WHERE id=?",
                      ('Não foi possível concluir este episódio. Confira as dependências locais e tente novamente.',core.stamp(),episode['id']))


def media_file(eid,name):
    if not isinstance(eid,str) or not re.fullmatch('[a-f0-9]{32}',eid):raise ValueError('Episódio inválido.')
    if name not in ('video.mp4','poster.png','legenda.txt','legendas.srt','roteiro.json'):
        raise ValueError('Arquivo de episódio inválido.')
    return Path(core.DATA)/'stories'/eid/name
