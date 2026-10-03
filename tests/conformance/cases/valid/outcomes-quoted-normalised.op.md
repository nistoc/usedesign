---
id: sample.order.place
title: Place an order
scenario: sample.flow
actors: [guest]
maturity: conceived
data_transition: { from: none, to: placed }
concurrency:
  mode: none_by_design
  rationale: Every order is a new record; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-open
    text: The café takes orders
    on_violation: { error: closed, http: 409 }
  - id: s2-exists
    text: The table still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-place
    text: The order is placed

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /tables/{id}/orders
    responses: [200, 404, 409]
  ui:
    transport: ui
    screen: OrderForm
    control: button[data-action="place-order"]
    covers_outcomes:
      placed: status line «Commande envoyée»
      closed: status line «Café fermé», each é one code point
      # written as \u0301 escapes so that an editor normalising this file cannot compose them unnoticed
      not_found: "the same line typed with separate accents, «Cafe\u0301 ferme\u0301», when the table was removed"

data:
  entities: [order]
provenance: none
reversibility: irreversible
---

One line typed two ways. In `closed` each `é` is one code point (U+00E9); in `not_found` it is an
`e` followed by a combining acute accent (U+0301) — the same text on screen, different code points
in the value. The value is NFC-normalised after case folding, so both spans read `café fermé`, and
that is one warning. An implementation that does not normalise compares `é` with `e` and an accent
and stays silent; so does one that reads the accent as a space, and so does 1.2.0.
