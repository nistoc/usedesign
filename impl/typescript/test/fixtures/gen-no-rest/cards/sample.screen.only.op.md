---
id: sample.screen.only
title: Show a welcome panel
scenario: sample.flow
actors: [visitor]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: Read-only; the screen only displays.
  source: docs/design.md:1
steps:
  - id: s1-shown
    text: The welcome panel is displayed

interfaces:
  ui:
    transport: ui
    screen: WelcomePanel
    control: panel[data-panel="welcome"]
    covers_steps: [s1-shown]

data:
  entities: [visitor]
provenance: none
reversibility: not_applicable
---

The only card in this fixture, and it has a `ui` interface alone, so `gen openapi` has no route
to derive and the gen test expects it to refuse.
