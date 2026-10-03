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
  source: docs/design.md#Concurrency
steps:
  - id: s1-check
    text: A precondition is checked
    source: src/things/ActHandler.ts#ActHandler.check

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

The form §5.7 prefers: a file and a symbol. A symbol survives every insertion above it; a line
number keeps resolving after one, to the wrong line, and nothing says so. `#Symbol` is a spelling
of `source` fields only — `maturity_evidence.implemented` and `variant_of.shared` still name a path,
optionally with `:line`.
