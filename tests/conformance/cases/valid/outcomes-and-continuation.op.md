---
id: sample.catalogue.ask
title: Answer a question against the catalogue
scenario: sample.flow
actors: [consumer_service]
maturity: conceived
data_transition: null
mutates: [call_audit]
concurrency:
  mode: none_by_design
  rationale: Read-only; two questions cannot collide.
  source: docs/design.md:1
steps:
  - id: s1-question-present
    text: The request carries a non-empty question
    on_violation: { error: invalid_question, http: 400 }
  - id: s2-plan
    text: A metric and a period are extracted from the question

outcomes:
  - id: answered
    means: The catalogue covered the question
    http: 200
    carries: [context, answer]
  - id: not_covered
    means: Nothing in the catalogue covers it — an honest empty answer, not a failure
    http: 200
    carries: []
    rationale: >
      Reaching the end and returning nothing IS the work here. There is no request the
      caller could send that would make an absent metric present.
  - id: ambiguous
    means: The phrase matches several catalogue entries
    http: 200
    carries: [candidates]

continuation:
  after: ambiguous
  resumed_by: human
  carries: selected_candidate
  same_operation: true
  rationale: >
    Not async execution: nothing progresses on its own and there is nothing to observe.
    A person chooses, or the operation never finishes.

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/ask
    responses: [200, 400]

data:
  entities: [catalogue_entry]
provenance: none
reversibility: not_applicable
---

Three terminal outcomes sharing one status code, and a continuation that only a human can move.
Both fields are optional; this card exists to show they hold together.
