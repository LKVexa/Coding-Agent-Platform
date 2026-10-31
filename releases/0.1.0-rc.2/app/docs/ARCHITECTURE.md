# Architecture and component inclusion

## Data flow

1. Validate the product and frozen foundation, task schema, state destination and committed repository baseline.
2. Read the permitted source file and create a separate baseline/candidate workspace.
3. Build bounded provider context from the public task and selected source. Invoke the authenticated provider without a model tool catalog.
4. Parse the proposal as data, validate its identity and single-file scope, then evaluate its supported syntax against public examples. At most one additional proposal may use this public feedback.
5. Freeze the selected candidate. Run independent private checks and compare failing and already-passing baseline cases.
6. Save the outcome and export the replacement, unified diff and review evidence. Verify that the original repository is unchanged.

Provider output never becomes a shell command. Candidate source never becomes a Python module. The platform uses trusted Git operations to identify and read a committed snapshot; it does not run repository hooks, test programs, dependency installers or build scripts as part of candidate evaluation.

## Boundaries

| Area | Responsibility | Excluded authority |
| --- | --- | --- |
| CLI and task parser | Validate explicit run inputs and budgets | Expand scope from repository instructions |
| Repository adapter | Read a committed baseline and selected source | Modify the original repository |
| Provider adapter | Obtain bounded proposal text from the configured real model | Shell, file, browser, connector or other model tools |
| Proposal validator | Enforce task identity, path, baseline and replacement limits | Accept arbitrary patch operations |
| Numeric evaluator | Interpret the permitted AST and score supplied cases | Import or execute arbitrary Python |
| Evidence/export writer | Save run outcomes and review artifacts in separate state | Merge, deploy or overwrite historical deliveries |
| Foundation dependency | Supply pinned contracts, integrity/path helpers and registry | Grant executable status to historical records |

## Why these building blocks are included

`component_foundation.safety` supplies bounded JSON parsing, duplicate-key rejection, canonical hashes, path checks, protected state handling and atomic evidence operations. The platform must still validate its own repository and proposal semantics; generic helpers alone do not establish safety.

`component_foundation.contracts` validates the explicitly supported JSON Schema vocabulary. Product schemas must stay within that vocabulary or receive an explicit independent validator. It is not a claim of full JSON Schema support.

The component registry supplies traceability to the original deliveries. Preserving raw historical fields prevents the new product's narrower evidence from being mistaken for completion of old training, integration or research claims.

The frozen foundation includes D0007 C0322-01 and C0322-02 authored initial/correct/regressive diagnostics. This product's `selftest` invokes C0322-01's correct and regression cases to check the known regression semantics. C0322-02 remains a preserved foundation capability. Neither diagnostic authors repository changes or substitutes for the real provider and independent numeric evaluator.

The AST evaluator, task corpus, provider boundary, repository snapshot handling and patch export are product-owned integrations. They are versioned and tested with this product. Unsupported delivery components stay reference material in the frozen registry; they are not silently run or merged into the platform.

## Separate lifecycles

The package is a fixed versioned input. Runtime state is an explicitly chosen external directory. Each attempt retains evidence even when it fails; later success does not replace earlier outcomes. Product versions, run identifiers, provider model identity and evaluator protocol versions are distinct values.

Private checks remain on the evaluator side. The selection stage sees public cases only. A held-out result may appear in local final evidence, but it must not be fed back to choose or revise that candidate. Exported reports may therefore contain private checks and should be shared deliberately.

The sibling workbench release and reserved research root are outside this product's source, state and package. They receive no implicit version bump or gate update.
