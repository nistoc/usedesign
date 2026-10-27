---
id: sample.loans.screen
title: Show the loans of a member
scenario: sample.flow
actors: [librarian]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: Read-only; the screen only displays.
  source: docs/design.md:1
steps:
  - id: s1-listed
    text: The member's open loans are listed

interfaces:
  ui:
    transport: ui
    screen: LoanList
    control: tab[data-tab="loans"]
    covers_steps: [s1-listed]

data:
  entities: [loan]
provenance: none
reversibility: not_applicable
---

A card with a `ui` interface only. The gen test expects it to count as a card read and to add no
REST interface and no route.
