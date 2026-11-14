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
        shows: You may not edit this item
        where: "[data-field=row-error]"
      not_found:
        silent: the row of an item that is gone leaves the list when it reloads, and nothing is left to tell

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

An item that is gone can still come back as `not_found`, and this screen says nothing about it
on purpose: the row leaves the list when it reloads. Declared `silent`, the outcome is not
outcome_unshown and is compared with nothing. Before round 36 the card could only write null
and carry the warning, and the reason lived in prose beside it.
