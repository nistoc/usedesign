---
id: sample.things.publish-many
title: Declare per_item and then write a per-item failure as a step anyway
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: any, to: published }
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one.
  source: docs/design.md:1

per_item:
  applies_to: ids
  independent: true
  reported_in: results
  failures:
    - { code: not_found, means: the item does not exist }

steps:
  - id: s1-item-exists
    text: Each named item exists
    on_violation: { error: not_found, http: 200 }

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

With `per_item` declared there is a true place for this failure, so putting it in `steps[]` with
a success status is a mistake rather than a shortage of vocabulary. Without `per_item` the same
card only warns — the rule tightens exactly when the vocabulary appears.
