"""Completed 3D library and conservative, local-only obsolete-video cleanup."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import core
from story_week_catalog import NUMBERS

ID = re.compile('[a-f0-9]{32}')
RECEIPTS = ('publicacao-tiktok.json', 'agendamento-tiktok.json')


def read_json(path, limit=512*1024):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
            return None
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def receipt(identifier):
    """Display a saved observation, never infer publication from a due date."""
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        return None
    for name in RECEIPTS:
        row = read_json(core.DATA/'stories'/identifier/name, 65536)
        if not row or row.get('media_id', identifier) != identifier:
            continue
        status = row.get('status')
        if status not in ('scheduled_confirmed', 'published_confirmed'):
            continue
        handle = row.get('handle', '')
        url = row.get('url', '')
        if not isinstance(handle, str) or not re.fullmatch('[A-Za-z0-9_.]{2,24}', handle) or not isinstance(url, str):
            continue
        try:
            parts = urlsplit(url)
            if parts.scheme != 'https' or parts.netloc != 'www.tiktok.com' or not re.fullmatch('/@'+re.escape(handle)+'/video/[0-9]{15,24}', parts.path):
                continue
        except ValueError:
            continue
        scheduled = row.get('scheduled_for')
        label = 'Publicação registrada no TikTok' if status == 'published_confirmed' else 'Agendamento registrado no TikTok'
        if status == 'scheduled_confirmed':
            try:
                due = datetime.fromisoformat(scheduled)
                if due.tzinfo is None:continue
                if due <= core.now():label = 'Horário agendado atingido; conferir no TikTok'
            except (ValueError, TypeError):
                continue
        return {'status':status, 'label':label, 'url':url, 'handle':handle,
                'scheduled_for':scheduled, 'observed_at':row.get('observed_at')}
    return None


def entries():
    rows = []
    root = core.DATA/'stories'
    if not root.is_dir():return rows
    for folder in root.iterdir():
        if not ID.fullmatch(folder.name) or folder.is_symlink() or not folder.is_dir():continue
        if folder.resolve().parent != root.resolve():continue
        meta = read_json(folder/'roteiro.json')
        if not meta or not (folder/'video.mp4').is_file() or (folder/'video.mp4').is_symlink():continue
        if (folder/'video.mp4').resolve().parent != folder.resolve():continue
        if type(meta.get('episode')) is not int or meta['episode'] not in NUMBERS:continue
        if not re.fullmatch('[a-f0-9]{64}', str(meta.get('sha256',''))):continue
        rows.append({'id':folder.name, 'meta':meta, 'updated':(folder/'roteiro.json').stat().st_mtime_ns})
    return rows


def latest_3d(rows):
    latest = {}
    import story_offers
    for row in sorted(rows, key=lambda r:(r['updated'],r['id']), reverse=True):
        meta = row['meta']
        if (meta.get('animation_type') != 'original_procedural_3d' or meta.get('character_animation') is not True or
                meta.get('voice') is not True or not isinstance(meta.get('duration'),(int,float)) or
                not 0 < meta['duration'] <= 180 or not story_offers.current(meta.get('offer'))):continue
        latest.setdefault(meta['episode'],row)
    return latest


def state():
    return [{'id':row['id'], 'number':number, 'title':f'A chave do 12 · capítulo {number} em 3D',
             'duration':row['meta']['duration'], 'receipt':receipt(row['id']),
             'mouth_alignment':row['meta'].get('mouth_alignment','procedural_not_phoneme_aligned'),
             'video_url':f"/stories/{row['id']}/video.mp4?v={row['meta']['sha256']}",
             'poster_url':f"/stories/{row['id']}/poster.png"}
            for number,row in sorted(latest_3d(entries()).items())]


def native_post_exists(content_key, handle):
    """An existing native schedule/publication must not be re-uploaded via API."""
    for row in entries():
        if row['meta'].get('animation_type') != 'original_procedural_3d':continue
        if content_key != f"3d:a-chave-do-12:{row['meta']['episode']}":continue
        saved=receipt(row['id'])
        if saved and saved['handle'].lower()==handle.lower():return True
    return False


def cleanup(execute=False):
    """Keep the newest ready 3D chapters, every receipt and every outbox reference.

    Only MP4s produced inside this library are eligible. Native source projects,
    captions, metadata and published/scheduled masters remain available.
    """
    rows = entries();latest = latest_3d(rows);protected = {r['id'] for r in latest.values()}
    with core.db() as c:
        protected.update(r['media_id'] for r in c.execute('SELECT media_id FROM story_publications'))
        protected.update(r['id'] for r in c.execute("SELECT id FROM story_episodes WHERE status IN ('queued','rendering')"))
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='story_week_slots'").fetchone():
            protected.update(r['media_id'] for r in c.execute("SELECT media_id FROM story_week_slots WHERE media_id!=''"))
    for row in rows:
        folder=core.DATA/'stories'/row['id']
        # Missing/unparseable receipt is still a hold, not permission to delete.
        if any((folder/name).exists() for name in RECEIPTS):protected.add(row['id'])
    paths=[];obsolete=[]
    for row in rows:
        identifier=row['id'];meta=row['meta']
        # Retire a 2D chapter only after its verified 3D replacement is complete.
        if identifier in protected or meta['episode'] not in latest:continue
        replacement=core.DATA/'stories'/latest[meta['episode']]['id']/'video.mp4'
        if hashlib.sha256(replacement.read_bytes()).hexdigest()!=latest[meta['episode']]['meta']['sha256']:
            raise ValueError('A versão 3D atual mudou. A limpeza foi interrompida.')
        master=core.DATA/'stories'/identifier/'video.mp4'
        if hashlib.sha256(master.read_bytes()).hexdigest()!=meta['sha256']:
            raise ValueError('Um vídeo antigo foi alterado. A limpeza foi interrompida para preservar o arquivo.')
        obsolete.append(identifier);paths.append(master)
        package=core.DATA/'story-3d'/identifier
        if package.is_dir():paths.extend(package.rglob('*.mp4'))
    verified=[]
    data_root=core.DATA.resolve()
    for path in paths:
        resolved=path.resolve()
        if path.is_symlink() or not resolved.is_relative_to(data_root) or resolved.suffix.lower()!='.mp4':
            raise ValueError('A limpeza encontrou um caminho fora da biblioteca e não foi executada.')
        if resolved not in verified:verified.append(resolved)
    report={'executed':bool(execute),'removed_files':len(verified),'bytes':sum(p.stat().st_size for p in verified),
            'obsolete_ids':obsolete,'protected_ids':sorted(protected),'scope':'Somente MP4s antigos da biblioteca local; nenhuma exclusão no TikTok.'}
    if execute:
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            # Refuse a concurrent request that just pinned a cleanup candidate.
            pinned={r['media_id'] for r in c.execute('SELECT media_id FROM story_publications')}
            active={r['id'] for r in c.execute("SELECT id FROM story_episodes WHERE status IN ('queued','rendering')")}
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='story_week_slots'").fetchone():
                pinned.update(r['media_id'] for r in c.execute("SELECT media_id FROM story_week_slots WHERE media_id!=''"))
            if (pinned|active).intersection(obsolete):raise ValueError('A fila mudou. Confira a biblioteca antes de limpar novamente.')
            for identifier in obsolete:
                if any((core.DATA/'stories'/identifier/name).exists() for name in RECEIPTS):
                    raise ValueError('Uma publicação foi registrada durante a limpeza; operação interrompida.')
            for path in verified:path.unlink()
            for identifier in obsolete:
                c.execute("UPDATE story_episodes SET status='archived',error='',updated_at=? WHERE id=?",(core.stamp(),identifier))
        log=core.DATA/'story-cleanup';log.mkdir(exist_ok=True)
        (log/(core.now().strftime('%Y%m%dT%H%M%S%f')+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
