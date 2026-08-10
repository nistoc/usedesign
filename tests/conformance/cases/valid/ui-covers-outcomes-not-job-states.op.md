---
id: sample.request.create
title: Open a request thread
scenario: sample.flow
actors: [customer]
maturity: conceived
data_transition: { from: none, to: pending }
concurrency:
  mode: none_by_design
  rationale: A request is created fresh; there is nothing to collide with.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-create
    text: The thread is created in `pending` and handed to the worker

async_execution:
  job_states: [pending, checking, executing, done, failed]
  terminal: [failed]
  worker: request worker
  observe_via: GET /requests/{id}

continuation:
  after: done
  resumed_by: human
  carries: the next message
  same_operation: false

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /requests
    responses: [200, 401]
  ui:
    transport: ui
    screen: RequestEditor
    control: button[data-action="create-request"]
    covers_outcomes:
      pending: the new thread appears in the list and opens
      unauthorized: an error line above the editor

data:
  entities: [request]
provenance: none
reversibility:
  reversible_via: sample.request.archive
---

The screen covers what the CALL can end with, and nothing else. `checking`, `executing`, `done`
and `failed` are job states the record reaches later, watched through `observe_via` — a different
operation with a screen of its own. Round 11 found the rule demanding all four here and failing an
honest card six times over; job states had leaked into the vocabulary from the continuation rule,
which asks a different question. An implementation that reports `outcome_not_covered` for a job
state has that leak.
