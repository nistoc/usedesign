---
id: sample.session.delete
title: Delete the training session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition:
  from: any
  to: deleted
concurrency:
  mode: none_unexplained
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised before the store is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-tombstone
    text: deletedAt is set; a second call writes nothing

interfaces:
  rest:
    transport: http_rest
    method: DELETE
    path: /session/{id}
    responses: [204, 401]

data:
  entities: [session]
provenance: none
reversibility: irreversible
---

`none_unexplained` without a `rationale` is an absence without its measurement: which neighbours
require a precondition, what was searched for and not found. The mode exists to record what was
seen; a bare label records nothing.
