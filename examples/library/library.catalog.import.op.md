---
id: library.catalog.import
title: Import catalogue records from an external provider
scenario: library.acquisition.new-titles-arrive
actors: [cataloguer, integration_service, api_agent]

maturity: in_production
maturity_evidence:
  implemented: src/catalog/ImportEndpoint.ts + src/workers/ImportWorker.ts
  tested: 5 tests
  deployed: { env: production, since: 2026-06-15 }

data_transition: null
mutates: [import_job.status, title.*, contributor.*]
since: { migration: "022", note: "import_job table" }

concurrency:
  mode: idempotency_by_formula
  rationale: >
    Callers are batch scripts that retry on timeout and cannot be relied upon to send a stable
    key. The server derives one from the payload so a retry joins the existing job instead of
    starting a second import of the same file.
  formula: sha256(provider + feedId + feedVersion + mappingVersion)
  on_duplicate: { http: 409, code: active_import_exists, returns: existing jobId and its status }
  source: src/catalog/ImportEndpoint.ts:71

quota:
  scheme: per_credential_per_minute
  categories:
    import: { bucket: 5, window_min: 1 }
  applies_to: api_key_callers_only
  on_exceeded: { error: rate_limit_exceeded, http: 429, retry_after: seconds }
  storage: counters table, reset by window

steps:
  - id: s1-payload
    text: Feed body is present and parses as the declared format
    on_violation: { error: unparsable_feed, http: 400 }
  - id: s2-identity
    text: Feed identity is derived from provider and content when not given explicitly
    source: src/catalog/ImportEndpoint.ts:52
  - id: s3-enqueue
    text: Job is queued; the caller receives 202 with a job id and stops waiting

async_execution:
  job_states: [queued, running, succeeded, partial, failed, cancel_requested, cancelled]
  terminal: [succeeded, partial, failed, cancelled]
  worker: src/workers/ImportWorker.ts
  observe_via: GET /v1/imports/{jobId}
  cancel_via: POST /v1/imports/{jobId}/cancel — requires cataloguer
  s2s_dependency:
    service: MetadataEnrichment
    purpose: resolve contributor names to authority records
    failure_mode: >
      Job ends as `partial`, not `failed` — titles are imported without authority links and the
      unresolved names are listed for manual review.

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/imports
    responses: [202, 400, 409, 429]
    source: src/catalog/routes.ts:19
  rpc:
    transport: json_rpc
    tool: catalog.import
    scope_required: catalog:write
    quota:
      scheme: per_token_per_category_per_minute
      categories: { write: { bucket: 2, window_min: 1 } }
      applies_to: all_rpc_callers
      on_exceeded: { error: rate_limit_exceeded, jsonrpc_code: -32000, retry_after: seconds }
    source: src/rpc/tools/importTool.ts:14

data:
  entities: [import_job, title, contributor]
  migrations: ["022"]

provenance:
  activity_kind: catalog_import
  attributed_to: the calling identity, carried into the worker
  on_failure: the job row keeps the reason; imported titles keep a link to the job

reversibility:
  reversible_via: library.catalog.rollback-import
  note: >
    Rollback removes titles created by the job. Titles that were merely updated are restored to
    their pre-import revision, which is why revisions are kept for the retention window.

tests:
  - { id: ImportTests.retry_joins_existing_job, covers: s1-payload, level: integration }
  - { id: ImportTests.derives_identity_from_content, covers: s2-identity, level: unit }
  - { id: ImportTests.returns_202_with_job_id, covers: s3-enqueue, level: integration }
  - { id: ImportWorkerTests.enrichment_failure_yields_partial, covers: s3-enqueue, level: integration }
  - { id: RpcImportTests.write_quota_is_stricter_than_rest, covers: s3-enqueue, level: contract }

coverage_gaps:
  - step: s3-enqueue
    gap: no test for cancel_requested arriving while the worker is mid-batch
---

# Import catalogue records from an external provider

The HTTP response to this operation means *the work has been accepted*, not *the work is done*.
Everything interesting happens afterwards in the worker, which is why the card carries an
`async_execution` section: the job has a life of its own, with states that have nothing to do
with the lifecycle of the titles it produces. A job can reach `succeeded` while every title it
touched stays a draft.

Two details are worth reading twice.

**`partial` is a success, not a failure.** When the enrichment service is unavailable, titles
still import — only the authority links are missing. Treating that as `failed` would tempt
operators to re-run the whole import and create duplicates.

**The same operation is throttled differently per transport.** Over REST it is five imports a
minute per credential; over RPC it falls into the `write` category with a bucket of two. This is
the kind of difference that lives in nobody's documentation and surprises the first external
integrator — hence the per-transport `quota` override rather than a single top-level number.
