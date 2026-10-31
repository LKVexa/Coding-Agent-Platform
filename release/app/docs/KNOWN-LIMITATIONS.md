# Known limitations

- The first release handles one declared Python source file containing a bounded numeric function. It does not run arbitrary Python, repository test suites, package installs, builds, loops, imports, attribute access or general application code.
- It requires a committed Git baseline and a separate writable state directory. Unsupported repositories, linked paths and changed baselines must be rejected rather than interpreted loosely.
- Model proposals depend on the installed pinned Codex runtime, supported configuration and existing ChatGPT authentication. Provider availability, latency and model behavior may change. A runtime/model mismatch requires a fresh compatibility decision and tests.
- The provider CLI retains built-in instructions and may inherit global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md` guidance even though project documents, user configuration and skills are disabled. The verified environment reported global guidance absent. Model tools remain absent; global guidance can still influence proposal text on another installation.
- At most two proposals are allowed. Only public examples inform a retry. The platform may finish with a failed or rejected candidate; it cannot guarantee a repair.
- `provider_calls` counts provider CLI invocations. The native provider transport may internally retry transient network failures within a call's timeout, so this value is not an exact count of remote requests. Cancellation or timeout does not imply zero remote usage.
- The two development tasks and one held-out diagnostic task are authored examples. Their results are not a SWE-bench score, general coding-quality estimate, training result or reproduction of original scientific claims.
- Custom task/check specifications can be incomplete or wrong. Independent evaluation means evaluation is separate from proposal generation; it does not prove the user's supplied specification is correct.
- Provider requests transmit the selected source and public task. The platform does not promise offline operation or automatic detection/removal of secrets embedded in that content.
- Local private checks are outside model context but accessible to the local operator. Final reports may reveal them. Repeated manual reruns after inspecting held-out evidence are no longer an untouched held-out evaluation.
- Cost is reported as `null`; no per-request monetary price is inferred from a subscription or model name. Usage counts are only as reliable and complete as the provider's reported metadata.
- Exported replacement source and a unified diff require human review and separate application. There is no automatic apply, merge, publishing or deployment workflow.
- Local hashes and separate state are integrity controls, not protection against a compromised host or someone who can replace the trusted program and manifests together.
- Original delivery statuses, exclusions, failures and scientific-validation gaps remain unchanged. The frozen registry is a historical record, not an assertion that every component executes in this product.

Read the release's gate/status files for observed limitations, unavailable checks and the exact runtime used. This document deliberately does not infer acceptance from a version label.
