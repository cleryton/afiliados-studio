from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta,datetime
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from PIL import Image
import autopilot,campaigns,catalog,catalog_media,content_engine,core,production,youtube_client


class CatalogMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        tester=patch.object(core,'TESTER',False);tester.start();self.addCleanup(tester.stop)
        core.init();autopilot.init();catalog.init();youtube_client.init()
        content_engine.configure({'mode':'rules'})
        self.item={'id':'sku','name':'Organizador','affiliate_url':'https://example.com/product?af=original',
                   'kind':'physical','description':'Possui três divisórias. Estrutura em madeira.',
                   'image_url':'https://example.com/authorized.png'}
        self.photo=self.png()

    def png(self,size=(128,96),color='red'):
        out=io.BytesIO();Image.new('RGB',size,color).save(out,format='PNG');return out.getvalue()

    def ingest(self,authorized=True):
        catalog.ingest([self.item],True,download_images=authorized)
        with core.db() as c:return c.execute('SELECT id FROM products LIMIT 1').fetchone()[0]

    def row(self,pid):
        with core.db() as c:return dict(c.execute('SELECT * FROM catalog_media WHERE product_id=?',(pid,)).fetchone())

    def image(self,pid):
        with core.db() as c:return c.execute('SELECT image FROM products WHERE id=?',(pid,)).fetchone()[0]

    def process(self,pid,raw=None):
        with patch.object(catalog_media,'fetch',return_value=catalog_media.normalize(raw or self.photo)):
            return catalog_media.process(pid)

    def test_photo_authorization_defaults_off_and_is_required(self):
        pid=self.ingest(False)
        with patch.object(catalog_media,'fetch') as fetch:catalog_media.tick()
        fetch.assert_not_called();self.assertEqual(self.image(pid),'')
        with self.assertRaises(ValueError):catalog.configure({'download_images':True,'authorized':False})

    def test_photo_is_normalized_locally_and_affiliate_link_preserved(self):
        pid=self.ingest();self.assertTrue(self.process(pid))
        path=core.DATA/'media'/self.image(pid)
        with Image.open(path) as photo:self.assertEqual(photo.format,'JPEG');self.assertEqual(photo.size,(128,96))
        self.assertEqual(self.row(pid)['status'],'ready')
        with core.db() as c:self.assertEqual(c.execute('SELECT url FROM products WHERE id=?',(pid,)).fetchone()[0],self.item['affiliate_url'])
        self.assertEqual(list((core.DATA/'media').glob('*.tmp')),[])

    def test_same_photo_after_refresh_reuses_file_without_product_change(self):
        pid=self.ingest();self.process(pid);before=self.image(pid)
        with core.db() as c:c.execute('UPDATE catalog_media SET next_check=NULL WHERE product_id=?',(pid,))
        self.process(pid)
        self.assertEqual(self.image(pid),before)
        self.assertEqual(len(list((core.DATA/'media').glob('*.jpg'))),1)

    def test_existing_manual_photo_is_preserved_without_download(self):
        pid=core.save_product({'name':'Foto própria','url':self.item['affiliate_url'],'kind':'physical',
                'description':self.item['description'],'image':'data:image/png;base64,'+__import__('base64').b64encode(self.photo).decode()})
        before=self.image(pid);self.ingest()
        with patch.object(catalog_media,'fetch') as fetch:self.assertIsNone(catalog_media.process(pid))
        fetch.assert_not_called();self.assertEqual(self.image(pid),before);self.assertEqual(self.row(pid)['status'],'manual')

    def test_revocation_detaches_only_managed_photo_and_preserves_file(self):
        pid=self.ingest();self.process(pid);before=self.image(pid)
        self.ingest(False)
        self.assertEqual(self.image(pid),'');self.assertFalse(self.row(pid)['authorized'])
        self.assertTrue((core.DATA/'media'/before).is_file())

    def test_removing_item_or_photo_url_retires_managed_photo(self):
        pid=self.ingest();self.process(pid)
        item={k:v for k,v in self.item.items() if k!='image_url'}
        catalog.ingest([item],True,download_images=True)
        self.assertEqual(self.image(pid),'')
        self.ingest();self.process(pid);catalog.ingest([],True,download_images=True)
        self.assertEqual(self.image(pid),'')

    def test_remote_pause_stops_download_and_keeps_already_authorized_photo(self):
        catalog.configure({'url':'https://example.com/feed','enabled':True,'authorized':True,'download_images':True})
        catalog.ingest([self.item],True,expected_revision=catalog.settings()['revision'])
        with core.db() as c:pid=c.execute('SELECT id FROM products').fetchone()[0]
        self.process(pid);before=self.image(pid)
        catalog.configure({'url':'https://example.com/feed','enabled':False,'authorized':True,'download_images':True})
        self.assertIsNone(self.process(pid));self.assertEqual(self.image(pid),before)
        catalog.configure({'url':'https://example.com/feed','enabled':True,'authorized':True,'download_images':False})
        self.assertEqual(self.image(pid),'')

    def test_tester_never_downloads_even_when_photo_authorized(self):
        pid=self.ingest()
        with patch.object(core,'TESTER',True),patch.object(catalog_media,'fetch') as fetch:
            self.assertIsNone(catalog_media.process(pid));catalog_media.tick()
        fetch.assert_not_called();self.assertEqual(self.row(pid)['attempts'],0)

    def test_race_revocation_source_switch_and_manual_change_discard_download(self):
        for action in ('revoke','source','manual'):
            with self.subTest(action=action):
                pid=self.ingest()
                def fetch(_):
                    if action=='revoke':self.ingest(False)
                    elif action=='source':
                        catalog.ingest([{**self.item,'image_url':'https://example.com/new.png'}],True,download_images=True)
                    else:
                        with core.db() as c:c.execute("UPDATE products SET image='manual-photo.jpg' WHERE id=?",(pid,))
                    return catalog_media.normalize(self.photo)
                with patch.object(catalog_media,'fetch',side_effect=fetch):self.assertFalse(catalog_media.process(pid))
                self.assertEqual(self.image(pid),'manual-photo.jpg' if action=='manual' else '')
                self.assertEqual(list((core.DATA/'media').glob('*.tmp')),[])
                with core.db() as c:
                    c.execute("UPDATE products SET image='' WHERE id=?",(pid,))
                    c.execute('UPDATE catalog_media SET next_check=NULL WHERE product_id=?',(pid,))

    def test_backoff_persists_and_valid_photo_resets_failures(self):
        pid=self.ingest();clock=core.now()
        for minutes in (5,15,60,240,240):
            with patch('core.now',return_value=clock),patch.object(catalog_media,'fetch',side_effect=OSError('offline')) as fetch:
                self.assertFalse(catalog_media.process(pid));self.assertIsNone(catalog_media.process(pid));self.assertEqual(fetch.call_count,1)
            row=self.row(pid);clock=datetime.fromisoformat(row['next_check'])
            self.assertEqual(clock-datetime.fromisoformat(row['last_attempt']),timedelta(minutes=minutes))
            catalog.init()
        with patch('core.now',return_value=clock):self.assertTrue(self.process(pid))
        self.assertEqual(self.row(pid)['attempts'],0)

    def test_batch_has_two_attempts_including_failures(self):
        catalog.ingest([{**self.item,'id':str(i),'affiliate_url':f'https://example.com/{i}?af=original'} for i in range(5)],True,download_images=True)
        with patch.object(catalog_media,'fetch',side_effect=OSError('offline')) as fetch:catalog_media.tick()
        self.assertEqual(fetch.call_count,2)

    def test_concurrent_claims_download_once(self):
        pid=self.ingest()
        with patch.object(catalog_media,'fetch',return_value=catalog_media.normalize(self.photo)) as fetch:
            with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(catalog_media.process,[pid,pid]))
            self.assertEqual(fetch.call_count,1);self.assertEqual(sum(result is True for result in results),1)

    def test_low_storage_and_paused_campaign_do_not_spend_attempts(self):
        pid=self.ingest()
        with patch.object(catalog_media.shutil,'disk_usage',return_value=SimpleNamespace(free=100)):
            self.assertIsNone(catalog_media.process(pid))
        self.assertEqual(self.row(pid)['attempts'],0)
        campaigns.save({'name':'Mesa','active':False,'product_ids':[pid]})
        with patch.object(catalog_media,'fetch') as fetch:self.assertIsNone(catalog_media.process(pid))
        fetch.assert_not_called()

    def test_invalid_images_and_dimensions_are_rejected(self):
        for raw in (b'<html>not an image</html>',b'x'*(catalog_media.MAX_BYTES+1),self.png(size=(32,32))):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):catalog_media.normalize(raw)
        with Image.new('RGB',(128,96),'red') as image:
            gif=io.BytesIO();image.save(gif,format='GIF')
        with self.assertRaises(ValueError):catalog_media.normalize(gif.getvalue())

    def test_transparency_is_flattened_and_metadata_removed(self):
        photo=Image.new('RGBA',(128,96),(255,0,0,0));photo.info['secret']='not copied'
        raw=io.BytesIO();photo.save(raw,format='PNG')
        clean=catalog_media.normalize(raw.getvalue())
        with Image.open(io.BytesIO(clean)) as result:
            self.assertEqual(result.mode,'RGB');self.assertTrue(all(c>245 for c in result.getpixel((0,0))));self.assertEqual(len(result.getexif()),0)

    def test_exif_orientation_applied_and_large_dimensions_rejected_before_decode(self):
        source=Image.new('RGB',(128,96),'red');exif=source.getexif();exif[274]=6
        raw=io.BytesIO();source.save(raw,format='JPEG',exif=exif)
        with Image.open(io.BytesIO(catalog_media.normalize(raw.getvalue()))) as result:
            self.assertEqual(result.size,(96,128));self.assertEqual(len(result.getexif()),0)
        huge=MagicMock(format='PNG',is_animated=False,width=5000,height=4000)
        huge.__enter__.return_value=huge
        with patch.object(catalog_media.Image,'open',return_value=huge),self.assertRaises(ValueError):catalog_media.normalize(b'header')
        huge.convert.assert_not_called()

    def test_private_photo_address_is_rejected_before_network(self):
        with self.assertRaises(ValueError):catalog.validate([{**self.item,'image_url':'http://127.0.0.1/photo.png'}])
        with patch.object(catalog_media,'build_opener') as opener:
            with self.assertRaises(ValueError):catalog_media.fetch('http://127.0.0.1/photo.png')
        opener.assert_not_called()

    def test_bounded_reader_rejects_slow_and_oversized_responses(self):
        for oversized in (False,True):
            response=io.BytesIO(b'x'*(catalog_media.MAX_BYTES+1) if oversized else self.photo)
            opener=MagicMock();opener.open.return_value=response
            with patch('core.public_url'),patch.object(catalog_media,'build_opener',return_value=opener),patch.object(catalog_media.time,'monotonic',side_effect=(0,21) if not oversized else lambda:0):
                with self.assertRaises(ValueError):catalog_media.fetch(self.item['image_url'])

    def test_photo_change_refreshes_unattempted_automatic_video(self):
        pid=self.ingest();autopilot.configure({'enabled':True});jid=autopilot.cycle()
        with core.db() as c:c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
        self.process(pid)
        self.assertIn(jid,production.refresh_ready())
        prepared=production.prepare(*production.claim_next())
        self.assertTrue(prepared[1]['image'])
        self.assertIn('af=original',prepared[0]['caption'])


if __name__=='__main__':unittest.main()
