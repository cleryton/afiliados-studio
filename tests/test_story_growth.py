from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import stories
import story_growth as growth
import story_offers


class StoryGrowthTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        data = patch.object(core, 'DATA', Path(temp.name));data.start();self.addCleanup(data.stop)
        core.init();stories.set_profile({'handle':'fiction_project'})
        self.payload = {'url':'https://www.tiktok.com/@fiction_project/video/7700416698603539718',
                        'published_at':'2026-10-24T18:00:00-03:00','duration':60,'views':0}
        clock = patch.object(core, 'now', return_value=datetime(2026,10,25,12,tzinfo=core.TZ))
        clock.start();self.addCleanup(clock.stop)

    def test_unknown_metrics_are_not_zero_or_performance_claims(self):
        self.assertEqual(growth.state()['posts'],[])
        growth.record(self.payload)
        row = growth.state()['posts'][0]
        self.assertEqual(row['views'],0);self.assertIsNone(row['likes'])
        self.assertIsNone(row['interaction_rate']);self.assertIsNone(row['watch_ratio'])
        self.assertIn('Ainda faltam',growth.state()['diagnosis'])

    def test_only_latest_snapshot_per_post_is_counted_without_summing_cumulative_views(self):
        growth.record(self.payload)
        with patch.object(core,'now',return_value=core.now()+timedelta(hours=24)):
            growth.record({**self.payload,'views':100,'likes':6,'comments':2,'shares':2,'average_watch':18,'completion':20})
        state = growth.state();self.assertEqual(len(state['posts']),1);self.assertEqual(state['observations'],2)
        self.assertEqual(state['posts'][0]['views'],100)
        self.assertEqual(state['posts'][0]['interaction_rate'],10)
        self.assertEqual(state['posts'][0]['watch_ratio'],30)
        self.assertEqual(state['posts'][0]['completion'],20)
        self.assertNotIn(str(core.DATA),json.dumps(state))

    def test_replayed_watch_time_is_not_mislabeled_as_completion(self):
        growth.record({**self.payload,'views':2,'average_watch':75,'completion':''})
        row = growth.state()['posts'][0]
        self.assertEqual(row['watch_ratio'],125);self.assertIsNone(row['completion'])

    def test_other_accounts_and_host_confusion_are_rejected(self):
        for url in ('http://www.tiktok.com/@fiction_project/video/7700416698603539718',
                    self.payload['url'].replace('@fiction_project','@personal'),
                    self.payload['url'].replace('www.tiktok.com','www.tiktok.com.evil.example'),
                    self.payload['url']+'?secret=fixture',self.payload['url']+'#fragment',
                    'javascript:alert(1)','https://www.tiktok.com/@fiction_project/video/1'):
            with self.subTest(url=url),self.assertRaises(ValueError):growth.record({**self.payload,'url':url})
        self.assertEqual(growth.state()['posts'],[])

    def test_invalid_numbers_and_future_publications_are_rejected(self):
        for key,value in (('views',-1),('likes',True),('shares',1.2),('duration',0),('duration',float('inf')),
                          ('average_watch',float('nan')),('completion',101),('comments','abc'),('followers',{}),
                          ('published_at','2027-01-01T18:00:00-03:00'),('published_at','2026-10-24T18:00:00')):
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):growth.record({**self.payload,key:value})
        with self.assertRaises(ValueError):growth.record({**self.payload,'views':''})

    def test_profile_change_hides_old_account_measurements(self):
        growth.record(self.payload);stories.set_profile({'handle':'another_project'})
        self.assertEqual(growth.state()['posts'],[])

    def test_editorial_has_original_finite_continuity_and_preserves_commercial_disclosures(self):
        offer={'name':'Curso autorizado','url':'https://example.com/own-affiliate','facts':['Uma característica verificada.']}
        kit = growth.editorial(2,offer)
        self.assertEqual(len(kit['scenes']),6);self.assertEqual(kit['scenes'][0]['text'],kit['hook'])
        self.assertIn('capítulo três',kit['scenes'][-1]['text'])
        self.assertTrue(growth.editorial(3)['scenes'][-1]['text'].endswith('Fim.'))
        self.assertIn(offer['url'],kit['caption']);self.assertIn('PUBLICIDADE',kit['caption'])
        self.assertIn('não são clientes nem depoimentos',kit['caption'])
        self.assertNotIn('link na bio',kit['caption'].lower())
        brief=story_offers.scenes(offer,brief=True)
        self.assertEqual(len(brief),1);self.assertIn('Publicidade',brief[0]['text'])
        self.assertIn('comissão',brief[0]['text']);self.assertEqual(len(story_offers.scenes(offer)),2)
