from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import stories
import story_library as library


class StoryLibraryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        change=patch.object(core,'DATA',Path(temp.name));change.start();self.addCleanup(change.stop)
        core.init();stories.create_pilot()
        with core.db() as c:
            self.old=c.execute('SELECT id FROM story_episodes WHERE number=2').fetchone()['id']
            c.execute("UPDATE story_episodes SET status='ready'")
        clock=patch.object(core,'now',return_value=datetime(2026,10,25,18,tzinfo=core.TZ));clock.start();self.addCleanup(clock.stop)

    def video(self,identifier,number=2,native=True,modified=100):
        folder=core.DATA/'stories'/identifier;folder.mkdir(parents=True,exist_ok=True)
        raw=('local fixture '+identifier).encode();(folder/'video.mp4').write_bytes(raw)
        meta={'episode':number,'voice':True,'duration':59.5,'sha256':hashlib.sha256(raw).hexdigest(),'offer':None}
        if native:meta.update(animation_type='original_procedural_3d',character_animation=True)
        file=folder/'roteiro.json';file.write_text(json.dumps(meta),encoding='utf-8');os.utime(file,ns=(modified,modified))
        (folder/'legenda.txt').write_text('Ficção de teste.',encoding='utf-8')
        return folder

    def receipt(self,folder,status='scheduled_confirmed',due='2026-10-26T18:00:00-03:00'):
        value={'media_id':folder.name,'status':status,'handle':'fiction_project','url':'https://www.tiktok.com/@fiction_project/video/7700697193698577682','scheduled_for':due}
        (folder/'agendamento-tiktok.json').write_text(json.dumps(value),encoding='utf-8')

    def test_library_keeps_latest_completed_version_of_each_chapter(self):
        self.video('a'*32,1,modified=100);self.video('b'*32,1,modified=200);self.video('c'*32,2)
        self.video(self.old,2,native=False)
        state=library.state();self.assertEqual([s['number'] for s in state],[1,2])
        self.assertEqual(state[0]['id'],'b'*32);self.assertNotIn(str(core.DATA),json.dumps(state))
        self.assertTrue(all(s['receipt'] is None for s in state))

    def test_cleanup_is_dry_until_requested_and_preserves_current_masters_and_sources(self):
        old=self.video(self.old,native=False);current=self.video('a'*32)
        package=core.DATA/'story-3d'/self.old;package.mkdir(parents=True)
        (package/'clip.mp4').write_bytes(b'old intermediate');(package/'scene.blend').write_bytes(b'original project')
        plan=library.cleanup();self.assertFalse(plan['executed']);self.assertEqual(plan['removed_files'],2)
        self.assertTrue((old/'video.mp4').is_file())
        result=library.cleanup(execute=True);self.assertEqual(result['removed_files'],2)
        self.assertFalse((old/'video.mp4').exists());self.assertTrue((old/'legenda.txt').is_file())
        self.assertTrue((current/'video.mp4').is_file());self.assertTrue((package/'scene.blend').is_file())
        with core.db() as c:self.assertEqual(c.execute('SELECT status FROM story_episodes WHERE id=?',(self.old,)).fetchone()['status'],'archived')
        self.assertEqual(library.cleanup(execute=True)['removed_files'],0)

    def test_any_receipt_protects_a_master_even_if_the_receipt_is_damaged(self):
        old=self.video(self.old,native=False);self.video('a'*32)
        (old/'publicacao-tiktok.json').write_text('damaged receipt',encoding='utf-8')
        self.assertEqual(library.cleanup(execute=True)['removed_files'],0)
        self.assertTrue((old/'video.mp4').is_file())

    def test_no_3d_replacement_or_current_queue_means_no_deletion(self):
        old=self.video(self.old,native=False)
        self.assertEqual(library.cleanup(execute=True)['removed_files'],0)
        self.video('a'*32)
        with core.db() as c:c.execute("UPDATE story_episodes SET status='rendering' WHERE id=?",(self.old,))
        self.assertEqual(library.cleanup(execute=True)['removed_files'],0)
        self.assertTrue((old/'video.mp4').exists())

    def test_tampered_replacement_stops_the_entire_cleanup(self):
        old=self.video(self.old,native=False);current=self.video('a'*32)
        (current/'video.mp4').write_bytes(b'modified')
        with self.assertRaises(ValueError):library.cleanup(execute=True)
        self.assertTrue((old/'video.mp4').is_file())

    def test_canonical_path_outside_data_stops_before_any_delete(self):
        old=self.video(self.old,native=False);self.video('a'*32)
        package=core.DATA/'story-3d'/self.old;package.mkdir(parents=True)
        clip=package/'clip.mp4';clip.write_bytes(b'fixture')
        original=Path.resolve
        def resolve(path,*args,**kwargs):
            return core.ROOT/'outside-fixture.mp4' if path==clip else original(path,*args,**kwargs)
        with patch.object(Path,'resolve',resolve):
            with self.assertRaises(ValueError):library.cleanup(execute=True)
        self.assertTrue((old/'video.mp4').is_file());self.assertTrue(clip.is_file())

    def test_scheduled_time_passing_does_not_claim_publication(self):
        folder=self.video('a'*32,1);self.receipt(folder)
        self.assertEqual(library.state()[0]['receipt']['label'],'Agendamento registrado no TikTok')
        self.receipt(folder,due='2026-10-25T17:00:00-03:00')
        row=library.state()[0]['receipt'];self.assertEqual(row['status'],'scheduled_confirmed')
        self.assertIn('conferir',row['label'])
        self.receipt(folder,status='published_confirmed')
        self.assertEqual(library.state()[0]['receipt']['label'],'Publicação registrada no TikTok')

    def test_confirmed_publication_takes_precedence_over_original_schedule(self):
        folder=self.video('a'*32,1);self.receipt(folder)
        scheduled=json.loads((folder/'agendamento-tiktok.json').read_text(encoding='utf-8'))
        (folder/'publicacao-tiktok.json').write_text(json.dumps({**scheduled,'status':'published_confirmed'}),encoding='utf-8')
        self.assertEqual(library.receipt(folder.name)['status'],'published_confirmed')

    def test_deleted_media_is_not_exposed_as_ready_download(self):
        self.video(self.old,native=False)
        self.assertIsNotNone(next(e for e in stories.state()['episodes'] if e['id']==self.old)['video_url'])
        (core.DATA/'stories'/self.old/'video.mp4').unlink()
        self.assertIsNone(next(e for e in stories.state()['episodes'] if e['id']==self.old)['video_url'])
