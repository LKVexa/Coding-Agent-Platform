"""Verify the preserved release without importing or executing its code."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "release"
manifest = json.loads((root / "RELEASE-MANIFEST.json").read_bytes())
expected = manifest["files"]
actual = set()
problems = []
for path in root.rglob("*"):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        problems.append("link: " + str(path.relative_to(root)))
    elif path.is_file():
        name = path.relative_to(root).as_posix()
        actual.add(name)
        if name in expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            problems.append("changed: " + name)
for name in sorted(set(expected) - actual):
    problems.append("missing: " + name)
for name in sorted(actual - set(expected) - {"RELEASE-MANIFEST.json"}):
    problems.append("unexpected: " + name)
publication = json.loads((root.parent / "PUBLICATION.json").read_bytes())
if hashlib.sha256((root / "RELEASE-MANIFEST.json").read_bytes()).hexdigest() != publication["release_manifest_sha256"]:
    problems.append("release manifest differs from publication pin")
if problems:
    raise SystemExit("Integrity check failed:\n" + "\n".join(problems))
print("PASS: " + str(len(actual)) + " preserved release files verified")
