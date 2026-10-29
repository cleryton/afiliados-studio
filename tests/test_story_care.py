from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
import core,stories
import story_week as week
import story_care as care
import story_week_renderer
import story_delivery
from story_week_catalog import STORIES
from instance_lock import InstanceLock


class StoryCareTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        data=patch.object(core,'DATA',Path(tmp.name));data.start();self.addCleanup(data.stop)
        self.now=datetime(2026,10,25,12,tzinfo=core.TZ)
        clock=patch.object(core,'now',side_effect=lambda:self.now);clock.start();self.addCleanup(clock.stop)
        disk=patch('shutil.disk_usage',return_value=type('Disk',(),{'free':2**30})());disk.start();self.addCleanup(disk.stop)
        core.init();stories.create_pilot();stories.set_profile({'handle':'fiction_project'})
        self.offer={'name':'Fixture','facts':['Fato verificado.'],'url':'https://example.com/own-affiliate','product_hash':'f'*64}
        for mock in (patch('story_offers.for_series',return_value=self.offer),patch('story_offers.current',return_value=True)):
            mock.start();self.addCleanup(mock.stop)
        self.plan=week.prepare({'start_date':'2026-10-26'})

    def media(self,n,slot):
        mid=f'{n:x}'*32;root=core.DATA/'stories'/mid;root.mkdir(parents=True,exist_ok=True)
        raw=f'local synthetic fixture {n}'.encode();(root/'video.mp4').write_bytes(raw)
        meta={'episode':n,'voice':True,'duration':5,'animation_type':'original_procedural_3d','character_animation':True,
              'sha256':hashlib.sha256(raw).hexdigest(),'offer':self.offer,'week_slot':slot,'scenes':STORIES.get(n,{}).get('scenes',[])}
        (root/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        Image.new('RGB',(720,1280)).save(root/'poster.png')
        (root/'legenda.txt').write_text('Ficção. PUBLICIDADE. https://example.com/own-affiliate',encoding='utf-8')
        (root/'legendas.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nFixture.\n',encoding='utf-8')
        return mid

    def finish(self):
        with patch('animation3d.render_pilot',side_effect=lambda **kw:{'id':self.media(kw['number'],'')}),patch.object(story_week_renderer,'render',side_effect=lambda n,o,s:self.media(n,s)):
            week.run_worker()

    def first(self):return week.state()['slots'][0]

    def test_storage_wait_does_not_consume_attempts_or_spawn_over_and_over(self):
        with patch.object(week,'capacity',return_value=False),patch.object(story_week_renderer,'render') as render:
            week.run_worker()
        self.assertEqual(self.first()['status'],'waiting_storage');self.assertEqual(self.first()['attempts'],0)
        self.assertTrue(week.state()['preparing']);render.assert_not_called()
        with patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called()
        self.now+=timedelta(minutes=6)
        with patch.object(week,'capacity',return_value=False),patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called();self.assertEqual(self.first()['attempts'],0)
        self.now+=timedelta(minutes=6)
        with patch.object(week.subprocess,'Popen') as spawn:week.tick()
        self.assertEqual(spawn.call_count,1);self.assertEqual(self.first()['status'],'queued')

    def test_temporary_timeouts_use_persisted_delays_then_stop_after_three_attempts(self):
        with patch('animation3d.render_pilot',side_effect=subprocess.TimeoutExpired('fixture',60)) as render:
            week.run_worker();self.assertEqual(self.first()['status'],'retry_wait')
            self.assertEqual(self.first()['attempts'],1)
            week.run_worker();self.assertEqual(render.call_count,1)
            self.now+=timedelta(minutes=2);week.wake_waiting();week.run_worker()
            self.assertEqual(self.first()['attempts'],2);self.assertEqual(self.first()['status'],'retry_wait')
            self.now+=timedelta(minutes=6);week.wake_waiting();week.run_worker()
            self.assertEqual(render.call_count,3)
        self.assertEqual(self.first()['status'],'error');self.assertFalse(week.state()['preparing'])

    def test_manual_pause_survives_restart_and_never_auto_wakes_resource_wait(self):
        with patch.object(week,'capacity',return_value=False):week.run_worker()
        week.pause({'id':self.plan['id']});week.init();self.now+=timedelta(minutes=10)
        with patch.object(week.subprocess,'Popen') as spawn:week.tick()
        spawn.assert_not_called();self.assertTrue(week.state()['paused'])
        week.resume({'id':self.plan['id']});self.assertFalse(week.state()['paused'])
        self.assertEqual(self.first()['status'],'queued')

    def test_third_interrupted_render_is_not_repeated(self):
        with core.db() as c:c.execute("UPDATE story_week_slots SET status='rendering',attempts=3 WHERE number=2")
        with patch('animation3d.render_pilot') as render:week.run_worker()
        render.assert_not_called();self.assertEqual(self.first()['block_code'],'attempts')

    def test_missing_or_corrupt_package_repairs_without_re_render_or_any_publication(self):
        self.finish();slot=self.first();archive=story_delivery.download(slot['media_id']);archive.write_bytes(b'corrupt fixture')
        master=core.DATA/'stories'/slot['media_id']/'video.mp4';before=master.read_bytes()
        with patch.object(story_week_renderer,'render') as render:care.tick()
        render.assert_not_called();self.assertTrue(story_delivery.download(slot['media_id']).is_file())
        self.assertEqual(master.read_bytes(),before);self.assertEqual(care.state()['total_repairs'],1)
        self.assertFalse(care.state()['posting_automatic'])
        with core.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM story_publications').fetchone()[0],0)
        with patch.object(story_delivery,'prepare') as prepare:care.tick()
        prepare.assert_not_called()

    def test_changed_master_is_held_not_silently_recreated(self):
        self.finish();slot=self.first();master=core.DATA/'stories'/slot['media_id']/'video.mp4';master.write_bytes(b'changed fixture')
        with patch.object(story_week_renderer,'render') as render:care.tick()
        render.assert_not_called();self.assertEqual(self.first()['block_code'],'integrity')
        self.assertEqual(master.read_bytes(),b'changed fixture');self.assertEqual(care.state()['code'],'review')

    def test_active_worker_pause_tester_and_profile_change_block_maintenance(self):
        self.finish()
        with InstanceLock(core.DATA/'story-week'/'worker'),patch.object(care,'audit') as audit:self.assertEqual(care.tick()['status'],'busy')
        audit.assert_not_called()
        with patch.object(core,'TESTER',True),patch.object(care,'audit') as audit:care.tick()
        audit.assert_not_called()
        week.pause({'id':self.plan['id']})
        with patch.object(care,'audit') as audit:care.tick(force=True)
        audit.assert_not_called();self.assertEqual(care.state()['code'],'paused')
        week.resume({'id':self.plan['id']});stories.set_profile({'handle':'another_project'});care.tick(force=True)
        self.assertEqual(care.state()['code'],'account');self.assertNotIn('video_url',care.state()['next_item'])

    def test_three_package_failures_stop_automatic_repair_until_explicit_check(self):
        self.finish();slot=self.first();story_delivery.download(slot['media_id']).unlink()
        with patch.object(story_delivery,'prepare',side_effect=PermissionError('private path')) as repair:
            for _ in range(4):care.tick();self.now+=timedelta(minutes=16)
            self.assertEqual(repair.call_count,3)
        self.assertEqual(care.state()['code'],'repair_review')
        self.assertNotIn('private path',json.dumps(care.state()))
        care.tick(force=True);self.assertEqual(care.state()['code'],'ready')

    def test_cleanup_only_removes_verified_duplicates_and_preserves_primary_video(self):
        self.finish();slot=self.first();mid=slot['media_id'];primary=core.DATA/'stories'/mid/'video.mp4'
        work=core.DATA/'story-week'/'renders'/mid/'stories'/mid;work.mkdir(parents=True)
        duplicate=work/'video.mp4';duplicate.write_bytes(primary.read_bytes())
        unrelated=work/'custom.mp4';unrelated.write_bytes(b'keep owner file')
        care.tick();self.assertFalse(duplicate.exists());self.assertTrue(primary.exists());self.assertTrue(unrelated.exists())
        self.assertGreater(care.state()['freed_bytes'],0)

    def test_completed_render_is_adopted_after_packaging_timeout_without_second_render(self):
        real_prepare=story_delivery.prepare;first=True
        def prepare(mid):
            nonlocal first
            if first:first=False;raise subprocess.TimeoutExpired('fixture package',60)
            return real_prepare(mid)
        with patch('animation3d.render_pilot',side_effect=lambda **kw:{'id':self.media(kw['number'],'')}) as native,patch.object(story_week_renderer,'render',side_effect=lambda n,o,s:self.media(n,s)),patch.object(story_delivery,'prepare',side_effect=prepare):
            week.run_worker();self.assertEqual(self.first()['status'],'retry_wait')
            self.now+=timedelta(minutes=2);week.wake_waiting();week.run_worker()
        self.assertEqual([c.kwargs['number'] for c in native.call_args_list],[2,3])
        self.assertEqual(week.state()['ready'],7);self.assertEqual(self.first()['attempts'],1)

    def test_legacy_schema_migrates_without_losing_existing_plan_or_slot(self):
        legacy=core.DATA/'legacy';legacy.mkdir()
        with patch.object(core,'DATA',legacy):
            with core.db() as c:
                c.executescript('''CREATE TABLE story_weeks(id TEXT PRIMARY KEY,handle TEXT NOT NULL,
                    start_date TEXT NOT NULL,offer TEXT NOT NULL,enabled INTEGER NOT NULL,created_at TEXT NOT NULL);
                    CREATE TABLE story_week_slots(id TEXT PRIMARY KEY,week_id TEXT NOT NULL,
                    number INTEGER NOT NULL,due_at TEXT NOT NULL,status TEXT NOT NULL,
                    media_id TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);''')
                c.execute('INSERT INTO story_weeks VALUES (?,?,?,?,?,?)',('e'*32,'fiction_project','2026-10-26',json.dumps(self.offer),1,core.stamp()))
                c.execute('INSERT INTO story_week_slots VALUES (?,?,?,?,?,?,?,?)',('d'*32,'e'*32,4,'2026-10-26T18:00:00-03:00','queued','','',core.stamp()))
            week.init()
            with core.db() as c:
                plan=c.execute('SELECT * FROM story_weeks').fetchone();slot=c.execute('SELECT * FROM story_week_slots').fetchone()
                self.assertEqual(plan['id'],'e'*32);self.assertEqual(plan['enabled'],1);self.assertEqual(plan['paused'],0)
                self.assertEqual(slot['id'],'d'*32);self.assertEqual(slot['attempts'],0);self.assertEqual(slot['status'],'queued')
                self.assertEqual(json.loads(slot['creative_plan']),{});self.assertIsNone(slot['retry_at'])
