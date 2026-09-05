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
      unauthorized: the panel closes and the start screen is shown

data:
  entities: [session]
provenance: none
reversibility: not_applicable
---

The same read, with a map that lists the refusal and not the success. A warning, not an error:
cards written before round 23 had no way to name the default success, and a gate must not turn
red on them for a word that did not exist when they were written.
