---
id: sample.thing.import
title: Import things from a feed
scenario: sample.flow
actors: [operator]
maturity: in_production
maturity_evidence:
  implemented: src/import.ts
  tested: 1 test
  deployed: production
data_transition: null
mutates: [thing.state]
concurrency:
  mode: idempotency_by_formula
  rationale: Callers retry on timeout and cannot supply a stable key.
  formula: sha256(provider + feedId + feedVersion)
  on_duplicate: { http: 409, code: active_import_exists }
  source: docs/design.md:1
steps:
  - id: s1-enqueue
    text: The job is queued and the caller is released

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/imports
  rpc:
    transport: json_rpc
    tool: thing.import
    quota:
      scheme: per_token_per_category_per_minute
      categories: { write: { bucket: 2, window_min: 1 } }
      applies_to: all_rpc_callers
      on_exceeded: { error: rate_limit_exceeded, jsonrpc_code: -32000, retry_after: seconds }

data:
  entities: [thing]
provenance: 
  activity_kind: thing_import
reversibility: reversible
async_execution:
  job_states: [queued, running, succeeded, failed]
  terminal: [succeeded, failed]
  worker: src/workers/import.ts
  observe_via: GET /v1/imports/{jobId}
quota:
  scheme: per_credential_per_minute
  categories: { import: { bucket: 5, window_min: 1 } }
  applies_to: api_key_callers_only
  on_exceeded: { error: rate_limit_exceeded, http: 429, retry_after: seconds }
tests:
  - { id: ImportTests.enqueues_and_returns_202, covers: s1-enqueue, level: integration }
---

Exercises three things at once: asynchronous execution as its own axis, a quota, and a per-transport override where the RPC bucket is stricter than the REST one.
