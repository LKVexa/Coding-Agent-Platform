import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = HERE / 'src'
SUFFIX = '-final' if '--final' in sys.argv else ''
STATE = ROOT / ('work/ca2-state' + SUFFIX)
REPO = ROOT / ('work/ca2-repo' + SUFFIX)
EXPORT = ROOT / ('work/ca2-export' + SUFFIX)
EVIDENCE = HERE / ('evidence/LAUNCH-AND-WORKFLOW' + SUFFIX.upper() + '.json')
assert not EVIDENCE.exists() and not STATE.exists() and not REPO.exists() and not EXPORT.exists()
env = os.environ.copy()
windows = Path(os.environ['SystemRoot'])
env['PATH'] = os.pathsep.join(map(str, [windows / 'System32', windows / 'System32/WindowsPowerShell/v1.0', windows]))
env.pop('CODING_AGENT_CODEX', None)
assert shutil.which('codex', path=env['PATH']) is None
records = []

def inventory(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

before_app = inventory(APP)

def save():
    EVIDENCE.write_text(json.dumps({'scenario': 'No Codex on PATH; no explicit CLI override',
                                   'app_manifest_sha256': before_app['MANIFEST.json'],
                                   'commands': records}, indent=2) + '\n', encoding='utf-8')

def run(args, launcher=False):
    command = ([str(windows / 'System32/cmd.exe'), '/d', '/c', 'Coding-Agent.cmd', *args]
               if launcher else [sys.executable, '-I', '-B', str(APP / 'agent.py'), *args])
    result = subprocess.run(command, cwd=APP, env=env, capture_output=True, text=True, timeout=300)
    records.append({'args': args, 'launcher': launcher, 'exit_code': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr})
    save()
    assert result.returncode == 0, (args, result.returncode, result.stderr[-1000:])
    value = json.loads(result.stdout)
    print(json.dumps({'command': args[0], 'status': value.get('status'), 'accepted': value.get('accepted')}), flush=True)
    return value

doctor = run(['doctor'], launcher=True)
assert doctor['status'] == 'pass' and doctor['version'] == '0.1.0-rc.2'
assert doctor['provider']['cli_sha256'] == '3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16'
run(['demo', '--destination', str(REPO)])
before_repo = inventory(REPO)
result = run(['run', '--repo', str(REPO), '--task', 'interval-overlap', '--state', str(STATE),
              '--run-id', 'external-launch-overlap', '--max-calls', '2', '--timeout', '120'])
assert result['accepted'] is True
replay = run(['replay', '--state', str(STATE), '--run-id', 'external-launch-overlap'])
assert replay['replay'] == 'pass'
run(['export', '--state', str(STATE), '--run-id', 'external-launch-overlap', '--destination', str(EXPORT)])
assert inventory(APP) == before_app
assert inventory(REPO) == before_repo
data = json.loads(EVIDENCE.read_bytes())
data.update(status='pass', app_unchanged=True, repository_unchanged=True,
            provider_calls=result['provider_calls'], model_tools='unchanged qualified policy',
            old_cli_hash_still_required=True)
EVIDENCE.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'status': 'pass', 'provider_calls': result['provider_calls']}))
