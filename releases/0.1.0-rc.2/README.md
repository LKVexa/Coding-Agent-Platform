# Coding Agent Platform 0.1.0-rc.2

This update fixes the startup error seen when launching from Windows outside
Codex. The approved Codex executable is discovered in its desktop installation
even when it is absent from PATH. Its exact hash and version are still checked.

Open **app/Coding-Agent.cmd** to check setup, or use
[the start guide](app/START_HERE.md) for a coding task.
See [installation details](app/INSTALL.md) for CODING_AGENT_CODEX when an approved
runtime is installed elsewhere. No global PATH or login changes are required.

The final package passed 26 provider/discovery tests and 6 integration tests.
With Codex absent from PATH, its Windows launcher passed setup and a real
interval-overlap repair used one provider call, passed independent evaluation,
replayed successfully and exported a patch without modifying the example repo.

This remains a bounded numeric-Python diagnostic platform. It does not run
arbitrary repository programs or establish broad coding performance.

Keep rc.1 and its existing run state for historical inspection/replay. New rc.2
runs have a new package identity; old evidence is not rewritten. The Research
Toolkit, Research Workbench and all original deliveries remain unchanged.

GPL-3.0-only. Copyright (C) 2026 RUSSELL PHILIP SMITHSON.
See LICENSE, NOTICE and COPYRIGHT; retained third-party terms still apply.
