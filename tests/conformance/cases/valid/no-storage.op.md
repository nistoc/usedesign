---
id: sample.build.stamp
title: Report the running build stamp
scenario: sample.ops
actors: [operator]
maturity: conceived
data_transition: null
concurrency:
  mode: none_by_design
  rationale: A read of process configuration; nothing to protect.
  source: docs/design.md:1
steps:
  - id: s1-read-config
    text: The commit, build time and environment name are read from process configuration

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /build-info

data:
  entities: []
provenance: none
reversibility: not_applicable
---

The operation that touches no storage at all (issue #2): the values come from process
configuration — no table, no document, no record. `entities: []` is the honest answer, and it
is an ANSWER: the list stays required so nobody forgets the question; empty says "none".
