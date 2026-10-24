import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
import app
import core
import autopilot
import catalog
import youtube_client
import diagnostics
import content_engine


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.override=patch.object(core,'DATA',Path(cls.temp.name))
        cls.override.start()
        core.init()
        autopilot.init()
        catalog.init();youtube_client.init()
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.override.stop()
        cls.temp.cleanup()

    def request(self,path,body=None,headers=None):
        headers=dict(headers or {})
        if body is not None:
            headers['Content-Type']='application/json'
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        try:
            with urlopen(req,timeout=5) as response:
                return response.status,response.headers,response.read()
        except HTTPError as response:
            return response.code,response.headers,response.read()

    def test_initial_state_no_phantom_results(self):
        status,headers,body=self.request('/api/state')
        self.assertEqual(status,200)
        state=json.loads(body)
        self.assertEqual(state['jobs'],[])
        self.assertEqual(state['products'],[])
        self.assertEqual(headers['Cache-Control'],'no-store')

    def test_health_identifies_installation_without_credentials(self):
        status,_,body=self.request('/api/health')
        value=json.loads(body)
        self.assertEqual(status,200);self.assertEqual(value['app'],'AfiliadosStudio')
        self.assertNotIn('token',value);self.assertNotIn(str(core.DATA),body.decode())

    def test_exit_requires_csrf_and_uses_graceful_server_shutdown(self):
        self.assertEqual(self.request('/api/system/exit',{})[0],403)
        with patch.object(self.server,'shutdown') as shutdown,patch.object(app.STOP,'set') as stop:
            self.assertEqual(self.request('/api/system/exit',{}, {'X-Studio-Token':app.TOKEN})[0],200)
            import time
            deadline=time.monotonic()+2
            while not shutdown.called and time.monotonic()<deadline:time.sleep(.01)
            shutdown.assert_called_once();stop.assert_called_once()

    def test_start_requires_products_and_channel(self):
        status,headers,body=self.request('/api/setup/start',{}, {'X-Studio-Token':app.TOKEN})
        self.assertEqual(status,400)
        self.assertFalse(autopilot.settings()['enabled'])
        self.assertFalse(youtube_client.settings()['enabled'])

    def test_immediate_endpoint_requires_csrf_and_blocks_tester(self):
        import publication
        path='/api/youtube/publish-now/'+'a'*32
        self.assertEqual(self.request(path,{})[0],403)
        with patch.object(core,'TESTER',True):self.assertEqual(self.request(path,{}, {'X-Studio-Token':app.TOKEN})[0],400)
        with patch.object(publication,'request_now',return_value={'requested':True}) as request:
            self.assertEqual(self.request(path,{}, {'X-Studio-Token':app.TOKEN})[0],200)
        request.assert_called_once_with('a'*32)

    def test_replayed_callback_does_not_mark_connected_channel_as_expired(self):
        client=youtube_client.secret_path('tokens');old=client.read_bytes() if client.exists() else None
        config=youtube_client.settings()
        try:
            client.write_bytes(b'fixture-never-read');youtube_client.put({'channel_verified':True,'last_error':''})
            with patch.object(youtube_client,'complete',side_effect=ValueError('fixture expired callback')):
                self.request('/oauth/youtube/callback?state=fixture&code=fixture')
            self.assertEqual(youtube_client.settings()['last_error'],'')
            self.assertTrue(youtube_client.settings()['channel_verified'])
        finally:
            youtube_client.put(config)
            if old is None:client.unlink(missing_ok=True)
            else:client.write_bytes(old)

    def test_expired_session_is_identified_before_any_mutation(self):
        with patch.object(content_engine,'configure') as configure:
            status,_,body=self.request('/api/content/settings',{'mode':'rules'},{'X-Studio-Token':'old-session'})
        self.assertEqual(status,403)
        self.assertEqual(json.loads(body)['code'],'session_expired')
        configure.assert_not_called()
        status,_,body=self.request('/api/content/settings',{'mode':'rules'},{'X-Studio-Token':app.TOKEN,'Origin':'https://example.com'})
        self.assertEqual(status,403)
        self.assertNotIn('code',json.loads(body))

    def test_start_preserves_custom_routine_and_generator(self):
        original=autopilot.settings();content=content_engine.settings()
        try:
            autopilot.configure({'enabled':False,'daily_limit':2,'hours':[9,20],'cooldown_days':14,'timing_mode':'fixed'})
            content_engine.configure({'mode':'rules'})
            with patch.object(app,'readiness',return_value={'ready':True}),patch.object(youtube_client,'verify_channel') as verify,patch.object(youtube_client,'configure'),patch.object(diagnostics,'require_runtime'):
                status,headers,body=self.request('/api/setup/start',{}, {'X-Studio-Token':app.TOKEN})
            self.assertEqual(status,200);verify.assert_called_once()
            self.assertEqual(autopilot.settings()['hours'],[9,20])
            self.assertEqual(autopilot.settings()['daily_limit'],2)
            self.assertEqual(autopilot.settings()['cooldown_days'],14)
            self.assertEqual(content_engine.settings()['mode'],'rules')
        finally:
            autopilot.put_settings(original);content_engine.configure(content)

    def test_diagnostic_media_does_not_expose_internal_files(self):
        folder=core.DATA/'media'/'diagnostics';folder.mkdir(exist_ok=True)
        (folder/'video.mp4').write_bytes(b'local-fixture')
        (folder/'speech.json').write_text('private fixture')
        self.assertEqual(self.request('/media/diagnostics/video.mp4')[0],200)
        self.assertEqual(self.request('/media/diagnostics/speech.json')[0],404)
        self.assertEqual(self.request('/media/diagnostics/../studio.sqlite')[0],404)

    def test_youtube_credentials_are_never_exported(self):
        youtube_client.credentials({'installed':{'client_id':'fixture.apps.googleusercontent.com','client_secret':'never-export-this-fixture'}})
        for path in ['/api/state','/api/export']:
            status,headers,body=self.request(path)
            self.assertEqual(status,200)
            self.assertNotIn(b'never-export-this-fixture',body)

    def test_tester_mode_rejects_external_setup_and_credentials(self):
        paths=['/api/setup/start','/api/youtube/credentials','/api/youtube/connect','/api/youtube/settings','/api/automation/connect']
        with patch.object(core,'TESTER',True):
            for path in paths:
                status,headers,body=self.request(path,{}, {'X-Studio-Token':app.TOKEN})
                self.assertEqual(status,400)
                self.assertIn('tester',json.loads(body)['error'])

    def test_manual_and_support_report_are_available(self):
        status,headers,body=self.request('/manual-tester.md')
        self.assertEqual(status,200);self.assertIn('Manual do usuário tester',body.decode('utf-8'))
        status,headers,body=self.request('/api/support/report')
        self.assertEqual(status,200)
        self.assertIn('app_version',json.loads(body))

    def test_normal_mode_cannot_create_demo_offers(self):
        status,headers,body=self.request('/api/tester/demo',{}, {'X-Studio-Token':app.TOKEN})
        self.assertEqual(status,400)

    def test_post_requires_token_and_same_origin(self):
        self.assertEqual(self.request('/api/products',{},{} )[0],403)
        self.assertEqual(self.request('/api/products',{}, {'X-Studio-Token':app.TOKEN,'Origin':'https://example.com'})[0],403)

    def test_dns_rebinding_host_header_blocked(self):
        self.assertEqual(self.request('/api/state',headers={'Host':'evil.example'})[0],403)

    def test_static_traversal_blocked(self):
        for path in ['/../core.py','/media/../studio.sqlite','/media/%2e%2e/studio.sqlite']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0],404)

    def test_video_range_serving(self):
        directory=core.DATA/'media'/('a'*32)
        directory.mkdir()
        (directory/'video.mp4').write_bytes(b'0123456789')
        status,headers,body=self.request('/media/'+('a'*32)+'/video.mp4',headers={'Range':'bytes=2-5'})
        self.assertEqual(status,206)
        self.assertEqual(headers['Content-Range'],'bytes 2-5/10')
        self.assertEqual(body,b'2345')


if __name__=='__main__':
    unittest.main()
