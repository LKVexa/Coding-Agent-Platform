"""Bounded numeric Python AST evaluation; candidate code is never exec'd or imported.

This deliberately small language profile supports the released demonstration
tasks. It is not a general Python runtime or arbitrary repository test runner.
"""
from __future__ import annotations

import ast
import hashlib
import math
from dataclasses import dataclass

VERSION = "1.0.0"
MAX_SOURCE_BYTES = 16384
MAX_NODES = 256
MAX_DEPTH = 24
MAX_STEPS = 512
MAX_ABS_VALUE = 10**12
MAX_NAME_LENGTH = 64
ALLOWED_CALLS = frozenset({"min", "max", "abs", "int"})
ALLOWED_TYPES = frozenset({"int", "float", "bool"})
NODE_TYPES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign,
    ast.If, ast.Expr, ast.Pass, ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp,
    ast.BoolOp, ast.Compare, ast.IfExp, ast.Call, ast.Load, ast.Store,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.UAdd,
    ast.USub, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt,
    ast.LtE, ast.Gt, ast.GtE,
)


class EvaluationRefused(ValueError):
    """The candidate exceeds or violates the explicitly supported language."""


class CandidateRuntimeError(ValueError):
    """A permitted expression failed for a declared test input."""


def numeric(value):
    if type(value) not in (int, float, bool):
        raise CandidateRuntimeError("Only finite numeric and boolean values are supported")
    if isinstance(value, float) and not math.isfinite(value):
        raise CandidateRuntimeError("Non-finite number")
    if abs(value) > MAX_ABS_VALUE:
        raise CandidateRuntimeError("Numeric magnitude exceeds the profile limit")
    return value


def safe_name(name):
    if not isinstance(name, str) or not name.isidentifier() or len(name) > MAX_NAME_LENGTH or name.startswith('_'):
        raise EvaluationRefused("Unsupported identifier")


def compile_source(source: str, function_name: str, parameter_names: list[str]):
    """Validate syntax into an AST. This function does not compile executable code."""
    if not isinstance(source, str) or len(source.encode('utf-8')) > MAX_SOURCE_BYTES:
        raise EvaluationRefused("Candidate source exceeds size limit")
    safe_name(function_name)
    for name in parameter_names:
        safe_name(name)
    if len(parameter_names) > 8 or len(set(parameter_names)) != len(parameter_names):
        raise EvaluationRefused("Unsupported function parameters")
    try:
        tree = ast.parse(source, mode='exec')
    except (SyntaxError, RecursionError, MemoryError, ValueError) as exc:
        raise EvaluationRefused("Candidate syntax is invalid") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise EvaluationRefused("Candidate AST exceeds node limit")
    def depth(node, level=0):
        if level > MAX_DEPTH:
            raise EvaluationRefused("Candidate AST exceeds depth limit")
        for child in ast.iter_child_nodes(node):
            depth(child, level + 1)
    depth(tree)
    for node in nodes:
        if type(node) not in NODE_TYPES:
            raise EvaluationRefused("Unsupported syntax: " + type(node).__name__)
        if isinstance(node, ast.Name):
            safe_name(node.id)
        if isinstance(node, ast.arg):
            safe_name(node.arg)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                if len(node.value) > 1024:
                    raise EvaluationRefused("Docstring exceeds limit")
            else:
                try:
                    numeric(node.value)
                except CandidateRuntimeError as exc:
                    raise EvaluationRefused(str(exc)) from exc
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_CALLS or node.keywords:
                raise EvaluationRefused("Only min, max, abs and int calls with positional numeric arguments are allowed")
            argc = len(node.args)
            if node.func.id in ('abs', 'int') and argc != 1:
                raise EvaluationRefused("Unsupported call arity")
            if node.func.id in ('min', 'max') and not 2 <= argc <= 8:
                raise EvaluationRefused("min/max require 2 to 8 positional numeric arguments")
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise EvaluationRefused("Only single local-name assignment is supported")
            if node.targets[0].id in ALLOWED_CALLS or node.targets[0].id in ALLOWED_TYPES:
                raise EvaluationRefused("Builtin name rebinding is unsupported")
        if isinstance(node, ast.Expr) and not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            raise EvaluationRefused("Only docstrings may appear as standalone expressions")
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise EvaluationRefused("The module must contain exactly one named function and an optional docstring")
    function = body[0]
    if function.name != function_name or function.decorator_list or function.type_comment or getattr(function, 'type_params', []):
        raise EvaluationRefused("Unexpected function name or function metadata")
    if any(isinstance(n, ast.FunctionDef) and n is not function for n in nodes):
        raise EvaluationRefused("Nested functions are unsupported")
    params = function.args
    if params.posonlyargs or params.vararg or params.kwonlyargs or params.kwarg or params.defaults or params.kw_defaults:
        raise EvaluationRefused("Defaults, positional-only, variadic and keyword-only arguments are unsupported")
    if [p.arg for p in params.args] != parameter_names:
        raise EvaluationRefused("Function parameter contract mismatch")
    if any(p.arg in ALLOWED_CALLS or p.arg in ALLOWED_TYPES for p in params.args):
        raise EvaluationRefused("Builtin names cannot be parameters")
    for annotation in [function.returns, *[p.annotation for p in params.args]]:
        if annotation is not None and not (isinstance(annotation, ast.Name) and annotation.id in ALLOWED_TYPES):
            raise EvaluationRefused("Only int, float and bool annotations are supported")
    return function


@dataclass
class Returned:
    value: object


class Interpreter:
    def __init__(self, function, arguments):
        self.function = function
        if len(arguments) != len(function.args.args):
            raise CandidateRuntimeError("Argument count mismatch")
        self.locals = {parameter.arg: numeric(value) for parameter, value in zip(function.args.args, arguments)}
        self.steps = 0

    def tick(self):
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise CandidateRuntimeError("Step budget exceeded")

    def expr(self, node):
        self.tick()
        if isinstance(node, ast.Constant):
            return numeric(node.value)
        if isinstance(node, ast.Name):
            if node.id not in self.locals:
                raise CandidateRuntimeError("Undefined local variable")
            return self.locals[node.id]
        if isinstance(node, ast.UnaryOp):
            value = self.expr(node.operand)
            if isinstance(node.op, ast.UAdd): return numeric(+value)
            if isinstance(node.op, ast.USub): return numeric(-value)
            if isinstance(node.op, ast.Not): return not value
        if isinstance(node, ast.BinOp):
            left, right = self.expr(node.left), self.expr(node.right)
            if isinstance(node.op, ast.Add): value = left + right
            elif isinstance(node.op, ast.Sub): value = left - right
            elif isinstance(node.op, ast.Mult): value = left * right
            elif isinstance(node.op, ast.Div): value = left / right
            elif isinstance(node.op, ast.FloorDiv): value = left // right
            elif isinstance(node.op, ast.Mod): value = left % right
            else: raise CandidateRuntimeError("Unsupported numeric operation")
            return numeric(value)
        if isinstance(node, ast.BoolOp):
            value = self.expr(node.values[0])
            for item in node.values[1:]:
                if isinstance(node.op, ast.And) and not value: break
                if isinstance(node.op, ast.Or) and value: break
                value = self.expr(item)
            return value
        if isinstance(node, ast.Compare):
            left = self.expr(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self.expr(comparator)
                if isinstance(op, ast.Eq): ok = left == right
                elif isinstance(op, ast.NotEq): ok = left != right
                elif isinstance(op, ast.Lt): ok = left < right
                elif isinstance(op, ast.LtE): ok = left <= right
                elif isinstance(op, ast.Gt): ok = left > right
                elif isinstance(op, ast.GtE): ok = left >= right
                else: raise CandidateRuntimeError("Unsupported comparison")
                if not ok: return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return self.expr(node.body if self.expr(node.test) else node.orelse)
        if isinstance(node, ast.Call):
            values = [self.expr(n) for n in node.args]
            name = node.func.id
            if name == 'min': result = min(values)
            elif name == 'max': result = max(values)
            elif name == 'abs': result = abs(values[0])
            elif name == 'int': result = int(values[0])
            else: raise CandidateRuntimeError("Unsupported call")
            return numeric(result)
        raise CandidateRuntimeError("Unsupported expression")

    def block(self, statements):
        for statement in statements:
            self.tick()
            if isinstance(statement, (ast.Expr, ast.Pass)):
                continue
            if isinstance(statement, ast.Return):
                if statement.value is None:
                    raise CandidateRuntimeError("Numeric return value required")
                return Returned(self.expr(statement.value))
            if isinstance(statement, ast.Assign):
                self.locals[statement.targets[0].id] = numeric(self.expr(statement.value))
            elif isinstance(statement, ast.If):
                result = self.block(statement.body if self.expr(statement.test) else statement.orelse)
                if isinstance(result, Returned): return result
            else:
                raise CandidateRuntimeError("Unsupported statement")
        return None

    def run(self):
        try:
            result = self.block(self.function.body)
            if not isinstance(result, Returned):
                raise CandidateRuntimeError("Function did not return a value")
            return numeric(result.value)
        except (ArithmeticError, OverflowError) as exc:
            raise CandidateRuntimeError(type(exc).__name__) from exc


def evaluate_source(source, function_name, cases, parameter_names):
    """Evaluate literal frozen cases; test values are never supplied to candidate code as files."""
    source_sha = hashlib.sha256(source.encode('utf-8')).hexdigest()
    try:
        function = compile_source(source, function_name, parameter_names)
    except EvaluationRefused as exc:
        return {'evaluator_version': VERSION, 'source_sha256': source_sha, 'syntax_allowed': False,
                'status': 'refused', 'reason': str(exc), 'cases': [], 'pass': 0, 'fail': len(cases)}
    output = []
    for case in cases:
        try:
            interpreter = Interpreter(function, case['args'])
            value = interpreter.run()
            expected = case['expected']
            correct_type = type(value) is not bool if type(expected) in (int, float) else type(value) is type(expected)
            if case.get('type') == 'int':
                correct_type = type(value) is int
            passed = correct_type and value == expected
            output.append({'id': case['id'], 'status': 'pass' if passed else 'fail',
                           'actual': value, 'expected': expected, 'steps': interpreter.steps})
        except CandidateRuntimeError as exc:
            output.append({'id': case['id'], 'status': 'fail', 'error': str(exc), 'expected': case['expected']})
    passed = sum(c['status']=='pass' for c in output)
    return {'evaluator_version': VERSION, 'source_sha256': source_sha, 'syntax_allowed': True,
            'status': 'pass' if passed==len(output) else 'fail', 'cases': output,
            'pass': passed, 'fail': len(output)-passed}
