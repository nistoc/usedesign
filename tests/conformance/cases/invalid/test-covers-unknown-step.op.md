---
id: sample.thing.mislinked
title: A test points at a step that does not exist
scenario: sample.flow
actors: [operator]
maturity: tested
maturity_evidence:
  implemented: src/mislinked.ts
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
  - { id: MislinkedTests.works, covers: s9-ghost, level: unit }
---

This is the failure the format exists to prevent: a reference that looks satisfied and points at nothing.
