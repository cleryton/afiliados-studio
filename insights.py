"""Bounded, read-only YouTube counters. Never infers affiliate sales or clicks."""
from datetime import timedelta
import re
import threading
from urllib.parse import urlencode
import core

_lock=threading.Lock()


def init():
    with core.db() as c:c.executescript('''CREATE TABLE IF NOT EXISTS youtube_metrics(
        job_id TEXT PRIMARY KEY REFERENCES jobs(id),video_id TEXT NOT NULL,channel_id TEXT NOT NULL,
        views INTEGER,likes INTEGER,comments INTEGER,checked_at TEXT,last_attempt TEXT NOT NULL,
        next_check TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL DEFAULT '');''')
    purge()


def purge():
    with core.db() as c:c.execute('DELETE FROM youtube_metrics WHERE COALESCE(checked_at,last_attempt)<?',((core.now()-timedelta(days=30)).isoformat(),))


def counter(value):
    if isinstance(value,str) and re.fullmatch('[0-9]{1,18}',value):value=int(value)
    return value if type(value) is int and 0<=value<=10**18-1 else None


def sync():
    import autopilot,youtube_client as yt
    if core.TESTER:return 0
    config=yt.settings()
    if not config['enabled'] or not config['channel_id'] or not yt.secret_path('tokens').is_file() or not autopilot.settings()['enabled']:return 0
    if not _lock.acquire(blocking=False):return 0
    try:
        purge();timestamp=core.stamp();retry=(core.now()+timedelta(minutes=15)).isoformat()
        with core.db() as c:
            c.execute('BEGIN IMMEDIATE')
            rows=c.execute("SELECT jobs.id,youtube_jobs.video_id FROM jobs JOIN youtube_jobs ON youtube_jobs.job_id=jobs.id LEFT JOIN youtube_metrics ON youtube_metrics.job_id=jobs.id WHERE jobs.status='published' AND youtube_jobs.stage='published' AND (youtube_metrics.next_check IS NULL OR youtube_metrics.next_check<=?) ORDER BY COALESCE(youtube_metrics.next_check,jobs.published_at),jobs.id LIMIT 20",(timestamp,)).fetchall()
            rows=[r for r in rows if re.fullmatch('[A-Za-z0-9_-]{11}',r['video_id'])]
            if not rows:return 0
            for row in rows:
                c.execute("INSERT INTO youtube_metrics(job_id,video_id,channel_id,last_attempt,next_check,status) VALUES (?,?,?,?,?,'checking') ON CONFLICT(job_id) DO UPDATE SET last_attempt=excluded.last_attempt,next_check=excluded.next_check,status='checking'",(row['id'],row['video_id'],config['channel_id'],timestamp,retry))
        try:
            response=yt.api('videos?'+urlencode({'part':'snippet,statistics,status','id':','.join(dict.fromkeys(r['video_id'] for r in rows))}))
            items=response.get('items',[])
            if not isinstance(items,list):raise ValueError('Invalid metrics response')
            indexed={item.get('id'):item for item in items if isinstance(item,dict) and isinstance(item.get('id'),str)}
        except Exception:
            with core.db() as c:
                for row in rows:c.execute("UPDATE youtube_metrics SET status='error',error=? WHERE job_id=?",('Não foi possível consultar as métricas. Nova leitura em pelo menos 15 minutos.',row['id']))
            return 0
        if yt.settings()['channel_id']!=config['channel_id'] or not yt.secret_path('tokens').is_file():return 0
        updated=0;next_check=(core.now()+timedelta(hours=6)).isoformat()
        with core.db() as c:
            for row in rows:
                video=indexed.get(row['video_id'],{})
                snippet=video.get('snippet') or {};status=video.get('status') or {};stats=video.get('statistics') or {}
                valid=isinstance(snippet,dict) and isinstance(status,dict) and isinstance(stats,dict)
                valid=valid and snippet.get('channelId')==config['channel_id'] and status.get('privacyStatus')=='public'
                views=counter(stats.get('viewCount')) if isinstance(stats,dict) else None
                if not valid or views is None:
                    c.execute("UPDATE youtube_metrics SET status='unavailable',error=?,next_check=? WHERE job_id=?",('Sem contagem pública confirmada para este vídeo no canal conectado.',next_check,row['id']))
                    continue
                c.execute("UPDATE youtube_metrics SET views=?,likes=?,comments=?,checked_at=?,video_id=?,channel_id=?,next_check=?,status='ok',error='' WHERE job_id=?",(views,counter(stats.get('likeCount')),counter(stats.get('commentCount')),core.stamp(),row['video_id'],config['channel_id'],next_check,row['id']))
                updated+=1
        return updated
    finally:_lock.release()


def state():
    purge()
    with core.db() as c:rows=[dict(r) for r in c.execute('SELECT * FROM youtube_metrics')]
    return rows
