import copy
import io
import json
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlparse
import app
import autopilot
import catalog
import content_engine
import core
import youtube_client as yt


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.override=patch.object(core,'DATA',Path(self.temp.name));self.override.start()
        core.init();autopilot.init();catalog.init();yt.init()
        # These fixtures test remote transitions; real media gates have their own tests.
        self.editorial=patch('quality.inspect',return_value={'allowed':True});self.editorial.start();self.addCleanup(self.editorial.stop)
        content_engine.configure({'mode':'rules','format':'landscape'})
        self.item={'id':'sku-1','name':'Organizador de mesa','description':'Possui três divisórias. Material em madeira. Medidas: 20 x 15 cm.',
                   'affiliate_url':'https://example.com/oferta?afiliado=meu-id','kind':'physical','category':'Casa'}

    def tearDown(self):
        self.override.stop();self.temp.cleanup()
        with yt._lock:yt._pending.clear()

    def ready(self):
        catalog.ingest([self.item],True)
        autopilot.configure({'enabled':True,'hours':[18]})
        jid=autopilot.cycle()
        with core.db() as c:
            c.execute("UPDATE jobs SET status='ready' WHERE id=?",(jid,))
            product=dict(c.execute('SELECT * FROM products').fetchone())
        directory=core.DATA/'media'/jid;directory.mkdir();(directory/'video.mp4').write_bytes(b'video-test-fixture')
        yt.put({'channel_id':'UC-test','channel_name':'Canal de teste','enabled':True})
        return core.get_job(jid),product

    def remote(self,jid,stage='processing',video_id='abc12345678'):
        with core.db() as c:c.execute('INSERT INTO youtube_jobs(job_id,stage,video_id,updated_at) VALUES (?,?,?,?)',(jid,stage,video_id,core.stamp()))

    def video(self,paid=True,privacy='private'):
        return {'id':'abc12345678','snippet':{'channelId':'UC-test','publishedAt':core.stamp()},'status':{'uploadStatus':'processed','privacyStatus':privacy},
                'paidProductPlacementDetails':{'hasPaidProductPlacement':paid},'statistics':{'viewCount':'42'}}

    def row(self,jid):
        with core.db() as c:
            row=c.execute('SELECT * FROM youtube_jobs WHERE job_id=?',(jid,)).fetchone()
            return dict(row) if row else None

    def test_catalog_is_atomic_and_preserves_tracking_link(self):
        catalog.ingest([self.item],True)
        invalid=copy.deepcopy(self.item);invalid['id']='bad';invalid['affiliate_url']='http://127.0.0.1/private'
        with self.assertRaises(ValueError):catalog.ingest([self.item,invalid],True)
        with core.db() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM products').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT url FROM products').fetchone()[0],self.item['affiliate_url'])
            self.assertEqual(c.execute('SELECT active FROM auto_products').fetchone()[0],1)

    def test_removed_products_and_stale_catalog_not_selected(self):
        catalog.ingest([self.item],True)
        with core.db() as c:pid=c.execute('SELECT id FROM products').fetchone()[0]
        catalog.ingest([],True)
        self.assertFalse(catalog.eligible(pid))
        catalog.ingest([self.item],True)
        with core.db() as c:c.execute('UPDATE catalog_items SET last_seen=?',((core.now()-timedelta(days=2)).isoformat(),))
        self.assertFalse(catalog.eligible(pid))
        self.assertEqual(autopilot.candidates(autopilot.settings(),core.now()),[])

    def test_catalog_reuses_manual_link_and_refreshes_source_before_generation(self):
        pid=core.save_product({'name':'Descrição antiga','url':self.item['affiliate_url'],'kind':'physical','category':'Casa','description':'Características antigas.'})
        result=catalog.ingest([self.item],True)
        self.assertEqual(result['added'],0)
        with core.db() as c:
            product=dict(c.execute('SELECT * FROM products WHERE id=?',(pid,)).fetchone())
            self.assertEqual(c.execute('SELECT COUNT(*) FROM products').fetchone()[0],1)
        self.assertEqual(product['description'],self.item['description'])
        autopilot.configure({'enabled':True,'hours':[18]})
        jid=autopilot.cycle()
        self.assertEqual(core.get_job(jid)['product_id'],pid)
        self.assertIn('Material em madeira.',json.loads(core.get_job(jid)['scenes']))

    def test_catalog_requires_authorization_and_real_links(self):
        with self.assertRaises(ValueError):catalog.ingest([self.item])
        with self.assertRaises(ValueError):catalog.configure({'enabled':True,'url':'https://example.com/catalog','authorized':False})
        self.assertFalse(app.readiness()['ready'])

    def test_renumbered_catalog_item_reuses_link_without_stale_mapping_block(self):
        catalog.ingest([self.item],True)
        catalog.ingest([{**self.item,'id':'new-sku'}],True)
        with core.db() as c:
            pid=c.execute('SELECT id FROM products').fetchone()[0]
            self.assertEqual(c.execute('SELECT COUNT(*) FROM products').fetchone()[0],1)
        self.assertTrue(catalog.eligible(pid))
        self.assertEqual(len(autopilot.candidates(autopilot.settings(),core.now())),1)
        catalog.ingest([{**self.item,'id':'new-sku','active':False}],True)
        self.assertFalse(catalog.eligible(pid))

    def test_catalog_refresh_does_not_override_operator_pause_or_variant_limit(self):
        catalog.ingest([self.item],True)
        with core.db() as c:pid=c.execute('SELECT id FROM products').fetchone()[0]
        autopilot.approve_product(pid,{'active':False,'approved':True,'max_variants':2})
        catalog.ingest([],True)
        catalog.ingest([self.item],True)
        with core.db() as c:rule=dict(c.execute('SELECT * FROM auto_products WHERE product_id=?',(pid,)).fetchone())
        self.assertEqual(rule['active'],0);self.assertEqual(rule['max_variants'],2)
        self.assertTrue(catalog.eligible(pid))
        self.assertEqual(autopilot.candidates(autopilot.settings(),core.now()),[])

    def test_source_pause_blocks_selection_then_resumes_without_changing_operator_choice(self):
        catalog.ingest([{**self.item,'active':False}],True)
        with core.db() as c:pid=c.execute('SELECT id FROM products').fetchone()[0]
        self.assertFalse(catalog.eligible(pid))
        self.assertEqual(autopilot.candidates(autopilot.settings(),core.now()),[])
        catalog.ingest([self.item],True)
        self.assertTrue(catalog.eligible(pid))
        self.assertEqual(len(autopilot.candidates(autopilot.settings(),core.now())),1)

    def test_credentials_encrypted_and_missing_channel_clear(self):
        document={'installed':{'client_id':'test.apps.googleusercontent.com','client_secret':'secret-fixture'}}
        yt.credentials(document)
        self.assertNotIn(b'secret-fixture',yt.secret_path('client').read_bytes())
        self.assertNotIn('secret-fixture',json.dumps(yt.state()))
        self.assertEqual(yt.read_secret('client')['client_secret'],'secret-fixture')
        with self.assertRaises(ValueError):yt.credentials({'web':{}})

    def test_oauth_has_pkce_and_rejects_wrong_or_replayed_state(self):
        yt.credentials({'installed':{'client_id':'test.apps.googleusercontent.com','client_secret':'fixture'}})
        query=parse_qs(urlparse(yt.begin(8765)).query)
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertEqual(query['redirect_uri'],['http://127.0.0.1:8765/oauth/youtube/callback'])
        with self.assertRaises(ValueError):yt.complete('wrong','code')
        with patch.object(yt,'token_request',return_value={'access_token':'fixture','refresh_token':'refresh'}),patch.object(yt,'api',return_value={'items':[]}):
            with self.assertRaisesRegex(ValueError,'Crie um canal'):yt.complete(query['state'][0],'code')
        self.assertFalse(yt.secret_path('tokens').exists())
        with self.assertRaises(ValueError):yt.complete(query['state'][0],'code')

    def test_description_keeps_link_and_native_disclosure(self):
        job,product=self.ready();job['caption']='á'*10000
        metadata=yt.metadata(job,product)
        self.assertIn(product['url'],metadata['snippet']['description'])
        self.assertLessEqual(len(metadata['snippet']['description'].encode()),4900)
        self.assertTrue(metadata['paidProductPlacementDetails']['hasPaidProductPlacement'])
        self.assertEqual(metadata['status']['privacyStatus'],'private')

    def test_session_url_is_fixed_google_upload_endpoint(self):
        self.assertTrue(yt.session_valid('https://www.googleapis.com/upload/youtube/v3/videos?upload_id=fixture'))
        for url in ['http://www.googleapis.com/upload/youtube/v3/videos','https://www.googleapis.com.evil.com/upload/youtube/v3/videos','https://www.googleapis.com:999/upload/youtube/v3/videos','https://x@www.googleapis.com/upload/youtube/v3/videos','https://www.googleapis.com/other']:
            self.assertFalse(yt.session_valid(url))

    def test_uncertain_initialization_is_never_retried_blindly(self):
        job,product=self.ready()
        with patch.object(yt,'initialize_upload',side_effect=OSError('connection lost')) as upload:
            yt.process(job,product);yt.process(job,product)
            self.assertEqual(upload.call_count,1)
        self.assertEqual(self.row(job['id'])['stage'],'uncertain')

    def test_upload_id_persisted_before_polling_processing(self):
        job,product=self.ready()
        with patch.object(yt,'initialize_upload'),patch.object(yt,'transfer',return_value={'id':'abc12345678'}) as transfer:
            yt.process(job,product)
        self.assertEqual(transfer.call_count,1)
        self.assertEqual(self.row(job['id'])['stage'],'processing')
        with patch.object(yt,'api',return_value={'items':[self.video()]}),patch.object(yt,'transfer') as second:
            yt.process(job,product)
        second.assert_not_called()
        self.assertEqual(self.row(job['id'])['stage'],'scheduled')

    def test_disclosure_confirmed_before_scheduling(self):
        job,product=self.ready();self.remote(job['id'])
        with patch.object(yt,'api',side_effect=[{'items':[self.video(paid=False)]},{}]) as api:
            yt.process(job,product)
        self.assertIn('part=paidProductPlacementDetails',api.call_args.args[0])
        self.assertEqual(self.row(job['id'])['stage'],'processing')
        yt.update_job(job['id'],next_check=None)
        with patch.object(yt,'api',side_effect=[{'items':[self.video()]},{}]) as api:
            yt.process(job,product)
        target=api.call_args.args[1]['status']
        self.assertEqual(target['privacyStatus'],'private');self.assertIn('publishAt',target)
        self.assertEqual(core.get_job(job['id'])['status'],'ready')

    def test_publication_requires_public_confirmation(self):
        job,product=self.ready();self.remote(job['id'],'scheduled')
        with patch.object(yt,'api',return_value={'items':[self.video(privacy='private')]}):yt.process(job,product)
        self.assertEqual(core.get_job(job['id'])['status'],'ready')
        with patch.object(yt,'api',return_value={'items':[self.video(privacy='public')]}):yt.process(job,product)
        result=core.get_job(job['id']);self.assertEqual(result['status'],'published');self.assertEqual(result['views'],42)
        self.assertTrue(result['tiktok_url'].startswith('https://www.youtube.com/'))

    def test_lost_schedule_response_reconciles_public_without_rescheduling(self):
        job,product=self.ready();self.remote(job['id'],'processing')
        with patch.object(yt,'api',return_value={'items':[self.video(privacy='public')]}) as api:yt.process(job,product)
        self.assertEqual(api.call_count,1)
        self.assertEqual(core.get_job(job['id'])['status'],'published')

    def test_revoked_catalog_unschedules_existing_private_video(self):
        job,product=self.ready();self.remote(job['id'],'scheduled');catalog.ingest([],True)
        with patch.object(yt,'api',return_value={}) as api:yt.process(job,product)
        self.assertEqual(api.call_args.args[1]['status']['privacyStatus'],'private')
        self.assertNotIn('publishAt',api.call_args.args[1]['status'])
        self.assertEqual(self.row(job['id'])['stage'],'held')

    def test_resume_probes_then_sends_only_missing_bytes(self):
        job,product=self.ready();file=core.DATA/'media'/job['id']/'video.mp4'
        yt.save_secret('session-'+job['id'],{'url':'https://www.googleapis.com/upload/youtube/v3/videos?upload_id=fixture'})
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"id":"abc12345678"}'
        calls=[]
        def send(request,**kwargs):
            calls.append(request)
            if len(calls)==1:raise HTTPError(request.full_url,308,'resume',{'Range':'bytes=0-4'},None)
            self.assertEqual(request.data.read(),file.read_bytes()[5:])
            return response
        opener=MagicMock();opener.open.side_effect=send
        with patch.object(yt,'build_opener',return_value=opener),patch.object(yt,'access_token',return_value='fixture'):
            self.assertEqual(yt.transfer(job['id'],file)['id'],'abc12345678')
        self.assertEqual(calls[0].get_header('Content-range'),f'bytes */{file.stat().st_size}')
        self.assertTrue(calls[1].get_header('Content-range').startswith('bytes 5-'))

    def test_reconcile_rejects_another_channel(self):
        job,product=self.ready();self.remote(job['id'],'uncertain','')
        video=self.video();video['snippet']['channelId']='another-channel'
        with patch.object(yt,'api',return_value={'items':[video]}):
            with self.assertRaises(ValueError):yt.reconcile(job['id'],'abc12345678')
        self.assertEqual(self.row(job['id'])['stage'],'uncertain')

    def test_pausing_product_holds_pending_upload(self):
        job,product=self.ready()
        autopilot.approve_product(product['id'],{'active':False,'approved':True})
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called()
        self.assertEqual(self.row(job['id'])['stage'],'held_local')

    def test_changed_catalog_regenerates_before_first_upload(self):
        job,product=self.ready()
        product['description']='Quatro divisórias. Estrutura em madeira. Medidas de 25 por 15 centímetros.'
        with core.db() as c:c.execute('UPDATE products SET description=? WHERE id=?',(product['description'],product['id']))
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called()
        self.assertEqual(core.get_job(job['id'])['status'],'queued')
        import production
        production.prepare(*production.claim_next())
        self.assertIn('Quatro divisórias',core.get_job(job['id'])['scenes'])

    def test_edit_is_locked_after_external_upload(self):
        job,product=self.ready();self.remote(job['id'],'scheduled')
        payload={'scenes':json.loads(job['scenes']),'caption':job['caption'],'due_at':job['due_at'],'rights':True,'action':'render'}
        with self.assertRaisesRegex(ValueError,'YouTube'):core.edit_job(job['id'],payload)

    def test_old_delivery_snapshot_cannot_upload_work_already_requeued(self):
        job,product=self.ready()
        with core.db() as c:c.execute("UPDATE jobs SET status='queued' WHERE id=?",(job['id'],))
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called()
        self.assertIsNone(self.row(job['id']))

    def test_pause_or_buffer_claim_during_review_blocks_youtube_initialization(self):
        job,product=self.ready()
        for condition in ('pause','buffer'):
            with self.subTest(condition=condition):
                autopilot.put_settings({'enabled':True})
                def review(*args,**kwargs):
                    if condition=='pause':autopilot.put_settings({'enabled':False})
                    else:
                        with core.db() as c:c.execute("UPDATE auto_jobs SET delivery='sending' WHERE job_id=?",(job['id'],))
                    return {'allowed':True}
                with patch('quality.inspect',side_effect=review),patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
                upload.assert_not_called();self.assertIsNone(self.row(job['id']))

    def test_missing_local_video_returns_to_production_without_false_remote_failure(self):
        job,product=self.ready()
        (core.DATA/'media'/job['id']/'video.mp4').unlink()
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called()
        self.assertIsNone(self.row(job['id']))
        self.assertEqual(core.get_job(job['id'])['status'],'queued')

    def immediate(self):
        import publication
        job,product=self.ready()
        yt.save_secret('tokens',{'access_token':'fixture-local-only'})
        publication.request_now(job['id'])
        return job,product

    def test_immediate_request_is_persistent_idempotent_and_keeps_reserved_time(self):
        import publication
        job,product=self.immediate()
        self.assertTrue(publication.request_now(job['id'])['already_requested'])
        self.assertEqual(core.get_job(job['id'])['due_at'],job['due_at'])
        self.assertEqual(len(publication.state()),1)
        yt.init()
        self.assertIsNotNone(publication.get(job['id']))

    def test_immediate_publication_uses_existing_video_and_waits_for_real_confirmation(self):
        job,product=self.immediate();self.remote(job['id'])
        with patch.object(yt,'api',side_effect=[{'items':[self.video()]},{}]) as api,patch.object(yt,'initialize_upload') as upload:
            yt.process(job,product)
        upload.assert_not_called()
        target=api.call_args.args[1]['status']
        self.assertEqual(target['privacyStatus'],'public');self.assertNotIn('publishAt',target)
        self.assertEqual(self.row(job['id'])['stage'],'publishing')
        self.assertEqual(core.get_job(job['id'])['status'],'ready')
        with patch.object(yt,'api',return_value={'items':[self.video(privacy='public')]}) as api:yt.process(job,product)
        self.assertEqual(api.call_count,1)
        self.assertEqual(core.get_job(job['id'])['status'],'published')

    def test_immediate_timeout_reads_same_video_without_repeating_visibility_or_upload(self):
        job,product=self.immediate();self.remote(job['id'])
        with patch.object(yt,'api',side_effect=[{'items':[self.video()]},TimeoutError('fixture timeout')]):yt.process(job,product)
        self.assertEqual(self.row(job['id'])['stage'],'publishing')
        with core.db() as c:c.execute('UPDATE youtube_jobs SET next_check=NULL WHERE job_id=?',(job['id'],))
        with patch.object(yt,'api',return_value={'items':[self.video()]}) as api,patch.object(yt,'initialize_upload') as upload:
            yt.process(job,product)
        self.assertEqual(api.call_count,1);upload.assert_not_called()
        self.assertEqual(core.get_job(job['id'])['status'],'ready')

    def test_immediate_request_cannot_bypass_pause_rights_review_or_tester(self):
        import publication
        job,product=self.ready();yt.save_secret('tokens',{'access_token':'fixture'})
        with patch.object(core,'TESTER',True):
            with self.assertRaisesRegex(ValueError,'tester'):publication.request_now(job['id'])
        autopilot.put_settings({'enabled':False})
        with self.assertRaisesRegex(ValueError,'operação pública'):publication.request_now(job['id'])
        autopilot.put_settings({'enabled':True})
        with patch('quality.inspect',return_value={'allowed':False}):
            with self.assertRaisesRegex(ValueError,'verificações'):publication.request_now(job['id'])
        with core.db() as c:c.execute('UPDATE jobs SET rights=0 WHERE id=?',(job['id'],))
        with self.assertRaisesRegex(ValueError,'autorizados'):publication.request_now(job['id'])
        self.assertIsNone(publication.get(job['id']))

    def test_immediate_request_rejects_scheduled_or_uncertain_remote_delivery(self):
        import publication
        job,product=self.ready();yt.save_secret('tokens',{'access_token':'fixture'})
        self.remote(job['id'],'scheduled')
        with self.assertRaises(ValueError):publication.request_now(job['id'])
        with core.db() as c:c.execute("UPDATE youtube_jobs SET stage='uncertain' WHERE job_id=?",(job['id'],))
        with self.assertRaises(ValueError):publication.request_now(job['id'])
        self.assertIsNone(publication.get(job['id']))

    def test_immediate_expiry_stops_without_new_upload(self):
        job,product=self.immediate()
        with core.db() as c:c.execute('UPDATE immediate_publications SET requested_at=? WHERE job_id=?',((core.now()-timedelta(minutes=31)).isoformat(),job['id']))
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called();self.assertEqual(self.row(job['id'])['stage'],'failed')

    def test_immediate_request_bound_to_channel_and_script(self):
        job,product=self.immediate()
        yt.put({'channel_id':'another-channel'})
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called();self.assertEqual(self.row(job['id'])['stage'],'failed')
        yt.put({'channel_id':'UC-test'})
        with core.db() as c:
            c.execute('DELETE FROM youtube_jobs WHERE job_id=?',(job['id'],))
            c.execute("UPDATE jobs SET caption=caption||' changed' WHERE id=?",(job['id'],))
        with patch.object(yt,'initialize_upload') as upload:yt.process(job,product)
        upload.assert_not_called();self.assertEqual(self.row(job['id'])['stage'],'failed')

    def test_immediate_disclosure_is_verified_before_public_request(self):
        job,product=self.immediate();self.remote(job['id'])
        with patch.object(yt,'api',side_effect=[{'items':[self.video(paid=False)]},{}]) as api:yt.process(job,product)
        self.assertIn('paidProductPlacementDetails',api.call_args.args[1])
        self.assertEqual(self.row(job['id'])['stage'],'processing')
        self.assertEqual(core.get_job(job['id'])['status'],'ready')

    def test_expired_immediate_can_be_renewed_only_without_any_remote_attempt(self):
        import publication
        job,product=self.immediate()
        with core.db() as c:c.execute('UPDATE immediate_publications SET requested_at=? WHERE job_id=?',((core.now()-timedelta(minutes=31)).isoformat(),job['id']))
        self.assertFalse(publication.request_now(job['id'])['already_requested'])
        self.remote(job['id'],'publishing')
        with core.db() as c:c.execute('UPDATE immediate_publications SET requested_at=? WHERE job_id=?',((core.now()-timedelta(minutes=31)).isoformat(),job['id']))
        with self.assertRaisesRegex(ValueError,'vídeo privado existente'):publication.request_now(job['id'])

    def test_reconciling_known_private_video_clears_old_immediate_intent(self):
        import publication
        job,product=self.immediate();self.remote(job['id'],'failed')
        with patch.object(yt,'api',return_value={'items':[self.video()]}):yt.reconcile(job['id'],'abc12345678')
        self.assertIsNone(publication.get(job['id']))
        self.assertFalse(publication.request_now(job['id'])['already_requested'])


if __name__=='__main__':unittest.main()
