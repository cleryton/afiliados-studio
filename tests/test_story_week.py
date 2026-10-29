from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import core
import stories
import story_week as week
import story_week_renderer
import story_delivery
import story_library
from story_week_catalog import STORIES,WEEK_NUMBERS
from instance_lock import InstanceLock


class StoryWeekTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        data=patch.object(core,'DATA',Path(temp.name));data.start();self.addCleanup(data.stop)
        clock=patch.object(core,'now',return_value=datetime(2026,10,25,18,tzinfo=core.TZ));clock.start();self.addCleanup(clock.stop)
        core.init();stories.create_pilot();stories.set_profile({'handle':'fiction_project'})
        self.offer={'name':'Curso fixture','facts':['Característica verificada.'],'url':'https://example.com/own-affiliate','product_hash':'f'*64}
        for mock in (patch('story_offers.for_series',return_value=self.offer),patch('story_offers.current',return_value=True)):
            mock.start();self.addCleanup(mock.stop)
        self.media(2);self.media(3)

    def media(self,number,slot=''):
        identifier=f'{number:x}'*32;folder=core.DATA/'stories'/identifier;folder.mkdir(parents=True,exist_ok=True)
        raw=f'unit fixture chapter {number}'.encode();(folder/'video.mp4').write_bytes(raw)
        meta={'episode':number,'voice':True,'duration':5,'animation_type':'original_procedural_3d','character_animation':True,
              'sha256':hashlib.sha256(raw).hexdigest(),'offer':self.offer,'week_slot':slot,'scenes':STORIES.get(number,{}).get('scenes',[])}
        (folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8');Image.new('RGB',(720,1280)).save(folder/'poster.png')
        (folder/'legenda.txt').write_text('Ficção. PUBLICIDADE. https://example.com/own-affiliate',encoding='utf-8')
        (folder/'legendas.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nFixture.\n',encoding='utf-8')
        return identifier

    def prepare(self):return week.prepare({'start_date':'2026-10-26','hour':18})

    def test_seven_dates_are_local_idempotent_and_never_cloud_schedules(self):
        first=self.prepare();again=self.prepare();state=week.state()
        self.assertEqual(first['id'],again['id']);self.assertTrue(again['existing'])
        self.assertEqual([s['number'] for s in state['slots']],list(WEEK_NUMBERS));self.assertEqual(state['ready'],2)
        self.assertEqual(state['slots'][0]['due_at'],'2026-10-26T18:00:00-03:00')
        self.assertEqual(state['slots'][-1]['due_at'],'2026-11-01T18:00:00-03:00')
        self.assertTrue(all(s['receipt'] is None for s in state['slots']))

    def test_worker_produces_only_five_missing_chapters_and_packages_every_slot(self):
        self.prepare()
        with patch.object(story_week_renderer,'render',side_effect=lambda n,offer,s:self.media(n,s)) as render:
            week.run_worker()
        self.assertEqual([c.args[0] for c in render.call_args_list],[4,5,6,7,8])
        state=week.state();self.assertEqual(state['ready'],7);self.assertFalse(state['preparing'])
        self.assertTrue(all(s['package']['ready'] for s in state['slots']))
        self.assertTrue(all(s['receipt'] is None for s in state['slots']))
        with core.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM story_publications').fetchone()[0],0)
        with patch.object(story_week_renderer,'render') as again:week.run_worker()
        again.assert_not_called()

    def test_worker_stops_after_failure_without_endless_retry_or_false_ready(self):
        self.prepare()
        with patch.object(story_week_renderer,'render',side_effect=ValueError('private path')) as render:week.run_worker()
        self.assertEqual(render.call_count,1);state=week.state();self.assertFalse(state['preparing'])
        self.assertEqual(state['slots'][2]['status'],'error');self.assertNotIn('private path',json.dumps(state))
        with patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called()

    def test_changed_profile_stops_before_rendering(self):
        self.prepare();stories.set_profile({'handle':'another_project'})
        with patch.object(story_week_renderer,'render') as render:week.run_worker()
        render.assert_not_called();self.assertFalse(week.state()['preparing'])

    def test_interrupted_completed_render_is_adopted_and_packaged_without_duplicate(self):
        self.prepare()
        with core.db() as c:
            slot=c.execute('SELECT id FROM story_week_slots WHERE number=4').fetchone()['id']
            c.execute("UPDATE story_week_slots SET status='rendering' WHERE id=?",(slot,))
        self.media(4,slot)
        with patch.object(story_week_renderer,'render',side_effect=lambda n,offer,s:self.media(n,s)) as render:week.run_worker()
        self.assertEqual([c.args[0] for c in render.call_args_list],[5,6,7,8])
        self.assertEqual(week.state()['ready'],7);self.assertTrue(story_delivery.info('4'*32)['ready'])

    def test_single_worker_lock_and_tester_mode_prevent_another_process(self):
        self.prepare()
        with InstanceLock(core.DATA/'story-week'/'worker'),patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called()
        with patch.object(core,'TESTER',True),patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called()
        with patch.object(week.subprocess,'Popen') as spawn:week.tick()
        self.assertEqual(spawn.call_count,1);self.assertEqual(spawn.call_args.kwargs['env']['AFILIADOS_DATA'],str(core.DATA))

    def test_revoked_offer_hides_prepared_downloads_in_calendar(self):
        self.prepare()
        with patch('story_offers.current',return_value=False):
            state=week.state();self.assertEqual(state['ready'],0)
            self.assertTrue(all(s['package'] is None for s in state['slots'][:2]))

    def test_bad_recovered_package_stops_instead_of_spawning_forever(self):
        self.prepare()
        with core.db() as c:
            slot=c.execute('SELECT id FROM story_week_slots WHERE number=4').fetchone()['id']
            c.execute("UPDATE story_week_slots SET status='rendering' WHERE id=?",(slot,))
        identifier=self.media(4,slot);(core.DATA/'stories'/identifier/'legendas.srt').unlink()
        with patch.object(story_week_renderer,'render') as render:week.run_worker()
        render.assert_not_called();self.assertFalse(week.state()['preparing'])
        self.assertEqual(week.state()['slots'][2]['status'],'error')

    def test_invalid_date_hour_and_already_posted_chapter_are_rejected(self):
        for payload in ({'start_date':'2026-10-24'},{'start_date':'bad'},{'start_date':'2026-10-26','hour':True},{'start_date':'2026-10-26','hour':24}):
            with self.subTest(payload=payload),self.assertRaises(ValueError):week.prepare(payload)
        with patch.object(story_library,'native_post_exists',return_value=True):
            with self.assertRaises(ValueError):self.prepare()

    def test_ongoing_week_references_protect_old_media_from_cleanup(self):
        self.prepare()
        plan=week.state();protected=story_library.cleanup()['protected_ids']
        self.assertIn(plan['slots'][0]['media_id'],protected)

    def test_next_collection_is_new_ordered_pinned_and_does_not_reuse_first_week(self):
        week.prepare({'start_date':'2026-11-02','collection':'standalone'})
        state=week.state()
        self.assertEqual([s['number'] for s in state['slots']],list(range(9,16)))
        self.assertEqual(state['ready'],0);self.assertEqual(state['native_registered'],0)
        self.assertEqual(state['slots'][-1]['due_at'],'2026-11-08T18:00:00-03:00')
        self.assertTrue(all(s['creative_plan']['report']['status']=='script_checked' for s in state['slots']))
        with self.assertRaises(ValueError):week.prepare({'start_date':'2026-11-02','collection':'first'})
        self.assertEqual(week.state()['slots'][0]['number'],9)
        with core.db() as c:c.execute('UPDATE story_weeks SET enabled=0')
        with self.assertRaises(ValueError):week.prepare({'start_date':'2026-11-09','collection':'standalone'})

    def test_resume_keeps_ready_slots_and_rechecks_resources_profile_and_native_receipts(self):
        result=self.prepare()
        with core.db() as c:
            c.execute('UPDATE story_weeks SET enabled=0 WHERE id=?',(result['id'],))
            c.execute("UPDATE story_week_slots SET status='error' WHERE number=4")
        payload={'id':result['id']}
        with patch.object(week.shutil,'disk_usage',return_value=type('Disk',(),{'free':0})()):
            with self.assertRaises(ValueError):week.resume(payload)
        with patch.object(story_library,'native_post_exists',return_value=True):
            with self.assertRaises(ValueError):week.resume(payload)
        with patch.object(week.shutil,'disk_usage',return_value=type('Disk',(),{'free':2**30})()):
            week.resume(payload)
        state=week.state();self.assertEqual(state['ready'],2);self.assertEqual(state['slots'][2]['status'],'queued')
        self.assertTrue(state['preparing'])
