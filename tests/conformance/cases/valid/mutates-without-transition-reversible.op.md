---
id: sample.pass.log-set
title: Log a set of a pass
scenario: sample.flow
actors: [athlete]
maturity: implemented
maturity_evidence:
  implemented: src/Endpoints.cs:72
data_transition: null
mutates: [set.status, set.actual, totals]
concurrency:
  mode: etag_optional
  rationale: The revision is honoured when sent and not required.
  source: src/Endpoints.cs:72
steps:
  - id: s1-commit
    text: The set's status and actual values are applied; totals are recomputed
interfaces:
  rest: { transport: http_rest, method: PATCH, path: "/passes/{id}/sets/{setId}" }
data:
  entities: [pass]
provenance: none
reversibility: reversible
---

A write that changes fields of the record but not its state: `data_transition: null` with `mutates`
naming what changed. Before round 21 the checker read the null transition alone and warned that a
read-only operation claims `reversible` — but the operation wrote three fields, and reversing it
(the same call with the previous values) is exactly what the claim means. No warning.
