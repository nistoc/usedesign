---
id: sample.draft.list
title: List the drafts
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
    text: The drafts are read
interfaces:
  rest: { transport: http_rest, method: GET, path: "/drafts" }
data:
  entities: [draft]
provenance: none
reversibility: not_applicable
---
A read: no transition, no `mutates`. Reread after every write.
