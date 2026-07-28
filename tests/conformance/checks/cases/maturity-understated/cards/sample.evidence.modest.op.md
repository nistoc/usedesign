---
id: sample.evidence.modest
title: Claims less than it can prove
scenario: A conformance case for check 3
actors: [staff]
maturity: designed

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
    path: /v1/modest

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# Claims less than it can prove

The card says designed while the test it names passes. Wrong in the pessimistic direction still sends people to build what exists.
