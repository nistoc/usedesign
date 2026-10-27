---
id: sample.session.finish
title: Finish the session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: active, to: finished }
concurrency:
  mode: none_by_design
  rationale: One athlete, one pass.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: Totals are written
interfaces:
  rest: { transport: http_rest, method: POST, path: "/session/{id}:finish" }
data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.resume
---
Undone by `sample.session.resume`, which this set describes: nothing is said.
