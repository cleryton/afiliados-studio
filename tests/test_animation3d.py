import json
import math
from array import array
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch
import animation3d
import core


class Animation3DTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        change=patch.object(core,'DATA',Path(self.temp.name));change.start();self.addCleanup(change.stop)

    def fixture(self):
        pointer=core.DATA/'story-3d'/'preview.json';pointer.parent.mkdir()
        identifier='a'*32;folder=core.DATA/'stories'/identifier;folder.mkdir(parents=True)
        (folder/'video.mp4').write_bytes(b'fixture, not render evidence')
        metadata={'animation_type':'original_procedural_3d','character_animation':True,'duration':52.5,'offer':None}
        (folder/'roteiro.json').write_text(json.dumps(metadata),encoding='utf-8')
        pointer.write_text(json.dumps({'id':identifier,'ready':True,'sha256':'0'*64}),encoding='utf-8')
        return pointer,folder,metadata

    def test_preview_requires_actual_completion_and_native_animation_metadata(self):
        self.assertIsNone(animation3d.preview_state())
        pointer,folder,metadata=self.fixture()
        ready=animation3d.preview_state()
        self.assertEqual(ready['duration'],52.5);self.assertIn('/stories/'+'a'*32,ready['video_url'])
        self.assertNotIn(str(core.DATA),json.dumps(ready))
        for value in ({'animation_type':'still'}, {'character_animation':False}, {'duration':-1}, {'duration':181}):
            (folder/'roteiro.json').write_text(json.dumps({**metadata,**value}),encoding='utf-8')
            self.assertIsNone(animation3d.preview_state())
        (folder/'roteiro.json').write_text(json.dumps(metadata),encoding='utf-8')
        (folder/'video.mp4').unlink();self.assertIsNone(animation3d.preview_state())

    def test_preview_rejects_traversal_invalid_json_and_incomplete_pointer(self):
        pointer,folder,metadata=self.fixture()
        for identifier in ('../secret','a'*31,'../../outside','<script>'):
            pointer.write_text(json.dumps({'id':identifier,'ready':True}),encoding='utf-8')
            self.assertIsNone(animation3d.preview_state())
        for content in ('not json','[]',json.dumps({'id':'a'*32,'ready':False})):
            pointer.write_text(content,encoding='utf-8');self.assertIsNone(animation3d.preview_state())

    def test_revoked_offer_does_not_offer_a_ready_preview(self):
        self.fixture()
        with patch('story_offers.current',return_value=False):self.assertIsNone(animation3d.preview_state())

    def test_missing_blender_fails_without_download_or_publication(self):
        with self.assertRaises(ValueError):animation3d.find_blender(core.DATA/'not-installed.exe')

    def test_preview_exposes_correct_chapter_and_rejects_invalid_numbers(self):
        pointer,folder,metadata=self.fixture()
        for number in (2,3,4,8):
            (folder/'roteiro.json').write_text(json.dumps({**metadata,'episode':number}),encoding='utf-8')
            self.assertEqual(animation3d.preview_state()['number'],number)
            self.assertIn(f'capítulo {number}',animation3d.preview_state()['title'])
        for number in (0,9,True,'2'):
            (folder/'roteiro.json').write_text(json.dumps({**metadata,'episode':number}),encoding='utf-8')
            self.assertIsNone(animation3d.preview_state())

    def test_invalid_chapter_or_cache_reuse_stops_before_render(self):
        with patch.object(animation3d,'find_blender') as blender:
            with self.assertRaises(ValueError):animation3d.render_pilot(number=4)
            with self.assertRaises(ValueError):animation3d.render_pilot(number=2,reuse_id='a'*32)
        blender.assert_not_called()

    def test_story_has_original_short_scenes_and_cliffhanger(self):
        self.assertEqual(len(animation3d.PILOT_3D),6)
        self.assertEqual([s['visual'] for s in animation3d.PILOT_3D],['key','letter','building','door','portrait','photo'])
        self.assertTrue(animation3d.PILOT_3D[-1]['text'].endswith('Continua.'))

    def test_speech_energy_follows_voice_and_settles_back_to_silence(self):
        audio=core.DATA/'voice.wav';rate=12000
        samples=array('h',[0]*rate+[round(10000*math.sin(2*math.pi*180*n/rate)) for n in range(rate)]+[0]*rate)
        with wave.open(str(audio),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate);stream.writeframes(samples.tobytes())
        envelope=animation3d.speech_energy(audio,12)
        self.assertEqual(len(envelope),36)
        self.assertEqual(max(envelope[:12]),0)
        self.assertGreater(max(envelope[12:24]),.9)
        self.assertLess(envelope[-1],.001)
        self.assertTrue(all(0<=v<=1 for v in envelope))
