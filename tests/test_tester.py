import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import autopilot,buffer_client,catalog,content_engine,core,diagnostics,support,youtube_client as yt


class TesterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start()
        self.mode=patch.object(core,'TESTER',True);self.mode.start()
        core.init();autopilot.init();catalog.init();yt.init();diagnostics.init()
        content_engine.configure({'mode':'rules'})

    def tearDown(self):
        self.mode.stop();self.override.stop();self.temp.cleanup()

    def test_demo_creates_local_job_and_reuses_unpublished_work(self):
        first=support.create_demo();second=support.create_demo()
        self.assertEqual(first['id'],second['id'])
        state=core.state()
        self.assertEqual(len(state['products']),1);self.assertEqual(len(state['jobs']),1)
        self.assertEqual(state['jobs'][0]['status'],'queued')
        self.assertIn('sem comissão',state['products'][0]['name'])
        self.assertIn(support.DEMO_URL,state['jobs'][0]['caption'])
        self.assertEqual(state['jobs'][0]['rights'],1)
        self.assertFalse(yt.settings()['enabled'])

    def test_demo_cannot_add_fake_product_to_normal_mode(self):
        with patch.object(core,'TESTER',False),self.assertRaises(ValueError):support.create_demo()
        self.assertEqual(core.state()['products'],[])

    def test_youtube_workers_and_process_never_send_in_tester(self):
        yt.put({'enabled':True})
        with patch.object(yt,'api') as api,patch.object(yt,'initialize_upload') as upload:
            yt.tick();yt.process({},{})
        api.assert_not_called();upload.assert_not_called()

    def test_youtube_upload_entrypoints_and_mutations_are_blocked(self):
        with patch.object(yt,'urlopen') as network:
            with self.assertRaises(ValueError):yt.api('videos',{'status':{}},'PUT')
            with self.assertRaises(ValueError):yt.initialize_upload({}, {}, Path('absent.mp4'))
            with self.assertRaises(ValueError):yt.transfer('test',Path('absent.mp4'))
            with self.assertRaises(ValueError):yt.begin(8766)
            with self.assertRaises(ValueError):yt.configure({'enabled':True})
        network.assert_not_called()

    def test_buffer_drafts_and_background_delivery_are_blocked(self):
        with patch.object(buffer_client,'query') as query:
            with self.assertRaises(ValueError):buffer_client.create_draft('channel','caption','https://example.com/video.mp4')
            autopilot.delivery_cycle(lambda _:self.fail('A ponte não deve ser chamada.'))
            autopilot.sync()
        query.assert_not_called()
        with self.assertRaises(ValueError):autopilot.configure({'enabled':True,'send_drafts':True})

    def test_support_report_never_includes_account_or_product_details(self):
        result=support.create_demo();job=core.get_job(result['id'])
        with core.db() as c:
            c.execute('UPDATE products SET name=?,url=? WHERE id=?',('NOME-PESSOAL-FIXTURE','https://example.com/segredo?affiliate=nao-compartilhar',job['product_id']))
            c.execute('UPDATE jobs SET caption=?,error=? WHERE id=?',('ROTEIRO-PRIVADO','MENSAGEM-SENSIVEL',job['id']))
        yt.put({'channel_id':'CANAL-PRIVADO','channel_name':'NOME-DA-CONTA'})
        yt.save_secret('client',{'client_secret':'CREDENCIAL-PRIVADA'})
        body=json.dumps(support.report())
        for value in ['NOME-PESSOAL-FIXTURE','nao-compartilhar','ROTEIRO-PRIVADO','MENSAGEM-SENSIVEL','CANAL-PRIVADO','NOME-DA-CONTA','CREDENCIAL-PRIVADA',self.temp.name]:
            self.assertNotIn(value,body)
        self.assertEqual(support.report()['counts']['products'],1)
        self.assertEqual(support.report()['mode'],'tester')

    def test_tester_checks_explain_that_accounts_are_not_required(self):
        check=next(c for c in diagnostics.state()['checks'] if c['label']=='Proteção contra publicação')
        self.assertEqual(check['status'],'ok')
        self.assertIn('não precisa',check['detail'])


if __name__=='__main__':unittest.main()
