# Changelog

## 0.1.0-rc.2

Fixes Codex discovery when the Windows launcher does not inherit the desktop
app's PATH. Adds an explicit CODING_AGENT_CODEX override and bounded discovery
of the installed desktop runtime, accepting only the previously approved
executable hash and version. Distinguishes a missing CLI from binary drift and
includes a stable error code in setup failures. Provider model, tool policy,
catalog, evaluator and shared-foundation pins remain unchanged.

Keep the complete rc.1 installation to inspect or replay its existing runs.
New runs use the rc.2 package identity; frozen rc.1 run evidence is not rewritten.

## Initial prerelease

Establishes a separate Coding Agent Platform using shared foundation `0.1.0-rc.1` at its verified manifest pin. Introduces a bounded repository-task contract, a real-model proposal boundary without model tools, a numeric AST evaluator, public-only retry feedback, independent final checks and replacement/diff export to separate state.

Adds two authored development tasks and one held-out diagnostic task, correct and regression controls, traceability to frozen foundation capabilities, preservation checks, product-owned schemas and release evidence. Runtime cost remains unknown (`null`).

No original delivery, shared foundation release, workbench release or research toolkit version is changed by this product. Original status and scientific claims retain their historical meaning.

The package's version and gate/status files are authoritative for the exact release identifier and observed acceptance. This changelog records scope rather than claiming test or provider results.
