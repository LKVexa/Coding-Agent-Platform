"""Pinned capability execution and append-only evidence storage."""
from __future__ import annotations

import datetime as dt
import importlib.metadata
import os
import platform
import sys
import uuid
from collections import Counter
from pathlib import Path

from .contracts import validate
from .process import execute
from .safety import (FoundationError, RunLock, atomic_json, canonical, digest,
                     inside, no_links, parse_json, prepare_state, read_json,
                     sha256, valid_run_id)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sidecar(path, kind):
    sha = {'type':'string','pattern':'^[0-9a-f]{64}$'}
    shapes = {
        'request-hash': {'type':'object','required':['sha256'],'properties':{'sha256':sha},'additionalProperties':False},
        'receipt': {'type':'object','required':['schema_version','result_sha256','request_sha256'],
                    'properties':{'schema_version':{'const':'1.0.0'},'result_sha256':sha,'request_sha256':sha},'additionalProperties':False},
        'resume': {'type':'object','required':['status','created_at'],
                   'properties':{'status':{'enum':['reserved','linked']},'created_at':{'type':'string'},
                                 'child_run_id':{'type':'string','pattern':'^[a-z0-9][a-z0-9_-]{0,63}$'}},'additionalProperties':False}}
    value = read_json(path)
    validate(value, shapes[kind])
    if kind=='resume' and (value['status']=='linked') != ('child_run_id' in value):
        raise FoundationError('Resume marker status/identity mismatch')
    return value


class Foundation:
    def __init__(self, root: Path, application_root: Path | None = None):
        self.root = root.absolute()
        self.application_root = application_root.absolute() if application_root else self.root
        no_links(self.root)
        self.manifest = read_json(self.root / 'MANIFEST.json')
        if not isinstance(self.manifest, dict) or self.manifest.get('product') != 'component-foundation' or self.manifest.get('schema_version') != '1.0.0':
            raise FoundationError('Unsupported foundation manifest')
        self.manifest_digest = digest(self.manifest)
        self.verify_package()
        self.config = read_json(self.root / 'CAPABILITIES.json')
        self.capabilities = self.config['capabilities']
        self.schemas = {p.stem: read_json(p) for p in (self.root / 'schemas').glob('*.json')}
        self.components = []
        ids = set()
        path = self.root / 'registry' / 'components.jsonl'
        with path.open('rb') as stream:
            for raw in stream:
                if not raw.strip():
                    continue
                obj = parse_json(raw, limit=4*1024*1024)
                validate(obj, self.schemas['component'])
                if obj['component_id'] in ids:
                    raise FoundationError('Duplicate component identity')
                ids.add(obj['component_id'])
                self.components.append(obj)
        self.by_id = {x['component_id']: x for x in self.components}
        for component_id in self.capabilities:
            if component_id not in self.by_id:
                raise FoundationError('Capability absent from catalog')

    def verify_package(self):
        records = self.manifest.get('files')
        if not isinstance(records, dict) or not records:
            raise FoundationError('Empty package inventory')
        for relative, expected in records.items():
            path = inside(self.root, relative)
            if not path.is_file() or sha256(path) != expected:
                raise FoundationError('Package integrity mismatch: ' + relative)
        # Reject shadow modules and hidden injected content as well as changed files.
        actual = set()
        for path in self.root.rglob('*'):
            no_links(path)
            if path.is_file():
                relative = path.relative_to(self.root).as_posix()
                if relative == 'MANIFEST.json':
                    continue
                actual.add(relative)
        if actual != set(records):
            raise FoundationError('Package contains unmanifested or missing files')
        return {'status': 'pass', 'file_count': len(records), 'manifest_sha256': digest(self.manifest)}

    def doctor(self):
        checks = []
        def record(key, expected, actual):
            checks.append({'id': key, 'status': 'pass' if expected == actual else 'fail', 'expected': expected, 'actual': actual})
        record('platform', 'Windows', platform.system())
        record('python_version', self.config['runtime']['python'], platform.python_version())
        try:
            numpy_version = importlib.metadata.version('numpy')
        except importlib.metadata.PackageNotFoundError:
            numpy_version = None
        record('numpy_version', self.config['runtime']['numpy'], numpy_version)
        record('foundation_integrity', 'pass', self.verify_package()['status'])
        return {'schema_version': '1.0.0', 'status': 'pass' if all(c['status']=='pass' for c in checks) else 'fail',
                'checks': checks, 'python_executable': sys.executable, 'python_sha256': sha256(Path(sys.executable)),
                'platform': platform.platform(), 'foundation_version': self.manifest['version'],
                'foundation_manifest_sha256': self.manifest_digest,
                'note': 'Windows .NET execution is verified by the D0007 run; no arbitrary plugin execution is supported.'}

    def state(self, root):
        return prepare_state(Path(root), getattr(self, 'application_root', self.root), self.config['protected_roots'])

    def catalog(self, query=None, executable_only=False, collection=None):
        result = []
        for source in self.components:
            if query and query.lower() not in (source['component_id'] + ' ' + source.get('maturity', '')).lower():
                continue
            if collection and source['collection'] != collection:
                continue
            enabled = source['component_id'] in self.capabilities
            if executable_only and not enabled:
                continue
            item = {k: source.get(k) for k in ('component_id','delivery_id','pair_id','collection','role','original_status','original_g2','maturity','native_check_counts','acceptance_check_counts','exclusion_reason')}
            item.update({'executable': enabled, 'scientific_validation': 'unverified',
                         'cases': self.capabilities[source['component_id']]['cases'] if enabled else [],
                         'capability_scope': 'bounded fixture diagnostics' if enabled else 'catalog only'})
            if enabled:
                item['exclusion_reason'] = None
            result.append(item)
        return result

    def totals(self):
        core = [r for r in self.components if r['role']=='core']
        supporting = [r for r in self.components if r['role']!='core']
        return {'core_count': len(core), 'core_original_status': dict(Counter(r['original_status'] for r in core)),
                'supporting_count': len(supporting), 'supporting_original_status': dict(Counter(r['original_status'] for r in supporting)),
                'enabled_fixture_capabilities': len(self.capabilities),
                'original_gates': {r['delivery_id']: r['original_g2'] for r in core}}

    def _command(self, component_id, case):
        if component_id not in self.capabilities:
            reason = self.by_id.get(component_id, {}).get('exclusion_reason', 'unknown or unsupported component')
            raise FoundationError('Component is not executable: ' + str(reason))
        spec = self.capabilities[component_id]
        if case not in spec['cases']:
            raise FoundationError('Unsupported case for selected component')
        entry = inside(self.root, spec['entrypoint'])
        if spec['runtime']=='python':
            argv = [sys.executable, '-I', '-B', str(entry), '--case', case]
        elif spec['runtime']=='dotnet-framework':
            argv = [str(entry), '--component', component_id, '--case', case]
        else:
            raise FoundationError('Unsupported adapter runtime')
        return argv, spec

    def run(self, state_root, component_id, case=None, timeout=30, parent_run_id=None):
        self.verify_package()
        doctor = self.doctor()
        if doctor['status'] != 'pass':
            raise FoundationError('Required runtime profile is unavailable; run doctor')
        spec = self.capabilities.get(component_id)
        if spec is None:
            self._command(component_id, case)
        case = case or spec['default_case']
        argv, spec = self._command(component_id, case)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.05 <= timeout <= 60:
            raise FoundationError('Timeout must be between 0.05 and 60 seconds')
        state = self.state(state_root)
        run_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S').lower() + '-' + uuid.uuid4().hex[:12]
        run_dir = inside(state, 'runs/' + run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        request = {'schema_version': '1.0.0', 'run_id': run_id, 'parent_run_id': parent_run_id,
                   'component_id': component_id, 'case': case, 'created_at': now(),
                   'foundation_version': self.manifest['version'], 'foundation_manifest_sha256': self.manifest_digest,
                   'timeout_seconds': timeout, 'python_sha256': doctor['python_sha256'],
                   'baseline_sha256': spec['baseline_sha256'][case]}
        validate(request, self.schemas['request'])
        with RunLock(run_dir / 'active.lock'):
            atomic_json(run_dir / 'request.json', request)
            atomic_json(run_dir / 'request.sha256.json', {'sha256': sha256(run_dir/'request.json')})
            result = {'schema_version': '1.0.0', 'run_id': run_id, 'component_id': component_id,
                      'case': case, 'request_sha256': sha256(run_dir/'request.json'),
                      'foundation_manifest_sha256': self.manifest_digest, 'started_at': now(),
                      'execution': 'fail', 'verification': 'unverified', 'scientific_validation': 'unverified',
                      'scope': 'authored_fixture', 'checks': [], 'argv': argv, 'artifacts': {}}
            try:
                proc = execute(argv, run_dir, timeout=timeout)
                for name in ('stdout', 'stderr'):
                    target = run_dir / (name + '.log')
                    target.write_bytes(proc[name])
                    result['artifacts'][target.name] = sha256(target)
                result['process'] = {k:v for k,v in proc.items() if k not in ('stdout','stderr')}
                if proc['outcome'] != 'completed' or proc['exit_code'] != 0:
                    raise FoundationError('Adapter process ' + proc['outcome'] + ', exit ' + str(proc['exit_code']))
                payload = parse_json(proc['stdout'], limit=1024*1024)
                validate(payload, self.schemas['adapter-result'])
                if payload['component_id'] != component_id or payload['scope'] != 'authored_fixture':
                    raise FoundationError('Adapter identity or scope mismatch')
                ids = [c['id'] for c in payload['checks']]
                if len(ids) != len(set(ids)) or not ids:
                    raise FoundationError('Adapter checks are empty or duplicated')
                atomic_json(run_dir/'adapter-result.json', payload)
                result['artifacts']['adapter-result.json'] = sha256(run_dir/'adapter-result.json')
                comparison = digest(payload) == spec['baseline_sha256'][case]
                result['checks'] = payload['checks'] + [{'id': 'pinned_baseline_match', 'status': 'pass' if comparison else 'fail', 'expected': spec['baseline_sha256'][case], 'actual': digest(payload)}]
                result['execution'] = payload['execution']
                result['verification'] = 'pass' if payload['execution']=='pass' and all(c['status']=='pass' for c in result['checks']) else 'fail'
                result['candidate_accepted'] = payload.get('candidate_accepted', payload.get('records', {}).get('candidate_accepted'))
            except (FoundationError, OSError, ValueError, KeyError) as exc:
                result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
                result['verification'] = 'fail'
            except KeyboardInterrupt:
                result['error'] = {'type': 'Cancelled', 'message': 'Operator cancelled run'}
                result['verification'] = 'fail'
            result['finished_at'] = now()
            validate(result, self.schemas['run-result'])
            atomic_json(run_dir/'result.json', result)
            atomic_json(run_dir/'receipt.json', {'schema_version': '1.0.0', 'result_sha256': sha256(run_dir/'result.json'),
                                               'request_sha256': sha256(run_dir/'request.json')})
        return result

    def verify_run(self, state_root, run_id):
        state = self.state(state_root)
        run_dir = inside(state, 'runs/' + valid_run_id(run_id))
        request = read_json(run_dir/'request.json')
        validate(request, self.schemas['request'])
        if request['run_id'] != run_id:
            raise FoundationError('Run identity mismatch')
        if request['foundation_manifest_sha256'] != self.manifest_digest:
            raise FoundationError('Run belongs to a different foundation version or content')
        if not (run_dir/'request.sha256.json').exists():
            with RunLock(run_dir/'active.lock'):
                pass
            return {'run_id': run_id, 'integrity': 'incomplete', 'state': 'interrupted_request', 'request': request}
        pinned = sidecar(run_dir/'request.sha256.json', 'request-hash')
        if sha256(run_dir/'request.json') != pinned['sha256']:
            raise FoundationError('Run request integrity mismatch')
        if not (run_dir/'result.json').exists():
            with RunLock(run_dir/'active.lock'):
                pass
            return {'run_id': run_id, 'integrity': 'incomplete', 'state': 'interrupted', 'request': request}
        if not (run_dir/'receipt.json').exists():
            with RunLock(run_dir/'active.lock'):
                pass
            return {'run_id': run_id, 'integrity': 'incomplete', 'state': 'interrupted_commit', 'request': request}
        receipt = sidecar(run_dir/'receipt.json', 'receipt')
        if receipt['request_sha256'] != sha256(run_dir/'request.json') or receipt['result_sha256'] != sha256(run_dir/'result.json'):
            raise FoundationError('Run receipt integrity mismatch')
        result = read_json(run_dir/'result.json')
        validate(result, self.schemas['run-result'])
        if result['run_id'] != run_id or result['request_sha256'] != receipt['request_sha256']:
            raise FoundationError('Run result identity mismatch')
        for relative, expected in result['artifacts'].items():
            if sha256(inside(run_dir, relative)) != expected:
                raise FoundationError('Run artifact integrity mismatch: ' + relative)
        return {'run_id': run_id, 'integrity': 'pass', 'state': 'completed', 'request': request, 'result': result}

    def resume(self, state_root, run_id):
        state = self.state(state_root)
        parent = inside(state, 'runs/' + valid_run_id(run_id))
        with RunLock(parent/'active.lock'):
            # Lock is already held here; verify the immutable request directly.
            request = read_json(parent/'request.json')
            validate(request, self.schemas['request'])
            if request['run_id'] != run_id:
                raise FoundationError('Resume request integrity mismatch')
            if (parent/'request.sha256.json').exists():
                if sha256(parent/'request.json') != sidecar(parent/'request.sha256.json', 'request-hash')['sha256']:
                    raise FoundationError('Resume request integrity mismatch')
            elif not (parent/'recovery.json').exists():
                atomic_json(parent/'recovery.json', {'reason':'request commit interrupted; new attempt will re-execute pinned read-only fixture',
                                                   'observed_request_sha256':sha256(parent/'request.json'),'created_at':now()})
            if request['foundation_manifest_sha256'] != self.manifest_digest or request['python_sha256'] != sha256(Path(sys.executable)):
                raise FoundationError('Resume inputs/runtime changed; start a new explicit run')
            if (parent/'result.json').exists() and (parent/'receipt.json').exists():
                receipt = sidecar(parent/'receipt.json', 'receipt')
                if receipt['result_sha256'] != sha256(parent/'result.json'):
                    raise FoundationError('Resume result integrity mismatch')
                previous = read_json(parent/'result.json')
                validate(previous, self.schemas['run-result'])
                if previous.get('verification') == 'pass':
                    raise FoundationError('Completed passing runs are immutable; use run or fresh verification')
            marker = parent/'resume.json'
            def child_identity(child_id):
                child_path = inside(state, 'runs/' + valid_run_id(child_id))
                child_request = read_json(child_path/'request.json')
                validate(child_request, self.schemas['request'])
                if child_request['run_id'] != child_id or child_request.get('parent_run_id') != run_id:
                    raise FoundationError('Resume child identity mismatch')
                for field in ('component_id','case','foundation_manifest_sha256','python_sha256','baseline_sha256'):
                    if child_request[field] != request[field]:
                        raise FoundationError('Resume child profile mismatch')
                if (child_path/'request.sha256.json').exists():
                    if sha256(child_path/'request.json') != sidecar(child_path/'request.sha256.json', 'request-hash')['sha256']:
                        raise FoundationError('Resume child request integrity mismatch')
                return child_request
            if marker.exists():
                data = sidecar(marker, 'resume')
                if data.get('child_run_id'):
                    child_identity(data['child_run_id'])
                    return {'resume_reused': True, 'run_id': data['child_run_id'], 'parent_run_id': run_id}
                # Recover a crash between child creation and writing its parent link.
                children = []
                for item in (state/'runs').iterdir():
                    req_path = item/'request.json'
                    if item.name == run_id or not req_path.is_file():
                        continue
                    child_request = read_json(req_path)
                    if child_request.get('parent_run_id') == run_id:
                        child_identity(item.name)
                        children.append(item.name)
                if len(children) > 1:
                    raise FoundationError('Multiple resume children require investigation')
                if children:
                    atomic_json(marker, {'status':'linked','child_run_id':children[0],'created_at':now()}, replace=True)
                    return {'resume_reused':True,'run_id':children[0],'parent_run_id':run_id}
            else:
                atomic_json(marker, {'status': 'reserved', 'created_at': now()})
            child = self.run(state, request['component_id'], request['case'], request['timeout_seconds'], parent_run_id=run_id)
            # Resume marker is coordination metadata; run requests/results remain immutable.
            atomic_json(marker, {'status': 'linked', 'child_run_id': child['run_id'], 'created_at': now()}, replace=True)
            return child

    def runs(self, state_root):
        state = self.state(state_root)
        rows = []
        directory = state/'runs'
        if not directory.exists():
            return rows
        for path in sorted(directory.iterdir()):
            try:
                verified = self.verify_run(state, path.name)
                rows.append(verified)
            except (FoundationError, OSError, KeyError) as exc:
                rows.append({'run_id': path.name, 'integrity': 'fail', 'error': str(exc)})
        return rows
