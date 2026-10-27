---
id: sample.loans.get-one
title: Read one loan
scenario: sample.flow
actors: [librarian]
maturity: designed
data_transition: null
concurrency:
  mode: none_by_design
  rationale: Read-only; two reads cannot collide.
  source: docs/design.md:1
steps:
  - id: s1-loan-exists
    text: The loan exists
    on_violation: { error: loan_not_found, http: 404 }

outcomes:
  - id: loan_open
    means: The loan is still running
    http: 200
  - id: loan_closed
    means: The loan was returned; only its record remains
    http: 410

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/loans/{loanId}
    responses: [200, 404, 410]

data:
  entities: [loan]
provenance: none
reversibility: not_applicable
---

The card whose outcomes name a status of their own and whose path carries a parameter, so the gen
test sees `parameters` and a description taken from `outcomes[]`.
