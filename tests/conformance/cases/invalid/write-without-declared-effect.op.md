---
id: sample.thing.silent
title: Writes something but says neither what nor where
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null

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
    method: POST
    path: /v1/things/{id}/act

data:
  entities: [thing]
provenance: 
  activity_kind: thing_touched
reversibility: reversible
---

`data_transition: null` says the lifecycle state does not move. Then either the card lists what it does change, or it declares itself a pure read. Silence on both is how a write disappears from the catalogue.
