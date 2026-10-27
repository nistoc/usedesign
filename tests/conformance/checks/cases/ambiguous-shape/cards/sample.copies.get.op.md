---
id: sample.copies.get
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
    path: /v1/copies/{copyId}
    responses: [200, 404]

data:
  entities: [copy]
provenance: none
reversibility: not_applicable
---

The older of two cards for one route. Its replacement, `sample.copies.show`, declares the same
route as `/v1/copies/:id`, and neither carries a `dispatch`: the checker cannot say which of the
two describes what the code serves.
