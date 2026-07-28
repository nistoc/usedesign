---
id: sample.evidence.spanning
title: One operation, two files
scenario: A conformance case for check 3
actors: [staff]
maturity: implemented
maturity_evidence:
  implemented: src/api/Endpoint.ts + src/workers/Worker.ts

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
    path: /v1/spanning

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# One operation, two files

Both halves exist. A checker that reads the value as a single path fails a card that is telling the truth.
