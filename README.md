# Coding Agent Platform

A bounded coding-agent workflow with model proposals, independent evaluation and patch export.

**Version 0.1.0-rc.1 · GPL-3.0-only**  
**Copyright (C) 2026 RUSSELL PHILIP SMITHSON**

## Getting started

Read the [start guide](release/README.md) and [environment requirements](release/INSTALL.md).
This is a Windows prerelease using the declared, pinned local runtimes.
Use a short checkout path and keep new run state outside the release folder.
The application and all its source are under [release/app](release/app).

This prerelease handles one committed numeric Python function per task. It requires the exact qualified local Codex runtime and an existing login; provider updates can require requalification.

## Integrity and evidence

The [release](release/) contains the original verified package, source,
documentation, examples and acceptance evidence. Its files are unchanged.
Run the following with an installed Python interpreter to check every file
against the preserved release manifest (this check needs only the standard
library and does not run the application):

```text
python verify_release.py
```

The repository disables Git text conversion so sealed file hashes survive
checkout. Historical local-only and earlier product-status descriptions in
the evidence describe the original build, not current publication status.
New publication metadata and licensing live outside the sealed release.

## Three separate products

- [Research Toolkit](https://github.com/LKVexa/Research-Toolkit)
- [Research Workbench](https://github.com/LKVexa/Research-Workbench)
- [Coding Agent Platform](https://github.com/LKVexa/Coding-Agent-Platform)

Each repository has its own application, state, version and release evidence.
The shared foundation is pinned within each release. Original deliveries and
the earlier local release packages remain preserved separately.

## License and attribution

See [LICENSE](LICENSE), [NOTICE](NOTICE) and [COPYRIGHT](COPYRIGHT).
GPL version 3 applies to the authored software and supplied authored material;
existing third-party notices and explicit dataset permissions are preserved.
