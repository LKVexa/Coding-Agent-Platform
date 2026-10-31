# Rollback and recovery

The platform exports review artifacts and writes candidate copies in its own state directory. A normal run does not change the source repository, so returning to the original source requires no reverse patch. Confirm this using the run's recorded baseline and post-run preservation evidence.

Keep each versioned package immutable. To stop using a version, stop its active runs and select the previous known-good package with its recorded foundation pin. Do not copy individual executables or modules across releases. Never point an older program at state from a newer schema unless compatibility is explicitly documented.

Keep incomplete and failed run folders for diagnosis. A stopped run is not a successful run. Resume only through a supported command whose recovery semantics are documented; otherwise start a fresh run identifier from the recorded baseline. Do not edit an old report or erase an earlier failed proposal to make the new result appear continuous.

If a patch was applied manually outside this platform, use the repository's normal review and version-control process to revert that separate change. The platform does not reset a user's working tree or discard their edits.

If integrity verification fails, do not repair the published package in place. Preserve the failed check, restore a complete known-good version from its trusted release artifact, and rerun integrity checks before use. A shared-foundation change requires a separately released version and updated consumer pin.

Archiving or deleting runtime state is a separate operator decision. Check the resolved destination and keep evidence required for later review. Original deliveries, shared and sibling releases, and the research root are never cleanup targets.
