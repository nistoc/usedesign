---
id: sample.order.cancel
title: Cancel an order
scenario: sample.flow
actors: [guest]
maturity: conceived
data_transition: { from: placed, to: cancelled }
concurrency:
  mode: none_by_design
  rationale: One guest cancels their own order; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-open
    text: The café takes changes
    on_violation: { error: closed, http: 409 }
  - id: s2-exists
    text: The order still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-cancel
    text: The order is cancelled

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /orders/{id}/cancel
    responses: [200, 404, 409]
  ui:
    transport: ui
    screen: OrderForm
    control: button[data-action="cancel-order"]
    covers_outcomes:
      cancelled: Commande annulée
      closed: Café fermé
      # written as \u0301 escapes so that an editor normalising this file cannot compose them unnoticed
      not_found: "CAFE\u0301 FERME\u0301"

data:
  entities: [order]
provenance: none
reversibility: irreversible
---

No quotes, so each value is compared whole — trimmed, case-folded and NFC-normalised. `closed`
writes each `é` as one code point (U+00E9); `not_found` writes the line in capitals, each `É` as an
`E` and a combining acute accent (U+0301). Folded and normalised, both read `café fermé`: one
warning. 1.2.0 lowercased and compared code points, and stays silent here; so does an
implementation that normalises only the quoted spans.
