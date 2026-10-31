"""Read committed Git blobs without checking out or executing repository content."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from component_foundation.safety import FoundationError, inside, no_links, sha256


def git_executable():
    candidate = os.environ.get('CODING_AGENT_GIT') or shutil.which('git')
    if not candidate:
        candidate = str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe')
    path = Path(candidate).absolute()
    no_links(path)
    if not path.is_file():
        raise FoundationError('Git is required. Set CODING_AGENT_GIT to its executable.')
    return path


def git_call(repo, args, limit=1024*1024):
    """No shell, network, checkout filters, hooks, pagers or repository programs."""
    exe = git_executable()
    env = {k: v for k, v in os.environ.items() if k.upper() in
           {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP', 'USERPROFILE', 'HOME'}}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1',
               GIT_PAGER='cat', GIT_ATTR_NOSYSTEM='1', GIT_CONFIG_COUNT='0')
    argv = [str(exe), '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull,
            '-c', 'protocol.allow=never', '-c', 'core.pager=cat', '-C', str(repo), *args]
    # All callers use bounded metadata or explicitly size-checked blobs. Tree output
    # uses a size-limited temporary stream rather than accumulating arbitrary stdout.
    import tempfile
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(argv, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                env=env, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        import time
        end = time.monotonic() + 15
        while proc.poll() is None:
            if time.monotonic() > end or os.fstat(out.fileno()).st_size > limit or os.fstat(err.fileno()).st_size > 65536:
                proc.kill(); proc.wait()
                raise FoundationError('Git read exceeded its time or output limit')
            time.sleep(.02)
        if proc.returncode:
            raise FoundationError('Git could not read the requested committed repository')
        if os.fstat(out.fileno()).st_size > limit:
            raise FoundationError('Git output exceeds limit')
        out.seek(0)
        return out.read(limit + 1)


def read_snapshot(repo: Path, revision: str, relative: str):
    repo = repo.absolute()
    no_links(repo)
    if not repo.is_dir():
        raise FoundationError('Repository directory does not exist')
    # Linked worktrees and alternate object stores are deliberately unsupported.
    gitdir = repo / '.git'
    no_links(gitdir)
    if not gitdir.is_dir():
        raise FoundationError('Use a normal local Git repository, with a .git directory')
    for item in gitdir.rglob('*'):
        no_links(item)
    if any((gitdir / relative).exists() for relative in
           ('commondir', 'gitdir', 'objects/info/alternates', 'objects/info/http-alternates', 'info/grafts')):
        raise FoundationError('Git linked worktrees, alternate object stores and grafts are unsupported')
    if not re.fullmatch(r'HEAD|[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', revision):
        raise FoundationError('Revision must be HEAD or a full commit hash')
    if not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*\.py', relative):
        raise FoundationError('Source path must be a simple relative .py path')
    inside(repo, relative)
    commit = git_call(repo, ['rev-parse', '--verify', revision + '^{commit}'], 256).decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
        raise FoundationError('Invalid resolved Git commit')
    tree = git_call(repo, ['ls-tree', '-z', commit, '--', relative], 2048)
    records = [x for x in tree.split(b'\0') if x]
    if len(records) != 1:
        raise FoundationError('The allowed source file must exist in the committed revision')
    metadata, name = records[0].split(b'\t', 1)
    mode, kind, oid = metadata.decode('ascii').split()
    if mode not in ('100644', '100755') or kind != 'blob' or name.decode('utf-8') != relative:
        raise FoundationError('Only regular committed source blobs are supported')
    size = int(git_call(repo, ['cat-file', '-s', oid], 64).strip())
    if not 1 <= size <= 16384:
        raise FoundationError('Source must be between 1 and 16,384 bytes')
    data = git_call(repo, ['cat-file', 'blob', oid], 16384)
    if len(data) != size:
        raise FoundationError('Git source size mismatch')
    try:
        source = data.decode('utf-8')
    except UnicodeError as exc:
        raise FoundationError('Source must be UTF-8') from exc
    if '\r' in source or '\0' in source or not source.endswith('\n'):
        raise FoundationError('Source must use LF newlines and end with a newline')
    return source, {'repository': str(repo.resolve()), 'revision': commit, 'requested_revision': revision,
                    'path': relative, 'blob_id': oid, 'mode': mode, 'source_sha256': hashlib.sha256(data).hexdigest(),
                    'git_sha256': sha256(git_executable()), 'working_tree_policy': 'committed-blob-only; working tree untouched'}


def create_demo(destination: Path, template: Path, protected):
    from .storage import new_destination
    destination = new_destination(destination, protected)
    destination.mkdir()
    for path in template.rglob('*'):
        no_links(path)
        if path.is_file():
            target = destination / path.relative_to(template)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    git_call(destination, ['init', '--quiet'])
    git_call(destination, ['-c', 'core.autocrlf=false', 'add', '--', 'src', 'README.md'])
    git_call(destination, ['-c', 'user.name=Coding Agent Demo', '-c', 'user.email=demo@localhost',
                           '-c', 'commit.gpgSign=false', '-c', 'core.autocrlf=false', 'commit', '--quiet', '-m', 'Frozen authored diagnostic tasks'])
    return {'status': 'created', 'repository': str(destination), 'scope': 'authored diagnostic repository'}
