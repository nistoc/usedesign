---
id: sample.thing.twice
title: Act on a thing
title: Act on a thing, again
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
    on_violation: { error: precondition_failed, http: 412 }

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

`title` written twice. The TypeScript implementation's YAML parser refuses a key written twice,
and the card is not read at all; PyYAML kept the last one, and Python validated the card.
