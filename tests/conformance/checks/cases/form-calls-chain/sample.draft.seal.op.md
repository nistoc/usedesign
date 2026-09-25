---
id: sample.draft.seal
title: Seal the draft under a name
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: draft, to: sealed }
concurrency:
  mode: none_by_design
  rationale: One author, one draft.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: The name is fixed and the draft is sealed
interfaces:
  rest: { transport: http_rest, method: POST, path: "/drafts/{id}:seal" }
data:
  entities: [draft]
provenance: none
reversibility: irreversible
---
First step of the chain: the chain departs from where this one does.
