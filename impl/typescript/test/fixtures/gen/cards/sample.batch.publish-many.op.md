---
id: sample.batch.publish-many
title: Publish a list of things
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: { from: draft, to: published }
concurrency:
  mode: none_by_design
  rationale: Items are processed one by one.
  source: docs/design.md:1
steps:
  - id: s1-authorised
    text: The caller may write things
    on_violation: { error: forbidden, http: 403 }
  - id: s2-may-publish
    text: The caller may publish, not only write
    on_violation: { error: publish_not_allowed, http: 403 }
  - id: s3-complete
    text: Every listed thing is complete
    on_violation: { error: draft_incomplete, http: 422 }
  - id: s4-unpublished
    text: No listed thing is published already
    on_violation: { error: already_published, http: 409 }
  - id: s5-publish
    text: The listed things become visible

outcomes:
  - id: published
    means: Every listed thing is visible now
    http: 200
  - id: queued
    means: The things are visible once the index catches up
    http: 200

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    responses: [200, 403, 409, 422]
    dispatch: { by: op, value: publish }

data:
  entities: [thing]
provenance: none
reversibility: irreversible
---

The sibling of `sample.batch.delete-many` on the same route. It repeats the `forbidden` error of
its sibling (same name, listed once after the merge), adds `publish_not_allowed` to the same
status, and names an outcome for `200` where the sibling names none.
