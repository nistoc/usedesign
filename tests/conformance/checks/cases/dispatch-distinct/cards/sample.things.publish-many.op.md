---
id: sample.things.publish-many
title: publish a list of things
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: any, to: publish }
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one.
  source: docs/design.md:1
steps:
  - id: s1-authorised
    text: The caller may write
    on_violation: { error: forbidden, http: 403 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    responses: [200, 403]
    dispatch: { by: op, value: publish }

data:
  entities: [thing]
provenance: none
reversibility: irreversible
---

One of several operations on a shared route.
