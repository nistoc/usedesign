---
id: sample.pass.resume
title: Return a pass to work
scenario: sample.flow
actors: [athlete]
maturity: conceived
data_transition:
  from: [abandoned]
  to: active
concurrency:
  mode: none_by_design
  rationale: One athlete, one pass.
  source: src/Endpoints.cs:168
steps:
  - id: s1-commit
    text: Status becomes active
interfaces:
  rest: { transport: http_rest, method: POST, path: "/passes/{id}:resume" }
data:
  entities: [pass]
provenance: none
reversibility: reversible
---

A one-element set is a string wearing brackets. Accepted, two spellings of the same fact would
drift apart in tooling that reads one and not the other; refused, the author writes the string.
