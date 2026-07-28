---
id: sample.thing.untested
title: Claims tested with no tests listed
scenario: sample.flow
actors: [operator]
maturity: tested
maturity_evidence:
  implemented: src/untested.ts
  tested: soon
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
---

Maturity may never outrun its evidence. An empty `tests[]` cannot support `tested`.

Note what this case does *not* catch: the note reads `soon`, which is plainly not a test count. A schema validates form, not meaning — that part belongs to the checker.
