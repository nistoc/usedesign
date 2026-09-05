---
id: sample.pass.resume
title: Return a pass to work
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition:
  from: [finished, partial, abandoned]
  to: active
concurrency:
  mode: etag_optional
  rationale: >
    The revision is honoured when sent (mismatch → 409) but a request without one is accepted —
    the surface is being migrated to a required precondition one flag at a time.
  source: src/Endpoints.cs:168
steps:
  - id: s1-commit
    text: Status becomes active; finishedAt and totals are cleared
interfaces:
  rest: { transport: http_rest, method: POST, path: "/passes/{id}:resume" }
data:
  entities: [pass]
provenance: none
reversibility: reversible
---

Round 18, two fields the vocabulary used to force a lie on. `from` as a SET: the operation departs
from any of three terminal states — before this the only truthful value was `from: any`, which
switches the shown_when rule off for every control that calls it. `etag_optional`: the revision
is honoured when sent and not required — before this the card had to claim `etag_required` (a
lie about the header) or `none_by_design` (a lie about the mechanism). Both measured on a live
service, in the same afternoon, on the same three cards.
