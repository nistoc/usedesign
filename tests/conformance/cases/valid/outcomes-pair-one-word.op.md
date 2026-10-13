---
id: sample.item.archive
title: Archive an item
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: active, to: archived }
concurrency:
  mode: none_by_design
  rationale: Archiving twice leaves the item archived.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-editor
    text: The caller may edit this item
    on_violation: { error: forbidden, http: 403 }
  - id: s3-archive
    text: The item moves to `archived`

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /items/{id}/archive
    responses: [200, 401, 403]
  ui:
    transport: ui
    screen: ItemList
    control: button[data-action="archive-item"]
    covers_outcomes:
      archived:
        shows: Archived
        where: "[data-field=row-status]"
      unauthorized:
        shows: Failed
        where: "[data-field=row-status]"
      forbidden:
        shows: failed!
        where: "[data-field=row-status]"

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

A line of one word. In a text value «Failed» is below the floor of rule 4 — a single quoted word is
more often a button than a message — and the values would be compared whole. A pair's `shows` is
the line by declaration, so the floor does not apply: two refusals showing one word are one line.
