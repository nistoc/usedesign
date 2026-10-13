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
        shows: "✓"
        where: "[data-field=row-status]"
      unauthorized:
        shows: "✗"
        where: "[data-field=row-status]"
      forbidden:
        shows: " ✗ "
        where: "[data-field=row-status]"

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

A line with no word at all. Rule 3 reads a glyph as a space and would leave nothing; a line with no
word left is compared as rule 1 leaves it — trimmed, folded, normalised. The tick stays apart from
the crosses, and the two crosses are one line.
