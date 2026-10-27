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
provenance: none
reversibility:
  reversible_via: sample.loan.return
---

The card names its entity and no store yet — written before anyone described the storage. The
inventory beside it lists no store at all: nothing in this run can disagree with anything, and
that is exactly why an empty inventory is an error of its own.
