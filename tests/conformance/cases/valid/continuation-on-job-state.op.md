---
id: sample.request.create
title: Open a thread that waits for a person between machine turns
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: none, to: pending }
concurrency:
  mode: none_by_design
  rationale: Created fresh; nothing to collide with.
  source: docs/design.md:1

steps:
  - id: s1-body
    text: The request carries text
    on_violation: { error: invalid_body, http: 400 }

async_execution:
  job_states: [pending, checking, executing, done, failed]
  terminal: [failed]
  worker: request handler
  observe_via: GET /v1/requests/{id}

continuation:
  after: done
  resumed_by: human
  carries: the next message
  same_operation: false

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/requests
    responses: [200, 400]

data:
  entities: [request]
provenance: none
reversibility:
  reversible_via: sample.request.archive
---

Axes E and F on one record, which is why they are separate axes. The machine turn runs by
itself; between turns nothing moves until a human writes. `continuation.after` names a job
state, not an outcome — the case that round 8's rule rejected because it was written from a
single example.
