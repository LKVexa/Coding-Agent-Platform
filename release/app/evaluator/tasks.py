"""Frozen task contracts and independent fail-to-pass/pass-to-pass assessment.

Provider context must use get_public_task/evaluate_public only. evaluate_task
returns private diagnostics for the local evidence report, never model feedback.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .safe_python import VERSION, evaluate_source

ROOT = Path(__file__).resolve().parent


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_public_tasks():
    return _json(ROOT / 'public' / 'tasks.json')['tasks']


def get_public_task(task_id):
    for task in list_public_tasks():
        if task['id'] == task_id:
            task['original_sha256'] = _sha(ROOT / 'repository-template' / task['path'])
            return task
    raise ValueError('Unknown authored task')


def verify_protocol():
    """Fail closed if the released protocol, evaluator, controls or task files change."""
    manifest_path = ROOT / 'PROTOCOL-MANIFEST.json'
    manifest = _json(manifest_path)
    expected_paths = {
        '__init__.py', 'safe_python.py', 'tasks.py', 'public/tasks.json',
        'evaluator-only/protocol.json', 'repository-template/README.md',
        'repository-template/src/clamp.py', 'repository-template/src/overlap.py',
        'repository-template/src/buckets.py',
        *('controls/' + task + '/' + name + '.py'
          for task in ('clamp-bounds', 'interval-overlap', 'bucket-index')
          for name in ('correct', 'regression')),
    }
    files = manifest.get('files', {})
    if set(files) != expected_paths:
        raise ValueError('Frozen protocol file set mismatch')
    for relative, expected_sha in files.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or _sha(path) != expected_sha:
            raise ValueError('Frozen evaluator integrity mismatch: ' + relative)
    return {'verified': True, 'manifest_sha256': _sha(manifest_path),
            'protocol_sha256': files['evaluator-only/protocol.json'],
            'file_count': len(files)}


def evaluate_public(task_id, candidate_source):
    """Only disclosed examples; safe to use as development feedback."""
    task = get_public_task(task_id)
    cases = [dict(example, id=f'public-{index + 1}')
             for index, example in enumerate(task['public_examples'])]
    if task_id == 'bucket-index':
        for case in cases:
            case['type'] = 'int'
    return evaluate_source(candidate_source, task['function'], cases, task['parameters'])


def evaluate_task(task_id, candidate_source, baseline_source=None):
    """Return independent final assessment. Never send this result to the provider.

    baseline_source, if supplied, must exactly match the frozen original source.
    The caller validates and applies its one-file patch separately; this function
    accepts the proposed text rather than importing a file from that repository.
    """
    integrity = verify_protocol()
    task = get_public_task(task_id)
    original_path = ROOT / 'repository-template' / task['path']
    original_bytes = original_path.read_bytes()
    original_source = original_bytes.decode('utf-8')
    if baseline_source is not None and baseline_source != original_source:
        raise ValueError('Baseline source does not match the frozen original')
    protocol = _json(ROOT / 'evaluator-only' / 'protocol.json')
    frozen = protocol['tasks'][task_id]
    cases = frozen['cases']
    baseline = evaluate_source(original_source, task['function'], cases, task['parameters'])
    if {key: baseline[key] for key in ('pass', 'fail')} != frozen['expected_baseline']:
        raise ValueError('Frozen baseline outcome changed')
    candidate = evaluate_source(candidate_source, task['function'], cases, task['parameters'])
    outcomes = {case['id']: case['status'] for case in candidate['cases']}
    f2p_ids = [case['id'] for case in baseline['cases'] if case['status'] == 'fail']
    p2p_ids = [case['id'] for case in baseline['cases'] if case['status'] == 'pass']

    def metric(ids):
        return {'passed': sum(outcomes.get(case_id) == 'pass' for case_id in ids),
                'total': len(ids), 'case_ids': ids}

    f2p, p2p = metric(f2p_ids), metric(p2p_ids)
    accepted = (candidate['syntax_allowed'] and candidate['fail'] == 0
                and f2p['total'] > 0 and f2p['passed'] == f2p['total']
                and p2p['total'] > 0 and p2p['passed'] == p2p['total'])
    return {
        'schema_version': '1.0.0', 'evaluator_version': VERSION,
        'task_id': task_id, 'partition': task['partition'],
        'scope': 'authored_repository_task', 'scientific_validation': 'unverified',
        'protocol_version': protocol['protocol_version'], **integrity,
        'original_file_sha256': hashlib.sha256(original_bytes).hexdigest(),
        'candidate_sha256': candidate['source_sha256'],
        'baseline': baseline, 'candidate': candidate,
        'f2p': f2p, 'p2p': p2p, 'accepted': bool(accepted),
        'private_evaluator_output': True,
    }
