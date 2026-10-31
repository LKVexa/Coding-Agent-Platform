"""Bounded parsing, path validation and atomic evidence writes (stdlib only)."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from pathlib import Path


class FoundationError(Exception):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(items):
    obj = {}
    for key, value in items:
        if key in obj:
            raise FoundationError('Duplicate JSON key: ' + str(key))
        obj[key] = value
    return obj


def parse_json(raw: bytes, limit=4 * 1024 * 1024):
    if len(raw) > limit:
        raise FoundationError('JSON exceeds size limit')
    try:
        obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(FoundationError('Non-finite JSON number')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise FoundationError('Invalid JSON: ' + str(exc)) from exc
    def check_depth(v, depth=0):
        if depth > 40:
            raise FoundationError('JSON exceeds nesting limit')
        if isinstance(v, float) and not math.isfinite(v):
            raise FoundationError('Non-finite JSON number')
        if isinstance(v, dict):
            for item in v.values():
                check_depth(item, depth + 1)
        elif isinstance(v, list):
            for item in v:
                check_depth(item, depth + 1)
    check_depth(obj)
    return obj


def read_json(path: Path, limit=4 * 1024 * 1024):
    no_links(path)
    if path.stat().st_size > limit:
        raise FoundationError('JSON exceeds size limit: ' + path.name)
    return parse_json(path.read_bytes(), limit)


def no_links(path: Path):
    path = path.absolute()
    for part in [path, *path.parents]:
        try:
            item = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(item.st_mode) or getattr(item, 'st_file_attributes', 0) & 0x400:
            raise FoundationError('Linked/reparse paths are not supported: ' + str(part))


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise FoundationError('Invalid relative path')
    rel = Path(relative)
    if rel.is_absolute() or any(p in ('..', '.') for p in relative.split('/')):
        raise FoundationError('Path traversal rejected')
    target = root / rel
    no_links(target)
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise FoundationError('Path escapes declared root') from exc
    return target


def prepare_state(path: Path, package: Path, protected_roots: list[str]) -> Path:
    path = path.absolute()
    no_links(path)
    resolved = path.resolve()
    for protected in [package, *[Path(p) for p in protected_roots]]:
        try:
            resolved.relative_to(protected.resolve())
        except ValueError:
            continue
        raise FoundationError('State directory is within a protected source/package root')
    path.mkdir(parents=True, exist_ok=True)
    no_links(path)
    return path.resolve()


def atomic_json(path: Path, value, replace=False):
    no_links(path)
    data = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix='.pending-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if not replace and path.exists():
            raise FoundationError('Immutable artifact already exists: ' + path.name)
        if replace:
            os.replace(tmp_name, path)
        else:
            # Windows rename fails if destination already exists, avoiding replacement.
            if os.name == 'nt':
                os.rename(tmp_name, path)
            else:
                os.link(tmp_name, path)
                os.unlink(tmp_name)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def valid_run_id(value: str):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', value):
        raise FoundationError('Invalid run identifier')
    return value


class RunLock:
    """OS advisory byte lock released automatically after process death."""
    def __init__(self, path: Path):
        self.path = path
        self.stream = None

    def __enter__(self):
        no_links(self.path)
        self.stream = self.path.open('a+b')
        if self.path.stat().st_size == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            self.stream = None
            raise FoundationError('Run is still active or is being resumed') from exc
        return self

    def __exit__(self, *args):
        if self.stream:
            self.stream.close()

