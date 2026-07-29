---
id: sample.thing.availability
title: Is the thing available
serves_step:
  operation: sample.thing.act
  step: s1-check
  purpose: Show the obstacle before the attempt, rather than as a rejection.
actors: [operator]
maturity: conceived
data_transition: null
mutates: []
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/things/{id}/availability

data:
  entities: [thing]
provenance: none
reversibility: not_applicable
---

A helper with no scenario of its own. `serves_step` is the alternative to `scenario`, not an addition to it.
