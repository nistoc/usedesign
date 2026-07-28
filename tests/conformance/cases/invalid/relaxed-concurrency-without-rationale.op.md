---
id: sample.thing.unguarded
title: Relaxes locking without saying why
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

Every weakening must be explained. A silent relaxation is a spec bug, because the next reader cannot tell a decision from an omission.
