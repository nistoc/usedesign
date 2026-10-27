---
id: sample.loans.renew
title: Renew a loan
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: on_loan, to: renewed }
concurrency:
  mode: none_by_design
  rationale: One loan, one renewal; the store rejects a second write on the same key.
  source: docs/design.md:1
steps:
  - id: s1-member
    text: The member is recognised
    on_violation: { error: unauthorized, http: 401 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    responses: [200, 401]

data:
  entities: [loan]
provenance: none
reversibility: irreversible
---

The method is chosen and the path is not: the card was written before the route was named.
Check 1 has nothing to compare with the inventory, and an interface it cannot compare is an
error, not a card it leaves out in silence.
