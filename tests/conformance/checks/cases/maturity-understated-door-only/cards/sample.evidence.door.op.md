---
id: sample.evidence.door
title: Proves the door, not the room
scenario: A conformance case for check 3
actors: [staff]
maturity: designed

steps:
  - id: s1-authenticated
    text: The caller is signed in
  - id: s2-allowed
    text: The caller may do the thing
  - id: s3-do
    text: The thing is done

concurrency:
  mode: none_by_design
  rationale: A conformance case does nothing concurrently.
  source: code/.keep

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/door

data:
  entities: [thing]
data_transition: null
mutates: [thing]
provenance: { activity_kind: sample }
reversibility: irreversible

tests:
  - { id: DoorTests.without_a_token_is_401, covers: s1-authenticated, level: integration }
  - { id: DoorTests.outside_the_group_is_403, covers: s2-allowed, level: integration }
---

# Proves the door, not the room

Both tests pass, and both stop at the door: sign-in and permission. The operation behind them answers
501 — nothing past the door exists yet — so `designed` is the honest claim. A rule that reads "its
tests pass" as "it is built" takes a necessary condition for a sufficient one.
