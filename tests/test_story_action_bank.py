import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import story_week_renderer as renderer


class ActionBankTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        change=patch.object(core,'DATA',Path(temporary.name));change.start();self.addCleanup(change.stop)
        self.folder=core.DATA/'stories'/('a'*32);self.folder.mkdir(parents=True)
        self.video=self.folder/'video.mp4';self.video.write_bytes(b'unit fixture, not render evidence')
        native=core.DATA/'animation-demos'/'fixture'/'reveal';native.mkdir(parents=True)
        self.project=native/'scene.blend';self.project.write_bytes(b'unit fixture')
        self.motion={'action':'reveal','frames':108,'fps':18,'maximum_hand_target_error':0,
                     'maximum_planted_foot_height_error':0,'maximum_planted_foot_slide_per_frame':0}
        self.report=native/'motion-state.json';self.report.write_text(json.dumps(self.motion),encoding='utf-8')
        meta={'native_project':str(self.project),'sha256':hashlib.sha256(self.video.read_bytes()).hexdigest()}
        (self.folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        change=patch('animation_demos.state',return_value=[{'id':'a'*32,'action':'reveal'}]);change.start();self.addCleanup(change.stop)

    def test_completed_verified_clip_can_replace_drawing_without_mutating_original_bank(self):
        bank={'drawing':{'path':'original'},'room':{'path':'room'}}
        selected=renderer.action_variants(bank)
        self.assertEqual(selected['drawing']['path'],self.video);self.assertEqual(selected['drawing']['fps'],18)
        self.assertEqual(bank['drawing']['path'],'original');self.assertEqual(selected['room'],bank['room'])
        with patch('animation_demos.state',return_value=[]):self.assertEqual(renderer.action_variants(bank),bank)

    def test_changed_video_or_unacceptable_native_motion_is_held(self):
        for field,value in (('maximum_hand_target_error',.01),('maximum_planted_foot_slide_per_frame',float('nan')),('frames',107)):
            self.report.write_text(json.dumps({**self.motion,field:value}),encoding='utf-8')
            with self.subTest(field=field),self.assertRaises(ValueError):renderer.action_variants({})
        self.report.write_text(json.dumps(self.motion),encoding='utf-8');self.video.write_bytes(b'changed')
        with self.assertRaises(ValueError):renderer.action_variants({})


if __name__=='__main__':unittest.main()
