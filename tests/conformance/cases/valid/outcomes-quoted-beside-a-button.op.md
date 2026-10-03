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
      unauthorized: pressing «Archive» shows the red line «Could not archive the item»
      forbidden: the same red line «Could not archive the item», under the row

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

The same message, and one value also names the button in passing. A quoted span of one word —
«Archive», «OK», «!» — is a control or a glyph, not a message, so it is not compared; the message
is, and it is the same. A checker that compared every quote would read two different sets here
and stay silent about a refusal the user cannot tell from the other.
