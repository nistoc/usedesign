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
  - id: s3-found
    text: The item exists
    on_violation: { error: not_found, http: 404 }
  - id: s4-archive
    text: The item moves to `archived`

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /items/{id}/archive
    responses: [200, 401, 403, 404]
  ui:
    transport: ui
    screen: ItemList
    control: button[data-action="archive-item"]
    covers_outcomes:
      archived:
        shows: Archived
        where: "[data-field=row-status]"
      unauthorized:
        shows: Could not archive the item — try again
        where: "[data-field=list-error]"
      forbidden:
        silent: the list reloads after every refusal and shows the item as it is
      not_found:

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

Two outcomes the user is not shown. `forbidden` is kept silent, and the card says why.
`not_found` is not shown and nobody has decided whether it should be — a silence still open,
so it keeps its warning.
