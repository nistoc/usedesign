---
id: sample.evidence.undated
title: A deployment claim with no date
scenario: A conformance case for check 3
actors: [staff]
maturity: in_production
maturity_evidence:
  implemented: src/api/Endpoint.ts
  tested: 1 test
  deployed: production

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
    path: /v1/undated

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# A deployment claim with no date

It can never go stale, so nobody will ever be asked to look at it again.
