---
id: corpus.filename.new-name
title: A card renamed in its id and not on disk
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

The id was renamed to `corpus.filename.new-name` and the file kept its old name. A card is found
on disk by its id (one file, one operation, the file named by the id), so this one can no longer
be found there. A warning, never an error: the card means what it says, it is only hard to find.
