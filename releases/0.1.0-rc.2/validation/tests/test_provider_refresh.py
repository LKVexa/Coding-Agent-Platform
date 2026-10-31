"""Fresh provider/resolver qualification; no model calls or real CLI execution."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
APP = HERE.parent / 'src'
sys.path.insert(0, str(APP))
from coding_agent import provider


class ResolverTests(unittest.TestCase):
    """Fake native files and controlled discovery; approved bytes are a test pin."""
    approved = b'MZ artificial resolver fixture; never execute this file\n'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='resolver-', dir=HERE)
        self.root = Path(self.temp.name)
        self.home = self.root / 'test home'
        self.local = self.home / 'AppData/Local'
        self.local.mkdir(parents=True)
        self.patches = [
            patch.dict(os.environ, {'LOCALAPPDATA': str(self.local), 'CODING_AGENT_CODEX': ''}),
            patch.object(Path, 'home', return_value=self.home),
            patch.object(provider.shutil, 'which', return_value=None),
            patch.object(provider, 'CLI_SHA256', hashlib.sha256(self.approved).hexdigest()),
            patch.object(provider, '_capture', side_effect=AssertionError('Resolver must not execute a CLI')),
        ]
        self.values = [p.start() for p in self.patches]
        os.environ.pop('CODING_AGENT_CODEX', None)
        self.which = self.values[2]

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def executable(self, relative, approved=True):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.approved if approved else b'MZ wrong and unqualified bytes\n')
        return path

    def managed(self, build='verified', approved=True):
        path = self.local / 'OpenAI/Codex/bin' / build / 'codex.exe'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.approved if approved else b'MZ unqualified managed bytes\n')
        return path

    def assert_resolves(self, expected):
        actual = provider._resolve_cli()
        self.assertEqual(Path(actual).resolve(), expected.resolve())
        self.assertEqual(provider._digest(Path(actual)), provider.CLI_SHA256)

    def test_explicit_approved_absolute_path_with_spaces(self):
        expected = self.executable('explicit cli/codex.exe')
        os.environ['CODING_AGENT_CODEX'] = str(expected)
        self.assert_resolves(expected)

    def test_explicit_relative_does_not_fall_back(self):
        fallback = self.managed()
        self.which.return_value = str(fallback)
        os.environ['CODING_AGENT_CODEX'] = 'relative/codex.exe'
        with self.assertRaises(provider.ProviderError):
            provider._resolve_cli()
        self.which.assert_not_called()

    def test_explicit_missing_does_not_fall_back(self):
        fallback = self.managed()
        self.which.return_value = str(fallback)
        os.environ['CODING_AGENT_CODEX'] = str(self.root / 'missing/codex.exe')
        with self.assertRaises(provider.ProviderError):
            provider._resolve_cli()
        self.which.assert_not_called()

    def test_explicit_unapproved_does_not_fall_back(self):
        wrong = self.executable('explicit/codex.exe', approved=False)
        fallback = self.managed()
        self.which.return_value = str(fallback)
        os.environ['CODING_AGENT_CODEX'] = str(wrong)
        with self.assertRaises(provider.ProviderError) as caught:
            provider._resolve_cli()
        self.assertEqual(caught.exception.code, 'cli_mismatch')
        self.which.assert_not_called()

    def test_path_approved_is_selected(self):
        expected = self.executable('path/codex.exe')
        self.which.return_value = str(expected)
        self.managed(approved=False)
        self.assert_resolves(expected)

    def test_approved_path_not_blocked_by_managed_discovery_limit(self):
        expected = self.executable('path/codex.exe')
        self.which.return_value = str(expected)
        managed = self.local / 'OpenAI/Codex/bin'
        managed.mkdir(parents=True)
        for index in range(129):
            (managed / ('unneeded-build-' + str(index))).mkdir()
        self.assert_resolves(expected)

    def test_managed_approved_found_when_path_missing(self):
        expected = self.managed()
        self.assert_resolves(expected)

    def test_unapproved_path_falls_back_to_qualified_managed(self):
        wrong = self.executable('path/codex.exe', approved=False)
        self.which.return_value = str(wrong)
        expected = self.managed()
        self.assert_resolves(expected)

    def test_unapproved_candidates_fail_without_execution(self):
        wrong = self.executable('path/codex.exe', approved=False)
        self.which.return_value = str(wrong)
        self.managed(approved=False)
        with self.assertRaises(provider.ProviderError) as caught:
            provider._resolve_cli()
        self.assertEqual(caught.exception.code, 'cli_mismatch')

    def test_no_files_reports_not_found_without_execution(self):
        with self.assertRaises(provider.ProviderError) as caught:
            provider._resolve_cli()
        self.assertEqual(caught.exception.code, 'cli_not_found')

    def test_managed_home_fallback_without_localappdata(self):
        expected = self.managed()
        os.environ.pop('LOCALAPPDATA', None)
        self.assert_resolves(expected)

    def test_explicit_symlink_is_rejected(self):
        target = self.executable('linked/codex.exe')
        os.environ['CODING_AGENT_CODEX'] = str(target)
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda p: p == target or original(p)):
            with self.assertRaises(provider.ProviderError):
                provider._resolve_cli()

    def test_explicit_junction_parent_is_rejected(self):
        target = self.executable('junction/codex.exe')
        os.environ['CODING_AGENT_CODEX'] = str(target)
        original = Path.is_junction
        with patch.object(Path, 'is_junction', lambda p: p == target.parent or original(p)):
            with self.assertRaises(provider.ProviderError):
                provider._resolve_cli()

    def test_managed_search_does_not_accept_deeper_descendant(self):
        self.managed('container/nested')
        with self.assertRaises(provider.ProviderError) as caught:
            provider._resolve_cli()
        self.assertEqual(caught.exception.code, 'cli_not_found')

    def test_explicit_script_wrapper_is_not_a_native_executable(self):
        target = self.executable('wrapper/codex.cmd')
        os.environ['CODING_AGENT_CODEX'] = str(target)
        with self.assertRaises(provider.ProviderError):
            provider._resolve_cli()


class ProviderTests(unittest.TestCase):
    """The prior nine checks, adapted only at the resolver seam, plus version gates."""
    def test_catalog_tool_surface(self):
        self.assertIn('gpt-6.1-sol', provider._verify_catalog())

    def test_environment_has_no_agent_pipes_or_api_key(self):
        with patch.dict(provider.os.environ, {'OPENAI_API_KEY': 'fake-test-value',
                                             'CODEX_APP_TOOLS_PIPE_PATH': 'fake-pipe',
                                             'OPENAI_BASE_URL': 'http://example.invalid'}):
            env = provider._environment()
        for name in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_APP_TOOLS_PIPE_PATH'):
            self.assertNotIn(name, env)

    def test_capture_limit(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            with self.assertRaises(provider.ProviderError) as caught:
                provider._capture([sys.executable, '-c', 'print("x" * 300000)'],
                                  cwd=Path(temp), env=provider._environment(), timeout=3)
            self.assertEqual('output_limit', caught.exception.code)

    def test_capture_timeout(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            with self.assertRaises(provider.ProviderError) as caught:
                provider._capture([sys.executable, '-c', 'import time; time.sleep(5)'],
                                  cwd=Path(temp), env=provider._environment(), timeout=0.2)
            self.assertEqual('timeout', caught.exception.code)

    def test_capture_cancellation(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            cancel = Path(temp) / 'cancel'
            timer = threading.Timer(0.2, lambda: cancel.write_text('cancel'))
            timer.start()
            with self.assertRaises(provider.ProviderError) as caught:
                provider._capture([sys.executable, '-c', 'import time; time.sleep(5)'],
                                  cwd=Path(temp), env=provider._environment(), timeout=3,
                                  cancel_path=cancel)
            timer.join()
            self.assertEqual('CANCELLED', caught.exception.code)

    def test_invalid_schema_response(self):
        schema = {'type': 'object', 'required': ['message'], 'properties': {'message': {'type': 'string'}},
                  'additionalProperties': False}
        with self.assertRaises(ValueError):
            provider._validate({'message': 3}, schema)
        with self.assertRaises(ValueError):
            provider._validate({'message': 'x', 'extra': True}, schema)
        provider._validate({'message': 'x'}, schema)

    def test_cli_drift_fails_closed_and_persists_safe_metadata(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            with patch.object(provider, '_resolve_cli', side_effect=provider.ProviderError('cli_mismatch', 'Unqualified CLI')), \
                 patch.object(provider, '_capture', side_effect=AssertionError('Unknown CLI executed')):
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.propose('Return a message.', {'type': 'object'}, Path(temp))
            self.assertEqual('cli_mismatch', caught.exception.code)
            metadata = json.loads(Path(caught.exception.evidence['metadata']).read_text())
            self.assertEqual('failed', metadata['status'])
            self.assertEqual('cli_mismatch', metadata['error']['code'])
            self.assertIsNone(metadata['cost'])

    def test_model_drift_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            results = [(0, provider.CLI_VERSION, ''), (0, '', 'Logged in using ChatGPT'),
                       (0, '', 'model: other-model\n')]
            with patch.object(provider, '_verify_catalog', return_value={'gpt-6.1-sol', 'other-model'}), \
                 patch.object(provider, '_resolve_cli', return_value='codex.exe'), \
                 patch.object(provider, '_digest', return_value=provider.CLI_SHA256), \
                 patch.object(provider, '_capture', side_effect=results):
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.propose('Return a message.', {'type': 'object'}, Path(temp))
            self.assertEqual('model_mismatch', caught.exception.code)
            metadata = json.loads(Path(caught.exception.evidence['metadata']).read_text())
            self.assertEqual('other-model', metadata['model'])

    def test_guidance_presence_only(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            (Path(temp) / 'AGENTS.md').write_text('Artificial private canary; must not be read.')
            with patch.dict(provider.os.environ, {'CODEX_HOME': temp}), \
                 patch.object(Path, 'read_text', side_effect=AssertionError('unexpected read')):
                result = provider._guidance_presence()
            self.assertEqual({'present': True, 'filename': 'AGENTS.md', 'contents_read': False}, result)

    def test_doctor_still_rejects_version_mismatch(self):
        with patch.object(provider, '_resolve_cli', return_value='codex.exe'), \
             patch.object(provider, '_capture', return_value=(0, 'codex-cli unexpected', '')) as capture:
            with self.assertRaises(provider.ProviderError) as caught:
                provider.provider_info()
        self.assertEqual('cli_mismatch', caught.exception.code)
        self.assertEqual(capture.call_count, 1)

    def test_proposal_still_rejects_version_mismatch(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            with patch.object(provider, '_resolve_cli', return_value='codex.exe'), \
                 patch.object(provider, '_capture', return_value=(0, 'codex-cli unexpected', '')) as capture:
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.propose('Return a message.', {'type': 'object'}, Path(temp))
            self.assertEqual('cli_mismatch', caught.exception.code)
            self.assertEqual(capture.call_count, 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
