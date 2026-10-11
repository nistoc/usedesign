---
id: sample.thing.nulls
title: Act on a thing
scenario: sample.flow
actors: [operator]
maturity: ~
data_transition: null
mutates: [thing.state]
concurrency:
  mode: null
  rationale: Additive and idempotent by construction.
  source: docs/design.md:1
steps:
  - id: s1-check
    text: A precondition is checked
    on_violation: { error: precondition_failed, http: 412 }
  - id: s9-notify
    text: Watchers are told
  - id: s3-write
    text: The thing is written

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act

coverage_gaps:
  - step: s3-write
    gap: The write cannot be observed from the test host
    kind: [harness, unreachable]
data:
  entities: [thing]
provenance: none
reversibility: reversible
---

`null` where a value is asked for — `maturity` and `concurrency.mode` — is a value outside the
list in both implementations, as is a gap's kind written as a list (`harness,unreachable`, as
JavaScript joins it). Python read `null` as absent and wrote the list as Python writes one. Two of
the three steps have no test and no gap, and their warnings come in the card's order: Python kept
the step ids in a set, whose order changed from run to run.
