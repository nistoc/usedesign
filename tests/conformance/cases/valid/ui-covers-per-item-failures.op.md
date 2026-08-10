---
id: sample.catalog.batch-publish
title: Publish a list of items
scenario: sample.flow
actors: [catalog_admin]
maturity: conceived
data_transition: { from: any, to: published }
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one; a per-item conflict returns its own code.
  source: docs/design.md:1

per_item:
  applies_to: ids
  independent: true
  reported_in: results
  failures:
    - { code: not_found, means: no such item in the catalogue }
    - { code: invalid_transition, means: publishing is not allowed from the current state }

steps:
  - id: s1-scope
    text: The caller may write to the catalogue
    on_violation: { error: forbidden, http: 403 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /catalogs:batch
    responses: [200, 403]
  ui:
    transport: ui
    screen: BulkBar
    control: the «Publish» button
    covers_outcomes:
      published: the list reloads and published rows change state
      forbidden: an error line above the table
      not_found:
      invalid_transition:

data:
  entities: [item]
provenance: none
reversibility:
  reversible_via: sample.catalog.batch-archive
---

Per-item failures are outcomes the user meets, and until round 11 the vocabulary had no room for
them: they carry no status, so nothing named them. Measured on a real bulk screen whose client
discards the response body outright — ten items selected, three rejected inside a 200, and the
page says nothing at all. Both `null`s here are that silence, declared.

The line between this and a job state is not taste. A per-item failure arrives in THIS call's
response, while the user is looking; a job state is the record's later life, watched through
`observe_via` by another operation with a screen of its own.
