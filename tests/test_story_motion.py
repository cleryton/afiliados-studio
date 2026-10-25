import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
from PIL import ImageChops
import core
import story_motion
import story_renderer


class StoryMotionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override = patch.object(core, 'DATA', Path(self.temp.name));override.start();self.addCleanup(override.stop)

    def test_shots_cover_exact_frames_without_gaps_and_are_at_most_four_seconds(self):
        for duration in (4.5, 10.125, 19.75, 30):
            shots = story_motion.shots({'visual': 'letter'}, duration)
            self.assertEqual(shots[0]['start_frame'], 0)
            self.assertEqual(shots[-1]['end_frame'], round(duration * 24))
            self.assertTrue(all(0 < s['end_frame'] - s['start_frame'] <= 96 for s in shots))
            self.assertTrue(all(a['end_frame'] == b['start_frame'] for a, b in zip(shots, shots[1:])))
            self.assertGreater(len({s['mode'] for s in shots}), 1)
        self.assertEqual(len(story_motion.shots({'visual': 'offer'}, 12)), 1)

    def test_key_and_letter_change_independently_of_static_background(self):
        for visual in ('key', 'letter', 'door', 'photo'):
            painter = story_motion.SceneFrames(story_renderer.asset_path('discovery.png'),
                {'visual': visual}, {'number': 1}, 12)
            shot = painter.timeline[1]
            first = painter.frame(shot['start_frame'] + 4)
            last = painter.frame(shot['end_frame'] - 5)
            self.assertEqual(first.size, (720, 1280))
            delta = ImageChops.difference(first, last)
            self.assertIsNotNone(delta.crop((120, 300, 590, 850)).getbbox())
            # Independent insert motion must not translate the background too.
            self.assertLess(sum(delta.crop((5, 180, 75, 240)).convert('L').tobytes()), 500)

    def test_footage_requires_origin_explicit_authorization_and_exact_hash(self):
        folder = core.DATA / 'story-clips';folder.mkdir()
        clip = folder / 'episode-2-scene-1.mp4';clip.write_bytes(b'fixture, not a real video')
        manifest = folder / 'manifest.json'
        entry = {'file': clip.name, 'approved': True, 'source': 'Original footage, test fixture',
                 'sha256': hashlib.sha256(clip.read_bytes()).hexdigest()}
        self.assertIsNone(story_motion.authorized_clip({'number': 2}, 0))
        for changed in ({'approved': False}, {'file': '../outside.mp4'}, {'sha256': '0' * 64}, {'source': ''}):
            manifest.write_text(json.dumps({'2:1': {**entry, **changed}}), encoding='utf-8')
            with self.assertRaises(ValueError):story_motion.authorized_clip({'number': 2}, 0)
        manifest.write_text(json.dumps({'2:1': entry}), encoding='utf-8')
        self.assertEqual(story_motion.authorized_clip({'number': 2}, 0)['path'], clip)
        self.assertIsNone(story_motion.authorized_clip({'number': 2}, 1))
        clip.write_bytes(b'changed');
        with self.assertRaises(ValueError):story_motion.authorized_clip({'number': 2}, 0)

    def test_original_effects_are_audible_bounded_and_match_timeline(self):
        path = core.DATA / 'sound.wav'
        story_motion.sound_design(path, [{'visual': 'key'}, {'visual': 'offer'}], [4.5, 1])
        with wave.open(str(path)) as stream:
            self.assertEqual(stream.getnchannels(), 1)
            self.assertAlmostEqual(stream.getnframes() / stream.getframerate(), 5.5, places=4)
            data = stream.readframes(stream.getnframes())
        from array import array
        samples = array('h', data)
        self.assertGreater(max(samples), 200)
        self.assertLess(max(abs(n) for n in samples), 3277)

    def test_real_footage_is_used_and_invalid_footage_preserves_previous_export(self):
        import subprocess
        import imageio_ffmpeg
        folder = core.DATA / 'story-clips';folder.mkdir()
        clip = folder / 'episode-1-scene-1.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-v', 'error', '-f', 'lavfi',
            '-i', 'testsrc2=s=360x640:r=24:d=0.5', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(clip)],
            check=True, capture_output=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        manifest = folder / 'manifest.json'
        def approve():
            manifest.write_text(json.dumps({'1:1': {'file': clip.name, 'approved': True,
                'source': 'Synthetic moving test pattern', 'sha256': hashlib.sha256(clip.read_bytes()).hexdigest()}}), encoding='utf-8')
        approve()
        episode = {'id': 'c' * 32, 'number': 1, 'title': 'Fixture', 'series_title': 'Fixture',
                   'scenes': json.dumps([{'text': 'Uma cena de teste.', 'visual': 'key'}])}
        real_run = subprocess.run
        def run(command, *args, **kwargs):
            if command[0] == 'powershell.exe':raise FileNotFoundError('No speech fixture')
            return real_run(command, *args, **kwargs)
        with patch('story_renderer.subprocess.run', side_effect=run):result = story_renderer.render(episode)
        output = core.DATA / 'stories' / episode['id'];prior = (output / 'video.mp4').read_bytes()
        meta = json.loads((output / 'roteiro.json').read_text(encoding='utf-8'))
        self.assertGreater(result['duration'], 4)
        self.assertEqual(meta['shot_timeline'][0]['source'], 'authorized_video')
        self.assertEqual(meta['shot_timeline'][0]['clip']['sha256'], hashlib.sha256(clip.read_bytes()).hexdigest())
        self.assertNotIn(str(core.DATA), json.dumps(meta['shot_timeline']))
        clip.write_bytes(b'Invalid movie');approve()
        with patch('story_renderer.subprocess.run', side_effect=run),self.assertRaises(subprocess.CalledProcessError):
            story_renderer.render(episode)
        self.assertEqual((output / 'video.mp4').read_bytes(), prior)
        self.assertFalse(list(output.glob('motion-*')))
