import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import content_engine
import core


class ContentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start();core.init()
        self.product={'name':'Organizador de mesa','category':'Casa','description':'Feito em madeira. Possui três divisórias. Mede 20 cm de largura. Inclui base removível.','url':'https://example.com/produto?afiliado=abc','kind':'physical'}

    def tearDown(self):self.override.stop();self.temp.cleanup()

    def test_rules_create_complete_storyboard_and_preserve_affiliate_link(self):
        scenes,caption,meta=content_engine.generate(self.product,config={'mode':'rules'})
        self.assertEqual(len(scenes),7)
        self.assertEqual(scenes[2:6],content_engine.facts_from(self.product['description']))
        self.assertIn(self.product['url'],caption)
        self.assertEqual(meta['engine'],'rules')

    def test_ollama_only_chooses_hook_and_order_never_rewrites_facts(self):
        local={'available':True,'models':[{'name':'local-model','size':1}]}
        with patch('content_engine.availability',return_value=local),patch('content_engine.ollama_plan',return_value=('O que observar neste organizador de mesa?',[3,2,1,0],content_engine.ANGLES[1])):
            scenes,_,meta=content_engine.generate(self.product)
        self.assertEqual(scenes[2:6],list(reversed(content_engine.facts_from(self.product['description']))))
        self.assertEqual(meta['engine'],'ollama')

    def test_no_ollama_falls_back_without_stopping_pipeline(self):
        with patch('content_engine.availability',return_value={'available':False,'models':[]}):
            scenes,_,meta=content_engine.generate(self.product)
        self.assertEqual(meta['engine'],'rules');self.assertEqual(len(scenes),7)
        self.assertIn('indisponível',meta['note'])

    def test_model_failure_also_falls_back(self):
        with patch('content_engine.availability',return_value={'available':True,'models':[{'name':'test','size':1}]}),patch('content_engine.ollama_plan',side_effect=TimeoutError):
            _,_,meta=content_engine.generate(self.product)
        self.assertEqual(meta['engine'],'rules')

    def test_hallucinated_discount_and_incomplete_fact_order_rejected(self):
        facts=content_engine.facts_from(self.product['description'])
        for plan in [{'hook':'Quer comprar com 90% de desconto?','fact_order':[0,1,2,3],'angle':content_engine.ANGLES[0]},
                     {'hook':'Você já conferiu os detalhes?','fact_order':[0,0,1,2],'angle':content_engine.ANGLES[0]},
                     {'hook':'Este é o melhor produto?','fact_order':[0,1,2,3],'angle':content_engine.ANGLES[0]}]:
            with self.subTest(plan=plan),self.assertRaises(ValueError):content_engine.validate_plan(plan,facts)

    def test_cloud_models_are_rejected(self):
        with self.assertRaises(ValueError):content_engine.configure({'mode':'auto','model':'model:cloud'})

    def test_source_text_and_scene_count_remain_bounded(self):
        facts=content_engine.facts_from(' '.join(['característica']*60))
        self.assertTrue(all(len(fact)<=220 for fact in facts));self.assertLessEqual(len(facts),4)

    def test_negative_values_and_decimal_units_are_preserved(self):
        facts=content_engine.facts_from('-5 °C de temperatura mínima. Peso de 1.5 kg.\n- Inclui base.')
        self.assertEqual(facts,['-5 °C de temperatura mínima.','Peso de 1.5 kg.','Inclui base.'])

    def test_manual_job_can_save_all_seven_scenes_and_records_edits(self):
        content_engine.configure({'mode':'rules'})
        pid=core.save_product(self.product);jid=core.create_job({'product_id':pid});job=core.get_job(jid)
        scenes=json.loads(job['scenes']);self.assertEqual(len(scenes),7)
        scenes[-1]='Veja a descrição completa antes de escolher.'
        core.edit_job(jid,{'scenes':scenes,'caption':job['caption'],'due_at':job['due_at'],'action':'save','rights':True})
        saved=core.state()['jobs'][0]
        self.assertEqual(saved['scenes'][-1],scenes[-1]);self.assertTrue(saved['content']['edited'])

    def test_malformed_ai_reply_cannot_replace_product_facts(self):
        with patch('content_engine.availability',return_value={'available':True,'models':[{'name':'test','size':1}]}),patch('content_engine.ollama_plan',side_effect=ValueError('plano inválido')):
            scenes,_,meta=content_engine.generate(self.product)
        self.assertEqual(meta['engine'],'rules')
        self.assertEqual(scenes[2:6],content_engine.facts_from(self.product['description']))


if __name__=='__main__':unittest.main()
