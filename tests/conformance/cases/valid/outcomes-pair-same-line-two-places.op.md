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
        shows: Could not archive the item — try again
        where: "[data-field=list-error]"
        note: pressing «Archive Now» first greys the row, then the list is reread
      forbidden:
        shows: could not archive the item. Try again!
        where: under the row, in red

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

One line written twice — in another case, with other punctuation, in another place, one of the
two with a note that quotes a button of two words. `shows` is compared as a quoted span is (rules 1
and 3); `where` and `note` are not compared. The user who may not edit is told to try again
wherever the sentence stands, and trying again cannot help.
