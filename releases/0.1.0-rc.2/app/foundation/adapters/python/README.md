# D0001 assistant token count adapter

Adapter version 0.1.0. Component identity: `D0001/C0081-03`.

This read-only adapter invokes the original `pairs_c.C0081_03()` bounded fixture. Five source modules are copied without changes and hashed in `SOURCE-MANIFEST.json`. Original pair documents and evidence remain in `historical/`. No legacy product runner is invoked, and the adapter does not write to either the original delivery or its local payload.

## Supported environment and invocation

Validated environment: Windows, Python 3.12.14, NumPy 2.3.5. The historical record states Python 3.14.0 and NumPy 2.5.1. The original four check definitions, values, records, iteration count and repair log reproduce exactly in the validated current profile. Historical runtime fingerprints are retained without relabeling them as current. This establishes compatibility for this bounded fixture only.

Invoke an installed Python interpreter from any working directory using an absolute adapter path:

```text
<python.exe> -I -B <adapter-directory>/entry.py --case baseline
<python.exe> -I -B <adapter-directory>/entry.py --case negative-control
```

The adapter derives its paths from its own file and verifies source/historical hashes before importing the selected modules. `-I` isolates the process from user Python environment configuration; `-B` prevents bytecode writes. NumPy is an installed prerequisite, not copied into this package. Python execution is not a security sandbox for arbitrary code; this adapter accepts only the two allowlisted cases and invokes reviewed pinned modules.

Exit 0 means the diagnostic executed. Candidate acceptance is a separate field. Exit 2 means invocation or execution failed; errors never become candidate passes. Stdout is one JSON object. Stderr carries command-line parser errors for an unsupported case. There are no network calls or arbitrary path/command inputs in the adapter.

## Baseline and negative control

Baseline runs the original four checks: known count 14, empty count 0, seed-23 randomized recount 605, and unknown-role rejection. A fifth wrapper check compares the actual legacy check/record payload to the pinned historical evidence, excluding only `fingerprint_inputs`, whose original contents remain unchanged in `historical/records.json`.

The negative control deliberately replaces `frog.assistant_token_count` in that one process with an incorrect `len(roles)` implementation. The original evaluator then rejects the candidate: it counts 30 instead of 14 in the known example, 1,000 instead of 605 in the randomized case, and accepts an unknown role. Those failed original checks remain in `candidate_checks` and `records`. The top-level `negative_control_rejected` diagnostic passes only when the evaluator actually rejects the faulty candidate. Original source bytes and expected definitions are never changed.

This does not validate the source paper, train a model or establish full coding-agent behavior. Both cases are authored-fixture diagnostics; `scientific_validation` remains `unverified`.

## Validation and provenance

Run `validate_adapter.py` with the same interpreter using `-I -B`. It records two independent baseline processes, a relocated copy with spaces in its path, mutation rejection, invalid-case rejection, corrupted-source rejection and original-source hash preservation. Each validation writes a new evidence directory. Do not redistribute development evidence or the mutated relocation copy as the runnable adapter payload.

Packaging inputs are `entry.py`, `SOURCE-MANIFEST.json`, `vendor/`, `historical/`, this README and `ADAPTER.json`. `validate_adapter.py` is optional validation source. The `evidence/` directory is development evidence, not runtime input. Original source license declarations were not present in this selected payload; this local user-owned assembly does not claim a right to public redistribution. NumPy remains an external dependency under its own license.
