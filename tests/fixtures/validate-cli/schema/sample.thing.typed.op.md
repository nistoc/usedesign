---
id: sample.thing.typed
title: Fields of another type
scenario: sample.flow
actors: [operator]
maturity: !!float 1
maturity_evidence: 5
data_transition: { from: active, to: { k: v } }
mutates: [thing.state]
concurrency: 5
steps:
  - id: 5
    text: A precondition is checked
    on_violation: 5
  - id: s2-write
    text: The thing is written
    on_violation: { error: [a, b], http: !!float 409 }
interfaces:
  rest:
    transport: http_rest
    method: POST
    path: 5
    parameters: { k: v }
    responses: 5
  ui:
    transport: ui
    covers_steps: { k: v }
tests: x
coverage_gaps: 5
outcomes: 5
per_item: { failures: x }
async_execution: { job_states: 5 }
data:
  entities: [thing]
provenance: none
reversibility: reversible
---

Fields the rules read, each of a type it should not be: a number where a list or a map belongs,
a map where a list or a text belongs, a list where a text belongs. Up to 1.4.2 the TypeScript
reference stopped with a stack trace on several of them (`steps is not iterable`,
`declared.includes is not a function`) and the Python prototype on more. Both now read a field
only in its type — anything else counts as absent — and the schema names what is wrong.

`!!float 1` is the text `1` in both implementations, as the TypeScript parser reads it: the tag
does not resolve there, and the text stays. Python read YAML 1.1 and wrote `1.0`.
