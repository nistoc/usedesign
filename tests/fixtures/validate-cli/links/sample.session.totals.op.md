---
id: sample.session.totals
title: Read the totals of a session
serves_step:
  operation: sample.session.finish
  step: s1-commit
  purpose: Show what finishing will write, before it is written.
actors: [athlete]
maturity: conceived
data_transition: null
mutates: []
concurrency:
  mode: none_by_design
  rationale: A read.
  source: docs/design.md:1
steps:
  - id: s1-read
    text: The totals are read
interfaces:
  rest: { transport: http_rest, method: GET, path: "/session/{id}/totals" }
data:
  entities: [session]
provenance: none
reversibility: not_applicable
---
Serves a step of `sample.session.finish`, which this set describes: nothing is said.
