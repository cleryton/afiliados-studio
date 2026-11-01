from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image
import core
import stories
import story_native as native
import story_week
import story_publishing


class NativeAttemptTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        data=patch.object(core,'DATA',Path(tmp.name));data.start();self.addCleanup(data.stop)
        clock=patch.object(core,'now',return_value=datetime(2026,10,25,12,tzinfo=core.TZ));clock.start();self.addCleanup(clock.stop)
        core.init();stories.create_pilot();stories.set_profile({'handle':'fiction_project'})
        self.offer={'name':'Fixture offer','facts':['Verified fixture fact.'],'url':'https://example.com/affiliate','product_hash':'f'*64}
        for change in (patch('story_offers.current',return_value=True),patch('story_offers.for_series',return_value=self.offer)):
            change.start();self.addCleanup(change.stop)
        for n in (2,3):self.media(n)
        story_week.prepare({'start_date':'2026-10-26','hour':18})
        self.addCleanup(patch.stopall)

    def media(self,n):
        mid=f'{n:x}'*32;root=core.DATA/'stories'/mid;root.mkdir(parents=True,exist_ok=True)
        raw=f'Synthetic unit-test fixture, never a real video {n}'.encode()
        (root/'video.mp4').write_bytes(raw)
        meta={'episode':n,'duration':5,'voice':True,'animation_type':'original_procedural_3d','character_animation':True,
              'sha256':hashlib.sha256(raw).hexdigest(),'offer':self.offer}
        (root/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        (root/'legenda.txt').write_text('PUBLICIDADE. https://example.com/affiliate Ficção com IA.',encoding='utf-8')
        (root/'legendas.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nFixture\n',encoding='utf-8')
        Image.new('RGB',(720,1280)).save(root/'poster.png')
        return mid

    def begin(self,n=2):
        return native.begin({'media_id':f'{n:x}'*32,'observed_handle':'fiction_project'})

    def evidence(self,identifier,stage):
        return {'id':identifier,'stage':stage,'caption_matches':True,'ai_label':True,'paid_partnership':True,
                'public_visibility':True,'checks_clear':True,'observed_handle':'fiction_project','due_at':'2026-10-26T18:00:00-03:00'}

    def submitted(self):
        identifier=self.begin()['id']
        for phase in ('upload_started','details_checked','submission_started'):native.advance(self.evidence(identifier,phase))
        return identifier

    def confirmation(self,identifier):
        return {'id':identifier,'url':'https://www.tiktok.com/@fiction_project/video/1234567890123456789',
                'due_at':'2026-10-26T18:00:00-03:00','caption_matches':True,'destination_reloaded':True}

    def test_one_dispatch_permission_then_observed_receipt_and_idempotent_confirmation(self):
        request=self.begin();identifier=request['id'];self.assertTrue(request['may_upload'])
        native.advance(self.evidence(identifier,'upload_started'))
        native.advance(self.evidence(identifier,'details_checked'))
        self.assertTrue(native.advance(self.evidence(identifier,'submission_started'))['may_dispatch'])
        self.assertFalse(native.advance(self.evidence(identifier,'submission_started'))['may_dispatch'])
        native.confirm(self.confirmation(identifier));again=native.confirm(self.confirmation(identifier))
        self.assertTrue(again['existing']);self.assertEqual(story_week.state()['native_registered'],1)
        self.assertFalse(native._get(identifier)['receipt'] is None)

    def test_duplicate_begin_and_restart_never_grant_another_upload(self):
        first=self.begin();again=self.begin()
        self.assertEqual(first['id'],again['id']);self.assertFalse(again['may_upload'])
        native.advance(self.evidence(first['id'],'upload_started'));native.init()
        self.assertEqual(self.begin()['stage'],'upload_started');self.assertFalse(self.begin()['may_upload'])

    def test_sequence_requires_first_ready_unregistered_chapter(self):
        with self.assertRaises(ValueError):self.begin(3)
        with core.db() as c:c.execute("UPDATE story_week_slots SET status='retry_wait' WHERE number=2")
        with self.assertRaises(ValueError):self.begin()

    def test_checklist_is_required_before_submission(self):
        identifier=self.begin()['id'];native.advance(self.evidence(identifier,'upload_started'))
        for key in ('caption_matches','ai_label','paid_partnership','public_visibility','checks_clear'):
            payload=self.evidence(identifier,'details_checked');payload[key]=False
            with self.subTest(key=key),self.assertRaises(ValueError):native.advance(payload)
        self.assertEqual(native._get(identifier)['stage'],'upload_started')

    def test_changed_caption_or_pause_blocks_final_dispatch(self):
        identifier=self.begin()['id'];native.advance(self.evidence(identifier,'upload_started'))
        native.advance(self.evidence(identifier,'details_checked'))
        with core.db() as c:c.execute('UPDATE story_weeks SET paused=1')
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'submission_started'))
        with core.db() as c:c.execute('UPDATE story_weeks SET paused=0')
        (core.DATA/'stories'/('2'*32)/'legenda.txt').write_text('Changed caption',encoding='utf-8')
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'submission_started'))
        self.assertIsNone(native._get(identifier)['submitted_at'])

    def test_uncertain_attempt_cannot_be_promoted_without_a_submission_checkpoint(self):
        identifier=self.begin()['id'];native.hold({'id':identifier,'reason':'captcha'})
        with self.assertRaises(ValueError):native.confirm(self.confirmation(identifier))
        self.assertFalse(self.begin()['may_upload'])

    def test_lost_submission_response_is_reconciled_without_new_dispatch(self):
        identifier=self.submitted();native.hold({'id':identifier,'reason':'network'});native.init()
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'submission_started'))
        native.confirm(self.confirmation(identifier))
        self.assertEqual(native._get(identifier)['stage'],'confirmed')

    def test_existing_preview_can_resume_without_reupload_but_submitted_request_cannot(self):
        identifier=self.begin()['id'];native.advance(self.evidence(identifier,'upload_started'))
        native.hold({'id':identifier,'reason':'captcha'})
        evidence={'id':identifier,'preview_matches':True,'destination_absent_after_reload':True,
                  'observed_handle':'fiction_project','media_id':'2'*32}
        resumed=native.resume_preview(evidence)
        self.assertFalse(resumed['may_upload']);self.assertFalse(resumed['may_dispatch'])
        for phase in ('details_checked','submission_started'):native.advance(self.evidence(identifier,phase))
        native.hold({'id':identifier,'reason':'network'})
        with self.assertRaises(ValueError):native.resume_preview(evidence)

    def test_confirmation_requires_reloaded_destination_expected_profile_and_date(self):
        identifier=self.submitted()
        for change in ({'destination_reloaded':False},{'caption_matches':False},{'due_at':'2026-10-27T18:00:00-03:00'},
                       {'url':'https://www.tiktok.com/@personal/video/1234567890123456789'},
                       {'url':'https://www.tiktok.com/@fiction_project/video/1234567890123456789?x=1'}):
            with self.subTest(change=change),self.assertRaises(ValueError):native.confirm({**self.confirmation(identifier),**change})
        self.assertEqual(story_week.state()['native_registered'],0)

    def test_receipt_write_failure_is_repaired_from_confirmed_result_without_resubmission(self):
        identifier=self.submitted()
        with patch.object(native,'_write_receipt',side_effect=OSError('Synthetic disk failure')):
            with self.assertRaises(OSError):native.confirm(self.confirmation(identifier))
            native.tick()
            self.assertEqual(native._get(identifier)['reason'],'receipt_write')
        self.assertEqual(native._get(identifier)['stage'],'confirmed')
        self.assertTrue(native.blocks_api('3d:a-chave-do-12:2','fiction_project'))
        native.tick();self.assertEqual(story_week.state()['native_registered'],1)
        self.assertEqual(native._get(identifier)['reason'],'')

    def test_cross_provider_duplicate_is_blocked_before_and_after_native_confirmation(self):
        identifier=self.submitted()
        story_publishing.put({'enabled':True,'binding':{'account_id':'fixture-id','handle':'fiction_project'}})
        with self.assertRaises(ValueError):story_publishing.queue('2'*32,allow_archive=True)
        native.confirm(self.confirmation(identifier))
        path=core.DATA/'stories'/('2'*32)/'agendamento-tiktok.json';path.unlink()
        with self.assertRaises(ValueError):story_publishing.queue('2'*32,allow_archive=True)

    def test_changed_profile_blocks_progress_but_later_pause_does_not_erase_remote_result(self):
        identifier=self.begin()['id'];stories.set_profile({'handle':'another_project'})
        with self.assertRaises(ValueError):native.advance(self.evidence(identifier,'upload_started'))
        stories.set_profile({'handle':'fiction_project'})
        for phase in ('upload_started','details_checked','submission_started'):native.advance(self.evidence(identifier,phase))
        with core.db() as c:c.execute('UPDATE story_weeks SET paused=1')
        native.confirm(self.confirmation(identifier));self.assertEqual(native._get(identifier)['stage'],'confirmed')

    def test_tester_cannot_start_advance_confirm_or_hold_external_attempts(self):
        identifier=self.begin()['id']
        with patch.object(core,'TESTER',True):
            for action,payload in ((native.begin,{'media_id':'2'*32,'observed_handle':'fiction_project'}),
                                   (native.advance,self.evidence(identifier,'upload_started')),
                                   (native.confirm,self.confirmation(identifier)),(native.hold,{'id':identifier,'reason':'login'}),
                                   (native.resume_preview,{'id':identifier})):
                with self.subTest(action=action.__name__),self.assertRaises(ValueError):action(payload)

    def test_hold_cannot_erase_confirmation_written_after_its_initial_read(self):
        identifier=self.submitted();stale=native._get(identifier)
        native.confirm(self.confirmation(identifier))
        with patch.object(native,'_get',return_value=stale),self.assertRaises(ValueError):
            native.hold({'id':identifier,'reason':'network'})
        self.assertEqual(native._get(identifier)['stage'],'confirmed')

    def test_api_queue_created_during_native_preparation_prevents_upload_permission(self):
        story_publishing.put({'enabled':True,'binding':{'account_id':'fixture-id','handle':'fiction_project'}})
        snapshot=native.story_delivery.snapshot
        def concurrent_queue(media):
            proof=snapshot(media)
            story_publishing.queue(media,allow_archive=True)
            return proof
        with patch.object(native.story_delivery,'snapshot',side_effect=concurrent_queue),self.assertRaises(ValueError):
            self.begin()
        self.assertEqual(native.state()['attempts'],[])

    def test_native_reservation_between_api_precheck_and_insert_prevents_api_queue(self):
        story_publishing.put({'enabled':True,'binding':{'account_id':'fixture-id','handle':'fiction_project'}})
        blocked=native.blocks_api
        def concurrent_begin(content,handle,**kwargs):
            if not kwargs:
                self.begin()
                return False  # The earlier check lost the race to the reservation.
            return blocked(content,handle,**kwargs)
        with patch.object(native,'blocks_api',side_effect=concurrent_begin),self.assertRaises(ValueError):
            story_publishing.queue('2'*32,allow_archive=True)
        with core.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM story_publications').fetchone()[0],0)

    def test_simultaneous_submission_checks_grant_exactly_one_dispatch(self):
        identifier=self.begin()['id']
        for phase in ('upload_started','details_checked'):native.advance(self.evidence(identifier,phase))
        barrier=threading.Barrier(2);unchanged=native._unchanged
        def check(row):
            proof=unchanged(row);barrier.wait(timeout=10);return proof
        with patch.object(native,'_unchanged',side_effect=check),ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:native.advance(self.evidence(identifier,'submission_started')),range(2)))
        self.assertEqual(sum(r['may_dispatch'] for r in results),1)


if __name__=='__main__':unittest.main()
