---
id: sample.thing.ask
title: Wait for a decision that no outcome announces
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [call_audit]
concurrency:
  mode: none_by_design
  rationale: Read-only.
  source: docs/design.md:1
steps:
  - id: s1-plan
    text: The request is planned

outcomes:
  - id: answered
    means: An answer was produced
    http: 200
  - id: not_covered
    means: Nothing matched
    http: 200

continuation:
  after: needs_clarification
  resumed_by: human
  carries: selected_candidate

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/ask
    responses: [200]

data:
  entities: [thing]
provenance: none
reversibility: not_applicable
---

`continuation.after` names an outcome the card never declares. The operation claims it can be
suspended by something that, as far as this card is concerned, cannot happen.
