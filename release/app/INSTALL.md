# Installation and environment

This release is a local Windows application. Keep the entire versioned package together; its manifest pins the application, evaluator and embedded shared foundation. Keep runtime state and repositories outside the application folder and protected delivery/sibling-product roots.

## Requirements

| Requirement | Contract |
| --- | --- |
| Python | Python `3.12.14`; the entry point requires Windows and isolated mode, with bytecode writes disabled |
| Git | A local Git executable for committed-blob reads and creation of the separate demo repository |
| Provider runtime | `codex-cli 0.166.0-alpha.5.1`, available as `codex` on PATH |
| Provider executable hash | SHA-256 `3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16` |
| Provider access | Existing ChatGPT login recognized by the pinned CLI; network access for proposal requests |
| Foundation diagnostics | Windows .NET Framework runtime for the embedded D0007 authored diagnostic |

The provider executable is an existing trusted local dependency, not a bundled credential or runtime download. The platform checks its exact hash and version and rejects an unexpected replacement. An automatic runtime update can therefore require compatibility verification before this package will run again. Do not disable the pin to bypass a mismatch.

## Runtime discovery

`Start-Platform.ps1` uses `CODING_AGENT_PYTHON` if set, then the bundled Codex Python location under the current user's profile, then a regular `python.exe`. It skips the Windows Store alias. An explicit Python path can be set for the current PowerShell session:

```powershell
$env:CODING_AGENT_PYTHON = 'C:\Path\To\Python312\python.exe'
```

Use an existing installation of Python 3.12.14 at that path. The placeholder above is not a download or installation command.

Git is discovered from `CODING_AGENT_GIT`, PATH or the local Codex runtime's bundled Git. If needed, set `CODING_AGENT_GIT` to the existing `git.exe` path. The provider is discovered as `codex` on PATH. Existing authentication remains with that runtime; do not copy credentials into the product or state folder.

Provider calls disable project documents, user configuration and skill discovery. The CLI still has its built-in instructions and may inherit global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md` guidance. The verified release environment reported `global_guidance.present: false`. Other installations can differ; presence is recorded without reading or copying that guidance into platform reports. This inheritance does not add model tools, which remain absent under the pinned policy.

## Verify before a run

From the application folder:

```powershell
& './Start-Platform.ps1' doctor
```

A successful `doctor` checks current package integrity, foundation pin, evaluator protocol and provider identity/login. It performs no model inference and is not itself proof that a repair task succeeds. Review the shipped release evidence for actual task outcomes.

No package installation, dependency installation or execution of repository code is part of a normal platform run. The trusted local Git and provider executables are still processes; the candidate function is evaluated only by the restricted numeric interpreter.

Do not edit files inside a released application folder. Changed files fail integrity checks. Preserve an entire known-good version for rollback and retain state under its exact originating package version.
