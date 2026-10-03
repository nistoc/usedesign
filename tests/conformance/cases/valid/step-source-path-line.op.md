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
    source: src/things/ActHandler.ts:12

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

The spelling 1.2 demanded still passes: `path:line` is one of the three forms of a `source`
(§5.7). Relaxing the field to a path alone must not narrow it — an implementation that swapped
one pattern for another and stopped accepting a position would fail here.
