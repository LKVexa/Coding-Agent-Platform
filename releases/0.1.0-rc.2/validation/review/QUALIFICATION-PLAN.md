# Coding CLI discovery refresh: independent review

The parent diagnosis found that the managed Codex executable still matches the approved SHA256 `3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16` and reported version `codex-cli 0.166.0-alpha.5.1`. The original provider resolves only `shutil.which('codex')` and reports the same `cli_mismatch` for a missing PATH entry and wrong bytes. A path change alone cannot cause rejection when `which` still finds identical approved bytes. This refresh therefore needs executable-discovery qualification; it does not justify changing the approved binary, model, catalog, or tool settings.

## Release criteria

1. An explicit `CODING_AGENT_CODEX` path is absolute, a native executable, free of links/junctions, and hash-approved. An invalid explicit selection fails immediately rather than silently using another installation.
2. Automatic discovery considers PATH, then only direct managed build directories under `LOCALAPPDATA/OpenAI/Codex/bin` (with declared user-home fallback). Wrong candidates are never executed. Only a byte-exact approved executable may be selected; discovery does not relax the version check or add a generic version-only allowlist.
3. Missing files produce `cli_not_found`; found but unqualified candidates produce `cli_mismatch`. Both doctor and proposal paths use the same resolver. Existing schema, model, timeout, cancellation, output, and credential-boundary checks continue to pass.
4. The user-facing PowerShell/CMD launch path works when Codex is absent from PATH. A bounded actual proposal, independent evaluation, replay and aggregate patch export succeed with the unchanged approved CLI, and provider metadata records the same approved runtime/model/catalog.
5. New release/application manifests bind the changed provider and docs. Original releases, source deliveries and the other products remain untouched. New state/evidence is separate; historical sealed runs retain their original pins.

## Fresh local tests

`tests/test_provider_refresh.py`: 25 tests; all original nine provider checks retained at the resolver seam, two explicit version gates, and fourteen discovery cases. Resolver tests use fake files under a temporary test directory and temporarily substitute a test-only hash. `_capture` is forbidden during resolution. The only child processes in this suite are Python fixtures for output cap, timeout and cancellation; no CLI or model calls are made.

`tests/integration.py`: six original fake-provider integration tests copied without changes. They validate patch/replay/export/resume, two attempts using public feedback only, private regression rejection, provider error preservation, cancellation and custom-task private evaluation. The copied script's relative imports now resolve to `work/coding-cli-refresh/src`. It writes fresh test evidence under `work/coding-cli-refresh/tests`; it does not modify old tests or old releases.

After the parent marks the candidate ready:

```powershell
& 'C:/Users/russe/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -I -B 'work/coding-cli-refresh/tests/test_provider_refresh.py'
& 'C:/Users/russe/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -I -B 'work/coding-cli-refresh/tests/integration.py'
```

The platform constructor in integration verifies the candidate manifest, so the candidate must be assembled before that suite runs. Commands should be captured in new refresh evidence files. Tests have not been run as part of writing this plan.

## Existing broader qualification material

The original `provider-research/probe_module_transport.py` probes the exact provider argument builder against a credential-free localhost Responses endpoint. It confirms no tools, no Authorization header, a structured output schema, excluded project/config canaries, and known inherited global guidance. `pure_prompt_isolation` remains false. Because the executable/catalog/settings remain byte-identical in this refresh, the original behavioral qualification still applies; a new loopback run is optional extra evidence rather than a requirement to rediscover the unchanged runtime.

If copied for a future binary change, improve two assertions: inspect decoded request strings rather than serialized JSON when checking Windows evaluator paths (JSON backslash escaping can conceal a match), and count every `SKILL.md` occurrence rather than the original `SKILL.md)` literal. Keep only safe counts/booleans, never entire request bodies or credentials. Do not rerun `probe_tools.py` in its original directory: it overwrites its catalog and discovery evidence.

Original `independent-review/test_platform_boundaries.py` has 15 broader fake-provider tests, but its hardcoded ancestor paths require adaptation in a new workspace. Original `release-validation/package_acceptance.py` hardcodes the old app path and old manifest pin. It must be copied and repointed before use; otherwise it tests the old release and writes into historical validation folders. The narrowed change does not need these suites to be rerun unless it changes repository/state/evaluator behavior.
