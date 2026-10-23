from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from contextlib import closing
from datetime import timedelta
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import app
import autopilot
import catalog
import core
import launcher
import maintenance
from runtime_service import Service
import youtube_client


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.override = patch.object(core, 'DATA', Path(self.temp.name));self.override.start();self.addCleanup(self.override.stop)
        core.init();autopilot.init();catalog.init();youtube_client.init()
        self.pid = core.save_product({'name':'Teste', 'url':'https://example.com/p?af=teste', 'kind':'physical',
                                      'category':'Casa','description':'Três divisórias.'})

    def test_consistent_copy_preserves_data_and_excludes_secret_files(self):
        (core.DATA/'youtube-tokens.secret').write_text('PRIVATE-SENTINEL')
        result = maintenance.tick()
        file = core.DATA/'backups'/result['file']
        with closing(sqlite3.connect(file)) as copied:
            self.assertEqual(copied.execute('PRAGMA quick_check').fetchone()[0], 'ok')
            self.assertEqual(copied.execute('SELECT id,url FROM products').fetchone(), (self.pid,'https://example.com/p?af=teste'))
        self.assertNotIn(b'PRIVATE-SENTINEL',file.read_bytes())
        self.assertEqual(result['sha256'],hashlib.sha256(file.read_bytes()).hexdigest())
        self.assertEqual([p.suffix for p in file.parent.iterdir()],['.sqlite'])
        with core.db() as c:c.execute('UPDATE products SET name=? WHERE id=?',('Atualizado',self.pid))
        with closing(sqlite3.connect(file)) as copied:self.assertEqual(copied.execute('SELECT name FROM products').fetchone()[0],'Teste')

    def test_once_per_24h_persists_after_restart_and_missing_copy_is_replaced(self):
        first=maintenance.tick()
        self.assertIsNone(maintenance.tick())
        self.assertEqual(maintenance.read()['file'],first['file'])
        (core.DATA/'backups'/first['file']).unlink()
        self.assertNotEqual(maintenance.tick()['file'],first['file'])
        future=core.now()+timedelta(hours=25)
        with patch.object(core,'now',return_value=future):self.assertEqual(maintenance.tick()['status'],'ok')

    def test_retains_seven_and_never_deletes_unrelated_files(self):
        directory=core.DATA/'backups';directory.mkdir()
        unrelated=directory/'minha-copia.sqlite';unrelated.write_text('preservar')
        for _ in range(9):maintenance.snapshot()
        self.assertEqual(sum(bool(maintenance.NAME.fullmatch(p.name)) for p in directory.iterdir()),7)
        self.assertEqual(unrelated.read_text(),'preservar')

    def test_failed_copy_preserves_last_good_and_retries_after_30m(self):
        good=maintenance.tick();future=core.now()+timedelta(hours=25)
        with patch.object(core,'now',return_value=future),patch.object(maintenance,'snapshot',side_effect=OSError('PRIVATE-SENTINEL')) as snapshot:
            bad=maintenance.tick()
            self.assertEqual(bad['last_success'],good['last_success'])
            self.assertEqual(bad['status'],'warning');self.assertNotIn('PRIVATE-SENTINEL',json.dumps(bad))
            self.assertIsNone(maintenance.tick());self.assertEqual(snapshot.call_count,1)
        with patch.object(core,'now',return_value=future+timedelta(minutes=31)):
            self.assertEqual(maintenance.tick()['status'],'ok')

    def test_disk_limit_never_consumes_last_good_copy(self):
        good=maintenance.tick()
        with patch.object(maintenance.shutil,'disk_usage',return_value=Mock(free=maintenance.MIN_FREE)):
            with self.assertRaises(ValueError):maintenance.snapshot()
        self.assertTrue((core.DATA/'backups'/good['file']).is_file())

    def test_interrupted_temp_removed_but_unrelated_temp_kept(self):
        directory=core.DATA/'backups';directory.mkdir()
        stale=directory/'studio-20261023T120000-abcdef012345.tmp';stale.write_bytes(b'partial')
        unrelated=directory/'anotacoes.tmp';unrelated.write_text('keep')
        maintenance.snapshot()
        self.assertFalse(stale.exists());self.assertTrue(unrelated.exists())

    def test_corrupt_snapshot_is_rejected_and_temp_removed(self):
        with patch.object(maintenance.sqlite3,'connect',side_effect=sqlite3.DatabaseError('corrupt')):
            self.assertEqual(maintenance.tick()['status'],'warning')
        self.assertEqual(list((core.DATA/'backups').iterdir()),[])

    def test_database_size_is_bounded(self):
        with patch.object(maintenance,'MAX_DATABASE',1):
            with self.assertRaises(ValueError):maintenance.snapshot()
        self.assertEqual(list((core.DATA/'backups').iterdir()),[])

    def test_invalid_references_cannot_replace_a_verified_snapshot(self):
        good=maintenance.tick()
        with closing(sqlite3.connect(core.DATA/'studio.sqlite')) as c:
            c.execute("INSERT INTO auto_products VALUES ('missing-product',1,1,4,?)",(core.stamp(),));c.commit()
        with self.assertRaises(ValueError):maintenance.snapshot()
        self.assertTrue((core.DATA/'backups'/good['file']).is_file())
        self.assertFalse(list((core.DATA/'backups').glob('*.tmp')))

    def test_concurrent_ticks_create_one_snapshot(self):
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:maintenance.tick(),range(2)))
        self.assertEqual(sum(r is not None for r in results),1)
        self.assertEqual(len(list((core.DATA/'backups').glob('*.sqlite'))),1)

    def test_report_never_exposes_snapshot_path_or_hash(self):
        maintenance.tick();state=maintenance.state()
        self.assertEqual(state['status'],'ok')
        self.assertNotIn('file',state);self.assertNotIn('sha256',state)

    def test_open_write_transaction_cannot_create_partial_snapshot(self):
        with core.db() as c:
            c.execute('UPDATE products SET name=? WHERE id=?',('Ainda não confirmado',self.pid))
            result=maintenance.snapshot()
        with closing(sqlite3.connect(core.DATA/'backups'/result['file'])) as copied:
            self.assertEqual(copied.execute('SELECT name FROM products').fetchone()[0],'Teste')


class ServiceTests(unittest.TestCase):
    def test_backoff_is_bounded_and_success_resets_failures(self):
        action=Mock(side_effect=[OSError('PRIVATE-SENTINEL')]*5+[None,OSError()])
        service=Service('teste',action,2,threading.Event())
        output=io.StringIO()
        with redirect_stdout(output):delays=[service.step() for _ in range(7)]
        self.assertEqual(delays,[5,15,60,300,300,2,5])
        self.assertNotIn('PRIVATE-SENTINEL',output.getvalue())
        self.assertIsNotNone(service.state()['last_success'])

    def test_stop_prevents_work_and_wait_is_interruptible(self):
        stop=threading.Event();stop.set();action=Mock()
        service=Service('teste',action,60,stop);service.run()
        action.assert_not_called();self.assertEqual(service.state()['status'],'stopped')
        stop.clear();action.side_effect=stop.set
        service.run();self.assertEqual(action.call_count,1)

    def test_slow_cycle_is_reported_without_a_duplicate_action(self):
        entered=threading.Event();release=threading.Event()
        def action():entered.set();release.wait(3)
        service=Service('teste',action,2,threading.Event(),slow_after=-1)
        task=threading.Thread(target=service.step);task.start()
        try:
            self.assertTrue(entered.wait(2));self.assertEqual(service.state()['status'],'slow')
        finally:release.set();task.join(4)
        self.assertEqual(service.state()['status'],'waiting')

    def test_catalog_cycle_does_not_hide_an_unexpected_error(self):
        with patch('catalog.tick',side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):app.catalog_worker()

    def test_tester_delivery_does_not_touch_remote(self):
        with patch.object(core,'TESTER',True),patch('youtube_client.tick') as remote,patch('autopilot.sync') as sync:
            app.delivery_worker();remote.assert_not_called();sync.assert_not_called()


class LauncherTests(unittest.TestCase):
    def test_real_child_process_restarts_and_preserves_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'app.py').write_text("import json,sys\nfrom pathlib import Path\np=Path('attempts.json')\na=json.loads(p.read_text()) if p.exists() else []\na.append(sys.argv[1:]);p.write_text(json.dumps(a))\nraise SystemExit(1 if len(a)==1 else 0)\n",encoding='utf-8')
            with patch.object(launcher,'ROOT',root),patch.object(launcher.time,'sleep'),redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.supervise(['--tester','--open']),0)
            self.assertEqual(json.loads((root/'attempts.json').read_text()),[['--tester','--open'],['--tester']])

    def test_deliberate_or_configuration_exit_never_restarts(self):
        for code in launcher.NORMAL_EXITS:
            with self.subTest(code=code),patch.object(launcher.subprocess,'Popen',return_value=Mock(wait=Mock(return_value=code))) as start:
                self.assertEqual(launcher.supervise(['--tester']),code);self.assertEqual(start.call_count,1)

    def test_crash_restarts_once_and_opens_browser_only_first_time(self):
        with patch.object(launcher.subprocess,'Popen',side_effect=[Mock(wait=Mock(return_value=1)),Mock(wait=Mock(return_value=0))]) as start,patch.object(launcher.time,'sleep') as sleep,redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.supervise(['--tester','--port','8767','--open']),0)
        sleep.assert_called_once_with(5)
        self.assertIn('--open',start.call_args_list[0].args[0]);self.assertNotIn('--open',start.call_args_list[1].args[0])
        self.assertIn('--tester',start.call_args_list[1].args[0])

    def test_restart_limit_stops_a_crash_loop(self):
        with patch.object(launcher.subprocess,'Popen',return_value=Mock(wait=Mock(return_value=1))) as start,patch.object(launcher.time,'sleep') as sleep,redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.supervise([]),1)
        self.assertEqual(start.call_count,6);self.assertEqual([c.args[0] for c in sleep.call_args_list],[5,15,30,60,120])

    def test_ctrl_c_waits_for_child_and_does_not_restart(self):
        child=Mock(wait=Mock(side_effect=[KeyboardInterrupt,0]))
        with patch.object(launcher.subprocess,'Popen',return_value=child) as start:
            self.assertEqual(launcher.supervise([]),0)
        self.assertEqual(start.call_count,1);child.terminate.assert_not_called()

    def test_ctrl_c_timeout_stops_only_owned_child(self):
        child=Mock(wait=Mock(side_effect=[KeyboardInterrupt,subprocess.TimeoutExpired('fixture',5),0]))
        with patch.object(launcher.subprocess,'Popen',return_value=child):self.assertEqual(launcher.supervise([]),0)
        child.terminate.assert_called_once_with()
