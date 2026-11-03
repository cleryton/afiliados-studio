import json
import unittest
from unittest.mock import Mock
from tests import test_cartoon_month as fixtures
import core
import cartoon_month
import story_local_archive as archive
import story_native


class LocalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.MonthlyQueueTests('runTest');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def confirm(self):
        request=self.fixture.begin();identifier=request['id']
        for stage in ('upload_started','details_checked','submission_started'):
            story_native.advance(self.fixture.evidence(identifier,stage))
        story_native.confirm({'id':identifier,'url':'https://www.tiktok.com/@novelitas0213/video/1234567890123456789',
                              'due_at':'2026-11-09T12:00:00-03:00','caption_matches':True,'destination_reloaded':True})
        return core.DATA/'stories'/('1'*32)

    def test_recycle_only_confirmed_preserves_receipt_and_pending_media(self):
        folder=self.confirm();receipt=(folder/'agendamento-tiktok.json').read_bytes()
        self.assertEqual(archive.plan()['count'],1)
        result=archive.execute(recycle=lambda p:p.unlink())
        self.assertEqual(result['recycled'],1);self.assertTrue(archive.archived('1'*32))
        self.assertEqual((folder/'agendamento-tiktok.json').read_bytes(),receipt)
        self.assertTrue((folder/'roteiro.json').is_file());self.assertTrue((folder/'legenda.txt').is_file())
        self.assertTrue((core.DATA/'stories'/('2'*32)/'video.mp4').is_file())
        s=cartoon_month.state();self.assertEqual(s['ready'],3);self.assertEqual(s['produced'],4)
        self.assertEqual(s['archived'],1);self.assertEqual(s['confirmed'],1)
        self.assertEqual(archive.execute(recycle=Mock())['recycled'],0)
        self.assertTrue(self.fixture.begin(2)['may_upload'])

    def test_no_receipt_or_changed_master_cannot_be_recycled(self):
        self.assertEqual(archive.plan()['count'],0)
        folder=self.confirm();(folder/'video.mp4').write_bytes(b'changed')
        callback=Mock()
        with self.assertRaises(ValueError):archive.execute(recycle=callback)
        callback.assert_not_called()

    def test_failed_trash_keeps_the_master_and_does_not_claim_retirement(self):
        folder=self.confirm()
        with self.assertRaises(ValueError):archive.execute(recycle=lambda p:None)
        self.assertTrue((folder/'video.mp4').is_file());self.assertFalse(archive.archived('1'*32))
        self.assertEqual(cartoon_month.state()['ready'],4)

    def test_native_duplicate_guard_survives_removal_of_the_local_mp4(self):
        import story_library
        folder=self.confirm();archive.execute(recycle=lambda p:p.unlink())
        meta=json.loads((folder/'roteiro.json').read_text(encoding='utf-8'))
        meta.update(animation_type='original_procedural_3d',episode=9)
        (folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        self.assertTrue(story_library.native_post_exists('3d:a-chave-do-12:9','novelitas0213'))
        self.assertFalse(story_library.native_post_exists('3d:a-chave-do-12:9','personal_account'))


if __name__=='__main__':unittest.main()
