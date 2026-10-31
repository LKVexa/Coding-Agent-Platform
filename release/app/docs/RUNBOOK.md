# Runbook

All command examples are PowerShell commands run from the application folder containing `Start-Platform.ps1`. Paths with spaces are quoted or passed as variables. Runtime state, repository, package and export locations must be separate; the application rejects protected destinations and linked/reparse paths.

## Commands

| Command | Purpose | Model proposal issued? |
| --- | --- | --- |
| `doctor` | Verify current package, foundation, evaluator and provider login | No |
| `tasks` | List authored public diagnostic tasks | No |
| `demo --destination PATH` | Create a new separate committed diagnostic repository | No |
| `run --repo PATH --task ID_OR_PATH --state PATH` | Propose, evaluate and retain evidence | Yes, at most `--max-calls` |
| `runs --state PATH` | List stored run outcomes and incomplete runs | No |
| `inspect --state PATH --run-id ID` | Verify a sealed run and display its result | No |
| `replay --state PATH --run-id ID` | Reconstruct its patch and repeat independent evaluation | No |
| `export --state PATH --run-id ID --destination PATH` | Export an accepted, replayed patch to a new directory | No |
| `resume --state PATH --run-id ID` | Recover local completion or record interruption | No |
| `cancel --state PATH --run-id ID` | Request cancellation of an active run | No |
| `selftest --state PATH` | Run authored foundation correct/regression diagnostics | No |

State defaults to `%LOCALAPPDATA%\CodingAgentPlatform\state` when omitted. Explicit `--state` makes each workflow's location easier to track. `doctor`, `tasks` and `demo` do not accept a state argument. A demo/export destination must not already exist, and its parent directory must already exist. State creation can create its missing parents.

## Repository input

Use a normal local Git repository with a `.git` directory. Linked worktrees and alternate Git object stores are unsupported. `--revision` accepts `HEAD` or a full commit hash. The source comes from that commit, so uncommitted working-tree edits are not used or discarded.

The permitted file must be a regular committed `.py` blob, 1–16,384 bytes, UTF-8, with LF line endings and a final newline. Its path uses forward slashes, for example `src/absolute.py`. It must contain one supported numeric function whose name and positional parameters match the task.

Supported source includes numeric/boolean expressions, local assignment, conditional statements/expressions, returns, optional docstrings and numeric annotations. The only function calls are `min`/`max` with 2–8 positional arguments and `abs`/`int` with one. Loops, imports, attributes, recursion, containers, decorators, defaults and extra functions are unsupported. The evaluator also bounds syntax size/depth, steps and numeric magnitudes.

## Custom task example

The packaged `docs/examples/custom-baseline.py` is an intentionally wrong but supported source file: it returns its input unchanged. To try it, copy its text into `src/absolute.py` in a separate repository and commit it using LF line endings. The supplied public task and private checks describe absolute value; its positive/zero baseline cases pass and its negative cases fail. These JSON files are reusable examples, not acceptance evidence from an executed run.

```powershell
$customRepo = 'C:\Projects\numeric-example'
$customState = Join-Path $env:LOCALAPPDATA 'CodingAgentCustom01\state'
& './Start-Platform.ps1' run --repo $customRepo --revision HEAD --task './docs/examples/custom-task.json' --checks './docs/examples/custom-checks.json' --state $customState --run-id absolute-01 --max-calls 2 --timeout 120
```

A custom task has `id`, `path`, `function`, `parameters`, `description` and `public_examples`. The checks file has the matching `task_id` and `cases`. Each example/case has positional `args` and numeric/boolean `expected`, with optional `id` and `type: "int"`. Private checks require 2–128 cases; public examples require 1–32. Each case must match the declared parameter count. Extra properties and duplicate identifiers are rejected.

The baseline must have both passing and failing private cases. The platform sends the public task, public examples and selected source to the provider. Private case values and final evaluation are excluded from provider feedback. At most the public feedback from the first attempt informs a second proposal. The selected candidate is then checked independently against the private cases.

## Budgets and outcomes

`--max-calls` accepts 1 or 2 (default 2). `--timeout` accepts 5–180 seconds per provider invocation (default 120). The adapter records each call intent before issuing the CLI. The provider's native transport may retry a transient network problem internally within that invocation's timeout. `provider_calls` counts CLI invocations; it is not an exact count of remote requests. Usage may already have occurred if an invocation times out or is cancelled. Monetary cost remains `null`.

`accepted` means the candidate passed the supplied private checks, including all previously passing cases and the baseline failing cases. `rejected` means acceptance failed or no usable candidate was selected. `provider_failed`, `failed`, `cancelled` and `interrupted` describe incomplete/error paths; their evidence stays available. Run acceptance is narrower than general correctness.

The CLI normally exits 0 for successful commands, 2 for an input/integrity/provider setup error, and 3 for a returned unsuccessful run outcome. Automation should also inspect JSON status: commands such as `inspect` return a wrapper around a historical result rather than rerunning it.

## Review and export

```powershell
& './Start-Platform.ps1' runs --state $customState
& './Start-Platform.ps1' inspect --state $customState --run-id absolute-01
& './Start-Platform.ps1' replay --state $customState --run-id absolute-01
$customExportParent = Join-Path $env:LOCALAPPDATA 'CodingAgentCustom01\review'
New-Item -ItemType Directory -Path $customExportParent -ErrorAction Stop | Out-Null
& './Start-Platform.ps1' export --state $customState --run-id absolute-01 --destination (Join-Path $customExportParent 'absolute-01')
```

`replay` verifies the receipt and frozen inputs, reconstructs the source from the unified diff and compares the new evaluation with the recorded one. It issues no provider call. `export` requires independent acceptance and successful replay.

The example creates a new export parent once. If that parent already exists, reuse the existing directory and choose a new, nonexistent child destination; do not rerun the creation line or overwrite an old export.

Exports contain `change.patch`, `replacement/<source path>`, `RESULT.json`, `README.txt` and `MANIFEST.json`. Private test values and provider prompts are omitted. Result metadata can include case identifiers, metrics, repository identity and provider metadata. Review the export before sharing or applying it. Full local state contains private checks, prompt text, attempts and evaluations.

## Cancel and recover

In another PowerShell window, use the same application version and state location:

```powershell
& './Start-Platform.ps1' cancel --state $customState --run-id absolute-01
```

Cancellation is a request, not a refund or assurance that no remote work occurred. Wait for the active worker to stop before recovery. A per-run lock prevents concurrent recovery of a live run.

```powershell
& './Start-Platform.ps1' resume --state $customState --run-id absolute-01
```

`resume` never reissues a provider call. It verifies an already sealed result, completes independent local processing of a frozen selection, or records the run as interrupted/cancelled. If a terminal result exists without its receipt and there is no frozen selection, recovery refuses to replace that evidence: preserve the run and explicitly start a fresh run ID. A run without any frozen selection cannot choose a new proposal during recovery.

Use a new ID for a deliberate retry. An existing run ID is never silently rerun, and old attempts remain intact. The exact originating package is required to inspect/replay/recover its state; do not mutate that package or reuse the state with mixed versions.

## Troubleshooting

| Message or symptom | Action |
| --- | --- |
| Provider CLI/version mismatch | Use the recorded compatible runtime or perform a separately tested compatibility upgrade; keep the pin intact |
| Existing ChatGPT login required | Restore the login through the provider's normal user interface, then rerun `doctor`; never paste credentials into task files |
| Baseline lacks passing or failing checks | Correct the task/check specification or select the intended committed source; do not alter expectations merely to manufacture a pass |
| Unsupported syntax | Narrow the task to the numeric profile; this release cannot run a general Python file |
| State/package/path rejection | Choose separate new directories outside originals, protected releases and the repository |
| Incomplete run | Stop/wait for its worker, preserve evidence, then use `resume` |
| Changed manifest or frozen inputs | Preserve the failure and use a complete known-good package/state copy; do not edit hashes to suppress the failure |

See `KNOWN-LIMITATIONS.md` and `ROLLBACK.md` before extending the product beyond this scope.
