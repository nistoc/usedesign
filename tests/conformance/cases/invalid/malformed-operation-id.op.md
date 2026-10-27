---
id: sample.checkout
title: Check out a copy
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
    path: /v1/copies/{copyId}:checkout
    responses: [200, 401]

data:
  entities: [copy]
provenance: none
reversibility: irreversible
---

An operation id of two segments — the area and the action, with no object between them. Ids are
`<area>.<object>.<action>`: every `reversible_via`, `serves_step` and `calls` names a card by its
id, and an id short of a segment collides with the next operation on another object that takes
the same action.
