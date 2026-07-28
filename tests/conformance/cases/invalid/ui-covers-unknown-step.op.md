---
id: sample.thing.screen
title: A screen claims a step that does not exist
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act
  ui:
    transport: ui
    screen: ThingPage
    covers_steps: [s4-ghost]

data:
  entities: [thing]
provenance: none
reversibility: reversible
---

The same defect from the interface side. This is exactly the UI-drifts-from-API case, caught at the description rather than in production.
