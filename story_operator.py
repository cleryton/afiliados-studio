"""Compact, read-only view for an operator using the native Studio checkpoints."""
import core
import cartoon_month
import story_delivery


def state():
    month=cartoon_month.state()
    if not month:return {'available':False,'message':'Nenhuma reserva mensal preparada.'}
    target=story_delivery.target()
    if target!='novelitas0213' or month['handle']!=target or core.TESTER:
        return {'available':False,'message':'Confira o perfil exclusivo e o modo normal.'}
    item=month['next_item']
    result={'available':True,'handle':target,'confirmed':month['confirmed'],'total':month['total'],
            'ready':month['ready'],'archived':month['archived'],'paused':bool(month['paused']),'item':item}
    if not item:return result
    with core.db() as c:
        attempt=c.execute('SELECT id,stage,reason FROM story_native_attempts WHERE media_id=? AND handle=? ORDER BY created_at DESC LIMIT 1',
                          (item['media_id'],target)).fetchone()
    result['attempt']=dict(attempt) if attempt else None
    if item['status']=='ready' and not month['paused']:
        cartoon_month.snapshot(item['media_id'])
        result['file']=str(core.DATA/'stories'/item['media_id']/'video.mp4')
        result['caption']=(core.DATA/'stories'/item['media_id']/'legenda.txt').read_text(encoding='utf-8')
    return result
