"""Bounded proposal, public feedback, independent evaluation and evidence workflow."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path

from component_foundation.runtime import Foundation
from component_foundation.safety import (FoundationError, RunLock, atomic_json, digest,
                                         inside, no_links, read_json, sha256, valid_run_id)
from evaluator import verify_protocol

from . import VERSION
from .patches import apply_patch, make_patch
from .repository import create_demo, read_snapshot
from .storage import (FOUNDATION_PIN, control_lock, inventory, new_destination, now, run_path, seal_run,
                      state_root, verify_inventory, verify_run, write_text)
from .tasks import (PROPOSAL_SCHEMA, assess, build_prompt, evaluate, load_task, validate_proposal)


class Platform:
    def __init__(self, root):
        self.root = Path(root).absolute()
        no_links(self.root)
        manifest = read_json(self.root / 'MANIFEST.json')
        if manifest.get('product') != 'coding-agent-platform' or manifest.get('version') != VERSION:
            raise FoundationError('Incompatible platform package')
        verify_inventory(self.root, manifest['files'], ('MANIFEST.json',))
        self.manifest_sha256 = digest(manifest)
        self.foundation = Foundation(self.root / 'foundation', application_root=self.root)
        if self.foundation.manifest_digest != FOUNDATION_PIN:
            raise FoundationError('Shared foundation dependency differs from the verified pin')
        self.protocol = verify_protocol()
        self.protected = [self.root, *self.foundation.config['protected_roots']]
        self.protected += read_json(self.root / 'PROTECTED-ROOTS.json')['paths']

    def state(self, path, extra=()):
        return state_root(path, [*self.protected, *extra])

    def doctor(self):
        from .provider import provider_info
        info = provider_info()
        return {'product': 'coding-agent-platform', 'version': VERSION, 'status': 'pass',
                'package_manifest_sha256': self.manifest_sha256, 'foundation_manifest_sha256': FOUNDATION_PIN,
                'evaluator': self.protocol, 'provider': info,
                'profile': 'one pure numeric Python function, committed source, no candidate process execution'}

    def demo(self, destination):
        return create_demo(Path(destination), self.root / 'evaluator/repository-template', self.protected)

    def run(self, state, repo, task_arg, checks_arg=None, revision='HEAD', max_calls=2, timeout=120, run_id=None):
        if type(max_calls) is not int or max_calls not in (1, 2) or type(timeout) is not int or not 5 <= timeout <= 180:
            raise FoundationError('Limits: 1–2 provider calls, 5–180 seconds per call')
        repo = Path(repo).absolute()
        state = self.state(state, [repo])
        task, cases = load_task(task_arg, checks_arg)
        original, repository = read_snapshot(repo, revision, task['path'])
        if task.get('original_sha256') and sha256_bytes(original) != task['original_sha256']:
            raise FoundationError('Authored diagnostic source differs from its frozen baseline')
        baseline = evaluate(task, original, cases)
        if not baseline['syntax_allowed'] or not baseline['pass'] or not baseline['fail']:
            raise FoundationError('The baseline must use the supported language and contain both passing and failing private checks')
        run_id = valid_run_id(run_id or ('r' + uuid.uuid4().hex))
        run = state / 'runs' / run_id
        no_links(run)
        run.mkdir(exist_ok=False)
        with RunLock(run / 'run.lock'):
            request = {'schema_version': '1.0.0', 'run_id': run_id, 'created_at': now(), 'product_version': VERSION,
                       'package_manifest_sha256': self.manifest_sha256, 'foundation_manifest_sha256': FOUNDATION_PIN,
                       'repository': repository, 'task_id': task['id'], 'partition': task['partition'],
                       'max_provider_calls': max_calls, 'provider_timeout_seconds': timeout,
                       'prompt_version': '1.0.0', 'tool_policy_version': '1.0.0', 'evaluator_version': '1.0.0'}
            atomic_json(run / 'request.json', request)
            atomic_json(run / 'task-public.json', task)
            atomic_json(run / 'private/checks.json', cases)
            atomic_json(run / 'private/baseline.json', baseline)
            write_text(run / 'snapshot' / task['path'], original)
            atomic_json(run / 'INPUTS.json', {'files': inventory(run, ('run.lock', 'INPUTS.json'))})
            previous, selected, calls = None, None, 0
            try:
                from .provider import ProviderError, propose
                for number in range(1, max_calls + 1):
                    if (run / 'cancel.request.json').exists():
                        return self._terminal(run, 'cancelled', calls, 'Cancellation requested before provider call')
                    attempt = run / f'attempt-{number}'
                    attempt.mkdir()
                    prompt = build_prompt(task, original, previous)
                    write_text(attempt / 'prompt.txt', prompt)
                    # The immutable call intent marks the side-effect boundary. Resume
                    # never reissues it when the remote outcome is unknown.
                    atomic_json(attempt / 'CALL-INTENT.json', {'created_at': now(), 'prompt_sha256': sha256_bytes(prompt)})
                    calls += 1
                    try:
                        response = propose(prompt, PROPOSAL_SCHEMA, attempt, timeout=timeout,
                                           cancel_path=run / 'cancel.request.json')
                    except ProviderError as exc:
                        atomic_json(attempt / 'failure.json', {'code': exc.code, 'message': str(exc)})
                        return self._terminal(run, 'cancelled' if exc.code == 'CANCELLED' else 'provider_failed', calls,
                                              'Provider did not return a usable proposal: ' + exc.code)
                    atomic_json(attempt / 'provider-return.json', response)
                    proposal = response['proposal']
                    atomic_json(attempt / 'proposal.json', proposal)
                    try:
                        candidate = validate_proposal(proposal, task, original)
                        public = evaluate(task, candidate, task['public_examples'])
                        write_text(attempt / 'candidate.py', candidate)
                        atomic_json(attempt / 'public-checks.json', public)
                        previous = {'replacement': candidate, 'public_checks': public}
                        if public['syntax_allowed']:
                            selected = number
                        if public['status'] == 'pass':
                            break
                    except FoundationError as exc:
                        atomic_json(attempt / 'rejected.json', {'reason': str(exc)})
                        previous = {'proposal_rejected': str(exc)}
                if (run / 'cancel.request.json').exists():
                    return self._terminal(run, 'cancelled', calls, 'Cancellation requested before final evaluation')
                if selected is None:
                    return self._terminal(run, 'rejected', calls, 'No valid source proposal within the call budget')
                atomic_json(run / 'SELECTION.json', {'attempt': selected, 'policy': 'first public pass, otherwise latest syntax-valid proposal',
                                                   'uses_private_results': False})
                return self._finish(run, calls)
            except KeyboardInterrupt:
                return self._terminal(run, 'cancelled', calls, 'Operator interrupted the run; remote usage may already have occurred')
            except Exception as exc:
                # Preserve failed attempts. Exception details may originate in external
                # input, so expose a stable category rather than arbitrary logs.
                return self._terminal(run, 'failed', calls, 'Workflow error: ' + type(exc).__name__)

    def _terminal(self, run, status, calls, reason):
        request = read_json(run / 'request.json')
        result = {'schema_version': '1.0.0', 'run_id': request['run_id'], 'status': status,
                  'accepted': False, 'completed_at': now(), 'provider_calls': calls, 'cost': None,
                  'task_id': request['task_id'], 'partition': request['partition'], 'reason': reason,
                  'package_manifest_sha256': request['package_manifest_sha256']}
        return seal_run(run, result)

    def _finish(self, run, calls):
        self._verify_inputs(run)
        task = read_json(run / 'task-public.json')
        selection = read_json(run / 'SELECTION.json')
        number = selection['attempt']
        if type(number) is not int or number not in (1, 2):
            raise FoundationError('Invalid selected attempt')
        attempt = run / f'attempt-{number}'
        original = inside(run / 'snapshot', task['path']).read_text(encoding='utf-8')
        proposal = read_json(attempt / 'proposal.json')
        candidate = validate_proposal(proposal, task, original)
        if (attempt / 'candidate.py').read_bytes() != candidate.encode('utf-8'):
            raise FoundationError('Selected candidate and proposal differ')
        checks = read_json(run / 'private/checks.json')
        evaluation = assess(task, read_json(run / 'private/baseline.json'), evaluate(task, candidate, checks))
        if not (run / 'private/evaluation.json').exists():
            atomic_json(run / 'private/evaluation.json', evaluation)
        elif read_json(run / 'private/evaluation.json') != evaluation:
            raise FoundationError('Existing evaluation differs from replay')
        patch = make_patch(task['path'], original, candidate)
        if apply_patch(task['path'], original, patch) != candidate:
            raise FoundationError('Patch failed independent reconstruction')
        target = run / 'candidate' / task['path']
        for path, text in [(target, candidate), (run / 'change.patch', patch)]:
            if path.exists():
                if path.read_bytes() != text.encode('utf-8'):
                    raise FoundationError('Interrupted output mismatch')
            else:
                write_text(path, text)
        request = read_json(run / 'request.json')
        provider = read_json(attempt / 'provider-return.json')['provider']
        result = {'schema_version': '1.0.0', 'run_id': request['run_id'],
                  'status': 'accepted' if evaluation['accepted'] else 'rejected', 'accepted': evaluation['accepted'],
                  'completed_at': now(), 'task_id': task['id'], 'partition': task['partition'], 'scope': task['scope'],
                  'provider_calls': calls, 'selected_attempt': number, 'provider': provider, 'cost': None,
                  'f2p': evaluation['f2p'], 'p2p': evaluation['p2p'], 'repository': request['repository'],
                  'candidate_sha256': sha256_bytes(candidate), 'patch_sha256': sha256_bytes(patch),
                  'package_manifest_sha256': request['package_manifest_sha256'],
                  'scientific_validation': 'unverified', 'source_repository_modified': False}
        return seal_run(run, result)

    def _verify_inputs(self, run):
        files = read_json(run / 'INPUTS.json')['files']
        for relative, expected in files.items():
            if sha256(inside(run, relative)) != expected:
                raise FoundationError('Frozen run input changed: ' + relative)
        request = read_json(run / 'request.json')
        if request['package_manifest_sha256'] != self.manifest_sha256:
            raise FoundationError('Run belongs to another exact package; use its preserved version')

    def resume(self, state, run_id):
        run = run_path(self.state(state), run_id)
        with RunLock(run / 'run.lock'):
            if (run / 'RECEIPT.json').exists():
                return verify_run(run)
            self._verify_inputs(run)
            calls = sum((run / f'attempt-{n}/CALL-INTENT.json').exists() for n in (1, 2))
            if (run / 'result.json').exists():
                if (run / 'SELECTION.json').exists():
                    return self._finish(run, calls)
                raise FoundationError('Terminal receipt was interrupted before sealing; preserve this run and start a new explicit run. Provider calls will not be repeated.')
            if (run / 'cancel.request.json').exists():
                return self._terminal(run, 'cancelled', calls, 'Cancelled before recovery; provider calls are not repeated')
            if (run / 'SELECTION.json').exists():
                return self._finish(run, calls)
            return self._terminal(run, 'interrupted', calls, 'No frozen selection; provider calls are never repeated by resume. Start an explicit new run if desired.')

    def cancel(self, state, run_id):
        run = run_path(self.state(state), run_id)
        with control_lock(run):
            if (run / 'result.json').exists():
                raise FoundationError('Run is already terminal')
            path = run / 'cancel.request.json'
            if not path.exists():
                atomic_json(path, {'requested_at': now()})
        return {'run_id': run_id, 'status': 'cancellation_requested', 'note': 'Remote usage may already have occurred'}

    def inspect(self, state, run_id):
        run = run_path(self.state(state), run_id)
        result = verify_run(run)
        return {'integrity': 'pass', 'result': result}

    def replay(self, state, run_id):
        run = run_path(self.state(state), run_id)
        result = verify_run(run)
        self._verify_inputs(run)
        if 'selected_attempt' not in result:
            raise FoundationError('Run has no patch to replay')
        task = read_json(run / 'task-public.json')
        original = inside(run / 'snapshot', task['path']).read_text(encoding='utf-8')
        source = apply_patch(task['path'], original, (run / 'change.patch').read_text(encoding='utf-8'))
        evaluation = assess(task, evaluate(task, original, read_json(run / 'private/checks.json')),
                            evaluate(task, source, read_json(run / 'private/checks.json')))
        if sha256_bytes(source) != result['candidate_sha256'] or evaluation != read_json(run / 'private/evaluation.json'):
            raise FoundationError('Replayed patch does not reproduce the recorded evaluation')
        return {'run_id': run_id, 'replay': 'pass', 'accepted': evaluation['accepted'],
                'f2p': evaluation['f2p'], 'p2p': evaluation['p2p'], 'provider_calls': 0}

    def export(self, state, run_id, destination):
        state = self.state(state)
        run = run_path(state, run_id)
        result = verify_run(run)
        self.replay(state, run_id)
        if not result['accepted']:
            raise FoundationError('Only independently accepted patches can be exported')
        destination = new_destination(destination, [*self.protected, state, result['repository']['repository']])
        destination.mkdir()
        task = read_json(run / 'task-public.json')
        write_text(destination / 'change.patch', (run / 'change.patch').read_text(encoding='utf-8'))
        write_text(destination / 'replacement' / task['path'], inside(run / 'candidate', task['path']).read_text(encoding='utf-8'))
        atomic_json(destination / 'RESULT.json', result)
        write_text(destination / 'README.txt', 'Review this patch before applying it to the recorded commit. The platform did not modify your repository.\nPrivate test values and provider prompts are omitted from this export. Full local evidence stays in the run state.\n')
        atomic_json(destination / 'MANIFEST.json', {'schema_version': '1.0.0', 'files': inventory(destination)})
        return {'status': 'exported', 'run_id': run_id, 'directory': str(destination), 'private_cases_included': False}

    def runs(self, state):
        result = []
        for path in sorted((self.state(state) / 'runs').iterdir()):
            no_links(path)
            if not path.is_dir():
                raise FoundationError('Unexpected file in runs directory')
            valid_run_id(path.name)
            if (path / 'RECEIPT.json').exists():
                item = verify_run(path)
                result.append({k: item.get(k) for k in ('run_id', 'task_id', 'status', 'provider_calls', 'partition')})
            else:
                result.append({'run_id': path.name, 'status': 'incomplete; use resume after the worker stops'})
        return result


def sha256_bytes(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()
