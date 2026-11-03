from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import cartoon2d
from cartoon_catalog import caption
import cartoon_month as month
import core
import stories
import story_native as native


class MonthlyQueueTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        change=patch.object(core,'DATA',Path(temporary.name));change.start();self.addCleanup(change.stop)
        change=patch.object(core,'now',return_value=datetime(2026,11,2,20,tzinfo=core.TZ));change.start();self.addCleanup(change.stop)
        core.init();stories.set_profile({'handle':'novelitas0213'})
        clips=[]
        for i,story in enumerate(cartoon2d.STORIES,1):
            identifier=str(i)*32;folder=core.DATA/'stories'/identifier;folder.mkdir(parents=True)
            raw=b'unit fixture, not real media evidence: '+str(i).encode();(folder/'video.mp4').write_bytes(raw)
            Image.new('RGB',(540,960)).save(folder/'poster.png')
            (folder/'legenda.txt').write_text(caption(story),encoding='utf-8')
            (folder/'legendas.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nFixture\n',encoding='utf-8')
            meta={'animation_type':'original_procedural_2d','title':story['title'],'voice':True,'duration':45,
                  'sha256':hashlib.sha256(raw).hexdigest(),'validation':{'decoded':True},'scenes':story['scenes'],'offer':None}
            (folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
            clips.append({'id':identifier})
        directory=core.DATA/'cartoon-2d';directory.mkdir()
        (directory/'catalog.json').write_text(json.dumps({'clips':clips}),encoding='utf-8')
        self.plan=month.prepare()['id']

    def begin(self,number=1):
        return native.begin({'media_id':str(number)*32,'observed_handle':'novelitas0213'})

    def evidence(self,identifier,stage):
        return {'id':identifier,'stage':stage,'observed_handle':'novelitas0213','due_at':'2026-11-09T12:00:00-03:00',
                'caption_matches':True,'ai_label':True,'public_visibility':True,'checks_clear':True}

    def test_finite_idempotent_month_keeps_four_original_files_and_96_distinct_slots(self):
        before=(core.DATA/'stories'/('1'*32)/'video.mp4').read_bytes()
        month.pause({'id':self.plan,'paused':True})
        self.assertTrue(month.prepare()['existing'])
        value=month.state();self.assertEqual(value['total'],96);self.assertEqual(value['ready'],4);self.assertTrue(value['paused'])
        self.assertEqual(value['slots'][0]['due_at'],'2026-11-09T12:00:00-03:00')
        self.assertEqual(value['slots'][-1]['due_at'],'2026-12-02T21:00:00-03:00')
        self.assertEqual(len({s['title'] for s in value['slots']}),96)
        self.assertEqual(before,(core.DATA/'stories'/('1'*32)/'video.mp4').read_bytes())

    def test_one_upload_and_dispatch_until_real_observation_is_recorded(self):
        request=self.begin();identifier=request['id'];self.assertTrue(request['may_upload'])
        self.assertFalse(self.begin()['may_upload'])
        with self.assertRaises(ValueError):self.begin(2)
        for stage in ('upload_started','details_checked','submission_started'):
            value=native.advance(self.evidence(identifier,stage))
        self.assertTrue(value['may_dispatch'])
        self.assertFalse(native.advance(self.evidence(identifier,'submission_started'))['may_dispatch'])
        proof={'id':identifier,'url':'https://www.tiktok.com/@novelitas0213/video/1234567890123456789',
               'due_at':'2026-11-09T12:00:00-03:00','caption_matches':True,'destination_reloaded':True}
        native.confirm(proof)
        self.assertEqual(month.state()['confirmed'],1)
        self.assertFalse(month.state()['slots'][0]['receipt']['publication_confirmed'])
        self.assertTrue(self.begin(2)['may_upload'])

    def test_concurrent_begin_cannot_issue_two_upload_permissions(self):
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:self.begin(),range(2)))
        self.assertEqual(sum(r['may_upload'] for r in results),1)
        self.assertEqual(results[0]['id'],results[1]['id'])

    def owner_evidence(self, identifier):
        return {'id':identifier,'owner_reported_submission':True,'destination_reloaded':True,
                'caption_matches':True,'public_visibility_observed':True,'observed_handle':'novelitas0213',
                'due_at':'2026-11-09T12:00:00-03:00',
                'url':'https://www.tiktok.com/@novelitas0213/video/1234567890123456789'}

    def test_owner_schedule_preserves_unknown_configuration_without_another_dispatch(self):
        identifier=self.begin()['id']
        native.advance(self.evidence(identifier,'upload_started'))
        native.hold({'id':identifier,'reason':'network'})
        evidence=self.owner_evidence(identifier)
        result=native.reconcile_owner(evidence)
        self.assertEqual(result['ai_label_observation'],'unknown')
        row=native._get(identifier);receipt=json.loads(row['receipt'])
        self.assertIsNone(row['submitted_at'])
        self.assertIsNone(receipt['dispatch_count'])
        self.assertIsNone(receipt['ai_label_confirmed_in_preview'])
        self.assertFalse(receipt['publication_confirmed'])
        self.assertEqual(month.state()['confirmed'],1)
        self.assertTrue(native.reconcile_owner(evidence)['existing'])
        self.assertFalse(self.begin(2)['existing'])

    def test_owner_reconciliation_requires_report_matching_destination_and_original_sources(self):
        identifier=self.begin()['id']
        native.advance(self.evidence(identifier,'upload_started'))
        evidence=self.owner_evidence(identifier)
        for key,value in [('owner_reported_submission',False),('destination_reloaded',False),
                          ('public_visibility_observed',False),('observed_handle','personal_account'),
                          ('due_at','2026-11-10T12:00:00-03:00'),
                          ('url','https://www.tiktok.com/@personal_account/video/1234567890123456789')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                native.reconcile_owner({**evidence,key:value})
        folder=core.DATA/'stories'/('1'*32)
        (folder/'legenda.txt').write_text('Changed caption',encoding='utf-8')
        with self.assertRaises(ValueError):native.reconcile_owner(evidence)
        self.assertEqual(month.state()['confirmed'],0)

    def test_owner_reconciliation_cannot_replace_an_already_submitted_request(self):
        identifier=self.begin()['id']
        for stage in ('upload_started','details_checked','submission_started'):
            native.advance(self.evidence(identifier,stage))
        with self.assertRaises(ValueError):native.reconcile_owner(self.owner_evidence(identifier))
        self.assertEqual(native._get(identifier)['stage'],'submission_started')

    def test_changed_caption_pause_or_wrong_identity_prevents_dispatch(self):
        request=self.begin();identifier=request['id']
        native.advance(self.evidence(identifier,'upload_started'))
        native.advance(self.evidence(identifier,'details_checked'))
        month.pause({'id':self.plan,'paused':True})
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'submission_started'))
        month.pause({'id':self.plan,'paused':False})
        folder=core.DATA/'stories'/('1'*32)
        with (folder/'legenda.txt').open('a',encoding='utf-8') as f:f.write('\nhttps://example.com/changed')
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'submission_started'))
        self.assertIsNone(native._get(identifier)['submitted_at'])
        with self.assertRaises(ValueError):native.begin({'media_id':'1'*32,'observed_handle':'personal_account'})

    def test_advance_rejects_overdue_slot_without_fallback_publication(self):
        request=self.begin()
        with patch.object(core,'now',return_value=datetime(2026,11,10,20,tzinfo=core.TZ)):
            with self.assertRaises(ValueError):self.begin()
        native.hold({'id':request['id'],'reason':'network'})
        self.assertFalse(self.begin()['may_upload'])

    def test_reviewed_retry_keeps_attempt_count_and_cannot_be_repeated(self):
        with core.db() as c:
            row=c.execute('SELECT id FROM cartoon_slots WHERE position=5').fetchone()
            c.execute("UPDATE cartoon_slots SET status='error',attempts=2 WHERE id=?",(row['id'],))
        with self.assertRaises(ValueError):month.retry_reviewed({'id':row['id']})
        month.retry_reviewed({'id':row['id'],'cause_reviewed':True})
        with core.db() as c:result=c.execute('SELECT * FROM cartoon_slots WHERE id=?',(row['id'],)).fetchone()
        self.assertEqual(result['attempts'],2)
        self.assertEqual(result['reviewed_retry'],1)
        self.assertEqual(result['status'],'queued')
        with self.assertRaises(ValueError):month.retry_reviewed({'id':row['id'],'cause_reviewed':True})

    def test_completed_interrupted_master_is_recovered_even_at_attempt_limit(self):
        with core.db() as c:
            row=dict(c.execute('SELECT * FROM cartoon_slots WHERE position=5').fetchone())
            c.execute("UPDATE cartoon_slots SET status='error' WHERE position>5")
            c.execute("UPDATE cartoon_slots SET status='rendering',attempts=2 WHERE id=?",(row['id'],))
        story=json.loads(row['story']);folder=core.DATA/'stories'/row['media_id'];folder.mkdir()
        raw=b'Synthetic completed fixture, not real media evidence'
        (folder/'video.mp4').write_bytes(raw)
        Image.new('RGB',(540,960)).save(folder/'poster.png')
        (folder/'legenda.txt').write_text(caption(story),encoding='utf-8')
        (folder/'legendas.srt').write_text('Test fixture',encoding='utf-8')
        meta={'animation_type':'original_procedural_2d','title':story['title'],'voice':True,'duration':45,
              'sha256':hashlib.sha256(raw).hexdigest(),'validation':{'decoded':True},'scenes':story['scenes'],'offer':None}
        (folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        with patch('cartoon2d.render_story') as render:
            month.run_worker()
            render.assert_not_called()
        with core.db() as c:result=c.execute('SELECT status,attempts FROM cartoon_slots WHERE id=?',(row['id'],)).fetchone()
        self.assertEqual(result['status'],'ready');self.assertEqual(result['attempts'],2)
        self.assertEqual((folder/'video.mp4').read_bytes(),raw)

    def test_catalog_action_frames_are_valid_for_every_scene(self):
        from cartoon_month_catalog import STORIES
        for story in STORIES:
            self.assertEqual(len(story['scenes']),6)
            for i in range(6):
                image=cartoon2d.frame(story,i,.5,2,'Legenda de teste.',.5)
                self.assertEqual(image.size,(540,960))


if __name__=='__main__':unittest.main()
