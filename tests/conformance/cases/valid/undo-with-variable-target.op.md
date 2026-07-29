---
id: sample.thing.unretire
title: Return a thing from retirement
scenario: sample.flow
actors: [curator]
maturity: conceived
data_transition:
  from: retired
  to: [draft, published]
  determined_by: the state the record held before it was retired
concurrency:
  mode: etag_required
  source: docs/design.md:1
steps:
  - id: s1-is-retired
    text: The record is currently retired
    on_violation: { error: invalid_transition, http: 409 }
  - id: s2-restore
    text: The record returns to the state it held before retirement, under the same id

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/unretire
    responses: [200, 409]

data:
  entities: [thing]
provenance:
  activity_kind: unretire
reversibility:
  reversible_via: sample.thing.retire
---

Every undo operation has this shape: it returns the system to where it was, not to where the
card says. A single constant `to:` would be false for half the records.
