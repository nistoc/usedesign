---
id: sample.thing.transportless
title: Interface omits its transport
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked

interfaces:
  rest:
    method: POST
    path: /v1/things/{id}/act

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

Without `transport`, an HTTP status on a refusal is meaningless for protocols whose errors are numeric RPC codes — and the reader cannot tell which kind this is.
