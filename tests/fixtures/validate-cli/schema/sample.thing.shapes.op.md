---
id: sample.thing.shapes
title: Many shapes the schema refuses
scenario: sample.flow
actors: []
maturity: in_production
maturity_evidence:
  implemented: src/thing.ts
  tested: 1 test
  deployed: { env: production, since: 2026-02-30 }
data_transition: { from: [active, active], to: finished }
mutates: [thing.state]
concurrency:
  mode: etag_optional
  source: docs/design.md:1
quota:
  scheme: per_credential_per_minute
  categories:
    act: { bucket: 5, window_min: 0 }
  applies_to: everyone
  on_exceeded: { error: rate_limit_exceeded, http: 429, retry_after: seconds }
steps:
  - id: s1-check
    text: A precondition is checked
    on_violation: { error: precondition_failed, http: 99 }
  - id: s2-write
    text: 42
    variant: yes
tests:
  - id: tests/thing.test.ts::acts
    level: e2e
    covers: [s1-check, s1-check]
interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things/{id}/act
    responses: [200, 200, 4120]
coverage_gaps:
  - step: s2-write
    gap: The write cannot be observed from the test host
    kind: null
data:
  entities: [thing]
provenance: none
reversibility: reversible
sensitivity:
  response_contains_secret: no
  disclosure: sometimes
---

Many of the keywords the schema uses, broken at once: an empty `actors`, a date that does not
exist (February 30), `window_min: 0` where it must be above zero, an HTTP status of 99 and one of
4120, a step text that is a number, an unknown key in a step, a test level the schema does not
list, a relaxed concurrency mode without its rationale, `no` and `sometimes` where a boolean and a
known disclosure belong, a gap whose kind is `null`, a set of `from` states that names one twice.
A step covered twice and a response listed twice are not among them: the schema allows both.

`validate` must print the same lines in both implementations — the messages, their order and
their count — as `run.sh` compares.
