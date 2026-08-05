---
id: sample.copy.checkout
title: Check out a copy
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: available, to: on_loan }
concurrency:
  mode: etag_required
  source: docs/design.md:1
steps:
  - id: s1-available
    text: The copy is available
    on_violation: { error: not_available, http: 409 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/copies/{copyId}:checkout
    responses: [200, 409]

data:
  entities: [copy]
provenance: none
reversibility:
  reversible_via: sample.copy.return
---

One of four actions written in the AIP-136 style. The other three are declared by nobody, and a
checker that reads `:checkout` as a parameter reports this repository as clean.
