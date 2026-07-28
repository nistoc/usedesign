---
id: sample.evidence.claimed
title: Claims tested while its only test fails
scenario: A conformance case for check 3
actors: [staff]
maturity: tested
maturity_evidence:
  implemented: src/api/Endpoint.ts
  tested: 1 test

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
    path: /v1/claimed

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# Claims tested while its only test fails

The prose says one test. The report says it failed. The prose is not the evidence.
