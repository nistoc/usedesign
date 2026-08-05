---
id: sample.things.batch
title: Act on a list of things, reporting each result inside a success
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [thing.state]
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one; a conflict on one is reported on that one.
  source: docs/design.md:1
steps:
  - id: s1-item-exists
    text: Each named item exists
    on_violation: { error: not_found, http: 200 }
  - id: s2-item-transition
    text: The transition is legal for each item
    on_violation: { error: invalid_transition, http: 200 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    responses: [200]

data:
  entities: [thing]
provenance: none
reversibility: irreversible
---

Structurally valid and quietly false. A bulk operation reports per-item failures inside a 200,
and `steps[]` cannot say that: its whole shape is *violated, therefore stopped, therefore an
error code*. Writing `http: 200` under `on_violation` is the only way through, and it means
nothing.

Found on a repository this format had never seen. The warning does not make the card true — it
makes the lie visible, which is all a checker can do until the format learns to say it.
