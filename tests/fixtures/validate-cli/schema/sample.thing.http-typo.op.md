---
id: sample.thing.http-typo
title: Act on a thing
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
    on_violation: { error: precondition_failed, http: 4120 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

`http: 4120` — a status written with a digit too many. No rule reads the number, so only the
schema refuses it (`maximum: 599`).

Before 1.4.3 the Python prototype had no schema layer and called this card valid, while the
TypeScript implementation reported a `schema_violation`. The conformance corpus holds no card the
schema alone refuses, so it never showed; `run.sh` compares what both print for this directory.
