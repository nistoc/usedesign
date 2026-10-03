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
      unauthorized: Session ended. Sign in again.
      forbidden: Session ended — sign in again!

data:
  entities: [session]
provenance: none
reversibility: irreversible
---

Without quotes the value is compared whole, and the whole value includes its punctuation: letters
and numbers are read apart from the rest only inside «…» or “…”. An implementation that normalised
every value would warn here, where 1.2 was silent — and disagree with the other implementation on
every card that quotes nothing. Quote the words the user reads and they are compared as words. The
manifest asserts the silence: `absent_warnings`.
