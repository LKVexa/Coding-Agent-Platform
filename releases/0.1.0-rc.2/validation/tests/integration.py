import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'src'
sys.path[:0] = [str(APP), str(APP / 'foundation')]
from coding_agent.platform import Platform
from coding_agent.provider import ProviderError
from component_foundation.safety import FoundationError, read_json


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.platform = Platform(APP)
        cls.temp = Path(tempfile.mkdtemp(prefix='coding-agent-integration-', dir=ROOT / 'tests'))
        cls.repo = cls.temp / 'repo'
        cls.platform.demo(cls.repo)
        cls.before = {p.relative_to(cls.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in cls.repo.rglob('*') if p.is_file()}

    def setUp(self):
        self.state = self.temp / self._testMethodName

    @classmethod
    def tearDownClass(cls):
        after = {p.relative_to(cls.repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in cls.repo.rglob('*') if p.is_file()}
        assert after == cls.before, 'Repository changed during read-only runs'

    def proposer(self, source, on_call=None):
        def fake(prompt, schema, run_dir, **kwargs):
            if on_call: on_call(prompt, run_dir, kwargs)
            task = read_json(run_dir.parent / 'task-public.json')
            original = (run_dir.parent / 'snapshot' / task['path']).read_bytes()
            return {'proposal': {'path': task['path'], 'base_sha256': hashlib.sha256(original).hexdigest(),
                                 'replacement': source, 'summary': 'Test response only'},
                    'provider': {'name': 'test-double', 'model': 'not-real', 'cost': None}, 'evidence': {}}
        return fake

    def correct(self):
        return (APP / 'evaluator/controls/clamp-bounds/correct.py').read_text(encoding='utf-8')

    def test_complete_patch_replay_export_and_idempotent_resume(self):
        with patch('coding_agent.provider.propose', side_effect=self.proposer(self.correct())) as provider:
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', run_id='full')
            self.assertTrue(result['accepted'])
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(self.platform.inspect(self.state, 'full')['integrity'], 'pass')
            self.assertEqual(self.platform.replay(self.state, 'full')['replay'], 'pass')
            self.assertEqual(self.platform.resume(self.state, 'full'), result)
            dest = self.temp / 'export'
            self.platform.export(self.state, 'full', dest)
            self.assertFalse((dest / 'private').exists())
            self.assertTrue((dest / 'change.patch').is_file())
            with self.assertRaises(FileExistsError):
                self.platform.run(self.state, self.repo, 'clamp-bounds', run_id='full')
            self.assertEqual(provider.call_count, 1)

    def test_two_attempts_only_public_feedback(self):
        attempts = []
        bad = 'def clamp(value, lo, hi):\n    return lo\n'
        def fake(prompt, schema, run_dir, **kwargs):
            attempts.append(prompt)
            return self.proposer(bad if len(attempts)==1 else self.correct())(prompt, schema, run_dir, **kwargs)
        with patch('coding_agent.provider.propose', side_effect=fake):
            result = self.platform.run(self.state, self.repo, 'clamp-bounds')
        self.assertTrue(result['accepted']); self.assertEqual(result['provider_calls'], 2)
        self.assertIn('previous_attempt_public_feedback', attempts[1])
        for prompt in attempts:
            self.assertNotIn('private/checks', prompt)
            self.assertNotIn('protocol_sha256', prompt)
            self.assertNotIn('p2p', prompt.lower())

    def test_regression_rejected_even_if_public_passes(self):
        # Overfit all disclosed examples but violate independent preservation cases.
        candidate = 'def clamp(value, lo, hi):\n    if value == 4:\n        return 4\n    if value == -1:\n        return 0\n    if value == 9:\n        return 8\n    return 0\n'
        with patch('coding_agent.provider.propose', side_effect=self.proposer(candidate)) as provider:
            result = self.platform.run(self.state, self.repo, 'clamp-bounds')
        self.assertFalse(result['accepted']); self.assertEqual(provider.call_count, 1)
        self.assertLess(result['p2p']['passed'], result['p2p']['total'])
        with self.assertRaises(FoundationError):
            self.platform.export(self.state, result['run_id'], self.temp / 'rejected-export')

    def test_provider_error_preserved_without_retry(self):
        with patch('coding_agent.provider.propose', side_effect=ProviderError('provider_limit', 'Provider usage limit')) as p:
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', run_id='error')
            self.assertEqual(result['status'], 'provider_failed')
            self.assertEqual(self.platform.resume(self.state, 'error'), result)
            self.assertEqual(p.call_count, 1)

    def test_cancel_before_independent_evaluation(self):
        def cancel(prompt, run_dir, kwargs):
            self.platform.cancel(self.state, 'cancelled')
        with patch('coding_agent.provider.propose', side_effect=self.proposer(self.correct(), cancel)):
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', run_id='cancelled')
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse((self.state / 'runs/cancelled/private/evaluation.json').exists())
        self.platform.inspect(self.state, 'cancelled')

    def test_custom_task_runs_separate_private_cases(self):
        task = self.temp / 'custom-task.json'
        checks = self.temp / 'custom-checks.json'
        task.write_text(json.dumps({'id':'custom-clamp','path':'src/clamp.py','function':'clamp',
            'parameters':['value','lo','hi'],'description':'Clamp to inclusive bounds.',
            'public_examples':[{'args':[4,0,8],'expected':4}]}), encoding='utf-8')
        checks.write_text(json.dumps({'task_id':'custom-clamp','cases':[
            {'id':'preserve','args':[3,0,9],'expected':3}, {'id':'fix','args':[11,0,9],'expected':9}]}), encoding='utf-8')
        with patch('coding_agent.provider.propose', side_effect=self.proposer(self.correct())):
            result = self.platform.run(self.state, self.repo, str(task), str(checks))
        self.assertTrue(result['accepted']); self.assertEqual(result['partition'], 'user-supplied')


if __name__ == '__main__':
    unittest.main(verbosity=2)
