---
id: sample.thing.act
title: Act on a thing, returning a code it never declared
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked
    on_violation: { error: precondition_failed, http: 409 }
  - id: s2-audit
    text: The action is recorded
    on_violation: { error: audit_write_failed, http: 500 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act
    responses: [200, 409]

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

The card contradicts itself: a step returns 500 and `responses` does not list it. This exact
defect sat in the project's own reference example until round 7, unnoticed, because nothing
compared the two lists.
