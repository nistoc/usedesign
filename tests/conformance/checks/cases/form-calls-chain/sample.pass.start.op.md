---
id: sample.pass.start
title: Start a pass over a plan
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: absent, to: active }
concurrency:
  mode: none_by_design
  rationale: One author, one draft.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: The pass is created
interfaces:
  rest: { transport: http_rest, method: POST, path: "/passes" }
data:
  entities: [pass]
provenance: none
reversibility: irreversible
---
Third step, over another entity: departs from `absent`.
