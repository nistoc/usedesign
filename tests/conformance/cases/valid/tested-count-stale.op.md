---
id: sample.pass.finish
title: Finish a pass
scenario: sample.flow
actors: [athlete]
maturity: tested
maturity_evidence:
  implemented: src/Endpoints.cs:144
  tested: 3 tests
data_transition:
  from: active
  to: finished
concurrency:
  mode: etag_optional
  rationale: The revision is honoured when sent and not required.
  source: src/Endpoints.cs:144
steps:
  - id: s1-authenticated
    text: Token recognised before the body is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-commit
    text: finishedAt and totals are set
tests:
  - { id: PassTests.Finish_sets_totals, covers: s2-commit, level: integration }
  - { id: PassTests.Finish_anonymous_is_401, covers: s1-authenticated, level: integration }
interfaces:
  rest: { transport: http_rest, method: POST, path: "/passes/{id}:finish" }
data:
  entities: [pass]
provenance: none
reversibility: reversible
---

`tested: 3 tests` with two entries in `tests[]`. The prose is advisory and stays valid; the number
in it is a claim, and this one went stale the way such numbers do — a test was dropped, or the
author counted the suite, not the citations. A warning, not an error: the truth is `tests[]`.
