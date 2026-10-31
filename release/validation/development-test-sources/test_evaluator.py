"""Regression/control and host-boundary tests; run with stdlib unittest."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluator.safe_python import evaluate_source, MAX_SOURCE_BYTES
from evaluator.tasks import ROOT, evaluate_task, evaluate_public, get_public_task, verify_protocol


class InterpreterTests(unittest.TestCase):
    def evaluate(self, source, arguments=(2,), expected=2):
        return evaluate_source(source, 'candidate', [{'id': 'case', 'args': list(arguments), 'expected': expected}], ['value'])

    def test_numeric_language(self):
        source = '''def candidate(value: int) -> int:
    """An allowed bounded function."""
    amount = abs(value)
    if 0 <= amount <= 4 and not amount == 3:
        return min(max(amount, 1), 4)
    return int(amount / 2) if amount > 8 else amount % 3
'''
        self.assertEqual(self.evaluate(source)['status'], 'pass')
        self.assertEqual(self.evaluate(source, (-10,), 5)['status'], 'pass')
        self.assertEqual(self.evaluate(source, (3,), 0)['status'], 'pass')

    def test_host_access_and_unbounded_syntax_refused(self):
        sources = [
            'import os\ndef candidate(value): return value',
            'def candidate(value): return open("secret")',
            'def candidate(value): return __import__("os")',
            'def candidate(value): return eval("value")',
            'def candidate(value): return value.__class__',
            'def candidate(value): return globals()',
            'def candidate(value): return locals()',
            'def candidate(value): return getattr(value,"x")',
            'def candidate(value): return [value][0]',
            'def candidate(value): return [x for x in range(value)]',
            'def candidate(value):\n while True: pass',
            'def candidate(value):\n for x in range(value): pass',
            'def candidate(value): return candidate(value)',
            'def candidate(value): return 2 ** value',
            '@open("secret")\ndef candidate(value): return value',
            'def candidate(value=open("secret")): return value',
            'def candidate(value: open("secret")): return value',
            'def candidate(value):\n global x\n x=value\n return x',
            'def candidate(value):\n def nested(x): return x\n return value',
            'def candidate(value): return (lambda: value)()',
            'def candidate(value): return f"{value}"',
            'def candidate(value):\n min = value\n return value',
            'x = 4\ndef candidate(value): return value',
            'def candidate(value): return min(*value)',
        ]
        for source in sources:
            with self.subTest(source=source):
                result = self.evaluate(source)
                self.assertFalse(result['syntax_allowed'])
                self.assertEqual(result['status'], 'refused')

    def test_candidate_does_not_execute(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / 'never-created.txt'
            source = 'def candidate(value):\n open(' + repr(str(sentinel)) + ', "w").write("bad")\n return value'
            self.assertFalse(self.evaluate(source)['syntax_allowed'])
            self.assertFalse(sentinel.exists())
        # A failing compile guard after parse verifies the interpreter never compiles
        # the AST to a code object; ast.parse itself internally uses compile to AST.
        tree = ast.parse('def candidate(value): return value + 0')
        with patch('ast.parse', return_value=tree), patch('builtins.compile', side_effect=AssertionError('Executable compilation forbidden')):
            self.assertEqual(self.evaluate('def candidate(value): return value + 0')['status'], 'pass')

    def test_limits_and_errors(self):
        for source in (
            'def candidate(value): return 1000000000001',
            'def candidate(value): return 1e999',
            'def candidate(value): return ' + '+'.join('value' for _ in range(200)),
            '#' * (MAX_SOURCE_BYTES + 1),
            'def candidate(value): return ' + '-' * 40 + 'value',
        ):
            self.assertEqual(self.evaluate(source)['status'], 'refused')
        for source in (
            'def candidate(value): return value / 0',
            'def candidate(value): return 1000000000000 * value',
            'def candidate(value): return missing',
            'def candidate(value): pass',
            'def candidate(value): return "data"',
        ):
            self.assertEqual(self.evaluate(source)['status'], 'fail')

    def test_boolean_not_numeric_label(self):
        self.assertEqual(self.evaluate('def candidate(value): return True', expected=1)['status'], 'fail')

    def test_branch_short_circuit(self):
        self.assertEqual(self.evaluate('def candidate(value): return value if value else 1 / 0')['status'], 'pass')
        self.assertEqual(self.evaluate('def candidate(value): return value or 1 / 0')['status'], 'pass')


class ProtocolTests(unittest.TestCase):
    def test_frozen_protocol_integrity(self):
        self.assertTrue(verify_protocol()['verified'])

    def test_all_controls(self):
        frozen = json.loads((ROOT / 'evaluator-only' / 'protocol.json').read_text())
        for task_id, declaration in frozen['tasks'].items():
            with self.subTest(task=task_id):
                task = get_public_task(task_id)
                original = (ROOT / 'repository-template' / task['path']).read_text()
                noop = evaluate_task(task_id, original)
                correct = evaluate_task(task_id, (ROOT / 'controls' / task_id / 'correct.py').read_text())
                regression = evaluate_task(task_id, (ROOT / 'controls' / task_id / 'regression.py').read_text())
                self.assertFalse(noop['accepted'])
                self.assertEqual(noop['f2p']['passed'], 0)
                self.assertEqual(noop['p2p']['passed'], noop['p2p']['total'])
                self.assertTrue(correct['accepted'])
                self.assertFalse(regression['accepted'])
                expected = declaration['expected_regression']
                self.assertEqual(regression['f2p']['passed'], expected['f2p_pass'])
                self.assertEqual(regression['f2p']['total'], expected['f2p_total'])
                self.assertEqual(regression['p2p']['passed'], expected['p2p_pass'])
                self.assertEqual(regression['p2p']['total'], expected['p2p_total'])

    def test_baseline_pin(self):
        with self.assertRaisesRegex(ValueError, 'Baseline source'):
            evaluate_task('clamp-bounds', 'def clamp(value, lo, hi): return value', baseline_source='not the original')

    def test_refused_candidate_cannot_pass(self):
        result = evaluate_task('clamp-bounds', 'import os\ndef clamp(value, lo, hi): return value')
        self.assertFalse(result['accepted'])
        self.assertEqual(result['f2p']['passed'], 0)
        self.assertEqual(result['p2p']['passed'], 0)

    def test_public_interface_excludes_private_cases(self):
        task = get_public_task('clamp-bounds')
        self.assertNotIn('cases', task)
        result = evaluate_public('clamp-bounds', (ROOT / 'controls' / 'clamp-bounds' / 'correct.py').read_text())
        self.assertEqual([case['id'] for case in result['cases']], ['public-1', 'public-2', 'public-3'])
        self.assertEqual(result['pass'], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
