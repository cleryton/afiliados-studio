from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import autopilot
import catalog
import channel_probe as probe
import core
import diagnostics
import quality
import youtube_client as yt


class ChannelProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        for name,value in [('DATA',Path(self.temp.name)),('TESTER',False)]:
            override=patch.object(core,name,value);override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();catalog.init();yt.init()

    def prepared(self):
        with patch.object(diagnostics,'require_runtime'):probe.prepare()
        item=probe.row();folder=core.DATA/'media'/item['id'];folder.mkdir()
        (folder/'video.mp4').write_bytes(b'private-test-fixture')
        probe.update(item['id'],stage='ready_local',active=0,size=(folder/'video.mp4').stat().st_size,sha256=quality.file_hash(folder/'video.mp4'),voice=1)
        return probe.row()

    def connected(self):
        yt.save_secret('tokens',{'access_token':'test-fixture'})
        yt.put({'channel_id':'UC-test','channel_verified':True})

    def start(self):
        self.connected()
        with patch.object(yt,'verify_channel',return_value={'ok':True}):probe.start()

    def stage(self,stage,video_id=''):
        item=self.prepared();self.start();probe.update(item['id'],stage=stage,video_id=video_id)
        return probe.row()

    def video(self,status='processed',privacy='private',channel='UC-test'):
        return {'items':[{'id':'abc12345678','snippet':{'channelId':channel},'status':{'privacyStatus':privacy,'uploadStatus':status}}]}

    def test_prepare_requires_no_product_affiliation_or_account_and_is_idempotent(self):
        with patch.object(diagnostics,'require_runtime'):
            first=probe.prepare();second=probe.prepare()
        self.assertEqual(first['id'],second['id']);self.assertEqual(first['stage'],'queued')
        self.assertEqual(core.state()['products'],[]);self.assertEqual(core.state()['jobs'],[])
        self.assertFalse(autopilot.settings()['enabled']);self.assertFalse(yt.settings()['enabled'])

    def test_two_prepare_requests_reserve_one_run(self):
        with patch.object(diagnostics,'require_runtime'),ThreadPoolExecutor(max_workers=2) as pool:
            runs=list(pool.map(lambda _:probe.prepare(),range(2)))
        self.assertEqual(runs[0]['id'],runs[1]['id'])

    def test_local_build_uses_private_test_text_and_copies_a_frozen_file(self):
        with patch.object(diagnostics,'require_runtime'):probe.prepare()
        def render(root,channel_test=False):
            self.assertTrue(channel_test)
            folder=root/'media'/'diagnostics';folder.mkdir(parents=True)
            (folder/'video.mp4').write_bytes(b'fixture-video');(folder/'poster.png').write_bytes(b'fixture-poster')
            diagnostics.write_report(root,{'status':'passed','voice':True})
        with patch.object(diagnostics,'require_runtime'),patch.object(diagnostics,'run_probe',side_effect=render):probe.tick()
        item=probe.row();self.assertEqual(item['stage'],'ready_local');self.assertFalse(item['active']);self.assertTrue(probe.state()['video_url'])
        self.assertEqual(item['sha256'],quality.file_hash(core.DATA/'media'/item['id']/'video.mp4'))

    def test_local_failure_can_be_retried_without_external_attempt(self):
        with patch.object(diagnostics,'require_runtime'):probe.prepare()
        with patch.object(diagnostics,'require_runtime',side_effect=ValueError('PRIVATE-SENTINEL')):probe.tick()
        self.assertEqual(probe.row()['stage'],'failed_local');self.assertNotIn('PRIVATE-SENTINEL',probe.state()['error'])
        with patch.object(diagnostics,'require_runtime'):probe.prepare()
        self.assertEqual(probe.row()['stage'],'queued')

    def test_prepare_does_not_replace_an_external_attempt(self):
        item=self.stage('uploading')
        with patch.object(diagnostics,'require_runtime'):probe.prepare()
        self.assertEqual(probe.row()['id'],item['id']);self.assertEqual(probe.row()['stage'],'uploading')

    def test_private_metadata_has_no_affiliate_or_public_visibility(self):
        item=self.prepared();metadata=probe.metadata(item)
        self.assertEqual(metadata['status']['privacyStatus'],'private')
        self.assertNotIn('publishAt',metadata['status'])
        self.assertFalse(metadata['paidProductPlacementDetails']['hasPaidProductPlacement'])
        self.assertNotIn('http',metadata['snippet']['description'])

    def test_start_verifies_channel_and_never_activates_public_routine(self):
        self.prepared();self.start()
        self.assertEqual(probe.row()['channel_id'],'UC-test')
        self.assertFalse(autopilot.settings()['enabled']);self.assertFalse(yt.settings()['enabled'])

    def test_tester_rejects_send_and_tick_never_contacts_youtube(self):
        self.stage('uploading')
        with patch.object(core,'TESTER',True),patch.object(yt,'transfer') as transfer,patch.object(yt,'initialize_media') as initialize:
            with self.assertRaises(ValueError):probe.start()
            probe.tick();transfer.assert_not_called();initialize.assert_not_called()

    def test_paused_queue_can_resume_local_preparation(self):
        with patch.object(diagnostics,'require_runtime'):
            probe.prepare();probe.pause();probe.prepare()
        self.assertTrue(probe.row()['active'])

    def test_pausing_before_initialize_prevents_network(self):
        self.prepared();self.start();probe.pause()
        with patch.object(yt,'initialize_media') as initialize:probe.tick();initialize.assert_not_called()

    def test_initialize_is_claimed_once_and_preserves_existing_session(self):
        self.prepared();self.start()
        with patch.object(yt,'initialize_media') as initialize,patch.object(yt,'transfer',return_value=None):
            probe.tick();probe.tick()
        self.assertEqual(initialize.call_count,1)
        self.assertEqual(probe.row()['stage'],'uploading')

    def test_uncertain_initialization_never_blindly_retries(self):
        self.prepared();self.start()
        with patch.object(yt,'initialize_media',side_effect=OSError('PRIVATE-SENTINEL')) as initialize:
            probe.tick();probe.tick()
        self.assertEqual(initialize.call_count,1);self.assertEqual(probe.row()['stage'],'uncertain')
        self.assertNotIn('PRIVATE-SENTINEL',probe.state()['error'])
        with self.assertRaises(ValueError):probe.start()

    def test_restart_recovers_local_preparation_but_holds_unknown_remote_claim(self):
        item=self.prepared();probe.update(item['id'],stage='preparing',active=1);probe.init()
        self.assertEqual(probe.row()['stage'],'queued')
        probe.update(item['id'],stage='initializing');probe.init()
        self.assertEqual(probe.row()['stage'],'uncertain');self.assertFalse(probe.row()['active'])

    def test_changed_channel_never_receives_original_test(self):
        self.stage('uploading');yt.put({'channel_id':'UC-another'})
        with patch.object(yt,'transfer') as transfer:probe.tick();transfer.assert_not_called()
        self.assertFalse(probe.row()['active'])
        with patch.object(yt,'verify_channel'):
            with self.assertRaisesRegex(ValueError,'destino'):probe.start()

    def test_file_change_after_claim_cannot_send_different_bytes(self):
        item=self.stage('uploading');(core.DATA/'media'/item['id']/'video.mp4').write_bytes(b'changed')
        with patch.object(yt,'transfer') as transfer:probe.tick();transfer.assert_not_called()
        self.assertFalse(probe.row()['active'])

    def test_transfer_ack_is_not_yet_success(self):
        self.stage('uploading')
        with patch.object(yt,'transfer',return_value={'id':'abc12345678'}):probe.tick()
        self.assertEqual(probe.row()['stage'],'processing')
        self.assertTrue(probe.row()['active']);self.assertIsNotNone(probe.state()['remote_url'])

    def test_processing_private_owned_video_is_the_only_success_path(self):
        self.stage('processing','abc12345678')
        with patch.object(yt,'api',return_value=self.video()) as api:probe.tick()
        self.assertEqual(probe.row()['stage'],'passed');self.assertFalse(probe.row()['active'])
        self.assertEqual(api.call_count,1);self.assertTrue(api.call_args.args[0].startswith('videos?'))
        self.assertEqual(core.state()['jobs'],[])

    def test_processing_waits_without_declaring_success(self):
        self.stage('processing','abc12345678')
        with patch.object(yt,'api',return_value=self.video(status='uploaded')):probe.tick()
        self.assertEqual(probe.row()['stage'],'processing');self.assertTrue(probe.row()['next_check'])

    def test_public_video_is_held_without_changing_visibility(self):
        self.stage('processing','abc12345678')
        with patch.object(yt,'api',return_value=self.video(privacy='public')) as api:probe.tick()
        self.assertFalse(probe.row()['active']);self.assertEqual(probe.row()['stage'],'processing')
        self.assertEqual(api.call_count,1)

    def test_network_failures_back_off_and_pause_after_six(self):
        self.stage('processing','abc12345678');current=core.now()
        with patch.object(yt,'api',side_effect=OSError('PRIVATE-SENTINEL')) as api:
            for n in range(6):
                with patch.object(core,'now',return_value=current+timedelta(hours=n)):probe.tick()
        self.assertEqual(api.call_count,6);self.assertFalse(probe.row()['active'])
        self.assertEqual(probe.row()['failures'],6);self.assertNotIn('PRIVATE-SENTINEL',probe.state()['error'])

    def test_malformed_processing_response_is_a_bounded_retry(self):
        self.stage('processing','abc12345678')
        with patch.object(yt,'api',return_value=[]):probe.tick()
        self.assertEqual(probe.row()['stage'],'processing');self.assertEqual(probe.row()['failures'],1)

    def test_shared_upload_transport_blocks_tester_before_metadata_or_credentials(self):
        with patch.object(core,'TESTER',True),patch.object(yt,'access_token') as access:
            with self.assertRaises(ValueError):yt.initialize_media('fixture',{},Path('absent.mp4'))
        access.assert_not_called()

    def test_support_state_excludes_channel_session_hash_and_path(self):
        self.stage('uploading');state=probe.state()
        for key in ('channel_id','sha256','size'):self.assertNotIn(key,state)
        self.assertNotIn(self.temp.name,json.dumps(state))

    def test_pause_during_initialization_keeps_session_but_never_transfers(self):
        self.prepared();self.start()
        with patch.object(yt,'initialize_media',side_effect=lambda *_:probe.pause()),patch.object(yt,'transfer') as transfer:
            probe.tick();probe.tick();transfer.assert_not_called()
        self.assertEqual(probe.row()['stage'],'uploading');self.assertFalse(probe.row()['active'])
