---
id: sample.things.publish-many
title: Publish a list of things
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
    - { code: invalid_transition, means: the item cannot make that move }

steps:
  - id: s1-authorised
    text: The caller may write to the catalogue
    on_violation: { error: forbidden, http: 403 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    responses: [200, 403]
    dispatch: { by: op, value: publish }

data:
  entities: [thing]
provenance: none
reversibility:
  reversible_via: sample.things.archive-many
---

The same operation as `bulk-violation-inside-success`, written after round 9 gave it somewhere
true to put the per-item failures. `steps[]` now holds only what actually stops the call.
