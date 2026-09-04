---
id: sample.card.create
title: Create a card
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: absent, to: live }
concurrency:
  mode: none_by_design
  rationale: One editor, one new card.
  source: docs/design.md:1
steps:
  - id: s1-write
    text: The card is written
interfaces:
  rest: { transport: http_rest, method: POST, path: "/cards" }
data:
  entities: [card]
provenance: none
reversibility: reversible
---
The data has exactly two states: the card is `absent`, then `live`.
