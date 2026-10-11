---
id: sample.evidence.impossible-day
title: A deployment claim dated on a day the calendar lacks
scenario: A conformance case for check 3
actors: [staff]
maturity: in_production
maturity_evidence:
  implemented: src/api/Endpoint.ts
  tested: 1 test
  deployed: { env: production, since: 2026-02-30 }

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
    path: /v1/impossible-day

data:
  entities: [thing]
data_transition: null
mutates: true
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: SampleTests.does_the_thing, covers: s1-do, level: unit }
---

# A deployment claim dated on a day the calendar lacks

February has no 30th. Read by carrying the extra day over, it became 2 March — a real day, stale or fresh as the clock goes. It is no date at all, and a date that is not one is an error.
