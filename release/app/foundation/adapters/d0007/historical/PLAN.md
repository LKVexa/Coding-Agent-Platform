# D0007 C0322 bounded P2P protocol, fixed before execution

(C) 2026 RUSSELL PHILIP SMITHSON. Author-only plan. No compilation, execution or product mutation has been performed by this author.

## Source, scope and completion boundary

Primary source: retained FrogNano v2 HTML, https://arxiv.org/html/2609.07925v2, section3 paragraphs S3.p2 and S3.p3; prepared copy raw-sources/frognano-2609.07925v2.html under Tools-harness-cs/preparation/D0007. SHA2566b4a629a61af45f208e7cd5e4fcba60f9d5961812bcfe66178b0e767b0eb090c,628270bytes. The inspected paragraphs define F2P tests as failing on the original and passing after the gold patch while existing P2P remains stable. They describe gold patches and generated F2P tests/outcomes as hidden from the solver. This supports the distinction and information boundary; it does not make authored examples original TaskPilot data.

Originals:
- C0322-01 Passing tests, payload F05836; SHA93d847e8d89a28dc4dc49cda84dc91fbf8da09b5374c299a94c803e1f4f74c3c,22762bytes. Data/records work type.
- C0322-02 Regression preservation; SHAccd256a383d0d3205df19c8d08cc3f68c2e561d76def52ea0f8d0dad86bf7664,22844bytes. Workflow/operation work type.

PROMPTS.json SHA c81806dd037630273b3f4722a7fcc030fe04f953a3402b2142d5961cbeb6cb13 preserves each typed contract and native8stage workflow. PREPARATION.json SHA699c091ba0fcb20aa39f0f848039ab1927871023a47e633ec7a700b8f4efa196. The implementation must retain both exact original prompts, source locators, identities and this protocol in each generated package. Every pair retains PROMPT-VERSION-MISMATCH: original pre-v3 source used.

Selected scope is an authored bounded P2P dataset and executable preservation step, permitted by the originals' explicit fixture-substitution clauses. It is not a faithful reproduction of TaskPilot, a repository benchmark, generated F2P data, model training, model selection, an RL result or an external deployment. The original native acceptance criteria are applied to this declared bounded artifact, not silently replaced by generic metadata checks. Component completion may be supported only after actual qualified execution, all scoped criteria, meaningful negative checks and replay evidence pass. Real parent integration remains unverified/fixture_tested separately. No blanket PARTIAL or COMPLETE result is assigned before evidence.

The frozen D5 OracleCoverage raw source (prepared copy SHA2402328bd364c1e82d494711c1b61ef0fe2ef4cfd1705bbb9f511c136166a547) informs only DEV Clamp fixture definitions. Fresh C0322 code and records are authored here. No D5 PARTIAL producer output is accepted as a completed dependency.

## Fixed two-group dataset and information boundary

There are two distinct task identities and task groups:
- DEV-CLAMP, task version clamp-v1, group DEV-CLAMP, split development, Int32 arguments/result.
- FINAL-MAGNITUDE, task version magnitude-v1, group FINAL-MAGNITUDE, split final-evaluation, Int32 argument and Int64 result.

Groups must never cross splits. Distinct task identities are an engineering partition, not a claim of statistical independence. All candidates and expected outcomes are fixed here before any DEV or FINAL result. There is no fitting, calibration, tuning or model/candidate selection based on either split.

Public input records contain exact case/task/version/group/split identity and integer argument arrays. Candidate methods receive only numeric arguments, never labels, transition kinds or observed outcomes. Evaluator labels reside in separate private-evaluator artifacts and a distinct literal oracle class. No actual solver is invoked; this enforces a method-interface boundary, not a claim of OS-level secrecy from arbitrary code reading artifact files.

| Case | Split/task | Arguments | Literal expectation | Initial category |
| --- | --- | --- | --- | --- |
| DEV-T01 | DEV-CLAMP | -2,0,5 | value:0 | P2P |
| DEV-T02 | DEV-CLAMP | 3,0,5 | value:3 | P2P |
| DEV-T03 | DEV-CLAMP | 9,0,5 | value:5 | F2P |
| DEV-T04 | DEV-CLAMP | 0,3,2 | exception:ArgumentException | P2P |
| DEV-T05 | DEV-CLAMP | 4,4,4 | value:4 | P2P |
| DEV-T06 | DEV-CLAMP | -2147483648,-10,10 | value:-10 | P2P |
| DEV-T07 | DEV-CLAMP | 2147483647,-10,10 | value:10 | F2P |
| DEV-T08 | DEV-CLAMP | 5,0,5 | value:5 | P2P |
| FINAL-T01 | FINAL-MAGNITUDE | -2147483648 | value:2147483648 | F2P |
| FINAL-T02 | FINAL-MAGNITUDE | -5 | value:5 | P2P |
| FINAL-T03 | FINAL-MAGNITUDE | -1 | value:1 | P2P |
| FINAL-T04 | FINAL-MAGNITUDE | 0 | value:0 | P2P |
| FINAL-T05 | FINAL-MAGNITUDE | 1 | value:1 | P2P |
| FINAL-T06 | FINAL-MAGNITUDE | 2147483647 | value:2147483647 | P2P |

Each task is executed against three predeclared compiled helper implementations: initial, correct, regression. DEV initial preserves invalid-bound rejection/lower clamping but returns the original value above the upper bound; correct clamps both ends; regression fixes the upper bound but returns lo for in-range values. FINAL initial negates in Int32 before widening, so MIN_VALUE overflows under explicit unchecked arithmetic; correct widens before negation; regression fixes MIN_VALUE but returns zero for other negative inputs. All 14cases x3versions =42 actual helper method calls whenever the experiment is invoked. No record stands in for an unexecuted call. Consumer and loader replay use retained outcomes and do not invoke helpers again.

Predeclared literal totals:
- DEV initial6/8, correct8/8, regression6/8. F2P set DEV-T03,DEV-T07; P2P six others. Correct F2P2/2,P2P6/6. Regression F2P2/2,P2P4/6; regressions DEV-T02,DEV-T08.
- FINAL initial5/6, correct6/6, regression4/6. F2P FINAL-T01; P2P five others. Correct F2P1/1,P2P5/5. Regression F2P1/1,P2P3/5; regressions FINAL-T02,FINAL-T03.
- Combined initial11/14, correct14/14, regression10/14. Correct passes F2P3/3 and P2P11/11. Regression passes F2P3/3 but P2P7/11.

Actual P2P/F2P membership is derived by comparing initial outcomes against independent literal expectations, then checked against these fixed category sets. The public candidate path cannot derive expected outputs by reusing candidate logic.

## Dataset, loader and provenance contract

The bounded population is exactly these14 declared authored cases and42 observed variant outcomes. Stable IDs join case, task, task version, split and variant. Inclusion excludes nothing silently:
- Raw inputs preserve all14 records.
- Raw outcomes preserve all42 actual calls, including wrong functional answers and expected exceptions.
- Processed passing-test slice contains11 initially passing P2P records only.
- Explicit exclusions retain the three initially failing cases, with their source IDs, actual initial outcomes, literal expected outcomes and reason excluded_from_P2P_initially_failing. They remain available to the F2P evaluator/control.
- Private labels preserve all14 literal expectations and declared category labels.
- A versioned manifest hashes raw inputs, raw outcomes, processed slice, exclusions and private labels; no self-referential digest.
- Each processed/excluded record binds its exact raw input/initial-observation fingerprints and unchanged identity.

Strict loaders validate exact field sets, types, IDs, version, numeric ranges/shapes, split/task/group consistency, the exact bounded record inventory and one observation per case+variant. Reject missing, duplicate, corrupt, unknown, wrong-version and mixed-split records. Do not coerce numeric strings or silently remove invalid records. Labels are joined by exact ID/version and independently checked against the literal oracle; swapping labels must fail. Unexpected runtime errors are invalid observations and cannot count as ordinary functional wrong answers.

Negative diagnostics are declared before execution: missing/extra field, string-instead-of-integer argument, wrong task version, duplicate case ID, missing case, unknown case, task-group crossing splits, corrupt observed outcome, unexpected execution state, duplicate observation, missing observation, wrong observation task/version, duplicate/swapped labels and mismatched provenance. Reordering valid raw records must preserve canonical processed identities and label alignment. Raw bytes remain unchanged by processing.

## Preservation consumer and failure-path contract

C0322-02 always declares a fresh_raw_fixture producer mode in this version; it regenerates and validates the raw authored fixture through the same producer pipeline. It accepts no prior product ledger or partial artifact as complete. This is the explicit sibling-unavailable substitution permitted by the original. A later completed-C0322-01 reuse adapter would have to validate COMPLETE status, exact original scope/version, producer ledger and every output hash; this version does not implement or claim that adapter.

The consumer receives the validated P2P records, exact case/outcome identity map, producer manifest hash and chosen predeclared variant. It checks every initially passing test remains passing, emits record-level before/after evidence and an explicit accepted/rejected result, and passes that structured report to a tiny downstream gate. No ambiguous truthy string or missing value is accepted.

Normal path: correct candidate preserves DEV6/6,FINAL5/5,combined11/11 P2P and downstream gate receives accept.
Regression path: regression candidate preserves DEV4/6,FINAL3/5,combined7/11, lists the four exact regressions and downstream gate receives reject.
Malformed/missing/duplicate/invalid outcomes must be rejected before an acceptance result; they are never omitted from the denominator.
The independent F2P-only control accepts the regression (3/3 repaired target cases), demonstrating why it is insufficient relative to the declared combined F2P+P2P criterion. The actual combined gate rejects it. This is a finite authored counterexample, not a statistical estimate or a claim about a trained system.
Replay the consumer from serialized validated inputs and compare canonical trace/result bytes; this replay requires zero additional candidate calls.

## Native criteria and stages, evaluated from actual evidence

Preserve the originals' exact eight-stage clauses in artifacts and provide a per-stage assessment with original criterion, evidence and result. Do not inherit D8's fixed incomplete-source assessment.

1. Verify meaning/scope: primary hash and exactS3.p2/p3 definition, original prompt contracts and bounded-fixture interpretation are established; unavailable reproduction inputs and their outside-scope consequences are explicit.
2. Establish inputs/interfaces/decisions: two immutable task groups, fixed split, literal oracle, candidate-only numeric interface, exact schemas/versions, malformed policy, bounded costs and dependency-substitution decision are recorded before execution.
3. Reference: the14 literal cases, P2P/F2P category sets and independent expected totals exist before invocation.
4. Artifact: actual42 calls, strict loader and producer transformation/operation perform their named roles with inspectable outcomes.
5. Independent validation: all relevant positive/negative checks pass, exact literal totals and regression IDs match, no label/split leakage or silently excluded failures occur.
6. Context integration: the bounded producer-to-consumer-to-downstream trace works for accept/reject and retains identities/manifest hashes. Real repository/TaskPilot parent integration remains unverified. The original permits component completion separate from parent integration and allows the remaining integration dependency to be precisely identified.
7. Resolve claims: intentional wrong candidates and unavailable reproduction claims remain visible; unforeseen implementation/check failures remain failures. No criterion is revised after outcomes.
8. Package/handoff: complete bounded evidence, reproducible reader/run procedure, deterministic serialization/consumer replay, independent qualification and safe writer verification permit handoff. The generic writer must provide actual file containment/hash/A1-A6 evidence; pure assembly alone is not a completed product delivery.

Pipeline.Build may return a reviewed candidate native assessment complete at8 only when every scoped stage/diagnostic actually passes; otherwise return the actual failed/partial result and earliest unmet stage with retained raw observations. Source/binding corruption refuses before work. Root's independent Tools qualification and the generic writer's mechanical checks remain mandatory before accepting the native package into a real product. A complete component does not make D0007 complete or deliverable.

## API and implementation boundary

Use C#5/.NET4.8 and frozen HarnessCommon.dll only. Pure API mirrors D8:
PreparationBindings.Load(preparationRoot,specRoot,versionRoot), then Pipeline.Build(exactPairId,bindings) -> Package { Dictionary<string,byte[]> Artifacts; Dictionary<string,object> NativeStatus }.
No file writes, network, process launches, model calls, queue access or product activation from the provider. Actual compiled helper calls occur inside Build and are recorded; no source generation is misreported as execution.

Bindings hash-check source HTML, prepared originals/PROMPTS/PREPARATION, this plan, current implementation source and all six audited spec files, then recheck before and after Build. The generic writer independently pins active ownership, passed preflight, compiler/harness/runner/source/policy/spec provenance, immutable outputs and ledgers. It must not overwrite native stages or infer completion from mechanical metadata alone.

Expose a read-only observation collector for qualification and a pure consumer API. Add independent isolated qualification entry source if needed; root alone compiles/runs it. Qualification must test known results, negative cases, two pair identities, native assessment consistency, deterministic replay ignoring only updated, source/spec pin changes and no writes. Each Build performs42 calls; report invocation counts honestly if qualification builds both pairs or replays them. Timing is not a learned-system benchmark.

All writes by the author remain in this new Tools version. Preserve originals before any later repair. At most3 repair attempts per failing check, unchanged acceptance criteria and retained prior outcomes. No Python, network, new spend or acceptance of D5 partial producers.
