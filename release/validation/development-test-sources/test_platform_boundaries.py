"""Independent local review. Fake provider only; no external calls.

The lightweight test Platform bypasses distribution construction deliberately;
package integrity is separately exercised through storage.verify_inventory.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

PRODUCT = Path(__file__).resolve().parent.parent
WORKSPACE = PRODUCT.parents[3]
sys.path[:0] = [str(PRODUCT / 'src'), str(PRODUCT),
               str(WORKSPACE / 'outputs/Shared_Foundation_v0.1.0-rc.1/foundation')]
from component_foundation.safety import FoundationError, atomic_json, read_json
from coding_agent.platform import Platform
from coding_agent import platform as platform_module, storage, repository, tasks, patches


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='review-', dir=Path(__file__).parent)
        self.base = Path(self.directory.name)
        self.package = self.base / 'package'
        self.package.mkdir()
        self.platform = Platform.__new__(Platform)
        self.platform.root = self.package
        self.platform.protected = [self.package]
        self.platform.manifest_sha256 = 'test-package-pin'
        self.repo = self.base / 'repository'
        self.platform.demo = lambda destination: repository.create_demo(Path(destination), PRODUCT / 'evaluator/repository-template', [self.package])
        self.platform.demo(self.repo)
        self.state = self.base / 'state'
        self.calls = []

    def tearDown(self):
        self.directory.cleanup()

    def correct_provider(self, prompt, schema, attempt, **kwargs):
        self.calls.append(prompt)
        payload = json.loads(prompt.split('BEGIN JSON TASK DATA\n', 1)[1].split('\nEND JSON TASK DATA', 1)[0])
        source = (PRODUCT / 'evaluator/controls' / payload['task']['id'] / 'correct.py').read_text()
        return {'proposal': {'path': payload['task']['path'], 'base_sha256': payload['base_sha256'],
                             'replacement': source, 'summary': 'Reviewed numeric repair'},
                'provider': {'name': 'independent-test-fake', 'live': False}}

    def run_correct(self, run_id='review'):
        with patch('coding_agent.provider.propose', self.correct_provider):
            return self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=1, run_id=run_id)

    def test_dirty_tree_preserved_committed_source_used(self):
        dirty = b'not committed, preserve these exact bytes\r\n'
        path = self.repo / 'src/clamp.py'
        path.write_bytes(dirty)
        result = self.run_correct()
        self.assertEqual(result['status'], 'accepted')
        self.assertEqual(path.read_bytes(), dirty)
        self.assertNotIn('not committed', self.calls[0])
        self.assertEqual(self.platform.replay(self.state, 'review')['replay'], 'pass')

    def test_provider_context_contains_public_only(self):
        result = self.run_correct()
        self.assertTrue(result['accepted'])
        payload = json.loads(self.calls[0].split('BEGIN JSON TASK DATA\n', 1)[1].split('\nEND JSON TASK DATA', 1)[0])
        self.assertEqual(set(payload), {'task', 'base_sha256', 'original_source'})
        self.assertEqual(set(payload['task']), {'id', 'path', 'function', 'parameters', 'description', 'public_examples'})
        self.assertNotIn('clamp-07', self.calls[0])
        export = self.base / 'export'
        self.platform.export(self.state, 'review', export)
        self.assertFalse(any('private' in p.relative_to(export).parts for p in export.rglob('*')))
        self.assertFalse(any(p.name == 'prompt.txt' for p in export.rglob('*')))

    def test_path_escape_and_baseline_substitution_rejected(self):
        task, _ = tasks.load_task('clamp-bounds')
        source, _ = repository.read_snapshot(self.repo, 'HEAD', task['path'])
        proposal = {'path': task['path'], 'base_sha256': hashlib.sha256(source.encode()).hexdigest(),
                    'replacement': 'def clamp(value, lo, hi): return min(max(value, lo), hi)\n', 'summary': 'x'}
        for bad in ('../outside.py', '/outside.py', 'C:/outside.py', 'src\\clamp.py', 'src/../outside.py'):
            with self.subTest(path=bad):
                with self.assertRaises(FoundationError):
                    repository.read_snapshot(self.repo, 'HEAD', bad)
                with self.assertRaises(FoundationError):
                    tasks.validate_proposal(dict(proposal, path=bad), task, source)
        with self.assertRaises(FoundationError):
            tasks.validate_proposal(dict(proposal, base_sha256='0' * 64), task, source)
        with self.assertRaises(FoundationError):
            storage.state_root(self.repo / 'agent-state', [self.repo])

    def test_junction_source_rejected(self):
        target = self.base / 'outside'
        target.mkdir()
        link = self.repo / 'linked'
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        command = 'New-Item -ItemType Junction -Path ' + quote(link) + ' -Target ' + quote(target) + ' | Out-Null'
        subprocess.run(['powershell', '-NoProfile', '-Command', command],
                       check=True, capture_output=True)
        try:
            with self.assertRaises(FoundationError):
                repository.read_snapshot(self.repo, 'HEAD', 'linked/escape.py')
        finally:
            # Remove only the junction, never the target tree.
            os.rmdir(link)

    def test_custom_cases_validation(self):
        public = {'id': 'custom', 'path': 'src/clamp.py', 'function': 'clamp',
                  'parameters': ['value', 'lo', 'hi'], 'description': 'repair',
                  'public_examples': [{'args': [3, 0, 2], 'expected': 2}]}
        private = {'task_id': 'custom', 'cases': [{'id': 'a', 'args': [1, 0, 2], 'expected': 1},
                                                 {'id': 'b', 'args': [3, 0, 2], 'expected': 2}]}
        task_path, checks_path = self.base / 'task.json', self.base / 'checks.json'
        task_path.write_text(json.dumps(public))
        checks_path.write_text(json.dumps(private))
        self.assertEqual(tasks.load_task(str(task_path), str(checks_path))[0]['partition'], 'user-supplied')
        for mutate in ('duplicate', 'arity', 'extra', 'wrong_task', 'magnitude'):
            value = copy.deepcopy(private)
            if mutate == 'duplicate': value['cases'][1]['id'] = 'a'
            if mutate == 'arity': value['cases'][1]['args'].pop()
            if mutate == 'extra': value['cases'][1]['execute'] = 'bad'
            if mutate == 'wrong_task': value['task_id'] = 'different'
            if mutate == 'magnitude': value['cases'][1]['args'][0] = 10**13
            checks_path.write_text(json.dumps(value))
            with self.subTest(mutate=mutate), self.assertRaises(FoundationError):
                tasks.load_task(str(task_path), str(checks_path))

    def test_two_attempt_repair_uses_public_feedback_only(self):
        def first_regression(prompt, schema, attempt, **kwargs):
            response = self.correct_provider(prompt, schema, attempt, **kwargs)
            if len(self.calls) == 1:
                response['proposal']['replacement'] = (PRODUCT / 'evaluator/controls/clamp-bounds/regression.py').read_text()
            return response
        with patch('coding_agent.provider.propose', first_regression):
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=2, run_id='two')
        self.assertTrue(result['accepted'])
        self.assertEqual(result['selected_attempt'], 2)
        self.assertEqual(result['provider_calls'], 2)
        self.assertIn('previous_attempt_public_feedback', self.calls[1])
        self.assertNotIn('clamp-07', self.calls[1])
        self.assertEqual(self.platform.replay(self.state, 'two')['replay'], 'pass')

    def test_private_failure_does_not_trigger_another_call(self):
        def overfits_public(prompt, schema, attempt, **kwargs):
            response = self.correct_provider(prompt, schema, attempt, **kwargs)
            response['proposal']['replacement'] = 'def clamp(value, lo, hi):\n    return 0 if value < lo else min(value, hi)\n'
            return response
        with patch('coding_agent.provider.propose', overfits_public):
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=2, run_id='overfit')
        self.assertFalse(result['accepted'])
        self.assertEqual(result['provider_calls'], 1)
        self.assertEqual(result['f2p']['passed'], result['f2p']['total'])
        self.assertLess(result['p2p']['passed'], result['p2p']['total'])

    def test_custom_task_end_to_end_private_values_absent(self):
        task = {'id': 'custom', 'path': 'src/clamp.py', 'function': 'clamp',
                'parameters': ['value', 'lo', 'hi'], 'description': 'Clamp to ordered numeric bounds.',
                'public_examples': [{'args': [4, 0, 3], 'expected': 3}]}
        checks = {'task_id': 'custom', 'cases': [{'id': 'secret-upper', 'args': [123456789, 0, 1], 'expected': 1},
                                                {'id': 'secret-keep', 'args': [1, 0, 3], 'expected': 1}]}
        task_path, checks_path = self.base / 'task.json', self.base / 'checks.json'
        task_path.write_text(json.dumps(task))
        checks_path.write_text(json.dumps(checks))
        def provider(prompt, schema, attempt, **kwargs):
            self.calls.append(prompt)
            payload = json.loads(prompt.split('BEGIN JSON TASK DATA\n', 1)[1].split('\nEND JSON TASK DATA', 1)[0])
            return {'proposal': {'path': payload['task']['path'], 'base_sha256': payload['base_sha256'],
                                 'replacement': 'def clamp(value, lo, hi):\n    return min(max(value, lo), hi)\n',
                                 'summary': 'Pure numeric replacement'}, 'provider': {'name': 'independent-test-fake', 'live': False}}
        with patch('coding_agent.provider.propose', provider):
            result = self.platform.run(self.state, self.repo, str(task_path), str(checks_path), max_calls=1, run_id='custom')
        self.assertTrue(result['accepted'])
        self.assertEqual(result['partition'], 'user-supplied')
        self.assertNotIn('123456789', self.calls[0])
        self.assertNotIn('secret-upper', self.calls[0])
        self.assertEqual(self.platform.replay(self.state, 'custom')['replay'], 'pass')

    def test_git_commondir_indirection_refused(self):
        shared = self.base / 'shared-repository'
        self.platform.demo(shared)
        (self.repo / '.git/commondir').write_text(str(shared / '.git') + '\n')
        with self.assertRaises(FoundationError):
            repository.read_snapshot(self.repo, 'HEAD', 'src/clamp.py')

    def test_patch_replay_rejects_redirect_and_context_change(self):
        original = 'def f(x):\n    return x\n'
        replacement = 'def f(x):\n    return x + 1\n'
        change = patches.make_patch('src/f.py', original, replacement)
        self.assertEqual(patches.apply_patch('src/f.py', original, change), replacement)
        with self.assertRaises(FoundationError):
            patches.apply_patch('src/f.py', original, change.replace('b/src/f.py', 'b/outside.py'))
        with self.assertRaises(FoundationError):
            patches.apply_patch('src/f.py', original.replace('return x', 'return 0'), change)

    def test_receipt_tampering_rejected(self):
        self.run_correct()
        source = self.state / 'runs/review/candidate/src/clamp.py'
        source.write_text('def clamp(value, lo, hi): return value\n')
        with self.assertRaises(FoundationError):
            self.platform.inspect(self.state, 'review')
        with self.assertRaises(FoundationError):
            self.platform.export(self.state, 'review', self.base / 'export')

    def test_resume_unknown_remote_outcome_never_reissues(self):
        def stop(*args, **kwargs):
            raise SystemExit('simulated process death')
        with patch('coding_agent.provider.propose', stop), self.assertRaises(SystemExit):
            self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=1, run_id='interrupted')
        with patch('coding_agent.provider.propose', side_effect=AssertionError('Unexpected second provider call')):
            result = self.platform.resume(self.state, 'interrupted')
        self.assertEqual(result['status'], 'interrupted')
        self.assertEqual(result['provider_calls'], 1)

    def test_cancel_between_precheck_and_receipt_cannot_corrupt_run(self):
        cancel_entered, permit_cancel = threading.Event(), threading.Event()
        results = []
        original_atomic = platform_module.atomic_json
        def held_atomic(path, value, *args, **kwargs):
            if Path(path).name == 'cancel.request.json':
                cancel_entered.set()
                if not permit_cancel.wait(5):
                    raise RuntimeError('Timed out waiting for finalization')
            return original_atomic(path, value, *args, **kwargs)
        def cancel():
            try: results.append(self.platform.cancel(self.state, 'race'))
            except Exception as exc: results.append(type(exc).__name__)
        def provider(*args, **kwargs):
            thread = threading.Thread(target=cancel)
            thread.start()
            self.cancel_thread = thread
            self.assertTrue(cancel_entered.wait(5))
            threading.Timer(.25, permit_cancel.set).start()
            return self.correct_provider(*args, **kwargs)
        try:
            with patch('coding_agent.provider.propose', provider), patch('coding_agent.platform.atomic_json', held_atomic):
                self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=1, run_id='race')
        finally:
            permit_cancel.set()
            self.cancel_thread.join(5)
        # Pre-fix this raises Unexpected or missing files: cancellation was added
        # after the completed receipt and invalidated its evidence inventory.
        self.platform.inspect(self.state, 'race')

    def test_resume_partial_terminal_must_validate_patch(self):
        self.run_correct()
        run = self.state / 'runs/review'
        (run / 'RECEIPT.json').unlink()
        (run / 'change.patch').write_text('corrupt patch\n')
        # Simulates a crash after result.json and corruption before recovery.
        # Recovery must refuse instead of blessing a new receipt over bad output.
        with self.assertRaises(FoundationError):
            self.platform.resume(self.state, 'review')

    def test_candidate_code_never_executes(self):
        marker = self.base / 'candidate-executed.txt'
        def malicious(prompt, schema, attempt, **kwargs):
            response = self.correct_provider(prompt, schema, attempt, **kwargs)
            response['proposal']['replacement'] = 'def clamp(value, lo, hi):\n    open(' + repr(str(marker)) + ', "w").write("bad")\n    return value\n'
            return response
        with patch('coding_agent.provider.propose', malicious):
            result = self.platform.run(self.state, self.repo, 'clamp-bounds', max_calls=1, run_id='malicious')
        self.assertEqual(result['status'], 'rejected')
        self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
