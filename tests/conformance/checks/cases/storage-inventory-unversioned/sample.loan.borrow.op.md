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
    - store: library-loans-*
      keyed_by: [LoanId]
      via_index: gsi-borrower
      note: The store name is a PATTERN — a card that named `-dev` would be false in production.
provenance: none
reversibility:
  reversible_via: sample.loan.return
---

The card claims a store, its key, and the index it depends on; the inventory agrees. The second
store in that inventory is touched by nobody, which is the mirror of a wild endpoint and earns a
warning: what do we keep that no description accounts for?
