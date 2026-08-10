---
id: sample.session.finish
title: Finish the training session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition:
  from: active
  to: [finished, partial]
  determined_by: whether every planned exercise of the pass is closed
concurrency:
  mode: none_by_design
  rationale: The pass belongs to one athlete; a race is possible only between their own devices.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised before the body is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-commit
    text: Server totals are written; the status is computed from completeness

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /session/{id}:finish
    responses: [200, 401]
  ui:
    transport: ui
    screen: SessionPanel
    control: button[data-action="finish"]
    covers_outcomes:
      finished: the footer label says the session is complete
      partial: the footer label says the session is partial

data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.resume
---

The map exists and `unauthorized` is simply not in it. That silence is exactly what the field
was built to forbid: the honest card writes `unauthorized:` as null and takes the warning.
An implementation that lets this pass has turned the map back into a wish list.
