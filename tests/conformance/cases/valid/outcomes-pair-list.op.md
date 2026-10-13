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
  - id: s9-exists
    text: The item exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-archive
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
        - { shows: Could not archive the item, where: "[data-field=row-error]" }
        - { shows: Your session has ended, where: "[data-field=session-banner]" }
      forbidden:
        shows: Could not archive the item
        where: "[data-field=row-error]"
      not_found:
        - { shows: Your session has ended, where: "[data-field=session-banner]" }
        - { shows: Could not archive the item, where: "[data-field=row-error]" }

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

An outcome that puts two lines on the screen is a list of pairs, compared as the set of its lines:
order does not matter, and a list is not the same as one of its lines. `unauthorized` and
`not_found` show the same two lines; `forbidden` shows one of them and stays apart.
