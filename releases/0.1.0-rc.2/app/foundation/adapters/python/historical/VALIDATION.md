# C0081-03 VALIDATION

Each check has an independent expectation (direct calculation, alternative implementation, analytic identity, or constructed case). `kind=evaluation` rows are measured outcomes; `blocked_prerequisite` rows are unverified.

| check | kind | description | expected | observed | result | evidence |
|---|---|---|---|---|---|---|
| known_example | independent | hand-counted trajectory: 7+3+4 | 14 | 14 | pass | evidence/records.json#/checks/known_example |
| empty | independent | empty trajectory counts 0 | 0 | 0 | pass | evidence/records.json#/checks/empty |
| recomputable | independent | matches collections-free recount | 605 | 605 | pass | evidence/records.json#/checks/recomputable |
| unknown_role | independent | unknown role rejected | raises ViolationError | ViolationError: unknown token role(s): ['sys'] | pass | evidence/records.json#/checks/unknown_role |

## Failure and revision log
- no failing check required repair (1 iteration)
