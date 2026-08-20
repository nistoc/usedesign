---
id: sample.record.read-audited
title: Read a record, recording who asked
scenario: sample.compliance
actors: [operator]
maturity: designed
data_transition: null
concurrency:
  mode: none_by_design
  rationale: A read; the audit entry is append-only and keyed by call.
  source: docs/design.md:1
steps:
  - id: s1-record-caller
    text: The caller's name reaches the journal, flagged verified or merely declared

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /records/{id}

data:
  entities: [record]
provenance:
  activity_kind: read_access
  attributed_to: caller
  records_only: true
reversibility: not_applicable
---

The audit-only read (issue #1): changes no domain state, records who asked. Before
`records_only` this card had to pick between two lies — `provenance: none` (false: an entry IS
recorded) or `mutates` (false: no domain data changes). The provenance is the declared write.
