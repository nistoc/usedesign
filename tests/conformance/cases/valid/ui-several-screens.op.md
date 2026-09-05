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
      finished: the footer label says the session is complete
      partial: the footer label says the session is partial
      unauthorized: a toast asks the athlete to sign in again
  ui-day-menu:
    transport: ui
    screen: DayList
    control: menu item «Finish» on the day's row
    covers_steps: [s2-commit]
    covers_outcomes:
      finished: the row moves to the history section
      partial: the row moves to the history section with a «partial» badge
      unauthorized: the menu closes and the sign-in banner appears

data:
  entities: [session]
provenance: none
reversibility:
  reversible_via: sample.session.resume
---

One operation, two screens. The interfaces map is open: each calling screen is its own entry —
`ui`, `ui-day-menu` — with its own control and its own map of what the user sees, and every rule
runs per entry. The format accepted this from the start; the specification did not say so, and
two rounds wrote three callers into one `control` as prose. This case pins the acceptance.
