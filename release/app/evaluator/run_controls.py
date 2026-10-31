"""Write independent no-op/correct/regression control evidence."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluator.tasks import ROOT, evaluate_task, list_public_tasks, verify_protocol


def main():
    results = []
    for task in list_public_tasks():
        original = (ROOT / 'repository-template' / task['path']).read_text(encoding='utf-8')
        candidates = {'noop': original}
        for kind in ('correct', 'regression'):
            candidates[kind] = (ROOT / 'controls' / task['id'] / (kind + '.py')).read_text(encoding='utf-8')
        for kind, source in candidates.items():
            result = evaluate_task(task['id'], source)
            result['control'] = kind
            results.append(result)
    success = all(row['accepted'] == (row['control'] == 'correct') for row in results)
    report = {'schema_version': '1.0.0', 'scope': 'authored fixtures; no benchmark validity claim',
              'private_evaluator_output': True, 'integrity': verify_protocol(),
              'all_controls_as_expected': success, 'results': results}
    destination = ROOT / 'evidence' / 'controls.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_controls_as_expected': success, 'controls': len(results),
                      'report': str(destination), 'manifest_sha256': report['integrity']['manifest_sha256']}))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
