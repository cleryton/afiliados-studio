import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import campaigns
import content_engine
import core
import creative
import renderer


class CreativeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start()
        self.addCleanup(self.override.stop);self.addCleanup(self.temp.cleanup);core.init()
        self.product={'name':'Organizador de mesa','url':'https://example.com/p?af=original','kind':'physical','category':'Organização e casa',
                      'description':'Feito em madeira. Possui três divisórias. Mede 20 cm de largura. Inclui base removível.'}
        content_engine.configure({'mode':'rules','format':'portrait','length':'complete','pace':'normal'})

    def test_four_openings_are_distinct_and_include_product_context(self):
        openings=[content_engine.generate(self.product,i)[0][0] for i in range(4)]
        self.assertEqual(len(set(openings)),4)
        self.assertTrue(all(self.product['name'] in hook for hook in openings))
        self.assertTrue(all(hook.endswith('?') for hook in openings))

    def test_short_mode_rotates_source_facts_without_inventing_features(self):
        content_engine.configure({'mode':'rules','length':'short','pace':'agil'})
        first,caption,meta=content_engine.generate(self.product)
        second,_,_=content_engine.generate(self.product,1)
        self.assertEqual(len(first),5);self.assertEqual(meta['source_fact_count'],4)
        self.assertEqual(set(first[2:-1]+second[2:-1]),set(content_engine.facts_from(self.product['description'])))
        self.assertIn(self.product['url'],caption);self.assertIn('Publicidade',caption)
        self.assertEqual(meta['reading']['pace'],'agil');self.assertTrue(meta['reading']['estimated'])

    def test_campaign_tones_and_public_remain_distinct(self):
        pid=core.save_product(self.product);product={**self.product,'id':pid}
        cid=campaigns.save({'name':'Casa','audience':'escritórios pequenos','tone':'educativo','product_ids':[pid]})
        first=content_engine.generate(product)[0][0]
        campaigns.save({'name':'Casa','audience':'escritórios pequenos','tone':'comparativo','product_ids':[pid]},cid)
        second=content_engine.generate(product)[0][0]
        self.assertNotEqual(first,second);self.assertIn('escritórios pequenos',first);self.assertIn('escritórios pequenos',second)

    def test_regeneration_avoids_previous_opening_when_alternative_exists(self):
        pid=core.save_product(self.product);jid=core.create_job({'product_id':pid})
        first=json.loads(core.get_job(jid)['scenes'])[0]
        core.regenerate_job(jid)
        self.assertNotEqual(json.loads(core.get_job(jid)['scenes'])[0],first)

    def test_tags_follow_kind_and_category_instead_of_generic_hype(self):
        tags=creative.hashtags({**self.product,'kind':'digital'})
        self.assertIn('#produtosdigitais',tags);self.assertIn('#organizacaoecasa',tags)
        self.assertNotIn('#achadinhos',tags);self.assertTrue(tags.endswith('#publicidade'))

    def test_content_options_are_validated_and_partial_updates_preserved(self):
        content_engine.configure({'mode':'rules','length':'short','pace':'agil'})
        content_engine.configure({'mode':'auto','format':'landscape'})
        self.assertEqual(content_engine.settings()['length'],'short');self.assertEqual(content_engine.settings()['pace'],'agil')
        for payload in [{'mode':'rules','length':'unknown'},{'mode':'rules','pace':'fastest'}]:
            with self.assertRaises(ValueError):content_engine.configure(payload)

    def test_long_name_and_audience_stay_bounded(self):
        product={**self.product,'name':'Nome comprido '*10}
        hook=creative.opening(product,{'tone':'educativo','audience':'Público com uma descrição muito longa '*4},0)
        self.assertLess(len(hook),230);self.assertTrue(hook.endswith('?'))

    def test_subtitles_fit_two_lines_and_cover_exact_scene_duration(self):
        scenes=['Texto de abertura.','Uma característica detalhada com '+('palavras verificadas '*15)]
        segments=creative.subtitle_segments(scenes,[4.5,12])
        self.assertGreater(len(segments),len(scenes))
        self.assertEqual(segments[0]['start'],0);self.assertEqual(segments[-1]['end'],16.5)
        for i,item in enumerate(segments):
            self.assertLessEqual(len(item['text'].splitlines()),2)
            self.assertTrue(all(len(line)<=42 for line in item['text'].splitlines()))
            self.assertGreater(item['end'],item['start'])
            if i:self.assertEqual(segments[i-1]['end'],item['start'])
        self.assertIn('00:00:16,500',creative.srt(segments))

    def test_subtitles_preserve_negative_numbers_decimals_and_every_word(self):
        scene='Temperatura mínima de -5 °C. Peso de 1.5 kg. Mede 20 x 15 cm. '+('Informação adicional. '*9)
        segments=creative.subtitle_segments([scene],[20])
        joined=' '.join(' '.join(s['text'].split()) for s in segments)
        self.assertEqual(joined,' '.join(scene.split()))

    def test_invalid_subtitle_inputs_fail_clearly(self):
        with self.assertRaises(ValueError):creative.subtitle_segments(['texto'],[])
        with self.assertRaises(ValueError):creative.subtitle_segments([''],[4.5])

    def test_manual_edits_refresh_reading_estimate(self):
        pid=core.save_product(self.product);jid=core.create_job({'product_id':pid});job=core.get_job(jid)
        scenes=json.loads(job['scenes']);scenes[0]='O que observar neste produto antes de escolher com informação?'
        core.edit_job(jid,{'scenes':scenes,'caption':job['caption'],'due_at':job['due_at'],'action':'save'})
        saved=core.state()['jobs'][0]['content']
        self.assertEqual(saved['reading'],creative.reading(scenes,'normal'))

    def test_both_layouts_fit_long_verified_facts_with_or_without_authorized_photo(self):
        from PIL import Image
        photo=core.DATA/'media'/'test.jpg'
        Image.new('RGB',(320,180),'#4d6c80').save(photo)
        text='Característica verificada com informações de dimensão e material. '*3
        for image in ('','test.jpg'):
            product={**self.product,'name':'Nome detalhado de um produto para verificar a composição visual. '*2,'image':image}
            for render,size in [(renderer.frame,(720,1280)),(renderer.landscape_frame,(1280,720))]:
                destination=core.DATA/'frame.png'
                render(product,text,2,destination,total=5)
                with Image.open(destination) as result:self.assertEqual(result.size,size)
