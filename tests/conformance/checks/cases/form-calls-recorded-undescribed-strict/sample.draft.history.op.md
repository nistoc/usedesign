---
id: sample.draft.history
title: Read a draft's history, recording who asked
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
    text: The caller is recorded and the history read
interfaces:
  rest: { transport: http_rest, method: GET, path: "/drafts/{id}/history" }
data:
  entities: [draft]
provenance: 
  activity_kind: read_access
  attributed_to: caller
  records_only: true
reversibility: not_applicable
---
An audited read: `records_only` — it changes no domain data, and a reread is a reread whether or not the server records who asked.
