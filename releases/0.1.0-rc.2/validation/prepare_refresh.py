import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'outputs/Coding_Agent_Platform_v0.1.0-rc.1'
APP = HERE / 'src'
assert not APP.exists()
shutil.copytree(OLD / 'app', APP)
(HERE / 'evidence').mkdir(exist_ok=True)
env = os.environ.copy()
env['PATH'] = os.pathsep.join([str(Path(os.environ['SystemRoot']) / 'System32'), os.environ['SystemRoot']])
assert shutil.which('codex', path=env['PATH']) is None
result = subprocess.run([sys.executable, '-I', '-B', str(OLD / 'app/agent.py'), 'doctor'],
                        env=env, capture_output=True, text=True, timeout=60)
assert result.returncode == 2 and 'differs from the verified release' in result.stderr
(HERE / 'evidence/BEFORE-EXTERNAL-LAUNCH.json').write_text(json.dumps({
    'scenario': 'Windows launcher environment without Codex-specific PATH injection',
    'codex_on_path': False, 'exit_code': result.returncode,
    'stdout': result.stdout, 'stderr': result.stderr,
    'installed_cli_sha256': hashlib.sha256(Path(shutil.which('codex')).read_bytes()).hexdigest(),
    'expected_cli_sha256': '3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16',
    'root_cause': 'Missing runtime discovery is reported as binary drift.'
}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'reproduced': True, 'new_source': str(APP), 'prior_release_modified': False}))
