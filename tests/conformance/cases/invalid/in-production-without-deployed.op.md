---
id: sample.thing.claim
title: Claims production without saying where
scenario: sample.flow
actors: [operator]
maturity: in_production
maturity_evidence:
  implemented: src/claim.ts
  tested: 1 test
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act

data:
  entities: [thing]
provenance: none
reversibility: reversible
tests:
  - { id: ClaimTests.works, covers: s1-check, level: unit }
---

`in_production` requires naming the environment it runs in.
