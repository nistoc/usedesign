---
id: sample.thing.search
title: Search things, describing a parameter that is not there
scenario: sample.flow
actors: [operator]
maturity: conceived
data_transition: null
mutates: [nothing]
concurrency:
  mode: none_by_design
  rationale: Read-only.
  source: docs/design.md:1
steps:
  - id: s1-query-present
    text: The query string is non-empty
    on_violation: { error: invalid_query, http: 400 }

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/things/search
    responses: [200, 400]
    parameters:
      - name: tenant
        handling: decorative
        note: The real tenant comes from the caller's identity
      - name: take
        handling: clamped
        range: [1, 100]
        note: A caller asking for more receives the maximum, and is not told

data:
  entities: [thing]
provenance: none
reversibility: not_applicable
---

`tenant` is declared decorative, but the path has no `{tenant}` in it — the declaration describes
nothing. The `take` entry beside it is correct and must not be reported.
