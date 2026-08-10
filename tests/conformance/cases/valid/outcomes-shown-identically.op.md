---
id: sample.request.submit
title: Submit a request
scenario: sample.flow
actors: [customer]
maturity: conceived
data_transition: { from: none, to: pending }
concurrency:
  mode: none_by_design
  rationale: A request is created fresh; there is nothing to collide with.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-consent
    text: The user has consented to requests being processed
    on_violation: { error: consent_required, http: 403 }
  - id: s3-create
    text: The request is created in `pending`

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /requests
    responses: [200, 401, 403]
  ui:
    transport: ui
    screen: RequestEditor
    control: button[data-action="create-request"]
    covers_outcomes:
      pending: the new request appears in the list
      unauthorized: "Something went wrong. Please try again."
      consent_required: "Something went wrong. Please try again."

data:
  entities: [request]
provenance: none
reversibility: irreversible
---

Valid, honest, and quietly harmful — the third state, between shown and not shown. Both failures
reach the user wearing one sentence, so the person who must give consent is told to retry, and
retrying can never work. Measured on a real screen in round 11. A warning rather than an error:
collapsing outcomes is sometimes deliberate, and the card is where that choice stops being
invisible.
