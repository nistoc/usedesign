---
id: sample.evidence.moved
title: The implementation moved and the card did not
scenario: A conformance case for check 3
actors: [staff]
maturity: implemented
maturity_evidence:
  implemented: src/handlers/Moved.ts

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
    path: /v1/moved

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# The implementation moved and the card did not

The file was renamed months ago. Nothing is broken; the card simply points at air.
