# Verified Codex proposal provider

The adapter uses the existing ChatGPT CLI login. It does not load API-key environment variables, copy credentials, or select a different model. It accepts bounded public task context and returns a JSON proposal for the host to validate independently. It never applies the proposal.

## Runtime API

`coding_agent.provider.propose(prompt, output_schema, run_dir, timeout=120, cancel_path=None)` returns `proposal`, `provider`, and `evidence`. `provider_info()` performs identity and login preflight without inference. `ProviderError` exposes a sanitized `code`, message, and available evidence paths.

The executable is pinned to `codex-cli 0.166.0-alpha.5.1` and SHA-256 `3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16`. The no-tools catalog is pinned to SHA-256 `8c88ee259973cae57cfd64953538d56c1d6b47ad22b8a7c4796bd1c69303dcda`. The adapter rejects a changed executable, version, catalog, or resolved model. The expected resolved model is `gpt-6.1-sol`; it is read from the CLI header, not overridden with `--model`. Backend model identity is not independently verified.

## Enforced boundary and residual trust

The pinned catalog removes shell, patch, search, and native agent tools. Explicit feature settings disable apps, plugins, MCP entry points, browser/computer use, image tools, hooks, code mode, memories, and tool suggestions. The provider starts in a new empty working directory, ignores user config and rules, disables project instructions, and retains authentication. The local capture using the adapter's command builder has no tools field and carries the declared JSON schema.

The CLI remains a trusted local process that can access its authentication storage. This is not operating-system file isolation. Its built-in model instructions and global `CODEX_HOME/AGENTS.override.md` or `AGENTS.md` guidance may be included. The adapter records that limitation and global-file presence without reading or copying their contents. Canary tests confirm project instructions/config are excluded and global guidance remains inherited. There are no skill resource entries in the captured prompt; generic skill guidance remains part of the pinned model instructions. No private evaluator path appeared in the capture. The evaluator and application must never supply private cases through the public prompt.

## Bounds and evidence

Prompt: 65,536 UTF-8 bytes. Schema: 32,768 bytes. Response: 131,072 bytes. Combined diagnostic buffers: 262,144 bytes. Timeout: 1–300 seconds, default 120, including identity/auth preflight plus bounded shutdown grace. Cancellation polls every 50 ms. Timeout, cancellation, or output overrun terminates the owned Windows process tree.

The adapter makes one application-level call and does not retry it. The pinned CLI can retry transient transport failures internally; the total timeout bounds those attempts. Built-in OpenAI provider retry overrides are rejected by this CLI and are therefore not used.

Only the declared schema, validated response, and sanitized metadata persist. Malformed or partial responses are removed. Raw diagnostic output and environment values are not persisted. Token usage is reported only when the CLI supplies it; cost is unknown/null for the existing ChatGPT subscription. A failed call records a safe error when its evidence directory is available. A changed CLI requires fresh tool-surface verification before updating the pins.

## Evidence

- `module-transport-probe.json`: exact-adapter local request capture, using an empty credential-free mock home and loopback endpoint; expected local HTTP error ends the probe without inference.
- `real-smoke-evidence/provider-a372b82abf964269a1cef69eea638c38/`: one authorized real ChatGPT call returning `{"message":"provider smoke test"}`; reported model `gpt-6.1-sol`, 4.906 seconds, CLI token count 4,753, cost unknown. Later adapter changes tightened metadata and instruction-discovery settings and were checked with the local capture.
- `test_provider.py`: nine tests covering cancellation, timeout, output cap, executable/catalog/model drift, environment stripping, schema validation, and global-guidance presence without content reads.

Do not include research mock homes, protocol dumps, downloaded source, diagnostic caches, or bytecode in the release. Runtime assets are `src/coding_agent/provider.py` and `src/coding_agent/resources/no-tools-models.json`; selected JSON evidence can be copied separately.

Primary references: [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [authentication](https://learn.chatgpt.com/docs/auth), [configuration schema](https://github.com/openai/codex/blob/main/codex-rs/core/config.schema.json), [tool registry construction](https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/spec_plan.rs), and [global-instruction configuration limitation](https://github.com/openai/codex/issues/42601).
