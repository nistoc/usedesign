---
id: sample.draft.rename
title: Rename the draft
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: null
mutates: [name]
concurrency:
  mode: none_by_design
  rationale: One author, one draft.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: The new name is stored
interfaces:
  rest: { transport: http_rest, method: PATCH, path: "/drafts/{id}" }
data:
  entities: [draft]
provenance: none
reversibility: reversible
---
A write without a state change: `mutates` names the field. Not a read.
