from datetime import timedelta
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import autopilot
import buffer_client
import core
import media_bridge
import catalog


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start()
        core.init();autopilot.init();catalog.init()
        self.product={'name':'Produto de teste','url':'https://example.com/p?afiliado=abc','kind':'digital','description':'Conteúdo demonstrativo com características verificadas para os testes locais.','category':'Teste','price':100,'commission':20}

    def tearDown(self):
        self.override.stop();self.temp.cleanup()

    def approve(self):
        pid=core.save_product(self.product)
        autopilot.approve_product(pid,{'active':True,'approved':True})
        return pid

    def enable(self):
        autopilot.configure({'enabled':True,'daily_limit':1,'cooldown_days':7,'hours':[12,18,20]})

    def ready(self):
        self.approve();self.enable();jid=autopilot.cycle()
        with core.db() as c:c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
        autopilot.put_settings({'send_drafts':True,'channel_id':'channel-test'})
        return jid

    def test_no_generation_without_activation_and_approval(self):
        core.save_product(self.product)
        self.assertIsNone(autopilot.cycle())
        self.enable();self.assertIsNone(autopilot.cycle())
        self.assertEqual(core.state()['jobs'],[])

    def test_generation_respects_daily_limit_unique_product_and_finite_backlog(self):
        for _ in range(5):self.approve()
        self.enable()
        ids=[autopilot.cycle() for _ in range(4)]
        self.assertEqual(sum(bool(i) for i in ids),3)
        jobs=core.state()['jobs']
        self.assertEqual(len({j['product_id'] for j in jobs}),3)
        self.assertEqual(len({j['due_at'][:10] for j in jobs}),3)
        self.assertTrue(all(j['status']=='queued' and j['rights']==1 for j in jobs))
        self.assertTrue(all(self.product['url'] in j['caption'] for j in jobs))

    def test_unverified_product_cannot_be_enabled(self):
        pid=core.save_product({**self.product,'description':''})
        with self.assertRaises(ValueError):autopilot.approve_product(pid,{'active':True,'approved':True})

    def test_buffer_channel_must_have_been_validated(self):
        with self.assertRaises(ValueError):autopilot.configure({'enabled':True,'send_drafts':True,'channel_id':'made-up'})

    def test_cooldown_and_variant_limits(self):
        self.approve();self.enable();jid=autopilot.cycle()
        with core.db() as c:c.execute("UPDATE jobs SET status='published' WHERE id=?",(jid,))
        self.assertIsNone(autopilot.cycle())
        future=core.now()+timedelta(days=8)
        with patch('core.now',return_value=future):second=autopilot.cycle()
        self.assertIsNotNone(second)
        self.assertNotEqual(core.get_job(jid)['scenes'],core.get_job(second)['scenes'])

    def test_expenses_reduce_return_and_no_credentials_in_state(self):
        autopilot.expense({'description':'Energia','amount':15})
        state=autopilot.state()
        self.assertEqual(state['profit']['net'],-15)
        self.assertNotIn('key',state['settings'])
        self.assertFalse(state['buffer']['automatic_commercial_posting'])

    def test_sender_stores_id_once_and_never_claims_publication_for_draft(self):
        jid=self.ready()
        with patch('buffer_client.create_draft',return_value={'id':'remote-1','status':'draft'}) as create:
            autopilot.delivery_cycle(lambda _: 'https://example.com/video.mp4')
            autopilot.delivery_cycle(lambda _: 'https://example.com/video.mp4')
            self.assertEqual(create.call_count,1)
        row=autopilot.state()['runs'][0]
        self.assertEqual(row['buffer_id'],'remote-1')
        self.assertEqual(row['delivery'],'draft')
        self.assertEqual(core.get_job(jid)['status'],'ready')

    def test_unknown_send_is_not_blindly_repeated(self):
        self.ready()
        with patch('buffer_client.create_draft',side_effect=TimeoutError('Resposta perdida')) as create:
            autopilot.delivery_cycle(lambda _: 'https://example.com/video.mp4')
            autopilot.delivery_cycle(lambda _: 'https://example.com/video.mp4')
            self.assertEqual(create.call_count,1)
        self.assertEqual(autopilot.state()['runs'][0]['delivery'],'uncertain')

    def test_restart_marks_inflight_delivery_unknown(self):
        jid=self.ready()
        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=?",(jid,))
        autopilot.init()
        self.assertEqual(autopilot.state()['runs'][0]['delivery'],'uncertain')

    def test_render_retry_is_bounded_and_does_not_retry_external_sends(self):
        jid=self.ready()
        for count in range(3):
            with core.db() as c:c.execute("UPDATE jobs SET status='error' WHERE id=?",(jid,))
            autopilot.render_failed(jid)
            self.assertEqual(core.get_job(jid)['status'],'queued' if count<2 else 'error')
        row=autopilot.state()['runs'][0]
        self.assertEqual(row['render_failures'],3)
        self.assertIsNone(row['retry_at'])

    def test_draft_request_keeps_native_commercial_step_pending(self):
        with patch('buffer_client.query',return_value={'createPost':{'post':{'id':'remote-test','status':'draft'}}}) as query:
            buffer_client.create_draft('channel','Publicidade','https://example.com/video.mp4',True)
            payload=query.call_args.args[1]['input']
            self.assertTrue(payload['saveToDraft'])
            self.assertEqual(payload['metadata']['tiktok'],{'isAiGenerated':True})
            self.assertEqual(payload['schedulingType'],'automatic')

    def test_reconcile_rejects_another_channel_and_can_link_existing_post(self):
        jid=self.ready()
        with patch('buffer_client.get_post',return_value={'id':'remote','channelId':'wrong-channel'}):
            with self.assertRaises(ValueError):autopilot.reconcile(jid,'remote')
        with patch('buffer_client.get_post',return_value={'id':'remote','channelId':'channel-test','status':'draft'}):
            autopilot.reconcile(jid,'remote')
        self.assertEqual(autopilot.state()['runs'][0]['buffer_id'],'remote')

    def test_public_bridge_accepts_only_signed_video_and_expires(self):
        jid='b'*32;folder=core.DATA/'media'/jid;folder.mkdir();(folder/'video.mp4').write_bytes(b'example video')
        expiry=int(time.time()+600)
        valid=f'/video/{jid}.mp4?expires={expiry}&signature={media_bridge.signature(jid,expiry)}'
        self.assertEqual(media_bridge.validate(valid),folder/'video.mp4')
        for invalid in ['/api/state','/../studio.sqlite',valid.replace('signature=','signature=x'),valid.replace(str(expiry),'1')]:
            with self.subTest(path=invalid):self.assertIsNone(media_bridge.validate(invalid))

    @unittest.skipUnless(os.name=='nt','Windows DPAPI')
    def test_windows_key_protection_roundtrip(self):
        value=b'synthetic-test-value-only'
        encrypted=buffer_client.crypt(value)
        self.assertNotIn(value,encrypted)
        self.assertEqual(buffer_client.crypt(encrypted,decrypt=True),value)


if __name__=='__main__':unittest.main()
