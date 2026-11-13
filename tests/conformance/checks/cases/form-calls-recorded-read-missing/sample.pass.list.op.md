---
id: sample.pass.list
title: List the passes
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: One author, one draft.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: The passes are read
interfaces:
  rest: { transport: http_rest, method: GET, path: "/passes" }
data:
  entities: [pass]
provenance: none
reversibility: not_applicable
---
A read.
