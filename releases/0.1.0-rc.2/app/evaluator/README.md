# Independent bounded evaluator

This evaluator reads proposed source as data, validates its syntax and interprets a small numeric language. It never executes or imports candidate Python. Candidate values can only be bounded numbers and booleans; they cannot become file handles, Python objects, host globals, environment variables or evaluator files. This is a deliberately limited local coding demonstrator, not a general repository test runner or a production security boundary for arbitrary Python execution.

The authored `repository-template` provides three deliberately broken utility functions: two development tasks and one held-out task. The platform initializes a real Git repository from this template and confines each patch to its declared source file. These tasks are newly authored examples. They do not reproduce D0005's experiments, SWE-bench or any external benchmark, and passing them does not establish scientific validation or general coding-agent quality.

## API

Import these functions from `evaluator` when the coding-agent directory is on Python's import path:

```python
evaluate_source(source, function_name, cases, parameter_names)
get_public_task(task_id)
list_public_tasks()
evaluate_public(task_id, candidate_source)
evaluate_task(task_id, candidate_source, baseline_source=None)
verify_protocol()
```

`evaluate_source` also supports custom local tasks independently of the built-in task set. The caller provides a source string, the exact function name, ordered parameter names, and trusted literal cases. A case is `{"id":"unique-id","args":[1,2],"expected":3}`. Add `"type":"int"` to require an actual integer result. Inputs and expected results are finite numeric values or booleans. The caller validates the custom case schema, unique IDs and the intended data partition; keep private cases outside provider context.

The source result contains `syntax_allowed`, `status` (`pass`, `fail` or `refused`), `source_sha256`, `pass`, `fail`, and `cases`. Each evaluated case contains `id`, `status`, `expected`, and either `actual`/`steps` or a bounded descriptive `error`. Refusal produces no evaluated cases and counts every supplied case as failed. Exact numerical equality is used; a boolean cannot satisfy a numeric expected result. No tolerance is inferred.

`get_public_task` returns the description, path, function, parameters, partition, public examples and original file SHA256. It does not return private cases. `evaluate_public` evaluates only disclosed examples and may be supplied as development feedback. Private final results from `evaluate_task` must never be sent to a provider. It returns baseline/candidate case results, `f2p` and `p2p` objects with `passed`, `total`, and `case_ids`, integrity hashes, and `accepted`. F2P means initially failing cases that now pass; P2P means initially passing cases that still pass. Acceptance requires every case passing, all F2P improvements, and no P2P regressions. The baseline is always the frozen original; an optional provided baseline must match exactly.

`verify_protocol` checks every entry in `PROTOCOL-MANIFEST.json` and the exact required file set. The parent release manifest separately pins this manifest. Freeze these hashes before live provider runs and record them with run evidence. This does not protect against a person who controls and changes both the released evaluator and its outer trusted hash.

## Supported language

One function per source module, with an optional module/function docstring. Exact parameter names, up to eight numeric parameters, optional `int`, `float` or `bool` annotations; no default or variadic arguments. Local assignment, `return`, `if`/`elif`/`else`, `pass`, arithmetic `+ - * / // %`, comparisons, `and`/`or`/`not`, and conditional expressions are supported. Calls are limited to `min`/`max` with two to eight numeric arguments and `abs`/`int` with one argument. Builtin names cannot be rebound.

Imports, attributes, subscripts, containers, comprehensions, loops, recursion, exception handling, decorators, lambdas, arbitrary calls, exponentiation, f-strings and underscore-prefixed names are refused. Strings serve only as docstrings; they are not supported values. There is no filesystem, process or network operation in the interpreted language.

Limits: source 16,384 UTF-8 bytes; 256 AST nodes; AST depth 24; 512 interpreter steps per case; numeric magnitude at most 10^12; identifiers at most 64 characters; docstrings at most 1,024 characters. Division by zero, undefined locals, missing return, magnitude overflow and invalid result types fail a case. The profile uses host float arithmetic; callers should design exact or expressly toleranced labels outside this profile where floating-point boundaries matter.

## Protocol and controls

`public/tasks.json` holds provider-safe metadata. `evaluator-only/protocol.json` holds frozen independent case inputs and labels. `controls` supplies known-correct and regression sources; the unmodified repository source is the no-op control. These controls and private cases are evaluator material, never provider context or retrieval material.

| Task | Partition | Baseline passing/failing | Correct F2P/P2P | Regression F2P/P2P |
|---|---|---:|---:|---:|
| clamp-bounds | development | 8 / 2 | 2/2 and 8/8 | 2/2 and 6/8 |
| interval-overlap | development | 6 / 2 | 2/2 and 6/6 | 2/2 and 3/6 |
| bucket-index | heldout | 7 / 3 | 3/3 and 7/7 | 3/3 and 2/7 |

The regression controls repair all initially failing cases while breaking initially passing cases. Their rejection tests that the gate checks both improvement and preservation. The no-op controls must retain every P2P case but fail to repair any F2P case. All three known-correct controls must pass. This validates the local gate, not broad benchmark performance.

Run `python -I -B evaluator/test_evaluator.py` from the product directory for boundary, language, protocol and control tests. Run `python -I -B evaluator/run_controls.py` for detailed local evidence in `evidence/controls.json`. `-B` avoids generated bytecode in the release. The evaluator itself has no third-party dependencies.
