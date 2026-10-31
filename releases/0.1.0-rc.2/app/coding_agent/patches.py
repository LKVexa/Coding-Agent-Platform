"""Single-file unified patches, constrained to an explicit source path."""
import difflib
import re
from component_foundation.safety import FoundationError


def make_patch(path, before, after):
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                        fromfile='a/' + path, tofile='b/' + path))


def apply_patch(path, before, patch):
    if len(patch.encode('utf-8')) > 65536:
        raise FoundationError('Patch size limit exceeded')
    lines = patch.splitlines(keepends=True)
    if lines[:2] != ['--- a/' + path + '\n', '+++ b/' + path + '\n']:
        raise FoundationError('Patch target mismatch')
    original = before.splitlines(keepends=True)
    output, cursor, index = [], 0, 2
    while index < len(lines):
        match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', lines[index])
        if not match:
            raise FoundationError('Unsupported patch hunk')
        old_start, old_count, new_start, new_count = [int(x) if x is not None else 1 for x in match.groups()]
        start = old_start - (1 if old_count else 0)
        if start < cursor or start > len(original):
            raise FoundationError('Patch hunk outside source')
        output.extend(original[cursor:start]); cursor = start
        if len(output) != new_start - (1 if new_count else 0):
            raise FoundationError('Patch new line position mismatch')
        index += 1; removed = added = 0
        while index < len(lines) and not lines[index].startswith('@@ '):
            line = lines[index]
            if not line or line[0] not in ' +-':
                raise FoundationError('Unsupported patch line')
            if line[0] in ' -':
                if cursor >= len(original) or original[cursor] != line[1:]:
                    raise FoundationError('Patch context does not match baseline')
                cursor += 1; removed += 1
            if line[0] in ' +':
                output.append(line[1:]); added += 1
            index += 1
        if removed != old_count or added != new_count:
            raise FoundationError('Patch hunk length mismatch')
    output.extend(original[cursor:])
    result = ''.join(output)
    if not result or len(result.encode('utf-8')) > 16384:
        raise FoundationError('Replayed source outside size limit')
    return result
