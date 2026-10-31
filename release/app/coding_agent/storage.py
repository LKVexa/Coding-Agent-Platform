"""Integrity and append-only local run storage using the pinned foundation."""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import time
from contextlib import contextmanager
from pathlib import Path

from component_foundation.safety import (FoundationError, RunLock, atomic_json, digest, inside,
                                         no_links, read_json, sha256, valid_run_id)

FOUNDATION_PIN = 'e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_text(path, value):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value.encode('utf-8')
    with path.open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())


def overlap(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def new_destination(path, protected):
    path = Path(path).absolute()
    no_links(path)
    if path.exists():
        raise FoundationError('Destination must be a new directory')
    for root in protected:
        if overlap(path, root):
            raise FoundationError('Destination overlaps a protected source, package or repository')
    if not path.parent.is_dir():
        raise FoundationError('Destination parent directory must already exist')
    return path


def inventory(root, exclude=()):
    files = {}
    for path in sorted(root.rglob('*')):
        no_links(path)
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                files[relative] = sha256(path)
    return files


def verify_inventory(root, manifest, exclude=()):
    if not isinstance(manifest, dict) or not manifest:
        raise FoundationError('Missing file inventory')
    for relative, expected in manifest.items():
        path = inside(root, relative)
        if not path.is_file() or sha256(path) != expected:
            raise FoundationError('Integrity mismatch: ' + relative)
    if set(inventory(root, exclude)) != set(manifest):
        raise FoundationError('Unexpected or missing files')


def state_root(path, protected):
    path = Path(path).absolute()
    no_links(path)
    for root in protected:
        if overlap(path, root):
            raise FoundationError('Run state overlaps a protected source, package or repository')
    marker = path / 'STATE.json'
    if path.exists() and not marker.exists() and any(path.iterdir()):
        raise FoundationError('State directory contains unrelated files')
    path.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        atomic_json(marker, {'product': 'coding-agent-platform', 'schema_version': '1.0.0'})
    if read_json(marker) != {'product': 'coding-agent-platform', 'schema_version': '1.0.0'}:
        raise FoundationError('Incompatible state directory')
    (path / 'runs').mkdir(exist_ok=True)
    no_links(path / 'runs')
    return path.resolve()


def run_path(state, run_id):
    valid_run_id(run_id)
    path = inside(state, 'runs/' + run_id)
    if not path.is_dir():
        raise FoundationError('Unknown run')
    return path


@contextmanager
def control_lock(run):
    """Wait briefly for cancellation/finalization, without relaxing the run lock."""
    deadline = time.monotonic() + 10
    while True:
        lock = RunLock(run / 'control.lock')
        try:
            lock.__enter__()
            break
        except FoundationError as exc:
            if 'Run is still active or is being resumed' not in str(exc) or time.monotonic() >= deadline:
                raise
            time.sleep(.02)
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


def seal_run(run, result):
    with control_lock(run):
        if (run / 'cancel.request.json').exists() and result['status'] in ('accepted', 'rejected'):
            result.update(status='cancelled', accepted=False, reason='Cancellation requested before evidence was sealed')
        if (run / 'result.json').exists():
            previous = read_json(run / 'result.json')
            result['completed_at'] = previous.get('completed_at')
            if result != previous:
                raise FoundationError('Interrupted result does not match independent recovery')
        else:
            atomic_json(run / 'result.json', result)
        files = inventory(run, exclude=('run.lock', 'control.lock', 'RECEIPT.json'))
        atomic_json(run / 'RECEIPT.json', {'schema_version': '1.0.0', 'files': files, 'files_sha256': digest(files)})
    return result


def verify_run(run):
    receipt = read_json(run / 'RECEIPT.json')
    if receipt.get('schema_version') != '1.0.0' or digest(receipt.get('files')) != receipt.get('files_sha256'):
        raise FoundationError('Invalid run receipt')
    verify_inventory(run, receipt['files'], ('run.lock', 'control.lock', 'RECEIPT.json'))
    return read_json(run / 'result.json')
