---
id: sample.loan.borrow
title: Borrow a copy
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: available, to: on_loan }
concurrency:
  mode: none_by_design
  rationale: One copy, one borrower; the store rejects a second write on the same key.
  source: docs/design.md:1
steps:
  - id: s1-member
    text: The member is recognised
    on_violation: { error: unauthorized, http: 401 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /loans
    responses: [200, 401]

data:
  entities: [loan]
  storage:
    - store: library-loan-*
      keyed_by: [LoanId]
      via_index: gsi-borrower
      note: The store name is a PATTERN — a card that named `-dev` would be false in production.
provenance: none
reversibility:
  reversible_via: sample.loan.return
---

The store is named a letter short — `library-loan-*` for `library-loans-*`. The pattern matches
no store the storage has, so the claim, its key and its index describe nothing.
