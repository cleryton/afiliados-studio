from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock,Mock,patch
from urllib.parse import parse_qs,urlparse
import background
import launcher
import core
import autopilot
import catalog
import youtube_client as yt


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)

    def test_health_accepts_only_same_installation_and_normal_mode(self):
        valid={'app':'AfiliadosStudio','version':'fixture','tester':False,'data_id':background.installation_id()}
        with patch.object(background,'request',return_value=valid):self.assertEqual(background.health(),valid)
        for change in ({'app':'other'},{'data_id':'other'},{'tester':True}):
            with patch.object(background,'request',return_value={**valid,**change}):
                with self.assertRaises(ValueError):background.health()

    def test_unavailable_health_is_not_considered_running(self):
        with patch.object(background,'request',side_effect=ConnectionRefusedError):self.assertIsNone(background.health())

    def test_already_running_does_not_launch_another_process(self):
        with patch.object(background,'health',return_value={'version':'fixture'}),patch.object(background.subprocess,'Popen') as popen,patch.object(background.webbrowser,'open') as browser:
            self.assertTrue(background.start(open_browser=True)['running'])
        popen.assert_not_called();browser.assert_called_once()

    def test_start_has_detached_process_and_no_inherited_console_streams(self):
        child=Mock();child.poll.return_value=None
        with patch.object(background,'health',side_effect=[None,{'version':'fixture'}]),patch.object(background.subprocess,'Popen',return_value=child) as popen:
            self.assertTrue(background.start(8767)['running'])
        args=popen.call_args
        self.assertIn('--background',args.args[0]);self.assertIn('8767',args.args[0])
        self.assertEqual(args.kwargs['stdout'],background.subprocess.DEVNULL)
        self.assertEqual(args.kwargs['stderr'],background.subprocess.DEVNULL)
        self.assertTrue(args.kwargs['close_fds'])
        if os.name=='nt':self.assertTrue(args.kwargs['creationflags'] & background.subprocess.DETACHED_PROCESS)

    def test_failed_child_reports_a_recovery_action_without_a_start_loop(self):
        child=Mock();child.poll.return_value=3
        with patch.object(background,'health',return_value=None),patch.object(background.subprocess,'Popen',return_value=child) as popen:
            with self.assertRaisesRegex(ValueError,'iniciar_console'):background.start()
        self.assertEqual(popen.call_count,1)

    def test_slow_start_is_bounded(self):
        child=Mock();child.poll.return_value=None
        with patch.object(background,'health',return_value=None),patch.object(background.subprocess,'Popen',return_value=child),patch.object(background.time,'monotonic',side_effect=[0,21]):
            with self.assertRaisesRegex(ValueError,'inicialização'):background.start()

    def test_stop_uses_csrf_and_does_not_kill_processes_by_name(self):
        with patch.object(background,'health',side_effect=[{'version':'fixture'},None]),patch.object(background,'request',side_effect=[{'token':'fixture-token'},{'ok':True}]) as request:
            self.assertFalse(background.stop()['running'])
        self.assertEqual(request.call_args.args,(8765,'/api/system/exit',{},'fixture-token'))

    def test_stop_is_idempotent_when_already_closed(self):
        with patch.object(background,'health',return_value=None),patch.object(background,'request') as request:
            self.assertFalse(background.stop()['running'])
        request.assert_not_called()

    def test_background_supervisor_rotates_real_child_logs(self):
        root=Path(self.temp.name)
        source="import sys\nfrom pathlib import Path\nsys.path.insert(0,"+repr(str(core.ROOT))+" )\nfrom background_output import install\ninstall(Path("+repr(str(root))+"))\nfor _ in range(2000): print('x'*2500)\n"
        (root/'app.py').write_text(source,encoding='utf-8')
        log=root/'background.log'
        with patch.object(launcher,'ROOT',root):self.assertEqual(launcher.supervise([],log),0)
        self.assertTrue(log.exists());self.assertTrue(log.with_name('background.log.1').exists())
        self.assertLessEqual(sum(p.stat().st_size for p in root.glob('background.log*')),4_000_000)

    @unittest.skipUnless(os.name=='nt','Registro de início automático é específico do Windows.')
    def test_startup_uses_current_user_only_and_is_reversible(self):
        registry=types.SimpleNamespace(HKEY_CURRENT_USER='current-user',KEY_QUERY_VALUE=1,KEY_SET_VALUE=2,REG_SZ=1,
            CreateKeyEx=MagicMock(),QueryValueEx=Mock(side_effect=FileNotFoundError),SetValueEx=Mock(),DeleteValue=Mock())
        with patch.object(core,'DATA',(core.ROOT/'data').resolve()),patch.dict('sys.modules',{'winreg':registry}):
            background.configure_startup(True)
            registry.SetValueEx.assert_called_once()
            self.assertEqual(registry.CreateKeyEx.call_args.args[0],'current-user')
            command=registry.SetValueEx.call_args.args[-1]
            self.assertIn('background.py',command);self.assertTrue(command.endswith(' start'))
            registry.QueryValueEx.side_effect=None;registry.QueryValueEx.return_value=(command,1)
            background.configure_startup(False);registry.DeleteValue.assert_called_once()

    @unittest.skipUnless(os.name=='nt','Registro de início automático é específico do Windows.')
    def test_startup_never_overwrites_another_installation(self):
        registry=types.SimpleNamespace(HKEY_CURRENT_USER='current-user',KEY_QUERY_VALUE=1,KEY_SET_VALUE=2,REG_SZ=1,
            CreateKeyEx=MagicMock(),QueryValueEx=Mock(return_value=('other-installation',1)),SetValueEx=Mock(),DeleteValue=Mock())
        with patch.object(core,'DATA',(core.ROOT/'data').resolve()),patch.dict('sys.modules',{'winreg':registry}):
            for enabled in (True,False):
                with self.assertRaisesRegex(ValueError,'preservada'):background.configure_startup(enabled)
        registry.SetValueEx.assert_not_called();registry.DeleteValue.assert_not_called()


class OAuthRestartTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        override=patch.object(core,'DATA',Path(self.temp.name));override.start();self.addCleanup(override.stop)
        core.init();autopilot.init();catalog.init();yt.init()
        yt.credentials({'installed':{'client_id':'fixture.apps.googleusercontent.com','client_secret':'fixture-secret'}})
        self.addCleanup(yt._pending.clear)

    def begin(self):return parse_qs(urlparse(yt.begin(8767)).query)['state'][0]

    def finish(self,state):
        with patch.object(yt,'token_request',return_value={'access_token':'fixture-token','refresh_token':'fixture-refresh'}),patch.object(yt,'api',return_value={'items':[{'id':'UC-fixture','snippet':{'title':'Canal de teste'}}]}):
            yt.complete(state,'fixture-code')

    def test_restart_restores_pending_pkce_and_accepts_callback_once(self):
        state=self.begin();saved=yt.read_secret('oauth-pending')
        self.assertNotIn(saved['verifier'].encode(),yt.secret_path('oauth-pending').read_bytes())
        yt._pending.clear();self.finish(state)
        self.assertFalse(yt.secret_path('oauth-pending').exists())
        self.assertTrue(yt.state()['connected'])
        with self.assertRaises(ValueError):self.finish(state)

    def test_wrong_state_does_not_consume_correct_pending_intent(self):
        state=self.begin();yt._pending.clear()
        with patch.object(yt,'token_request') as token:
            with self.assertRaises(ValueError):yt.complete('wrong-state','fixture-code')
        token.assert_not_called();self.finish(state)

    def test_expired_pending_after_restart_never_requests_a_token(self):
        state=self.begin();saved=yt.read_secret('oauth-pending');saved['expires_at']=0
        yt.save_secret('oauth-pending',saved);yt._pending.clear()
        with patch.object(yt,'token_request') as token:
            with self.assertRaises(ValueError):yt.complete(state,'fixture-code')
        token.assert_not_called()

    def test_new_attempt_invalidates_older_state(self):
        first=self.begin();second=self.begin();yt._pending.clear()
        with self.assertRaises(ValueError):self.finish(first)
        self.finish(second)

    def test_disconnect_removes_pending_authorization(self):
        state=self.begin();yt.disconnect()
        self.assertFalse(yt.secret_path('oauth-pending').exists())
        with self.assertRaises(ValueError):self.finish(state)

    def test_failed_token_exchange_cannot_reuse_pending_authorization(self):
        state=self.begin();yt._pending.clear()
        with patch.object(yt,'token_request',side_effect=ValueError('fixture-denied')):
            with self.assertRaises(ValueError):yt.complete(state,'fixture-code')
        self.assertFalse(yt.secret_path('oauth-pending').exists())
        with self.assertRaises(ValueError):self.finish(state)

    def test_health_and_support_exports_do_not_leak_pending_state(self):
        state=self.begin();snapshot=yt.state()
        self.assertNotIn(state,json.dumps(snapshot));self.assertNotIn('verifier',json.dumps(snapshot))

    def test_connect_and_test_requires_a_prepared_private_video(self):
        with self.assertRaisesRegex(ValueError,'Prepare o vídeo'):yt.begin(8767,run_private_test=True)
        self.assertFalse(yt.secret_path('oauth-pending').exists())

    def test_explicit_private_test_intent_survives_restart(self):
        with patch('channel_probe.row',return_value={'stage':'ready_local'}):
            state=parse_qs(urlparse(yt.begin(8767,run_private_test=True)).query)['state'][0]
        yt._pending.clear()
        with patch('channel_probe.start') as start:self.finish(state)
        start.assert_called_once_with()
        self.assertFalse(autopilot.settings()['enabled']);self.assertFalse(yt.settings()['enabled'])

    def test_connect_without_test_intent_never_starts_uploads(self):
        state=self.begin();yt._pending.clear()
        with patch('channel_probe.start') as start:self.finish(state)
        start.assert_not_called()

    def test_private_test_error_does_not_discard_successful_channel_authorization(self):
        with patch('channel_probe.row',return_value={'stage':'ready_local'}):
            state=parse_qs(urlparse(yt.begin(8767,run_private_test=True)).query)['state'][0]
        with patch('channel_probe.start',side_effect=ValueError('fixture')):
            with self.assertRaisesRegex(ValueError,'Canal conectado'):self.finish(state)
        self.assertTrue(yt.state()['connected'])
