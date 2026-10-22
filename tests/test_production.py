from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import autopilot
import campaigns
import catalog
import content_engine
import core
import production
import youtube_client
from instance_lock import InstanceLock


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();catalog.init();youtube_client.init()
        content_engine.configure({'mode':'rules'})
        self.item={'name':'Organizador','url':'https://example.com/p?af=original','kind':'physical','category':'Casa',
                   'description':'Possui três divisórias. Estrutura em madeira.'}

    def auto(self):
        pid=core.save_product(self.item)
        autopilot.approve_product(pid,{'active':True,'approved':True})
        autopilot.configure({'enabled':True})
        jid=autopilot.cycle()
        return pid,jid

    def manual(self):
        pid=core.save_product(self.item);jid=core.create_job({'product_id':pid});job=core.get_job(jid)
        core.edit_job(jid,{'scenes':json.loads(job['scenes']),'caption':job['caption'],'due_at':job['due_at'],'rights':True,'action':'render'})
        return pid,jid

    def test_two_workers_cannot_claim_same_video(self):
        _,jid=self.auto()
        with ThreadPoolExecutor(max_workers=2) as pool:claims=list(pool.map(lambda _:production.claim_next(),range(2)))
        self.assertEqual(sum(bool(c) for c in claims),1)
        self.assertEqual(core.get_job(jid)['status'],'rendering')

    def test_paused_product_waits_without_blocking_another_video(self):
        pid,jid=self.auto();_,manual=self.manual()
        autopilot.approve_product(pid,{'active':False,'approved':True})
        claimed=production.claim_next()
        self.assertEqual(claimed[0]['id'],manual)
        self.assertEqual(core.get_job(jid)['status'],'queued')
        self.assertEqual(next(r for r in production.queue() if r['id']==jid)['state'],'blocked')

    def test_routine_pause_blocks_automatic_but_allows_explicit_manual_generation(self):
        _,jid=self.auto();_,manual=self.manual();autopilot.put_settings({'enabled':False})
        self.assertEqual(production.claim_next()[0]['id'],manual)
        self.assertEqual(core.get_job(jid)['status'],'queued')

    def test_campaign_pause_is_checked_before_render_and_resumes(self):
        pid,jid=self.auto()
        cid=campaigns.save({'name':'Casa','active':False,'product_ids':[pid]})
        self.assertIsNone(production.claim_next())
        self.assertIn('Campanha',production.queue()[0]['detail'])
        campaigns.save({'name':'Casa','active':True,'product_ids':[pid]},cid)
        self.assertEqual(production.claim_next()[0]['id'],jid)

    def test_stale_catalog_and_unconfirmed_materials_do_not_render(self):
        pid,jid=self.auto()
        with core.db() as c:c.execute('INSERT INTO catalog_items VALUES (?,?,?,?)',('sku',pid,1,(core.now()-timedelta(days=2)).isoformat()))
        self.assertIsNone(production.claim_next())
        with core.db() as c:
            c.execute('UPDATE catalog_items SET last_seen=?',(core.stamp(),))
            c.execute('UPDATE jobs SET rights=0 WHERE id=?',(jid,))
        self.assertIsNone(production.claim_next())
        self.assertEqual(production.queue()[0]['state'],'blocked')

    def test_source_refresh_happens_before_render_and_preserves_affiliate_link(self):
        pid,jid=self.auto()
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Possui quatro divisórias. Estrutura em aço.',pid))
        job,product=production.prepare(*production.claim_next())
        self.assertIn('Possui quatro divisórias.',json.loads(job['scenes']))
        self.assertIn(self.item['url'],job['caption'])
        with core.db() as c:meta=json.loads(c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()[0])
        self.assertFalse(production.changed(product,meta))

    def test_source_change_during_planning_requeues_instead_of_rendering_old_data(self):
        pid,jid=self.auto()
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Possui quatro divisórias. Estrutura em aço.',pid))
        claimed=production.claim_next();original=content_engine.generate
        def generate(*args,**kwargs):
            result=original(*args,**kwargs)
            with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Possui cinco divisórias. Estrutura em aço.',pid))
            return result
        with patch.object(content_engine,'generate',side_effect=generate):self.assertIsNone(production.prepare(*claimed))
        self.assertEqual(core.get_job(jid)['status'],'queued')

    def test_manual_source_changes_require_recreation_and_preserve_edited_text(self):
        pid,jid=self.manual();before=core.get_job(jid)['scenes']
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Descrição alterada depois da revisão.',pid))
        self.assertIsNone(production.prepare(*production.claim_next()))
        self.assertEqual(core.get_job(jid)['status'],'draft')
        self.assertEqual(core.get_job(jid)['scenes'],before)

    def test_automatic_job_with_manual_edit_is_not_silently_replaced(self):
        pid,jid=self.auto();job=core.get_job(jid);scenes=json.loads(job['scenes'])
        scenes[0]='Minha pergunta editorial revisada sobre as características?'
        with core.db() as c:c.execute("UPDATE jobs SET status='draft' WHERE id=?",(jid,))
        core.edit_job(jid,{'scenes':scenes,'caption':job['caption'],'due_at':job['due_at'],'rights':True,'action':'render'})
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Descrição atualizada depois da edição manual.',pid))
        self.assertIsNone(production.prepare(*production.claim_next()))
        self.assertEqual(json.loads(core.get_job(jid)['scenes'])[0],scenes[0])
        self.assertEqual(core.get_job(jid)['status'],'draft')

    def test_pause_during_planning_requeues_without_starting_encoder(self):
        pid,jid=self.auto()
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Dados atualizados antes da preparação do vídeo.',pid))
        claimed=production.claim_next();original=content_engine.generate
        def generate(*args,**kwargs):
            result=original(*args,**kwargs);autopilot.put_settings({'enabled':False});return result
        with patch.object(content_engine,'generate',side_effect=generate):self.assertIsNone(production.prepare(*claimed))
        self.assertEqual(core.get_job(jid)['status'],'queued')
        self.assertEqual(production.queue()[0]['state'],'blocked')

    def test_restart_recovers_local_automatic_job_once_with_bounded_delay(self):
        _,jid=self.auto();production.claim_next();core.init()
        self.assertEqual(core.get_job(jid)['status'],'error')
        self.assertIsNone(production.claim_next())
        self.assertEqual(core.get_job(jid)['status'],'queued')
        with core.db() as c:self.assertEqual(c.execute('SELECT render_failures FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()[0],1)
        core.init();production.recover_interrupted()
        self.assertEqual(production.queue()[0]['state'],'retry')
        future=core.now()+timedelta(minutes=3)
        with patch('core.now',return_value=future):self.assertEqual(production.claim_next()[0]['id'],jid)

    def test_three_interrupted_renders_stop_without_endless_retries(self):
        _,jid=self.auto()
        for i in range(3):
            with patch('core.now',return_value=core.now()+timedelta(hours=i)):
                self.assertIsNotNone(production.claim_next());core.init();production.recover_interrupted()
        self.assertEqual(core.get_job(jid)['status'],'error')
        production.recover_interrupted()
        with core.db() as c:self.assertEqual(c.execute('SELECT render_failures FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()[0],3)

    def test_manual_interrupted_job_requires_manual_retry(self):
        _,jid=self.manual();production.claim_next();core.init();production.recover_interrupted()
        self.assertEqual(core.get_job(jid)['status'],'error')

    def test_external_attempts_never_recover_or_render_again(self):
        _,jid=self.auto();production.claim_next();core.init()
        with core.db() as c:c.execute('INSERT INTO youtube_jobs(job_id,stage,updated_at) VALUES (?,?,?)',(jid,'uncertain',core.stamp()))
        production.recover_interrupted()
        self.assertEqual(core.get_job(jid)['status'],'error')
        with core.db() as c:
            c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(jid,))
            c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=?",(jid,))
        production.recover_interrupted()
        self.assertEqual(core.get_job(jid)['status'],'error')

    def test_lock_prevents_second_process_and_releases_after_exit(self):
        script='''
import sys
from instance_lock import InstanceLock
try:
    with InstanceLock(sys.argv[1]): pass
except ValueError: sys.exit(23)
'''
        with InstanceLock(core.DATA):
            result=subprocess.run([sys.executable,'-c',script,str(core.DATA)],capture_output=True,timeout=10)
            self.assertEqual(result.returncode,23)
        result=subprocess.run([sys.executable,'-c',script,str(core.DATA)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0)
