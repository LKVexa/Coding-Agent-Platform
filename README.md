# Coding Agent Platform

A bounded coding-agent workflow with model proposals, independent evaluation
and patch export for one committed numeric Python function.

**Current version: 0.1.0-rc.2 · GPL-3.0-only**  
**Copyright (C) 2026 RUSSELL PHILIP SMITHSON**

## Windows startup fix

Version 0.1.0-rc.2 fixes the misleading CLI-mismatch error when the Windows
launcher does not inherit Codex on PATH. It discovers the already-approved
desktop installation while retaining exact executable hash/version checks.
No global PATH or login changes are needed for that installation.

Use [releases/0.1.0-rc.2/app/Coding-Agent.cmd](releases/0.1.0-rc.2/app/Coding-Agent.cmd),
then follow the [start guide](releases/0.1.0-rc.2/app/START_HERE.md).
See [installation requirements](releases/0.1.0-rc.2/app/INSTALL.md) for the
supported environment and explicit CODING_AGENT_CODEX override.
Keep new state outside the application and use a short checkout path.

The final application passed 26 provider/discovery tests and 6 integration
tests. A real repair launched without Codex on PATH passed independent checks,
replayed and exported a patch in one provider call. Scope remains the bounded
authored diagnostics; this does not establish general coding performance.

## Source, evidence and previous release

The [current release](releases/0.1.0-rc.2/) includes runtime source, documentation,
validation evidence and an accepted example patch.
The original [0.1.0-rc.1 release](release/) remains unchanged for historical
inspection and replay. Old run evidence is not migrated or rewritten.

Run `python verify_release.py` to check both release inventories and manifest
pins using only Python's standard library. Git text conversion is disabled to
preserve sealed bytes across checkout.

## Separate products

- [Research Toolkit](https://github.com/LKVexa/Research-Toolkit)
- [Research Workbench](https://github.com/LKVexa/Research-Workbench)
- [Coding Agent Platform](https://github.com/LKVexa/Coding-Agent-Platform)

The workbench, research toolkit, shared foundation and original deliveries
remain separate and unchanged by this fix.

See [LICENSE](LICENSE), [NOTICE](NOTICE) and [COPYRIGHT](COPYRIGHT).
Existing third-party notices and terms are retained.
