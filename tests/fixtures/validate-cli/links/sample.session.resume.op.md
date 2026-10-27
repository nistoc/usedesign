---
id: sample.session.resume
title: Resume a finished session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: finished, to: active }
concurrency:
  mode: none_by_design
  rationale: One athlete, one pass.
  source: docs/design.md:1
steps:
  - id: s1-reopen
    text: The session is open again
interfaces:
  rest: { transport: http_rest, method: POST, path: "/session/{id}:resume" }
data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.finsh
---
Undone by `sample.session.finsh`, a typo for `finish` that no card in this set describes —
`undescribed_counterpart`, a warning.
