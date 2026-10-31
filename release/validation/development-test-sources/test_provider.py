import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from coding_agent import provider

class ProviderTests(unittest.TestCase):
    def test_catalog_tool_surface(self):
        models = provider._verify_catalog()
        self.assertIn('gpt-6.1-sol', models)

    def test_environment_has_no_agent_pipes_or_api_key(self):
        with patch.dict(provider.os.environ, {'OPENAI_API_KEY':'fake-test-value',
                                              'CODEX_APP_TOOLS_PIPE_PATH':'fake-pipe',
                                              'OPENAI_BASE_URL':'http://example.invalid'}):
            env = provider._environment()
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('OPENAI_BASE_URL', env)
        self.assertNotIn('CODEX_APP_TOOLS_PIPE_PATH', env)

    def test_capture_limit(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            with self.assertRaises(provider.ProviderError) as caught:
                provider._capture([sys.executable, '-c', 'print("x" * 300000)'],
                                  cwd=Path(temp), env=provider._environment(), timeout=3)
            self.assertEqual('output_limit', caught.exception.code)

    def test_capture_timeout(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            with self.assertRaises(provider.ProviderError) as caught:
                provider._capture([sys.executable, '-c', 'import time; time.sleep(5)'],
                                  cwd=Path(temp), env=provider._environment(), timeout=0.2)
            self.assertEqual('timeout', caught.exception.code)

    def test_capture_cancellation(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
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
        schema = {'type':'object', 'required':['message'], 'properties':{'message':{'type':'string'}},
                  'additionalProperties':False}
        with self.assertRaises(ValueError):
            provider._validate({'message':3}, schema)
        with self.assertRaises(ValueError):
            provider._validate({'message':'x','extra':True}, schema)
        provider._validate({'message':'x'}, schema)

    def test_cli_drift_fails_closed_and_persists_safe_metadata(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            with patch.object(provider.shutil, 'which', return_value=None):
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.propose('Return a message.', {'type':'object'}, Path(temp))
            self.assertEqual('cli_mismatch', caught.exception.code)
            metadata = json.loads(Path(caught.exception.evidence['metadata']).read_text())
            self.assertEqual('failed', metadata['status'])
            self.assertEqual('cli_mismatch', metadata['error']['code'])
            self.assertIsNone(metadata['cost'])

    def test_model_drift_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            results=[(0,provider.CLI_VERSION,''),(0,'','Logged in using ChatGPT'),
                     (0,'','model: other-model\n')]
            with patch.object(provider,'_verify_catalog',return_value={'gpt-6.1-sol','other-model'}), \
                 patch.object(provider.shutil,'which',return_value='codex.exe'), \
                 patch.object(provider,'_digest',return_value=provider.CLI_SHA256), \
                 patch.object(provider,'_capture',side_effect=results):
                with self.assertRaises(provider.ProviderError) as caught:
                    provider.propose('Return a message.', {'type':'object'}, Path(temp))
            self.assertEqual('model_mismatch', caught.exception.code)
            metadata=json.loads(Path(caught.exception.evidence['metadata']).read_text())
            self.assertEqual('other-model',metadata['model'])

    def test_guidance_presence_only(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            (Path(temp)/'AGENTS.md').write_text('Artificial private canary; must not be read.')
            with patch.dict(provider.os.environ,{'CODEX_HOME':temp}), \
                 patch.object(Path,'read_text',side_effect=AssertionError('unexpected read')):
                result=provider._guidance_presence()
            self.assertEqual({'present':True,'filename':'AGENTS.md','contents_read':False},result)

if __name__ == '__main__':
    unittest.main(verbosity=2)
