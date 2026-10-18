import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import core


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.override = patch.object(core, 'DATA', Path(self.temp.name))
        self.override.start()
        core.init()
        self.product = {'name':'Fone de teste', 'url':'https://example.com/produto?ref=meu-id&origem=tiktok', 'kind':'physical', 'description':'Conexão Bluetooth e estojo de recarga.', 'category':'Tecnologia', 'price':199.9, 'commission':8}

    def tearDown(self):
        self.override.stop()
        self.temp.cleanup()

    def job(self):
        pid = core.save_product(self.product)
        return core.create_job({'product_id':pid})

    def edit(self, jid, **changes):
        job = core.get_job(jid)
        payload = {'scenes':json.loads(job['scenes']), 'caption':job['caption'], 'due_at':job['due_at'], 'rights':True, 'action':'render'}
        payload.update(changes)
        return core.edit_job(jid, payload)

    def test_affiliate_url_persistence_and_no_invented_claims(self):
        jid = self.job()
        state = core.state()
        self.assertEqual(state['products'][0]['url'], self.product['url'])
        self.assertIn(self.product['description'], state['jobs'][0]['scenes'])
        self.assertIn(self.product['url'], state['jobs'][0]['caption'])
        self.assertNotIn('testei', state['jobs'][0]['caption'].lower())
        self.assertFalse(state['posting']['connected'])
        self.assertEqual(core.get_job(jid)['status'], 'draft')

    def test_private_and_unsafe_urls_rejected(self):
        for value in ['file:///etc/passwd','http://localhost/x','http://127.0.0.1/x','http://169.254.169.254/x','http://[::1]/x','https://foo.internal/x','http://example.com:8000/x','https://a:b@example.com']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                core.public_url(value)

    def test_dns_rebinding_blocked_at_socket_connection(self):
        with patch('core.socket.getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1',443))]), patch('core.socket.create_connection') as connect:
            with self.assertRaises(ValueError):
                core.public_connection(('example.com',443))
            connect.assert_not_called()

    def test_redirect_validation(self):
        with self.assertRaises(ValueError):
            core.PublicRedirect().redirect_request(None,None,302,'',{},'http://127.0.0.1/admin')

    def test_metadata_parsing_ignores_script_content(self):
        parser=core.MetadataParser()
        parser.feed('<title>Produto &amp; teste</title><meta property="og:description" content="Descrição &amp; fatos"><script>alert(1)</script>')
        self.assertEqual(parser.title,'Produto & teste')
        self.assertEqual(parser.meta['og:description'],'Descrição & fatos')

    def test_consent_past_schedule_and_busy_state(self):
        jid=self.job()
        with self.assertRaises(ValueError):
            self.edit(jid, rights=False)
        self.assertEqual(core.get_job(jid)['status'],'draft')
        with self.assertRaises(ValueError):
            self.edit(jid, action='schedule',due_at=(core.now()-timedelta(days=1)).isoformat())
        self.assertEqual(self.edit(jid),'queued')
        with self.assertRaises(ValueError):
            self.edit(jid)

    def test_no_duplicate_active_jobs(self):
        jid=self.job()
        pid=core.get_job(jid)['product_id']
        with self.assertRaises(ValueError):
            core.create_job({'product_id':pid})

    def test_invalid_numbers_cannot_poison_totals(self):
        for number in ['NaN','Infinity',-1,True]:
            with self.subTest(number=number),self.assertRaises(ValueError):
                core.numeric(number,100)

    def test_results_need_generated_video_and_tiktok_link(self):
        jid=self.job()
        result={'tiktok_url':'https://www.tiktok.com/@teste/video/123','published_at':core.stamp(),'views':250,'clicks':12,'revenue':17.5}
        with self.assertRaises(ValueError):
            core.record_results(jid,result)
        with core.db() as c:
            c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
        with self.assertRaises(ValueError):
            core.record_results(jid,{**result,'tiktok_url':'https://example.com'})
        core.record_results(jid,result)
        self.assertEqual(core.state()['jobs'][0]['revenue'],17.5)
        self.assertEqual(core.state()['jobs'][0]['status'],'published')

    def test_history_only_recommends_after_comparable_samples(self):
        self.assertFalse(core.suggestion()['learned'])
        for index in range(6):
            jid=self.job()
            when=(core.now()-timedelta(days=10+index)).replace(hour=12 if index<3 else 18)
            with core.db() as c:
                c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
            core.record_results(jid,{'tiktok_url':'https://www.tiktok.com/@teste/video/123','published_at':when.isoformat(),'views':100,'clicks':2 if index<3 else 12,'revenue':0})
        recommendation=core.suggestion()
        self.assertTrue(recommendation['learned'])
        self.assertEqual(recommendation['hours'][0],18)

    def test_restart_preserves_schedule_but_reports_interrupted_render(self):
        jid=self.job()
        self.edit(jid,action='schedule')
        core.init()
        self.assertEqual(core.get_job(jid)['status'],'scheduled')
        with core.db() as c:
            c.execute("UPDATE jobs SET status='rendering' WHERE id=?",(jid,))
        core.init()
        self.assertEqual(core.get_job(jid)['status'],'error')

    def test_schedule_slots_are_not_reused(self):
        self.job()
        initial=core.state()['jobs'][0]['due_at']
        self.job()
        self.assertNotEqual(core.state()['jobs'][0]['due_at'],initial)


if __name__=='__main__':
    unittest.main()
