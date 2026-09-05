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
    covers_steps: [s2-commit]
    covers_outcomes:
      ok: the footer label changes
      finished: the footer label says the session is complete
      partial: the footer label says the session is partial
      unauthorized: a toast asks the athlete to sign in again

data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.resume
---

`ok` beside named successes is the residue of a template: this operation ends in `finished` or
`partial`, and the map must say which of them the user sees. The reserved name belongs only to an
operation that names no success of its own.
