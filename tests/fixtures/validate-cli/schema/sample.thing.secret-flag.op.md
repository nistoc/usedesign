---
id: sample.thing.secret-flag
title: Act on a thing
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
sensitivity:
  response_contains_secret: yes
---

`yes` where the schema wants a boolean. The TypeScript implementation reads front matter as
YAML 1.2, where `yes` is a string and only `true` and `false` are booleans, so the card is refused:
`/sensitivity/response_contains_secret must be boolean`.

YAML 1.1 reads `yes` as `true`. An implementation that validates against `schema/` but hands it
front matter read as YAML 1.1 — PyYAML's default — calls this card valid; the same reading turns
an unquoted `2026-10-11` into a date the schema's `"type": "string"` refuses. The Python
prototype's schema layer reads YAML 1.2 for that reason (1.4.3); its rules still read YAML 1.1,
with the differences §5.7 lists.
