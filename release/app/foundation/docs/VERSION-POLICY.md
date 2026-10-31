# Independent version policy

The prompt pack remains 1.0.0. This is a new shared foundation 0.1.0-rc.1 and a separately identified new workbench 0.1.0-rc.1. Their coincident initial version numbers do not couple future releases. Source delivery IDs, historical harness versions, original catalog versions and scientific protocols remain unchanged in provenance. The coding-agent and research products remain unversioned and deferred.

Before 1.0, patch increments preserve interfaces; minor increments may introduce documented breaking contracts with explicit migration. After 1.0, incompatible public contracts require a major increment. Added compatible capabilities use minor increments and compatible fixes use patch increments. A prerelease must still pass all mandatory acceptance for its advertised scope.

Candidates are built into new directories. The final release manifest pins exact content, adapter versions and schemas. Once accepted, the package is immutable. Changing code, baseline, version strings or included data requires a new candidate and affected validation. Scientific protocol revisions never overwrite historical results.
