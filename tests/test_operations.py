from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
import autopilot,catalog,content_engine,core,diagnostics,youtube_client as yt


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start()
        core.init();autopilot.init();catalog.init();yt.init();diagnostics.init()
        content_engine.configure({'mode':'rules'})
        self.pid=core.save_product({'name':'Produto de teste','url':'https://example.com/produto?ref=meu-id',
          'kind':'physical','category':'Teste','description':'Possui três divisórias e estrutura em madeira.'})

    def tearDown(self):
        self.override.stop();self.temp.cleanup()

    def publication(self,hour,clicks,recorded=True):
        jid=core.create_job({'product_id':self.pid})
        published=(core.now()-timedelta(days=20)).replace(hour=hour,minute=0,second=0)
        with core.db() as c:c.execute("UPDATE jobs SET status='published',published_at=?,clicks=?,results_recorded_at=? WHERE id=?",(published.isoformat(),clicks,core.stamp() if recorded else None,jid))
        return jid

    def samples(self):
        for _ in range(3):self.publication(12,2);self.publication(18,15)

    def failed_render(self):
        autopilot.approve_product(self.pid,{'active':True,'approved':True})
        autopilot.configure({'enabled':True,'hours':[18]})
        jid=autopilot.cycle()
        with core.db() as c:
            c.execute("UPDATE jobs SET status='error' WHERE id=?",(jid,))
            c.execute('UPDATE auto_jobs SET render_failures=3 WHERE job_id=?',(jid,))
        return jid

    def test_unreported_publications_do_not_teach_zero_clicks(self):
        for _ in range(3):self.publication(12,0,False);self.publication(18,0,False)
        self.assertFalse(core.suggestion()['learned'])
        self.assertEqual(diagnostics.state()['pending_results'],6)

    def test_explicit_zero_results_count_as_observations(self):
        for hour in [12,12,12,18,18,18]:self.publication(hour,0,True)
        self.assertTrue(core.suggestion()['learned'])
        self.assertEqual(diagnostics.state()['pending_results'],0)

    def test_adaptive_timing_requires_samples_and_honors_rank(self):
        config={**autopilot.settings(),'timing_mode':'history','hours':[9]}
        self.assertEqual(autopilot.timing(config)['hours'],[9])
        self.assertFalse(autopilot.timing(config)['learned'])
        self.samples()
        self.assertEqual(autopilot.timing(config)['hours'][0],18)
        current=core.now().replace(hour=8,minute=0,second=0)
        self.assertEqual(autopilot.next_slot(config,current).hour,18)

    def test_fixed_timing_does_not_change_when_history_is_available(self):
        self.samples()
        config={**autopilot.settings(),'timing_mode':'fixed','hours':[9]}
        self.assertEqual(autopilot.timing(config)['hours'],[9])
        self.assertFalse(autopilot.timing(config)['learned'])
        with self.assertRaises(ValueError):autopilot.configure({'timing_mode':'invented'})

    def test_cooldown_starts_at_publication_not_early_render(self):
        jid=self.failed_render()
        with core.db() as c:c.execute("UPDATE jobs SET status='published',published_at=?,created_at=? WHERE id=?",((core.now()-timedelta(days=1)).isoformat(),(core.now()-timedelta(days=20)).isoformat(),jid))
        self.assertEqual(autopilot.candidates(autopilot.settings(),core.now()),[])
        self.assertEqual(len(autopilot.candidates(autopilot.settings(),core.now()+timedelta(days=8))),1)

    def test_migration_preserves_manual_zero_results_without_inventing_automatic_results(self):
        manual=self.publication(12,0,False);automatic=self.publication(18,0,False)
        with core.db() as c:
            c.execute("INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,'published','abcdefghijk',?)",(automatic,core.stamp()))
            c.execute('ALTER TABLE jobs DROP COLUMN results_recorded_at')
        core.init()
        self.assertIsNotNone(core.get_job(manual)['results_recorded_at'])
        self.assertIsNone(core.get_job(automatic)['results_recorded_at'])

    def test_retry_resets_only_local_render_failures(self):
        jid=self.failed_render();diagnostics.retry_render(jid)
        self.assertEqual(core.get_job(jid)['status'],'queued')
        with core.db() as c:row=c.execute('SELECT render_failures,retry_at FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()
        self.assertEqual(row['render_failures'],0);self.assertIsNone(row['retry_at'])

    def test_retry_rejects_any_external_upload_record(self):
        jid=self.failed_render()
        with core.db() as c:c.execute("INSERT INTO youtube_jobs(job_id,stage,updated_at) VALUES (?,'uncertain',?)",(jid,core.stamp()))
        with self.assertRaisesRegex(ValueError,'envio externo'):diagnostics.retry_render(jid)
        self.assertEqual(core.get_job(jid)['status'],'error')

    def test_retry_cannot_override_paused_product_or_paused_routine(self):
        jid=self.failed_render()
        autopilot.approve_product(self.pid,{'active':False,'approved':True})
        with self.assertRaises(ValueError):diagnostics.retry_render(jid)
        autopilot.put_settings({'enabled':False})
        with self.assertRaises(ValueError):diagnostics.retry_render(jid)

    def test_restarted_probe_is_reported_as_interrupted(self):
        diagnostics.write_report(core.DATA,{'status':'running','message':'testing'})
        diagnostics.init()
        self.assertEqual(diagnostics.report()['status'],'error')
        self.assertIn('interrompido',diagnostics.report()['message'])

    def test_malformed_probe_report_does_not_break_dashboard(self):
        diagnostics.report_path().write_text('[]')
        self.assertEqual(diagnostics.report()['status'],'idle')
        self.assertEqual(len(diagnostics.state()['checks']),5)

    def test_probe_is_single_flight_and_does_not_create_product_jobs(self):
        fake=MagicMock();fake.is_alive.return_value=True
        with patch.object(diagnostics,'_thread',fake),patch.object(diagnostics,'run_probe') as generate:
            self.assertEqual(diagnostics.start_probe()['status'],'running')
        generate.assert_not_called()
        self.assertEqual(core.state()['jobs'],[])

    def test_low_disk_blocks_generation_without_network(self):
        with patch.object(diagnostics,'runtime',return_value={'renderer':True,'disk_ok':False,'free_mb':20}):
            with self.assertRaisesRegex(ValueError,'512 MB'):diagnostics.require_runtime()

    def test_probe_failure_report_does_not_expose_exception_content(self):
        with patch('renderer.font',side_effect=ValueError('secret-fixture-not-for-ui')):diagnostics.run_probe(core.DATA)
        report=diagnostics.report()
        self.assertEqual(report['status'],'error')
        self.assertNotIn('secret-fixture',json.dumps(report))
        self.assertIsNone(report['video_url'])

    def test_channel_verification_confirms_configured_channel(self):
        yt.save_secret('tokens',{'access_token':'fixture'})
        yt.put({'channel_id':'UC-fixture'})
        with patch.object(yt,'api',return_value={'items':[{'id':'UC-fixture','snippet':{'title':'Canal de teste'}}]}) as api:
            self.assertTrue(yt.verify_channel()['ok'])
        self.assertEqual(len(api.call_args.args),1)
        self.assertTrue(yt.settings()['channel_verified'])
        self.assertIsNotNone(yt.settings()['last_verified_at'])

    def test_channel_verification_cannot_accept_another_channel(self):
        yt.save_secret('tokens',{'access_token':'fixture'})
        yt.put({'channel_id':'UC-fixture'})
        with patch.object(yt,'api',return_value={'items':[{'id':'different','snippet':{'title':'Outro'}}]}):
            with self.assertRaises(ValueError):yt.verify_channel()
        self.assertFalse(yt.settings()['channel_verified'])

    def test_channel_verification_without_credentials_never_calls_google(self):
        with patch.object(yt,'api') as api:
            with self.assertRaises(ValueError):yt.verify_channel()
        api.assert_not_called()


if __name__=='__main__':unittest.main()
