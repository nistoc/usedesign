---
id: sample.draft.publish
title: Publish the sealed draft
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: sealed, to: published }
concurrency:
  mode: none_by_design
  rationale: One author, one draft.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: A published version is cut
interfaces:
  rest: { transport: http_rest, method: POST, path: "/drafts/{id}:publish" }
data:
  entities: [draft]
provenance: none
reversibility: irreversible
---
Second step: departs from `sealed`, a state the step before it left and no screen state shows.
