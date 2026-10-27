---
id: sample.session.progress
title: Read how far a session has gone
serves_step:
  operation: sample.session.start
  step: s1-open
  purpose: Show the plan of the pass as it starts.
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
    text: The progress is read
interfaces:
  rest: { transport: http_rest, method: GET, path: "/session/{id}/progress" }
data:
  entities: [session]
provenance: none
reversibility: not_applicable
---
Serves a step of `sample.session.start`, which no card in this set describes —
`undescribed_counterpart`, a warning.
