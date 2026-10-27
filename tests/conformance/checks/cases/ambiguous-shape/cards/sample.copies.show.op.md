---
id: sample.copies.show
title: Show one copy
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: Read-only query; nothing to collide with.
  source: docs/design.md:1
steps:
  - id: s1-found
    text: The copy exists
    on_violation: { error: not_found, http: 404 }

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/copies/:id
    responses: [200, 404]

data:
  entities: [copy]
provenance: none
reversibility: not_applicable
---

The replacement of `sample.copies.get`, written for the same route in the framework's own
parameter syntax. The old card was never removed.
