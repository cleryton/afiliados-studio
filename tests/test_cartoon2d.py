import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cartoon2d


class CartoonGalleryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        change = patch.object(cartoon2d.core, 'DATA', root)
        change.start()
        self.addCleanup(change.stop)
        self.identifier = 'c' * 32
        self.folder = root / 'stories' / self.identifier
        self.folder.mkdir(parents=True)
        for name in ('video.mp4', 'poster.png', 'legenda.txt', 'legendas.srt'):
            (self.folder / name).write_bytes(b'local-test-fixture; not a real render')
        self.meta = {'animation_type': 'original_procedural_2d', 'title': 'Teste local', 'voice': True,
                     'duration': 40, 'sha256': 'a' * 64, 'validation': {'decoded': True}}
        self.save(self.meta)
        self.catalog = root / 'cartoon-2d' / 'catalog.json'
        self.catalog.parent.mkdir()
        self.catalog.write_text(json.dumps({'clips': [{'id': self.identifier}]}), encoding='utf-8')

    def save(self, meta):
        (self.folder / 'roteiro.json').write_text(json.dumps(meta), encoding='utf-8')

    def test_gallery_requires_complete_voiced_decoded_media(self):
        self.assertEqual(cartoon2d.state()[0]['id'], self.identifier)
        for field, value in (('voice', False), ('validation', {}), ('episode', 9)):
            self.save({**self.meta, field: value})
            self.assertEqual(cartoon2d.state(), [])
        self.save(self.meta)
        (self.folder / 'legendas.srt').unlink()
        self.assertEqual(cartoon2d.state(), [])

    def test_gallery_ignores_path_traversal_and_duplicate_entries(self):
        rows = [{'id': '../outside'}, {'id': self.identifier}, {'id': self.identifier}]
        self.catalog.write_text(json.dumps({'clips': rows}), encoding='utf-8')
        self.assertEqual(len(cartoon2d.state()), 1)


class CartoonMotionTests(unittest.TestCase):
    def test_characters_and_props_move_within_each_scene(self):
        for story in cartoon2d.STORIES:
            for scene in range(6):
                images = [cartoon2d.frame(story, scene, .2, t, 'Legenda fixa.', .5) for t in (2.1, 2.6)]
                # Ignore subtitles and header: the animation itself must change.
                digests = {hashlib.sha256(image.crop((0, 220, 540, 760)).tobytes()).hexdigest() for image in images}
                with self.subTest(story=story['key'], scene=scene):
                    self.assertEqual(len(digests), 2)


class PartialRenderTests(unittest.TestCase):
    def test_partial_resume_does_not_overwrite_any_master_or_receipt(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(cartoon2d.core,'DATA',Path(directory)):
            folder=cartoon2d.output_folder('e'*32)
            (folder/'speech-0.json').write_text('{}',encoding='utf-8')
            self.assertEqual(cartoon2d.output_folder('e'*32,resume_incomplete=True),folder)
            for name in ('video.mp4','roteiro.json','agendamento-tiktok.json','unknown.txt'):
                with self.subTest(name=name):
                    target=folder/name;target.write_bytes(b'preserve')
                    with self.assertRaises(ValueError):cartoon2d.output_folder('e'*32,resume_incomplete=True)
                    self.assertEqual(target.read_bytes(),b'preserve');target.unlink()
            with self.assertRaises(ValueError):cartoon2d.output_folder('e'*32)


if __name__ == '__main__':
    unittest.main()
