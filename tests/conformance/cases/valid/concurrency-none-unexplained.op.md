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
  rationale: >
    The handler reads no If-Match. Its two neighbours — delete a set, delete an exercise —
    require one; no comment and no flag explain the difference. Measured, not designed.
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

The sixth mode. Before round 24 this card could only say `none_by_design` — an intent nobody
measured — and put the contradiction into `rationale`, where nothing checks it. Now the absence
has a name, and the warning keeps it visible in every run until someone explains it or adds a
precondition.
