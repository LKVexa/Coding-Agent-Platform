# Local bounded fixture threat model

Trusted computing base: the reviewed installed foundation code, its manifest supplied with the release, the installed Python/.NET runtimes, NumPy and the selected pinned adapter sources/binaries. Manifests detect changes against that trusted release; they are not signatures and cannot authenticate an attacker-replaced installation. An administrator or process able to rewrite both program and manifest is outside this release's boundary.

Untrusted data: source notes, archived metadata, arbitrary CLI component/case/run identifiers, run logs, persisted JSON and interrupted output. Notes are parsed as data. The catalog does not create executable commands. Capability entries are pinned release data, and the runtime supports only the reviewed Python and C# entry points with fixed case choices.

Controls: strict bounded JSON; duplicate/non-finite/nesting rejection; schema validation; output-path confinement; no reparse paths; source/package protected roots; structured process argument lists; explicit environment allowlist; no shell interpolation; Windows Job limits for one active child process, 512 MB process memory, timeout and kill on parent closure; bounded output streams; atomic result commits; OS-backed run locks; append-only attempts; package and run-content hashes.

The selected algorithms perform no network access or filesystem writes. There is no claim of a general OS network/filesystem security boundary for arbitrary hostile code. Importing a new executable plugin is unsupported and requires a new audited release. Windows process limits govern this reviewed fixture execution, not general hostile-code containment. In-process literal fixture expectations are public diagnostics; no secret evaluator or D0008 training pipeline is included.

Local state contains source provenance paths and diagnostic outcomes, not credentials. Only a small environment allowlist is passed; model/service credentials are never needed. Public redistribution rights for all archived research metadata have not been established, so this build is a private local handoff. No external publication is part of this release.
