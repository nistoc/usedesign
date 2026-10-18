---
id: sample.session.archive
title: Archive the session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: { from: finished, to: archived }
concurrency:
  mode: none_by_design
  rationale: One athlete, one pass.
  source: docs/design.md:1
steps:
  - id: s1-commit
    text: The session is archived
interfaces:
  rest: { transport: http_rest, method: POST, path: "/session/{id}:archive" }
  ui:
    transport: ui
    screen: SesionPanel
    control: >-
      button[data-action="archive"]
    covers_steps: [s1-commit]
data:
  entities: [session]
provenance: none
reversibility: irreversible
---
A second operation, for the chain.
