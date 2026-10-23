from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import app
import autopilot
import campaigns
import catalog
import content_engine
import core
import production
import youtube_client as yt


class AutonomyCase(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();catalog.init();yt.init()
        content_engine.configure({'mode':'rules'})
        self.item={'id':'sku','name':'Organizador','affiliate_url':'https://example.com/p?af=original',
                   'kind':'physical','description':'Possui três divisórias. Estrutura em madeira.'}

    def product(self,index=0):
        pid=core.save_product({'name':f'Organizador {index}','url':f'https://example.com/{index}?af=original',
                              'kind':'physical','description':self.item['description'],'category':'Casa'})
        autopilot.approve_product(pid,{'active':True,'approved':True})
        return pid

    def ready(self):
        pid=self.product();autopilot.configure({'enabled':True})
        jid=autopilot.cycle()
        with core.db() as c:
            c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
            c.execute('UPDATE products SET description=? WHERE id=?',('Possui quatro divisórias. Estrutura em aço.',pid))
        return pid,jid


class AutonomyTests(AutonomyCase):
    def test_ready_video_refreshes_without_a_publishing_connection(self):
        _,jid=self.ready();before=core.get_job(jid)['scenes']
        claimed=production.claim_next()
        self.assertEqual(claimed[0]['id'],jid)
        self.assertEqual(core.get_job(jid)['scenes'],before)
        job,_=production.prepare(*claimed)
        self.assertIn('quatro divisórias',job['scenes'])
        self.assertEqual(production.refresh_ready(),[])
        self.assertIn('af=original',job['caption'])

    def test_ready_refresh_preserves_manual_edits_and_requests_review(self):
        _,jid=self.ready()
        with core.db() as c:
            meta=json.loads(c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()[0]);meta['edited']=True
            c.execute('UPDATE content_meta SET payload=? WHERE job_id=?',(json.dumps(meta),jid))
        before=core.get_job(jid)['scenes']
        self.assertEqual(production.refresh_ready(),[jid])
        self.assertEqual(core.get_job(jid)['status'],'draft')
        self.assertEqual(core.get_job(jid)['scenes'],before)
        self.assertEqual(production.refresh_ready(),[])

    def test_only_a_local_hold_without_video_id_can_be_requeued(self):
        _,jid=self.ready()
        for stage,video in [('uncertain',''),('initializing',''),('uploading',''),('failed',''),('held_local','abc12345678')]:
            with core.db() as c:c.execute('INSERT OR REPLACE INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,stage,video,core.stamp()))
            self.assertEqual(production.refresh_ready(),[])
        with core.db() as c:c.execute("UPDATE youtube_jobs SET stage='held_local',video_id='' WHERE job_id=?",(jid,))
        self.assertEqual(production.refresh_ready(),[jid])
        with core.db() as c:self.assertIsNone(c.execute('SELECT 1 FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone())

    def test_buffer_attempt_or_pause_cannot_refresh_a_ready_video(self):
        pid,jid=self.ready()
        autopilot.approve_product(pid,{'approved':True,'active':False})
        self.assertEqual(production.refresh_ready(),[])
        autopilot.approve_product(pid,{'approved':True,'active':True})
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=?",(jid,))
        self.assertEqual(production.refresh_ready(),[])
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='local',buffer_id='existing' WHERE job_id=?",(jid,))
        self.assertEqual(production.refresh_ready(),[])

    def test_refresh_is_claimed_once_by_concurrent_workers(self):
        _,jid=self.ready()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:production.refresh_ready(),range(2)))
        self.assertEqual(sum(jid in result for result in results),1)

    def test_low_storage_waits_without_consuming_a_render_attempt(self):
        self.product();autopilot.configure({'enabled':True});jid=autopilot.cycle()
        with patch('diagnostics.runtime',return_value={'disk_ok':False,'renderer':True,'free_mb':100}):
            self.assertIsNone(production.claim_next())
            self.assertIn('512 MB',production.queue()[0]['detail'])
        with core.db() as c:self.assertEqual(c.execute('SELECT render_failures FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()[0],0)
        self.assertEqual(production.claim_next()[0]['id'],jid)

    def test_missing_local_file_requeues_preserving_current_edited_script(self):
        self.product();autopilot.configure({'enabled':True});jid=autopilot.cycle()
        with core.db() as c:
            meta=json.loads(c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()[0]);meta['edited']=True
            c.execute('UPDATE content_meta SET payload=? WHERE job_id=?',(json.dumps(meta),jid))
            c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
        before=core.get_job(jid)['scenes']
        self.assertEqual(production.refresh_ready(),[jid])
        job,_=production.prepare(*production.claim_next())
        self.assertEqual(job['scenes'],before)

    def test_pause_or_source_change_during_generation_cannot_create_work(self):
        pid=self.product();autopilot.configure({'enabled':True});generate=content_engine.generate
        for change in ('pause','source','campaign','product'):
            autopilot.put_settings({'enabled':True});autopilot.approve_product(pid,{'active':True,'approved':True})
            def changed(*args,**kwargs):
                result=generate(*args,**kwargs)
                if change=='pause':autopilot.put_settings({'enabled':False})
                elif change=='product':autopilot.approve_product(pid,{'active':False,'approved':True})
                elif change=='campaign':campaigns.save({'name':'Mesa','product_ids':[pid],'active':False})
                else:
                    with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',('Dados modificados enquanto o roteiro era planejado.',pid))
                return result
            with self.subTest(change=change),patch.object(content_engine,'generate',side_effect=changed):
                self.assertIsNone(autopilot.cycle())
            with core.db() as c:c.execute('UPDATE campaigns SET active=1')
        self.assertEqual(core.state()['jobs'],[])

    def parallel_cycles(self):
        options=autopilot.candidates(autopilot.settings(),core.now())
        generate=content_engine.generate;candidates=autopilot.candidates
        barrier=threading.Barrier(2);lock=threading.Lock();calls=0
        def distinct(*args):
            nonlocal calls
            with lock:index=calls;calls+=1
            return [options[index]] if index<2 else candidates(*args)
        def delayed(*args):
            result=generate(*args);barrier.wait(timeout=10);return result
        with patch.object(autopilot,'candidates',side_effect=distinct),patch.object(content_engine,'generate',side_effect=delayed):
            with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(lambda _:autopilot.cycle(),range(2)))

    def test_parallel_planning_reserves_different_slots(self):
        for i in range(2):self.product(i)
        autopilot.configure({'enabled':True,'daily_limit':1,'hours':[12,18]})
        self.assertEqual(sum(bool(jid) for jid in self.parallel_cycles()),2)
        jobs=core.state()['jobs']
        self.assertEqual(len({j['due_at'][:10] for j in jobs}),2)

    def test_parallel_planning_cannot_overfill_backlog(self):
        for i in range(4):self.product(i)
        autopilot.configure({'enabled':True})
        autopilot.cycle();autopilot.cycle()
        self.assertEqual(sum(bool(jid) for jid in self.parallel_cycles()),1)
        self.assertEqual(len(core.state()['jobs']),3)

    def test_youtube_tick_skips_held_backoff_and_other_provider_work(self):
        for i in range(6):self.product(i)
        autopilot.configure({'enabled':True})
        ids=[]
        # Build a historical queue larger than today's production cap.
        for _ in range(6):
            jid=autopilot.cycle();ids.append(jid)
            with core.db() as c:c.execute("UPDATE jobs SET status='published' WHERE id=?",(jid,))
        with core.db() as c:
            c.execute("UPDATE jobs SET status='ready'")
            for jid,stage,due in [(ids[0],'uncertain',None),(ids[1],'failed',None),(ids[2],'processing',(core.now()+timedelta(hours=1)).isoformat())]:
                c.execute('INSERT INTO youtube_jobs(job_id,stage,next_check,updated_at) VALUES (?,?,?,?)',(jid,stage,due,core.stamp()))
            c.execute("UPDATE auto_jobs SET delivery='draft',buffer_id='buffer-post' WHERE job_id=?",(ids[3],))
        yt.put({'enabled':True})
        with patch.object(core,'TESTER',False),patch.object(yt,'process') as process,patch('insights.sync'):
            yt.tick()
        self.assertEqual({call.args[0]['id'] for call in process.call_args_list},set(ids[4:]))

    def test_paused_campaign_is_not_counted_as_ready_product(self):
        pid=self.product();campaigns.save({'name':'Mesa','product_ids':[pid],'active':False})
        with patch.object(yt,'state',return_value={'connected':True}):
            self.assertEqual(app.readiness(),{'products':0,'channel':True,'ready':False})


class CatalogContinuityTests(AutonomyCase):
    def configure_source(self):
        catalog.configure({'url':'https://example.com/catalog.json','enabled':True,'authorized':True})

    def test_transient_retries_persist_backoff_and_reset_after_success(self):
        self.configure_source();clock=core.now()
        for minutes in (5,15,30,60,120,240,240):
            with patch('core.now',return_value=clock),patch.object(catalog,'fetch',side_effect=catalog.FetchError('Sem resposta.',True)) as fetch:
                catalog.tick();catalog.tick()
                self.assertEqual(fetch.call_count,1)
                due=datetime.fromisoformat(catalog.settings()['next_check'])
                self.assertEqual(due-clock,timedelta(minutes=minutes))
                catalog.init();catalog.tick();self.assertEqual(fetch.call_count,1)
            clock=due
        with patch('core.now',return_value=clock),patch.object(catalog,'fetch',return_value=[self.item]):catalog.tick()
        config=catalog.settings()
        self.assertEqual(config['failures'],0);self.assertEqual(config['last_error'],'')
        self.assertEqual(datetime.fromisoformat(config['next_check'])-clock,timedelta(hours=4))

    def test_invalid_catalog_preserves_previous_source_and_waits_four_hours(self):
        catalog.ingest([self.item],True);before=core.state()['products']
        self.configure_source();clock=core.now()
        with patch('core.now',return_value=clock),patch.object(catalog,'fetch',return_value=[{**self.item,'description':'inválido'}]):catalog.tick()
        self.assertEqual(core.state()['products'],before)
        self.assertEqual(datetime.fromisoformat(catalog.settings()['next_check'])-clock,timedelta(hours=4))
        self.assertIsNotNone(catalog.settings()['last_success'])

    def test_pausing_or_switching_source_discards_response_in_flight(self):
        for enabled in (False,True):
            self.configure_source()
            def fetch(_):
                catalog.configure({'url':'https://example.com/new.json','enabled':enabled,'authorized':True})
                return [self.item]
            with patch.object(catalog,'fetch',side_effect=fetch):catalog.tick()
            self.assertEqual(core.state()['products'],[])
            self.assertEqual(catalog.settings()['url'],'https://example.com/new.json')
            self.assertIsNone(catalog.settings()['next_check'])

    def test_manual_import_during_fetch_wins_over_old_response_or_failure(self):
        for fails in (False,True):
            self.configure_source()
            def fetch(_):
                catalog.ingest([{**self.item,'name':'Escolha atual'}],True)
                if fails:raise catalog.FetchError('Consulta antiga falhou.',True)
                return [self.item]
            with patch.object(catalog,'fetch',side_effect=fetch):catalog.tick()
            self.assertEqual(core.state()['products'][0]['name'],'Escolha atual')
            self.assertEqual(catalog.settings()['last_error'],'')

    def test_two_ticks_make_one_external_read(self):
        self.configure_source();entered=threading.Event();release=threading.Event()
        def fetch(_):
            entered.set();release.wait(5);return [self.item]
        with patch.object(catalog,'fetch',side_effect=fetch) as fetch_mock:
            with ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(catalog.tick);self.assertTrue(entered.wait(5))
                second=pool.submit(catalog.tick);second.result(timeout=5);release.set();first.result(timeout=5)
            self.assertEqual(fetch_mock.call_count,1)


if __name__=='__main__':unittest.main()
