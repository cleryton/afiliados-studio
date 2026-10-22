import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageChops,ImageStat
import content_engine
import core
import renderer
import imageio_ffmpeg


class RenderPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init()

    def test_real_mp4_changes_phrase_cards_in_both_formats_and_matches_metadata(self):
        real_run=subprocess.run
        def run(command,*args,**kwargs):
            if command[0]=='powershell.exe':raise FileNotFoundError('No speech for this fixture')
            return real_run(command,*args,**kwargs)
        for orientation,presentation in [('portrait','phrases'),('landscape','phrases'),('portrait','scene')]:
            with self.subTest(orientation=orientation,presentation=presentation):
                content_engine.configure({'mode':'rules','format':orientation,'presentation':presentation})
                pid=core.save_product({'name':'Organizador de mesa','url':'https://example.com/p?af=original','kind':'physical','category':'Casa',
                                       'description':'Possui três divisórias. Estrutura em madeira.'})
                jid=core.create_job({'product_id':pid});job=core.get_job(jid)
                scenes=['Confira as dimensões deste organizador de mesa e os materiais informados na ficha, pensando no espaço disponível para guardar seus objetos.',
                        'Conheça: Organizador de mesa','Possui três divisórias.','Confira as especificações e condições na página do produto.']
                core.edit_job(jid,{'scenes':scenes,'caption':job['caption'],'due_at':job['due_at'],'rights':True,'action':'render'})
                with core.db() as c:product=dict(c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone())
                with patch('renderer.subprocess.run',side_effect=run):voiced,warning=renderer.render(core.get_job(jid),product)
                self.assertFalse(voiced);self.assertIn('Sem voz',warning)
                directory=core.DATA/'media'/jid
                metadata=json.loads((directory/'conteudo.json').read_text(encoding='utf-8'))
                cards=metadata['presentation_segments']
                if presentation=='scene':
                    self.assertEqual(cards,[])
                    self.assertTrue((directory/'video.mp4').is_file())
                    continue
                self.assertGreater(len(cards),len(scenes));self.assertEqual(cards[-1]['end'],sum(metadata['durations']))
                self.assertEqual(' '.join(c['text'].replace('\n',' ') for c in cards),' '.join(scenes))
                self.assertFalse(list(directory.glob('speech-*.wav')));self.assertFalse(list(directory.glob('cards-*.txt')))
                self.assertFalse(list(directory.glob('clip-*.mp4')))
                second=cards[1];self.assertEqual(second['scene'],0)
                frame=directory/'decoded-test.png'
                real_run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-ss',str(second['start']+.3),'-i',str(directory/'video.mp4'),'-frames:v','1',str(frame)],check=True,capture_output=True,timeout=20)
                box=(60,650,660,1005) if orientation=='portrait' else (60,170,700,560)
                with Image.open(frame) as actual,Image.open(directory/'card-0-0.png') as first,Image.open(directory/'card-0-1.png') as expected:
                    def distance(reference):return sum(ImageStat.Stat(ImageChops.difference(actual.convert('RGB').crop(box),reference.convert('RGB').crop(box))).mean)
                    self.assertLess(distance(expected),distance(first))

    def test_failed_render_cleans_intermediates_but_preserves_original_video(self):
        jid='a'*32;directory=core.DATA/'media'/jid;directory.mkdir()
        (directory/'video.mp4').write_bytes(b'original')
        for name in ('speech-0.wav','speech-0.json','clip-0.mp4','cards-0.txt','building.mp4'):(directory/name).write_bytes(b'temporary')
        with patch.object(renderer,'_render',side_effect=ValueError('fixture failure')):
            with self.assertRaisesRegex(ValueError,'fixture failure'):renderer.render({'id':jid},{})
        self.assertEqual([p.name for p in directory.iterdir()],['video.mp4'])
