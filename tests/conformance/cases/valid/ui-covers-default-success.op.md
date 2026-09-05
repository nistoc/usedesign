---
id: sample.session.read
title: Show the current session
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: A read by key; nothing to collide with.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised before the store is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-lookup
    text: The session is returned as stored

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /session/current
    responses: [200, 401]
  ui:
    transport: ui
    screen: SessionPanel
    control: page load of the session screen — no dedicated control
    covers_steps: [s2-lookup]
    covers_outcomes:
      ok: the panel shows the session with its exercises
      unauthorized: the panel closes and the start screen is shown

data:
  entities: [session]
provenance: none
reversibility: not_applicable
---

A read with one ending: no `outcomes[]` — the list exists only for endings that differ in
shape — and no `data_transition.to`. Before round 23 the map could name the refusal and not the
success, and "the panel shows the session" lived in `note`, where nothing checks it. `ok` is the
reserved name of that default success.
