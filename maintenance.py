"""Verified, bounded local SQLite snapshots. Never restores or copies secrets."""
from datetime import datetime, timedelta
from contextlib import closing
import hashlib
import json
import re
import shutil
import sqlite3
import threading
import time
from uuid import uuid4
import core

_lock = threading.Lock()
MAX_DATABASE = 256 * 1024 * 1024
MIN_FREE = 512 * 1024 * 1024
KEEP = 7
NAME = re.compile(r'studio-\d{8}T\d{6}-[a-f0-9]{12}\.sqlite')


def read():
    try:
        value = json.loads((core.DATA / 'maintenance.json').read_text(encoding='utf-8'))
        if isinstance(value, dict):
            return value
    except (OSError, ValueError):
        pass
    return {}


def write(value):
    temporary = core.DATA / 'maintenance.tmp'
    temporary.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    temporary.replace(core.DATA / 'maintenance.json')


def due(value, current):
    for key in ('next_attempt',):
        try:
            if datetime.fromisoformat(value[key]) > current:
                return False
        except (KeyError, TypeError, ValueError):
            pass
    try:
        name = value.get('file', '')
        valid = isinstance(name, str) and NAME.fullmatch(name) and (core.DATA / 'backups' / name).is_file()
        if valid and current - datetime.fromisoformat(value['last_success']) < timedelta(hours=24):
            return False
    except (KeyError, TypeError, ValueError):
        pass
    return True


def snapshot():
    source = core.DATA / 'studio.sqlite'
    directory = core.DATA / 'backups'
    directory.mkdir(exist_ok=True)
    # The application instance lock excludes other writers to this data folder.
    # An interrupted snapshot has never been accepted as a recovery copy.
    for stale in directory.iterdir():
        if stale.suffix == '.tmp' and NAME.fullmatch(stale.with_suffix('.sqlite').name):
            stale.unlink()
    size = source.stat().st_size
    if size > MAX_DATABASE:
        raise ValueError('database_limit')
    if shutil.disk_usage(core.DATA).free < MIN_FREE + size * 2:
        raise ValueError('storage')
    name = 'studio-' + core.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:12] + '.sqlite'
    final = directory / name
    temporary = final.with_suffix('.tmp')
    deadline = time.monotonic() + 30
    page_size = 4096

    def progress(status, remaining, total):
        if time.monotonic() > deadline:
            raise TimeoutError('backup_timeout')
        if total * page_size > MAX_DATABASE:
            raise ValueError('database_limit')
        if shutil.disk_usage(core.DATA).free < MIN_FREE:
            raise ValueError('storage')

    try:
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=2)) as origin:
            page_size = origin.execute('PRAGMA page_size').fetchone()[0]
            destination = sqlite3.connect(temporary)
            try:
                origin.backup(destination, pages=128, progress=progress, sleep=.05)
                destination.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
                if destination.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                    raise ValueError('integrity')
                if destination.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('references')
            finally:
                destination.close()
        if temporary.stat().st_size > MAX_DATABASE:
            raise ValueError('database_limit')
        with temporary.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        temporary.replace(final)
        # Only our exact snapshot names are eligible for retention.
        files = sorted((p for p in directory.iterdir() if NAME.fullmatch(p.name) and p.is_file()),
                       key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
        for old in files[KEEP:]:
            if old != final:
                old.unlink()
        return {'file': name, 'sha256': digest, 'bytes': final.stat().st_size,
                'last_success': core.stamp(), 'status': 'ok', 'next_attempt': None,
                'message': 'Cópia local do banco verificada. Vídeos e credenciais são armazenados separadamente.'}
    finally:
        temporary.unlink(missing_ok=True)


def tick():
    if not _lock.acquire(blocking=False):
        return None
    try:
        previous = read()
        if not due(previous, core.now()):
            return None
        try:
            result = snapshot()
        except (OSError, ValueError, sqlite3.Error, TimeoutError):
            result = {**previous, 'status': 'warning', 'next_attempt': (core.now() + timedelta(minutes=30)).isoformat(),
                      'message': 'Cópia local pendente. Confira espaço e acesso à pasta; nova tentativa em 30 minutos.'}
        write(result)
        return result
    finally:
        _lock.release()


def state():
    value = read()
    return {'status': value.get('status', 'pending'), 'last_success': value.get('last_success'),
            'message': value.get('message', 'A primeira cópia local será verificada após abrir o programa.'),
            'next_attempt': value.get('next_attempt')}
