import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = HERE / 'src'
VERSION = '0.1.0-rc.2'

def write(path, value):
    path.write_text(value, encoding='utf-8', newline='\n')

for relative in ['INSTALL.md', 'docs/INSTALL.md']:
    path = APP / relative
    text = path.read_text(encoding='utf-8')
    text = text.replace('`codex-cli 0.166.0-alpha.5.1`, available as `codex` on PATH', '`codex-cli 0.166.0-alpha.5.1`, exact approved executable hash below')
    text = text.replace('The provider is discovered as `codex` on PATH.',
        'The provider is discovered from `CODING_AGENT_CODEX` when explicitly set; otherwise it checks PATH and the desktop installation under `%LOCALAPPDATA%/OpenAI/Codex/bin`. Only the exact approved native executable is accepted. An explicit override must be an absolute `.exe` path and never falls back silently.')
    if '## Missing CLI and changed CLI' not in text:
        text += '''
## Missing CLI and changed CLI

Version 0.1.0-rc.2 fixes launch from Explorer or a terminal that has no Codex
entry on PATH. No environment changes or new runtime installation are needed
when the approved executable is already in the desktop installation.

For an existing approved installation in another folder, set its full path:

```powershell
$env:CODING_AGENT_CODEX = 'C:\\Path\\To\\codex.exe'
& './Start-Platform.ps1' doctor
```

`cli_not_found` means no executable was found. `cli_mismatch` means discovered
executables do not match the approved hash. `invalid_cli_path` means the explicit
override is not an absolute native executable path. The hash and version checks
remain mandatory; a different CLI still requires a separately verified update.
'''
    write(path, text)
for relative in ['CHANGELOG.md', 'docs/CHANGELOG.md']:
    path = APP / relative
    text = path.read_text(encoding='utf-8')
    if '## 0.1.0-rc.2' not in text:
        text = text.replace('# Changelog\n', '''# Changelog

## 0.1.0-rc.2

Fixes Codex discovery when the Windows launcher does not inherit the desktop
app's PATH. Adds an explicit CODING_AGENT_CODEX override and bounded discovery
of the installed desktop runtime, accepting only the previously approved
executable hash and version. Distinguishes a missing CLI from binary drift and
includes a stable error code in setup failures. Provider model, tool policy,
catalog, evaluator and shared-foundation pins remain unchanged.

Keep the complete rc.1 installation to inspect or replay its existing runs.
New runs use the rc.2 package identity; frozen rc.1 run evidence is not rewritten.
''', 1)
    write(path, text)
for relative in ['RUNBOOK.md', 'docs/RUNBOOK.md']:
    path = APP / relative
    text = path.read_text(encoding='utf-8')
    if '| Provider CLI missing |' not in text:
        text = text.replace('| Provider CLI/version mismatch |', '| Provider CLI missing | Open or install Codex, or set CODING_AGENT_CODEX to the existing approved codex.exe; the desktop installation is also searched without PATH |\n| Provider CLI/version mismatch |')
    write(path, text)
write(APP / 'VERSION', VERSION + '\n')
lock = json.loads((APP / 'COMPONENT-LOCK.json').read_bytes())
lock['product_version'] = VERSION
lock['provider']['adapter_version'] = '1.0.1'
lock['provider']['discovery_policy'] = 'explicit override, otherwise PATH and bounded desktop installation lookup; exact existing binary hash and version required'
write(APP / 'COMPONENT-LOCK.json', json.dumps(lock, indent=2) + '\n')
protected = json.loads((APP / 'PROTECTED-ROOTS.json').read_bytes())
for name in ['Coding_Agent_Platform_v0.1.0-rc.1', 'Research_Replication_Toolkit_v0.1.0-rc.1']:
    path = str(ROOT / 'outputs' / name)
    if path not in protected['paths']:
        protected['paths'].append(path)
write(APP / 'PROTECTED-ROOTS.json', json.dumps(protected, indent=2) + '\n')
assert not list(APP.rglob('*.pyc'))
files = {p.relative_to(APP).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(APP.rglob('*')) if p.is_file() and p != APP / 'MANIFEST.json'}
manifest = {'schema_version': '1.0.0', 'product': 'coding-agent-platform', 'version': VERSION, 'files': files}
write(APP / 'MANIFEST.json', json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n')
print(json.dumps({'version': VERSION, 'files': len(files), 'manifest_sha256': hashlib.sha256((APP / 'MANIFEST.json').read_bytes()).hexdigest()}))
