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
  rationale: >
    The caller sends no revision. The handler reads the request, decides, and writes only over the
    revision it read — a conditional write on the stored updatedAt; a writer that got in between
    is refused with 409 request_changed, and their write stays.
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

The seventh mode. Before round 29 this card could only say `none_by_design` — "no protection
needed" — and then explain in `rationale` that a conditional write does protect it: the caller
needs no revision because the server keeps its own. The label said the opposite of the code.
