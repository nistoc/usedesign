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
      archived: the row leaves the list
      unauthorized: the red line «Could not archive the item» under the row
      forbidden:
        shows: Could not archive the item
        where: "[data-field=row-error]"

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

A map half rewritten into pairs. A pair is compared by its line beside the quoted spans of a text
value, so the text value that quotes that line alone and the pair compare equal — rewriting one
outcome into a pair does not hide the line it shares with the outcome still in prose.
