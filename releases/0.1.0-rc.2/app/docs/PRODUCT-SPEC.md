# Coding Agent Platform — product contract

This product turns a bounded repository task into a model-proposed source change, an independent evaluation and a patch for review. The platform has its own version, state, manifest and release gates. The Local Component Workbench and research toolkit are separate products.

## Supported first release

The command interface accepts `run --repo PATH --task ID_OR_JSON --checks PRIVATE_JSON --state ROOT`. Built-in task IDs select authored diagnostic presets. A custom task JSON selects one source file, a named numeric function, parameters, the requested behavior and public examples. Private checks are provided separately. Exact fields and optional switches are defined by the shipped command help and schemas.

The repository must provide a committed Git baseline. The platform reads the selected baseline and creates a separate candidate workspace under its state directory. One declared source file may change. The original repository is never a patch destination. Export contains the replacement source, unified diff and evaluation evidence; applying, merging, publishing and deployment are user-controlled steps outside this product.

The first language profile contains bounded Python numeric functions. It supports local assignments, conditional returns, comparisons, arithmetic and the specific pure numeric calls admitted by the evaluator. It excludes imports, attributes, collections, loops, arbitrary call targets and filesystem, network or process operations. The evaluator walks a validated syntax tree; it never imports or executes candidate Python with `exec` or `eval`.

## Proposal and evaluation contract

The provider adapter uses the installed Codex runtime with existing ChatGPT authentication. Its configured model catalog exposes no model tools. The provider receives the task, selected source, public examples and bounded public-check feedback. It receives no private checks, hidden expectations, unrelated repository files or saved credentials as prompt content.

A run permits at most two real proposals. Public evaluation may inform the second proposal. Independent private evaluation occurs after candidate selection and cannot become retry feedback. A model's claim that tests passed has no effect on evaluator results. Missing provider access, malformed output, failed checks and resource limits produce explicit outcomes; a scripted response is never evidence of a real provider run.

The diagnostic preset set has two development tasks and one held-out task. These small authored exercises demonstrate the workflow only. They are not a general coding benchmark or evidence of scientific reproduction. Custom task quality depends on the caller's task and checks.

## Foundation use and preservation

The platform pins shared foundation `0.1.0-rc.1` to manifest SHA-256 `e01d3f340239f4abe0daa27cb3e7c64190f95f4f3a0419f493bc14e7b07d571d`. Reuse is limited to the verified safety helpers, strict contract validator, component registry and authored D0007 regression diagnostics. The registry's historical execution, completion, gate and scientific-validation fields remain intact. Product success cannot promote the original delivery claims.

D0001–D0008, their technical notes, the shared release, workbench release and reserved research root remain preserved. A shared dependency upgrade requires a new shared release and a deliberate change to this product's pin. Candidate state and exported patches cannot be placed in those protected roots or in the product package.

## Evidence and release meaning

Run evidence identifies the baseline, source and proposal hashes, actual provider/model metadata, attempts, selected candidate, public results, final independent results and exported files. Usage is recorded only when supplied by the provider. Monetary cost remains `null` because authenticated usage does not supply an independently verified price for each request.

Acceptance requires fresh integrity checks, a real-provider repair workflow, independent fail-to-pass and pass-to-pass checks, a deliberately regressive control, boundary tests, patch replay and post-build preservation evidence. Gate files and release status determine what actually passed. This contract does not assert any gate result.
