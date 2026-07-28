---
id: sample.thing.settle
title: Settle a thing
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked
  - id: s3-notify
    text: Added later, runs here
    emits_notice: queue_advanced
  - id: s2-commit
    text: The change is committed

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

`s3` runs before `s2` and that is correct. Step ids are identifiers, not positions; a step added later takes the next free number instead of displacing an existing one.

An implementation that sorts steps by id, or that rejects this card, has misread the specification in the way that silently breaks external references.
