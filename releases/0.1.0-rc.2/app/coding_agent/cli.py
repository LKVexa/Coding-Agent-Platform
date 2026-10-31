"""Plain local command-line workflow; JSON output is also suitable for automation."""
import argparse
import json
import os
import sys
from pathlib import Path

from component_foundation.safety import FoundationError
from evaluator import list_public_tasks
from .platform import Platform
from .provider import ProviderError


def main(root):
    parser = argparse.ArgumentParser(description='Coding Agent Platform — propose, independently check and export one bounded Python change.')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor', help='Check package, foundation, evaluator and model login')
    commands.add_parser('tasks', help='List the three authored diagnostic tasks')
    demo = commands.add_parser('demo', help='Create a separate diagnostic Git repository')
    demo.add_argument('--destination', required=True)
    for name in ('run', 'runs', 'inspect', 'replay', 'export', 'resume', 'cancel', 'selftest'):
        p = commands.add_parser(name)
        p.add_argument('--state', default=str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CodingAgentPlatform/state'))
        if name in ('inspect', 'replay', 'export', 'resume', 'cancel'):
            p.add_argument('--run-id', required=True)
        if name == 'export':
            p.add_argument('--destination', required=True)
        if name == 'run':
            p.add_argument('--repo', required=True)
            p.add_argument('--task', required=True, help='Diagnostic ID or custom public task JSON path')
            p.add_argument('--checks', help='Separate private checks JSON for a custom task')
            p.add_argument('--revision', default='HEAD')
            p.add_argument('--max-calls', type=int, default=2)
            p.add_argument('--timeout', type=int, default=120)
            p.add_argument('--run-id', help='Optional stable ID; an existing ID is never rerun')
    args = parser.parse_args()
    try:
        platform = Platform(root)
        if args.command == 'doctor':
            output = platform.doctor()
        elif args.command == 'tasks':
            output = {'tasks': list_public_tasks(), 'scope': 'authored diagnostics, not a research benchmark'}
        elif args.command == 'demo':
            output = platform.demo(args.destination)
        elif args.command == 'run':
            output = platform.run(args.state, args.repo, args.task, args.checks, args.revision,
                                  args.max_calls, args.timeout, args.run_id)
        elif args.command == 'runs':
            output = {'runs': platform.runs(args.state)}
        elif args.command == 'export':
            output = platform.export(args.state, args.run_id, args.destination)
        elif args.command == 'selftest':
            state = platform.state(args.state)
            results = [platform.foundation.run(state / 'foundation-diagnostics', 'D0007/C0322-01', case=case)
                       for case in ('correct', 'regression')]
            output = {'scope': 'original authored foundation regression diagnostics', 'runs': results}
        else:
            output = getattr(platform, args.command)(args.state, args.run_id)
        print(json.dumps(output, ensure_ascii=True, allow_nan=False, indent=2))
        if isinstance(output, dict) and output.get('status') in ('rejected', 'failed', 'provider_failed', 'cancelled', 'interrupted'):
            return 3
        return 0
    except (FoundationError, ProviderError, ValueError, OSError, KeyError, TypeError) as exc:
        message = str(exc) if isinstance(exc, (FoundationError, ProviderError, FileExistsError)) else type(exc).__name__ + ': invalid or unavailable input'
        error = {'status': 'error', 'message': message}
        if isinstance(exc, ProviderError):
            error['code'] = exc.code
        print(json.dumps(error, ensure_ascii=True), file=sys.stderr)
        return 2
