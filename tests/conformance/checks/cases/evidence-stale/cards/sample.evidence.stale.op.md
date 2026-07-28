---
id: sample.evidence.stale
title: A deployment claim nobody has re-affirmed
scenario: A conformance case for check 3
actors: [staff]
maturity: in_production
maturity_evidence:
  implemented: src/api/Endpoint.ts
  tested: 1 test
  deployed: { env: production, since: 2020-01-15 }

steps:
  - id: s1-do
    text: The thing is done

concurrency:
  mode: none_by_design
  rationale: A conformance case does nothing concurrently.

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/stale

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# A deployment claim nobody has re-affirmed

Dated, and far past the horizon. The operation may well still be in production — the point is that nobody has said so in years.
