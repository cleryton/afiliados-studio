from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image
import core
import stories
import story_delivery as delivery


class StoryDeliveryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        change=patch.object(core,'DATA',Path(temp.name));change.start();self.addCleanup(change.stop)
        core.init();stories.set_profile({'handle':'fiction_project'})
        self.identifier='a'*32;self.source=core.DATA/'stories'/self.identifier;self.source.mkdir(parents=True)
        raw=b'local unit fixture; not real render evidence'
        (self.source/'video.mp4').write_bytes(raw)
        self.meta={'episode':2,'voice':True,'duration':59.54,'animation_type':'original_procedural_3d',
                   'character_animation':True,'sha256':hashlib.sha256(raw).hexdigest(),'offer':None}
        self.write_meta();Image.new('RGB',(720,1280),'#14211d').save(self.source/'poster.png')
        (self.source/'legenda.txt').write_text('Ficção original. Fotografia de IA e narração sintética.',encoding='utf-8')
        (self.source/'legendas.srt').write_text('1\n00:00:00,000 --> 00:00:03,000\nFicção original.\n',encoding='utf-8')

    def write_meta(self):
        (self.source/'roteiro.json').write_text(json.dumps(self.meta),encoding='utf-8')

    def test_bundle_has_only_fixed_members_and_keeps_real_destination_and_not_sent_status(self):
        delivery.prepare(self.identifier);archive=delivery.download(self.identifier)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(set(z.namelist()),{'video.mp4','capa.png','legenda.txt','legendas.srt','publicacao.json','LEIA.txt'})
            manifest=json.loads(z.read('publicacao.json'));self.assertEqual(manifest['handle'],'fiction_project')
            self.assertEqual(manifest['status'],'local_ready_not_sent');self.assertFalse(manifest['scheduled'])
            self.assertTrue(manifest['ai_label_required']);self.assertFalse(manifest['third_party_commercial_label_required'])
            self.assertEqual(z.read('video.mp4'),(self.source/'video.mp4').read_bytes())
            self.assertNotIn(str(core.DATA),z.read('publicacao.json').decode('utf-8'))

    def test_repeated_and_concurrent_preparation_reuses_one_valid_bundle(self):
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(delivery.prepare,[self.identifier]*2))
        self.assertEqual(sorted(r['existing'] for r in results),[False,True])
        self.assertTrue(delivery.info(self.identifier)['ready']);self.assertTrue(zipfile.is_zipfile(delivery.download(self.identifier)))

    def test_changed_video_or_caption_prevents_stale_download(self):
        delivery.prepare(self.identifier)
        (self.source/'legenda.txt').write_text('Texto alterado depois da preparação.',encoding='utf-8')
        self.assertIsNone(delivery.info(self.identifier))
        with self.assertRaises(ValueError):delivery.download(self.identifier)
        delivery.prepare(self.identifier)
        (self.source/'video.mp4').write_bytes(b'modified')
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)
        with self.assertRaises(ValueError):delivery.download(self.identifier)

    def test_profile_change_invalidates_package_and_requires_new_preparation(self):
        delivery.prepare(self.identifier);stories.set_profile({'handle':'another_project'})
        self.assertIsNone(delivery.info(self.identifier))
        with self.assertRaises(ValueError):delivery.download(self.identifier)
        delivery.prepare(self.identifier)
        with zipfile.ZipFile(delivery.download(self.identifier)) as z:self.assertEqual(json.loads(z.read('publicacao.json'))['handle'],'another_project')

    def test_corrupted_archive_is_rejected_then_can_be_rebuilt_from_valid_sources(self):
        delivery.prepare(self.identifier);archive=delivery.download(self.identifier);archive.write_bytes(b'corrupted archive')
        with self.assertRaises(ValueError):delivery.download(self.identifier)
        self.assertFalse(delivery.prepare(self.identifier)['existing']);self.assertTrue(zipfile.is_zipfile(delivery.download(self.identifier)))

    def test_registered_native_publication_blocks_another_delivery(self):
        receipt={'media_id':self.identifier,'handle':'fiction_project','status':'published_confirmed',
                 'url':'https://www.tiktok.com/@fiction_project/video/7700697193698577682'}
        (self.source/'publicacao-tiktok.json').write_text(json.dumps(receipt),encoding='utf-8')
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)

    def test_new_collection_cannot_be_packaged_without_a_matching_editorial_review(self):
        import story_director
        from story_week_catalog import STORIES
        story,report=story_director.plan(STORIES[9])
        self.meta.update(episode=9,scenes=story['scenes']);self.write_meta()
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)
        cards=[{'start':i*5,'end':(i+1)*5,'text':'Legenda de teste.'} for i in range(6)]
        self.meta['director']=story_director.review(report,[5]*6,cards,[True]*6);self.write_meta()
        delivery.prepare(self.identifier)
        self.meta['scenes'][1]['text']='Alterado após a revisão.';self.write_meta()
        with self.assertRaises(ValueError):delivery.download(self.identifier)

    def test_offer_revocation_and_missing_affiliate_disclosure_are_rejected(self):
        self.meta['offer']={'product_hash':'f'*64,'url':'https://example.com/own-affiliate'};self.write_meta()
        with patch('story_offers.current',return_value=True):
            with self.assertRaises(ValueError):delivery.prepare(self.identifier)
            (self.source/'legenda.txt').write_text('PUBLICIDADE. Link: https://example.com/own-affiliate',encoding='utf-8')
            delivery.prepare(self.identifier)
            with zipfile.ZipFile(delivery.download(self.identifier)) as z:self.assertTrue(json.loads(z.read('publicacao.json'))['third_party_commercial_label_required'])
        with patch('story_offers.current',return_value=False):
            with self.assertRaises(ValueError):delivery.download(self.identifier)

    def test_invalid_paths_missing_subtitles_and_wrong_cover_size_are_rejected(self):
        for value in ('../secret','a'*31,'../../outside',None):
            with self.subTest(value=value),self.assertRaises(ValueError):delivery.prepare(value)
        Image.new('RGB',(100,100)).save(self.source/'poster.png')
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)
        Image.new('RGB',(720,1280)).save(self.source/'poster.png');(self.source/'legendas.srt').unlink()
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)

    def test_existing_api_outbox_entry_prevents_another_delivery(self):
        stamp=core.stamp()
        with core.db() as c:
            c.execute('''INSERT INTO story_publications(id,media_id,content_key,account_id,binding,media_hash,caption_hash,offer,status,due_at,created_at,updated_at)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',('b'*32,self.identifier,'3d:a-chave-do-12:2','fixture-account','{}','f'*64,'e'*64,'null','queued',stamp,stamp,stamp))
        with self.assertRaises(ValueError):delivery.prepare(self.identifier)
