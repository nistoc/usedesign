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
      unauthorized:
      completed: the footer label says the session is complete

data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.resume
---

`completed` is what the route was renamed to in somebody's head — no outcome, transition
target, violation, or job state declares it. This is the drift the key check exists for:
without it, a renamed outcome leaves the map still looking fully covered.
