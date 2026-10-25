from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core
import stories
import story_publishing as publishing
import upload_post_client as provider

BINDING={'profile':'project-profile','account_id':'stable-open-id','handle':'novelitas0213','capabilities':['video_privacy']}
PROFILES=[{'username':'project-profile','social_accounts':{'tiktok':{'username':'stable-open-id','handle':'novelitas0213','capabilities':['video_privacy']}}}]


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        change=patch.object(core,'DATA',Path(self.temp.name));change.start();self.addCleanup(change.stop)
        core.init();stories.create_pilot();stories.set_profile({'handle':'novelitas0213'})
        publishing.put({'binding':BINDING,'enabled':True})
        clock=patch.object(core,'now',return_value=datetime(2026,10,25,12,tzinfo=core.TZ));clock.start();self.addCleanup(clock.stop)

    def media(self,number=1):
        with core.db() as c:
            row=c.execute('SELECT * FROM story_episodes WHERE number=?',(number,)).fetchone()
            c.execute("UPDATE story_episodes SET status='ready' WHERE id=?",(row['id'],))
        folder=core.DATA/'stories'/row['id'];folder.mkdir(parents=True,exist_ok=True)
        video=b'Synthetic fixture only, not real render evidence '+str(number).encode()
        (folder/'video.mp4').write_bytes(video)
        meta={'duration':5,'voice':True,'sha256':hashlib.sha256(video).hexdigest(),'offer':None}
        (folder/'roteiro.json').write_text(json.dumps(meta),encoding='utf-8')
        (folder/'legenda.txt').write_text('Ficção original com narração sintética.',encoding='utf-8')
        return row['id']

    def due(self,number=1):
        identifier=self.media(number);request=publishing.queue(identifier,now=True)['id']
        return identifier,request

    def test_queue_deduplicates_content_and_reserves_different_days(self):
        media=self.media();a=publishing.queue(media);b=publishing.queue(media)
        self.assertEqual(a['id'],b['id']);self.assertTrue(b['existing'])
        publishing.queue(self.media(2))
        rows=sorted(publishing.state()['jobs'],key=lambda row:row['due_at'])
        self.assertEqual(rows[0]['due_at'][:10],'2026-10-25');self.assertEqual(rows[1]['due_at'][:10],'2026-10-26')

    def test_native_3d_chapters_have_distinct_logical_keys_but_versions_do_not(self):
        import animation3d
        media=self.media();folder=core.DATA/'stories'/media
        with core.db() as c:c.execute('DELETE FROM story_episodes WHERE id=?',(media,))
        meta=json.loads((folder/'roteiro.json').read_text(encoding='utf-8'))
        with patch.object(animation3d,'preview_state',return_value={'id':media}):
            for number in (1,2,3):
                (folder/'roteiro.json').write_text(json.dumps({**meta,'episode':number}),encoding='utf-8')
                self.assertEqual(publishing.media_snapshot(media)['content_key'],f'3d:a-chave-do-12:{number}')
            (folder/'roteiro.json').write_text(json.dumps({**meta,'episode':4}),encoding='utf-8')
            with self.assertRaises(ValueError):publishing.media_snapshot(media)

    def test_success_requires_real_destination_url_and_no_fallback(self):
        good={'results':{'tiktok':{'success':True,'url':'https://www.tiktok.com/@novelitas0213/video/12345'}}}
        self.assertEqual(publishing.publication_result(good,BINDING)[0],'published')
        for result,expected in [({'success':True,'fallback_to_inbox':True},'draft'),
            ({'success':True,'url':'https://evil.example/@novelitas0213/video/12345'},'processing'),
            ({'success':True,'url':'https://www.tiktok.com/@personal/video/12345'},'processing'),
            ({'success':False,'skipped':True},'blocked'),
            ({'success':True,'url':'https://www.tiktok.com/@novelitas0213/video/12345','warnings':['is_aigc ignored']},'needs_review')]:
            with self.subTest(result=result):self.assertEqual(publishing.publication_result({'results':{'tiktok':result}},BINDING)[0],expected)

    def test_one_upload_then_only_status_reads(self):
        media,request=self.due()
        with patch.object(provider,'profiles',return_value=PROFILES),patch.object(provider,'upload',return_value={'success':True,'request_id':request}) as upload:
            publishing.tick();publishing.tick()
        upload.assert_called_once()
        self.assertEqual(publishing.state()['jobs'][0]['status'],'processing')
        with core.db() as c:c.execute('UPDATE story_publications SET checked_at=NULL')
        with patch.object(provider,'upload') as resend,patch.object(provider,'status',return_value={'status':'completed','results':[{'platform':'tiktok','success':True,'post_url':'https://www.tiktok.com/@novelitas0213/video/12345'}]}):
            publishing.tick()
        resend.assert_not_called();self.assertEqual(publishing.state()['jobs'][0]['status'],'published')

    def test_response_loss_and_restart_never_reupload(self):
        self.due()
        with patch.object(provider,'profiles',return_value=PROFILES),patch.object(provider,'upload',side_effect=provider.ProviderError('Unknown delivery',uncertain=True)) as upload:
            publishing.tick()
        self.assertEqual(upload.call_count,1);self.assertEqual(publishing.state()['jobs'][0]['status'],'uncertain')
        publishing.init()
        with core.db() as c:c.execute('UPDATE story_publications SET checked_at=NULL')
        with patch.object(provider,'upload') as resend,patch.object(provider,'status',side_effect=provider.ProviderError('Not found')):
            publishing.tick()
        resend.assert_not_called();self.assertEqual(publishing.state()['jobs'][0]['status'],'uncertain')

    def test_pending_requests_are_still_checked_when_paused(self):
        self.due()
        with core.db() as c:c.execute("UPDATE story_publications SET status='processing'")
        publishing.put({'enabled':False})
        with patch.object(provider,'status',return_value={'status':'pending'}) as status:publishing.tick()
        status.assert_called_once()

    def test_replacing_account_or_caption_blocks_the_send(self):
        for mutation in ('account','caption'):
            with self.subTest(mutation=mutation):
                with core.db() as c:c.execute('DELETE FROM story_publications')
                media,request=self.due()
                if mutation=='caption':(core.DATA/'stories'/media/'legenda.txt').write_text('Edited after approval',encoding='utf-8')
                profiles=PROFILES if mutation=='caption' else [{'username':'project-profile','social_accounts':{'tiktok':{'handle':'novelitas0213','username':'different-account'}}}]
                with patch.object(provider,'profiles',return_value=profiles),patch.object(provider,'upload') as upload:publishing.tick()
                upload.assert_not_called();self.assertEqual(publishing.state()['jobs'][0]['status'],'blocked')

    def test_daily_and_monthly_caps_do_not_send_extra_requests(self):
        self.due()
        with core.db() as c:
            c.execute("UPDATE story_publications SET status='published',attempted_at=?",(core.stamp(),))
        second=self.media(2);publishing.queue(second,now=True)
        with core.db() as c:c.execute('UPDATE story_publications SET due_at=? WHERE media_id=?',(core.stamp(),second))
        with patch.object(provider,'upload') as upload:publishing.tick()
        upload.assert_not_called()
        with core.db() as c:c.execute("UPDATE story_publications SET attempted_at='2026-10-24T12:00:00-03:00' WHERE status='published'")
        publishing.put({'monthly_limit':1})
        with patch.object(provider,'upload') as upload:publishing.tick()
        upload.assert_not_called()

    def test_tester_blocks_connection_configuration_and_delivery(self):
        self.due()
        with patch.object(core,'TESTER',True),patch.object(provider,'profiles') as profiles,patch.object(provider,'upload') as upload:
            with self.assertRaises(ValueError):publishing.connect({'api_key':'fake-local-key-that-is-not-a-secret','handle':'novelitas0213'})
            with self.assertRaises(ValueError):publishing.configure({'enabled':True,'approved':True})
            with self.assertRaises(ValueError):publishing.queue(self.media(2))
            publishing.tick()
        profiles.assert_not_called();upload.assert_not_called()

    def test_connection_binds_id_and_never_returns_the_secret(self):
        with patch.object(provider,'profiles',return_value=PROFILES),patch.object(provider,'store_key') as store:
            result=publishing.connect({'handle':'novelitas0213','api_key':'fake-local-key-that-is-not-a-secret'})
        self.assertEqual(publishing.settings()['binding']['account_id'],'stable-open-id')
        self.assertFalse(publishing.settings()['enabled']);store.assert_called_once()
        self.assertNotIn('fake-local',json.dumps(result)+json.dumps(publishing.state()))
        with patch.object(provider,'profiles') as remote,self.assertRaises(ValueError):publishing.connect({'handle':'personal','api_key':'fake-local-key-that-is-not-a-secret'})
        remote.assert_not_called()

    def test_modified_movie_or_unknown_media_is_rejected(self):
        media=self.media();(core.DATA/'stories'/media/'video.mp4').write_bytes(b'changed')
        for identifier in (media,'../secret','b'*32):
            with self.subTest(identifier=identifier),self.assertRaises(ValueError):publishing.queue(identifier)


class ProviderTests(unittest.TestCase):
    def test_destination_requires_stable_id_handle_and_unique_profile(self):
        self.assertEqual(provider.destination(PROFILES,'novelitas0213')['account_id'],'stable-open-id')
        for rows in ([],PROFILES+PROFILES,[{'username':'project','social_accounts':{'tiktok':{'handle':'novelitas0213'}}}]):
            with self.assertRaises(ValueError):provider.destination(rows,'novelitas0213')

    def test_free_tiktok_rejection_is_reported_without_secret_or_upgrade(self):
        class Response:
            status=403
            def read(self,n):return json.dumps({'message':'TikTok uploads are not available on the Free plan. Please upgrade.'}).encode()
        with self.assertRaises(provider.ProviderError) as caught:provider.response_json(Response(),True)
        self.assertIn('plano pago',str(caught.exception));self.assertFalse(caught.exception.uncertain)

    def test_multipart_streams_local_file_with_identity_and_disclosures(self):
        class Response:
            status=200
            def read(self,n):return b'{"success":true,"request_id":"stable-request"}'
        class Connection:
            def __init__(self,*a,**kw):self.headers={};self.parts=[]
            def putrequest(self,method,path):self.method=method;self.path=path
            def putheader(self,k,v):self.headers[k]=v
            def endheaders(self):pass
            def send(self,value):self.parts.append(value)
            def getresponse(self):return Response()
            def close(self):pass
        with tempfile.TemporaryDirectory() as directory:
            movie=Path(directory)/'video.mp4';movie.write_bytes(b'x'*600000);connection=Connection()
            with patch.object(provider.http.client,'HTTPSConnection',return_value=connection),patch.object(provider,'load_key',return_value='fixture-key'),patch.object(core,'TESTER',False):
                provider.upload(movie,'PUBLICIDADE. Fixture.',BINDING,'stable-request',True)
        body=b''.join(connection.parts);self.assertEqual(int(connection.headers['Content-Length']),len(body))
        self.assertEqual(connection.headers['Idempotency-Key'],'stable-request')
        for expected in (b'name="brand_content_toggle"\r\n\r\ntrue',b'name="is_aigc"\r\n\r\ntrue',b'name="post_mode"\r\n\r\nDIRECT_POST',b'PUBLIC_TO_EVERYONE'):
            self.assertIn(expected,body)
        self.assertGreater(len(connection.parts),3);self.assertNotIn(b'fixture-key',body)
