---
id: sample.request.cancel
title: Cancel a request
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition:
  from: [submitted, checking]
  to: cancelled
concurrency:
  mode: server_read_version
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised before the store is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-cancel
    text: The status becomes cancelled, written over the revision the handler read
    on_violation: { error: request_changed, http: 409 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: "/request/{id}:cancel"
    responses: [200, 401, 409]

data:
  entities: [request]
provenance: none
reversibility: irreversible
---

The seventh mode without its `rationale`: which revision the handler reads, how the write is
conditioned on it, and what a writer who got in between receives. Without them the label records
nothing a reader can check.
