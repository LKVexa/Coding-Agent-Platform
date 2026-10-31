# Coding Agent Platform 0.1.0-rc.1

The coding-agent platform is built and verified as a separate local product. It asks the configured model for a source change, checks that change independently, rejects regressions and exports a reviewable patch. This first release handles one committed numeric Python function at a time.

Open [the start guide](app/START_HERE.md), then use `app/Start-Platform.ps1` or `app/Coding-Agent.cmd`. [Installation](app/INSTALL.md) lists the exact supported Windows, Python and Codex runtime. The product uses the existing ChatGPT login; it includes no credentials.

Extract the archive to a short Windows folder, such as `C:\Tools`. The evidence contains nested paths; very deep destinations can exceed the host's Windows path-length limit. This release does not change Windows settings.

Three real-model diagnostic tasks passed and their patches replayed independently. All 81 automated checks passed. Read the [acceptance report](ACCEPTANCE-REPORT.md) and [known limitations](KNOWN-LIMITATIONS.md) for the evidence and scope.

Saved diagnostic runs are under `evidence/verified-state`. From the app folder you can replay one without making a model call:

```powershell
& './Start-Platform.ps1' replay --state '../evidence/verified-state' --run-id verified-clamp
```

All original deliveries and the existing foundation/workbench releases were preserved. The research toolkit remains separate and unbuilt. The platform does not automatically apply patches, run arbitrary repository programs, merge, deploy or train models.
