import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import app
import autopilot
import campaigns
import catalog
import content_engine
import core
import quality
import youtube_client as yt


class EditorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import imageio_ffmpeg
        cls.media=tempfile.TemporaryDirectory(prefix='edição-');cls.fixture=Path(cls.media.name)/'válido.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=green:s=1280x720:r=1','-t','4','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',str(cls.fixture)],check=True,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    @classmethod
    def tearDownClass(cls):cls.media.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='revisão-');self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start();self.addCleanup(self.override.stop);self.addCleanup(self.temp.cleanup)
        core.init();autopilot.init();catalog.init();yt.init();content_engine.configure({'mode':'rules','format':'landscape'})
        self.pid=core.save_product({'name':'Organizador','url':'https://example.com/p?af=real','kind':'physical','category':'Casa','description':'Possui três divisórias para organização.'})

    def campaign(self,**values):
        return campaigns.save({'name':'Home office','audience':'escritórios pequenos','tone':'educativo','cta':'comparar','review_mode':'manual','active':True,'product_ids':[self.pid],**values})

    def ready(self):
        jid=core.create_job({'product_id':self.pid});job=core.get_job(jid)
        with core.db() as c:c.execute("UPDATE jobs SET status='ready',rights=1 WHERE id=?",(jid,))
        directory=core.DATA/'media'/jid;directory.mkdir();(directory/'video.mp4').write_bytes(self.fixture.read_bytes())
        (directory/'conteudo.json').write_text(json.dumps({'scenes':json.loads(job['scenes']),'caption':job['caption'],'format':'landscape','durations':[1]*4}),encoding='utf-8')
        return jid

    def test_brief_shapes_hook_cta_and_keeps_source_facts(self):
        self.campaign();jid=core.create_job({'product_id':self.pid});job=core.get_job(jid);scenes=json.loads(job['scenes'])
        self.assertIn('escritórios pequenos',scenes[0]);self.assertIn('Compare',scenes[-1]);self.assertEqual(scenes[2],'Possui três divisórias para organização.')
        with core.db() as c:meta=json.loads(c.execute('SELECT payload FROM content_meta WHERE job_id=?',(jid,)).fetchone()[0])
        self.assertEqual(meta['campaign']['review_mode'],'manual');self.assertIn('af=real',job['caption'])

    def test_product_assignment_is_unique_and_edit_is_atomic(self):
        cid=self.campaign()
        with self.assertRaises(ValueError):self.campaign(name='Conflito')
        with self.assertRaises(ValueError):campaigns.save({'name':'Não salvar','product_ids':['missing']},cid)
        self.assertEqual(campaigns.state()[0]['name'],'Home office');self.assertEqual(len(campaigns.state()),1)

    def test_paused_campaign_excludes_product_from_automation(self):
        self.campaign(active=False);autopilot.approve_product(self.pid,{'active':True,'approved':True})
        self.assertEqual(autopilot.candidates(autopilot.settings(),core.now()),[])

    def test_missing_or_corrupted_mp4_blocks_approval_and_youtube(self):
        jid=self.ready();file=core.DATA/'media'/jid/'video.mp4';file.write_bytes(b'not a video')
        with self.assertRaises(ValueError):quality.validate_media(jid)
        with self.assertRaises(ValueError):quality.decide(jid,{'decision':'approved'})
        autopilot.approve_product(self.pid,{'active':True,'approved':True})
        with core.db() as c:product=dict(c.execute('SELECT * FROM products').fetchone())
        with patch.object(yt,'initialize_upload') as upload,patch.object(yt,'api') as remote:yt.process(core.get_job(jid),product);upload.assert_not_called();remote.assert_not_called()

    def test_real_decode_and_manual_approval_then_invalidate_edited_script(self):
        self.campaign();jid=self.ready();q=quality.validate_media(jid)
        self.assertEqual(q['status'],'review');self.assertFalse(q['allowed']);self.assertEqual(q['media']['width'],1280)
        self.assertTrue(quality.decide(jid,{'decision':'approved'})['allowed'])
        with core.db() as c:c.execute("UPDATE jobs SET caption=caption||' Alterado' WHERE id=?",(jid,))
        q=quality.inspect(jid);self.assertFalse(q['allowed']);self.assertIsNone(q['decision'])
        with self.assertRaisesRegex(ValueError,'roteiro mudou'):quality.validate_media(jid)

    def test_campaign_change_invalidates_approval_and_regenerate_uses_current_brief(self):
        cid=self.campaign();jid=self.ready();quality.validate_media(jid);quality.decide(jid,{'decision':'approved'})
        campaigns.save({'name':'Novo briefing','audience':'quem organiza a cozinha','product_ids':[self.pid],'review_mode':'manual'},cid)
        self.assertFalse(quality.inspect(jid)['allowed']);core.regenerate_job(jid)
        self.assertEqual(core.get_job(jid)['status'],'draft');self.assertIn('cozinha',core.get_job(jid)['scenes']);self.assertIsNone(quality.inspect(jid)['decision'])

    def test_media_substitution_with_preserved_size_and_time_detected_before_send(self):
        jid=self.ready();quality.validate_media(jid);file=core.DATA/'media'/jid/'video.mp4';stat=file.stat();raw=bytearray(file.read_bytes());raw[-1]^=1;file.write_bytes(raw);os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertFalse(quality.inspect(jid,verify_media=True)['allowed'])

    def test_rejected_content_cannot_pass_automatic_mode(self):
        jid=self.ready();quality.validate_media(jid);self.assertTrue(quality.inspect(jid)['allowed'])
        self.assertFalse(quality.decide(jid,{'decision':'rejected','note':'Revisar texto'})['allowed'])

    def test_remote_delivery_prevents_local_script_replacement_or_review(self):
        jid=self.ready()
        with core.db() as c:c.execute('INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,'processing','abc12345678',core.stamp()))
        with self.assertRaises(ValueError):core.regenerate_job(jid)
        with self.assertRaises(ValueError):quality.decide(jid,{'decision':'rejected'})

    def test_pending_manual_review_blocks_buffer_before_media_exposure(self):
        self.campaign();jid=self.ready();quality.validate_media(jid)
        with core.db() as c:c.execute('INSERT INTO auto_jobs(job_id,variant) VALUES (?,0)',(jid,))
        autopilot.put_settings({'enabled':True,'send_drafts':True,'channel_id':'fixture'})
        with patch('buffer_client.create_draft') as send,patch('media_bridge.media_url') as expose:autopilot.delivery_cycle(expose);send.assert_not_called();expose.assert_not_called()

    def test_pending_manual_review_blocks_youtube_initial_upload(self):
        self.campaign();jid=self.ready();quality.validate_media(jid);autopilot.approve_product(self.pid,{'active':True,'approved':True})
        with core.db() as c:product=dict(c.execute('SELECT * FROM products').fetchone())
        with patch.object(yt,'initialize_upload') as upload,patch.object(yt,'api') as remote:yt.process(core.get_job(jid),product);upload.assert_not_called();remote.assert_not_called()

    def test_missing_review_holds_remote_private_before_scheduling(self):
        self.campaign();jid=self.ready();quality.validate_media(jid);autopilot.approve_product(self.pid,{'active':True,'approved':True})
        with core.db() as c:
            product=dict(c.execute('SELECT * FROM products').fetchone())
            c.execute('INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,'processing','abc12345678',core.stamp()))
        with patch.object(yt,'api',return_value={}) as remote:
            yt.process(core.get_job(jid),product)
            self.assertEqual(remote.call_count,1);self.assertEqual(remote.call_args.args[1]['status']['privacyStatus'],'private')
        with core.db() as c:self.assertEqual(c.execute('SELECT stage FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()[0],'held')

    def test_uncertain_buffer_send_prevents_script_replacement_and_review(self):
        jid=self.ready()
        with core.db() as c:c.execute("INSERT INTO auto_jobs(job_id,variant,delivery) VALUES (?,0,'uncertain')",(jid,))
        with self.assertRaisesRegex(ValueError,'Buffer'):core.regenerate_job(jid)
        with self.assertRaisesRegex(ValueError,'Buffer'):quality.decide(jid,{'decision':'rejected'})

    def test_shortened_product_name_also_invalidates_quality(self):
        jid=self.ready();quality.validate_media(jid)
        with core.db() as c:c.execute("UPDATE products SET name='Organiza' WHERE id=?",(self.pid,))
        self.assertFalse(quality.inspect(jid)['allowed'])

    def test_regeneration_never_preserves_previous_approval_even_when_text_unchanged(self):
        self.campaign();jid=self.ready();quality.validate_media(jid);quality.decide(jid,{'decision':'approved'})
        job=core.get_job(jid);core.edit_job(jid,{'scenes':json.loads(job['scenes']),'caption':job['caption'],'due_at':job['due_at'],'rights':True,'action':'render'})
        self.assertIsNone(quality.inspect(jid)['decision'])

    def test_review_changed_while_claiming_upload_prevents_external_initialization(self):
        jid=self.ready();autopilot.approve_product(self.pid,{'active':True,'approved':True})
        with core.db() as c:product=dict(c.execute('SELECT * FROM products').fetchone())
        with patch('quality.inspect',side_effect=[{'allowed':True},{'allowed':False}]),patch.object(yt,'initialize_upload') as upload:
            yt.process(core.get_job(jid),product);upload.assert_not_called()
        with core.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM youtube_jobs').fetchone()[0],0)

    def test_review_changed_while_claiming_buffer_send_returns_to_local(self):
        jid=self.ready()
        with core.db() as c:c.execute('INSERT INTO auto_jobs(job_id,variant) VALUES (?,0)',(jid,))
        autopilot.put_settings({'enabled':True,'send_drafts':True,'channel_id':'fixture'})
        with patch('quality.inspect',side_effect=[{'allowed':True},{'allowed':False}]),patch('buffer_client.create_draft') as send:
            autopilot.delivery_cycle(lambda _:'https://example.com/v.mp4');send.assert_not_called()
        with core.db() as c:self.assertEqual(c.execute('SELECT delivery FROM auto_jobs WHERE job_id=?',(jid,)).fetchone()[0],'local')
