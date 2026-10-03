---
id: sample.item.duplicate
title: Duplicate an item
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: none, to: draft }
concurrency:
  mode: none_by_design
  rationale: Every duplicate is a new item; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-exists
    text: The source item still exists
    on_violation: { error: not_found, http: 404 }
  - id: s2-name-free
    text: No item already carries the copy's name
    on_violation: { error: id_conflict, http: 409 }
  - id: s3-copy
    text: The copy is created as a draft

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /items/{id}/duplicate
    responses: [200, 404, 409]
  ui:
    transport: ui
    screen: ItemList
    control: button[data-action="duplicate-item"]
    covers_outcomes:
      draft: the copy appears at the top of the list
      not_found: «Duplicate» reports that the item no longer exists
      id_conflict: «Duplicate» reports that a copy with that name already exists

data:
  entities: [item]
provenance: none
reversibility: irreversible
---

Two different messages that share only the button's name. The one quoted word is a control, not
what the user reads as either ending, so neither value keeps a span, and each is compared whole —
as in 1.2 — and they differ. A checker that compared every quote would warn here, about two endings
the user can tell apart. The manifest asserts the silence: `absent_warnings`.
