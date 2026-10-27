---
id: sample.batch.delete-many
title: Delete a list of things
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: any, to: deleted }
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one.
  source: docs/design.md:1
steps:
  - id: s1-authorised
    text: The caller may delete things
    on_violation: { error: forbidden, http: 403 }
  - id: s2-exist
    text: Every listed thing exists
    on_violation: { error: thing_not_found, http: 404 }
  - id: s3-unlocked
    text: No listed thing is locked
    on_violation: { error: thing_locked, http: 409 }
  - id: s4-delete
    text: The listed things are removed

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    responses: [200, 403, 404, 409]
    dispatch: { by: op, value: delete }

data:
  entities: [thing]
provenance: none
reversibility: irreversible
---

One of two operations that share the route `POST /v1/things:batch`. The gen test expects it to be
merged with its sibling into a single OpenAPI operation, with the response descriptions unioned.
