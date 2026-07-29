---
id: sample.thing.lookup
title: Look something up, and claim it can be undone
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: Read-only.
  source: docs/design.md:1
steps:
  - id: s1-exists
    text: The reference resolves
    on_violation: { error: not_found, http: 404 }

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/things/{id}
    responses: [200, 404]

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

Structurally valid, and quietly nonsense: the operation does nothing, so there is nothing to
undo. `reversible` here answers a different question than the one asked.

Both read-only cards in this project said exactly this until round 7 — not from carelessness,
but because `reversibility` is required and had no honest value for a read. A format that
requires an answer must supply one that is true.
