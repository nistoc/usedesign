---
id: corpus.filename.matches-id
title: A card named after its id
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

The guard for `filename_mismatch`: the file is `corpus.filename.matches-id.op.md` and the id is
`corpus.filename.matches-id`. Almost every other case here is named for what it probes, so it
draws the warning; this one must not. An implementation that compares the name with `.op`
left on, with the directory, or with the `.md` kept, warns here.
