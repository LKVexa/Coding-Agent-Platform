# D0007 bounded regression adapter

Version 0.1.0. This adapter executes the original C0322 authored diagnostics in a fresh process. It supports the data and preservation views `D0007/C0322-01` and `D0007/C0322-02` with the same fixed 14-case, 42-method-call fixture. It does not run the original pair writer, update delivery status, invoke models, train a system, or establish real-repository or paper-scale results.

## Run

From this package directory in PowerShell:

```powershell
& './bin/WorkbenchD7.exe' --component D0007/C0322-02 --case all
& './bin/WorkbenchD7.exe' --component D0007/C0322-02 --case regression
```

The case selector accepts `all`, `initial`, `correct`, or `regression`. Every call executes the entire frozen fixture and its 38 diagnostic checks; the selector chooses the reported candidate summary. Results are JSON on standard output. The application writes no files. Caller-owned run directories retain stdout/stderr and timing.

Exit 0 means every diagnostic expectation passed. Exit 1 means a diagnostic failed. Exit 2 rejects unsupported arguments or reports an unexpected execution exception. The regression candidate is correctly rejected while operational execution succeeds. Consumers must inspect `candidate_accepted` and the per-candidate records, not treat exit 0 as candidate acceptance.

Expected controls: correct candidate preserves 11/11 previously passing cases and is accepted. The regression fixes all 3 initially failing cases but preserves only 7/11 previously passing cases and is rejected. For DEV-CLAMP alone, the regression has F2P 2/2 and P2P 4/6. Both scientific validation and real parent integration remain unverified.

## Build from source

```powershell
& './build.ps1'
```

The builder creates a new unique `builds/build-<id>` directory and prints a receipt identifying the executable. Existing build directories are never overwritten. It verifies the vendored upstream hashes, uses the locally installed .NET Framework compiler, and requires no original delivery folders. The recovered invocation uses `/nologo /langversion:5 /target:exe /main:WorkbenchAdapter /r:System.Web.Extensions.dll`, an explicit output path and the three files in `src/`. The tested compiler is Framework64 csc 4.8.9232.0 on Windows.

## Verify

```powershell
& './verify.ps1'
# To verify a fresh build, pass its printed binary path:
& './verify.ps1' -Binary './builds/<build-id>/WorkbenchD7.exe'
```

The verifier creates a fresh evidence directory, runs repeat executions, compares six record families to retained historical evidence, checks all candidate cases, rejects invalid invocations, and checks vendored hashes. It compares parsed JSON semantically for historical files; fresh repeated stdout must be byte-identical. No scientific criterion is weakened or changed.

## Provenance and changes

`src/P2PDiagnostics.cs` and `src/HarnessCommon.cs` are exact copies from D0007/C0322-01. Their upstream attribution remains intact. `SOURCE-MANIFEST.json` records the original paths and hashes, including historical comparison fixtures. These paths are evidence only and are never used by the runtime or builder. `WorkbenchAdapter.cs` is new: it directly calls the existing in-memory `Pipeline.ExecuteAll`, `CreateDataset`, `Diagnostics`, `Preserve` and `Downstream` logic via the diagnostics; it maps check keys and summarizes existing observed outcomes.

The original `PreparationBindings.Load` and `Pipeline.Build` packaging path is not invoked. Consequently this package proves fresh bounded method execution and equivalence of selected diagnostic records; it does not claim to rerun the legacy writer's ownership/preflight checks or recreate every original package byte. Historical source labels and unverified parent integration remain visible.

## Execution boundary

The runtime accepts only fixed component/case enums. It performs no filesystem writes, launches no child processes, and makes no network calls on the selected call path. The compiled upstream utility class contains unused file helpers; the wrapper exposes none of them. This is an allowlisted trusted fixture, not a general untrusted-code execution environment. Literal fixture expectations exist in the same assembly and are not secret evaluator material. The workbench must enforce timeout, output-size, process and evidence boundaries around this subprocess.

The package is prepared for the user's local work. Original authored attribution is retained; no broader redistribution license is inferred.
