import io
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from scripts import validate


class ValidatorTests(unittest.TestCase):
    def test_incomplete_suite_fails_with_recent_test_progress(self):
        progress=b'Unrelated process output\ntest_first (tests.Suite) ... ok\ntest_waiting (tests.Suite) ... '
        error=subprocess.TimeoutExpired(['python','-m','unittest'],480,stderr=progress)
        output=io.StringIO()
        with patch.object(validate.subprocess,'run',side_effect=error),redirect_stdout(output):
            errors=validate.check_tests()
        self.assertTrue(errors)
        self.assertIn('test_waiting',output.getvalue())
        self.assertNotIn('Unrelated process output',output.getvalue())

    def test_blocks_private_data_even_when_nested_or_disguised_by_case(self):
        for path in ['data/studio.sqlite', 'data-tester/video.mp4', 'artifacts/report.json', '.venv/pyvenv.cfg',
                     'docs/client_secret_google.json', 'web/CREDENTIALS.json', '.env.local', 'tokens.json',
                     '../outside.py', '/absolute.py', 'web/node_modules/file.js', 'C:/outside.py', '..\\outside.py']:
            with self.subTest(path=path):
                self.assertTrue(validate.private_paths([path]))
        self.assertEqual(validate.private_paths(['app.py', 'web/professional.js', 'requirements-validation.txt']), [])

    def test_rejects_invalid_python_and_missing_tracked_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'broken.py').write_text('def incomplete(', encoding='utf-8')
            self.assertEqual(len(validate.check_sources(['broken.py', 'missing.py'], root)), 2)

    def test_checks_html_assets_and_forbids_inline_handlers(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'web').mkdir()
            file = root / 'web/index.html'
            file.write_text('<script src="/missing.js"></script><button onclick="run()">A</button>', encoding='utf-8')
            self.assertEqual(len(validate.check_assets(root)), 2)
            file.write_text('<script src="/app.js"></script>', encoding='utf-8')
            (root / 'web/app.js').write_text('"use strict";', encoding='utf-8')
            self.assertEqual(validate.check_assets(root), [])

    def test_does_not_accept_unpinned_dependencies_or_arbitrary_install_urls(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'requirements.txt').write_text('Pillow==12.3.0\nexample>=1\nhttps://example.com/package\n', encoding='utf-8')
            self.assertEqual(len(validate.check_requirements(['requirements.txt'], root)), 2)

    def test_package_rejects_added_private_files_and_missing_commit_sources(self):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, 'w') as archive:
            archive.writestr('app.py', '# source')
            archive.writestr('data/studio.sqlite', 'private fixture')
        self.assertTrue(validate.check_archive(raw.getvalue(), ['app.py', 'README.md']))

    def test_history_blocks_file_removed_from_latest_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            def git(*args):
                return subprocess.run(['git', '-c', 'user.name=Validator', '-c', 'user.email=validator@example.invalid', *args],
                                      cwd=root, check=True, capture_output=True)
            (root / 'credentials.json').write_text('{}', encoding='utf-8')
            git('add', 'credentials.json')
            git('commit', '-qm', 'Fixture only')
            git('rm', 'credentials.json')
            git('commit', '-qm', 'Remove fixture')
            self.assertTrue(validate.check_history(root))
            self.assertEqual(validate.private_paths(validate.source_files(root)), [])
