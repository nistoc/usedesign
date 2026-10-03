---
id: sample.thing.act
title: Act on a thing
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked
    source: src/things/ActHandler.ts

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

A step's `source` names a file and nothing more. SPEC §5.7 already said that `source` is a
human aid no checker may rely on, and that a durable reference names a file rather than a
position — yet until 1.3 the schema demanded `path:line` here (issue #12). The pilot that filed
the issue named files only, because a line-numbered source had drifted 110 lines in silence.
