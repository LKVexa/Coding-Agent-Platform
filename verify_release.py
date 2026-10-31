"""Verify current and preserved releases without running application code."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parent
publication = json.loads((base / 'PUBLICATION.json').read_bytes())
specs = [
    {'path': publication['release_path'], 'release_manifest_sha256': publication['release_manifest_sha256']},
    publication['previous_release'],
]
for spec in specs:
    root = base / spec['path']
    if not root.resolve().is_relative_to(base):
        raise SystemExit('Release path escapes repository')
    raw = (root / 'RELEASE-MANIFEST.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != spec['release_manifest_sha256']:
        raise SystemExit('Release manifest changed: ' + spec['path'])
    expected = json.loads(raw)['files']
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise SystemExit('Linked release path')
        if path.is_file():
            name = path.relative_to(root).as_posix()
            actual.add(name)
            if name in expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
                raise SystemExit('Changed release file: ' + name)
    if actual != set(expected) | {'RELEASE-MANIFEST.json'}:
        raise SystemExit('Release file inventory differs: ' + spec['path'])
    print('PASS: ' + spec['path'] + ' (' + str(len(actual)) + ' files)')
