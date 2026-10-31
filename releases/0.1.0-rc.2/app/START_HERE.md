# Start here

Coding Agent Platform proposes one numeric Python source change, checks it independently and exports a patch for your review. It reads a committed Git file and keeps the original repository unchanged. The component workbench and research toolkit remain separate products.

The first release supports a deliberately small Python language. It does not run your repository's programs, test suite, install scripts or build system. The source, task and public examples are sent to the configured real model; choose content appropriate for that provider.

## Check the installation

Open PowerShell in the package's application folder, where `Start-Platform.ps1` is located. Run:

```powershell
& './Start-Platform.ps1' doctor
& './Start-Platform.ps1' tasks
```

`doctor` checks the package, frozen foundation, evaluator and existing provider login. It does not generate a model proposal. The required environment is described in `INSTALL.md`.

## Try a separate example repository

These commands create new local example folders. Choose another name if the example repository or export already exists. Keep the package, repository, state and export in separate locations.

```powershell
$exampleRoot = Join-Path $env:LOCALAPPDATA 'CodingAgentExample01'
New-Item -ItemType Directory -Path $exampleRoot -ErrorAction Stop | Out-Null
$exampleRepo = Join-Path $exampleRoot 'repository'
$exampleState = Join-Path $exampleRoot 'state'
$exampleExport = Join-Path $exampleRoot 'review-patch'
& './Start-Platform.ps1' demo --destination $exampleRepo
& './Start-Platform.ps1' run --repo $exampleRepo --task clamp-bounds --state $exampleState --run-id example-clamp-01 --max-calls 2 --timeout 120
```

The run may take up to two provider invocations. A second invocation uses public example feedback only. Each invocation has its own timeout. The provider's native transport may retry a transient network error internally within that timeout; `provider_calls` counts CLI invocations, not individual network requests.

Project instructions, user configuration and skill discovery are disabled for the provider call. The trusted CLI retains its built-in instructions and may inherit global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md` guidance; no such global file was present in the verified release environment. Model tools remain absent. The platform records presence only, never the contents of global guidance.

Review and reproduce the result:

```powershell
& './Start-Platform.ps1' inspect --state $exampleState --run-id example-clamp-01
& './Start-Platform.ps1' replay --state $exampleState --run-id example-clamp-01
& './Start-Platform.ps1' export --state $exampleState --run-id example-clamp-01 --destination $exampleExport
```

Only an independently accepted patch can be exported. A failed or rejected result stays in the run history. Export contains the source replacement, unified diff, result and hashes; it omits private test values and provider prompts. Full local evidence stays in the separate state directory. No command above applies the patch to the original repository.

## Use your own task

Provide one committed `.py` file with a supported numeric function, a public task JSON and separate private checks JSON. See `docs/examples/custom-task.json`, `docs/examples/custom-checks.json` and `RUNBOOK.md` from the application folder. Private baseline cases must include at least one already-passing case and one failing case, so the result can measure both repair and regression preservation.

Use `runs` to list results, `cancel` to request cancellation and `resume` to recover a stopped local workflow without issuing another provider call. The runbook explains the cases where a fresh run is required.

The three included diagnostic tasks establish a bounded workflow demonstration. They do not establish broad coding performance or complete the original deliveries' research claims. Release gate files record the evidence for this particular package.
