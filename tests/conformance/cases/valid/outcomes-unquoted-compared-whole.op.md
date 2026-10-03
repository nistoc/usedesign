---
id: sample.session.refresh
title: Refresh a session
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: none, to: active }
concurrency:
  mode: none_by_design
  rationale: A refresh issues a new session; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The refresh token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-allowed
    text: The member is not suspended
    on_violation: { error: forbidden, http: 403 }
  - id: s3-issue
    text: A new session is issued

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /sessions/refresh
    responses: [200, 401, 403]
  ui:
    transport: ui
    screen: SessionGuard
    control: background refresh
    covers_outcomes:
      active: nothing visible — the page keeps working
      unauthorized: "  Session ended. Sign in again. "
      forbidden: "SESSION ENDED. SIGN IN AGAIN."

data:
  entities: [session]
provenance: none
reversibility: irreversible
---

No quotes at all: each value is compared whole, as 1.2 compared it — trimmed and case-folded. The
quoted-words rule must not lose this: a card written before round 28 never quoted anything, and
every collapse 1.2 reported on it is still reported.
