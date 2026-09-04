---
id: sample.card.archive
title: Archive a card
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: live, to: archived }
concurrency:
  mode: none_by_design
  rationale: One editor, one card.
  source: docs/design.md:1
steps:
  - id: s1-dark
    text: Without a reason the button stays dark
  - id: s2-post
    text: With a reason a POST leaves for the card
tests:
  - { id: "archive > hide: without a reason the button stays dark", covers: s1-dark, level: component }
  - { id: "web/src/Archive.test.tsx:archive > hide: with a reason a POST leaves for the card", covers: s2-post, level: component }
interfaces:
  rest: { transport: http_rest, method: POST, path: "/cards/{id}:archive" }
data:
  entities: [card]
provenance: none
reversibility: reversible
---
Two test ids with a colon INSIDE the name — one bare, one in the file-and-name shape whose name
part itself carries a colon. Both exist verbatim in the report.
