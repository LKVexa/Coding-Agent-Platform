# Preservation plan

Inventory and SHA-256 hash the original D0001–D0008 files before source execution. Never invoke a legacy writer or runner against its original delivery. Reject linked/reparse sources during copying. Copy only reviewed selected code and metadata into the isolated foundation directory. Record original paths and byte hashes for every vendored source.

Adapters emit JSON to stdout and execute from isolated run directories. The coordinator writes only to a user-selected state root after rejecting protected roots, links and path escapes. No runtime import path points at the originals. Before delivery, compare the original tree against the initial inventory and report any additions, removals or changed hashes, including externally caused changes without assigning them to this workflow.

All implementation changes can be discarded by removing the isolated product workspace; source restoration is unnecessary. Released packages are immutable. Run evidence remains separate from application files and survives upgrades/removal.
