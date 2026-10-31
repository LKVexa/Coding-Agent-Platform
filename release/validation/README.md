# Validation evidence

The release contains 81 automated checks: 11 evaluator checks, 9 provider checks, 6 workflow scenarios, 15 independent boundary tests and 40 exact-package/launcher checks. Nine correct/no-op/regression controls are recorded separately. Three real model tasks on the exact relocated package were independently replayed with Git and the frozen evaluator.

The development test sources preserve their original setup and paths for audit. They are not a separate installed test runner. Use the application runbook for supported reproduction: doctor, demo, run, inspect, replay, export and the original-foundation selftest. The saved final run state can be replayed without a model call using this exact package; its original repository paths remain provenance, while replay uses the saved source snapshot.

The authored evaluator cases and local example reports are non-secret diagnostic data withheld from the model during execution. Customer task data and credentials are not included. Provider failures retain sanitized status and validated responses; raw CLI diagnostics and malformed response bodies are intentionally discarded.

Manifest file SHA-256 and canonical JSON digest are separate identities. The application stores the canonical digest in run requests. The outer release manifest records both so line-ending differences in manifest serialization are unambiguous.
