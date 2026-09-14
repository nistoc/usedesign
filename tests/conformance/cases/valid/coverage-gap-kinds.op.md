---
id: sample.copy.reserve
title: Reserve a copy for a member
scenario: sample.flow
actors: [member]
maturity: tested
maturity_evidence:
  implemented: src/loans/ReserveHandler.ts
  tested: 1 test
data_transition:
  from: available
  to: reserved
concurrency:
  mode: none_by_design
  rationale: One conditional write on the copy's status; a second reservation finds the copy already taken.
  source: src/loans/ReserveHandler.ts:20
steps:
  - id: s1-authenticated
    text: The token is recognised before the store is read
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-member-lookup
    text: The member is resolved through the directory service
    on_violation: { error: member_not_found, http: 404 }
  - id: s3-id-unique
    text: The generated reservation id is not already taken
    on_violation: { error: id_conflict, http: 409 }
  - id: s4-commit
    text: The copy becomes reserved for the member

tests:
  - { id: ReserveTests.member_reserves_an_available_copy, covers: s4-commit, level: integration }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /copies/{id}/reservations
    responses: [201, 401, 404, 409]

data:
  entities: [copy, reservation]
provenance: none
reversibility:
  reversible_via: sample.copy.release

coverage_gaps:
  - step: s1-authenticated
    gap: No test calls the route without a token
  - step: s2-member-lookup
    gap: The test host stubs the directory service with one that never fails — a failed lookup cannot be produced until the stub can fail
    kind: harness
  - step: s3-id-unique
    gap: The id is random; a collision cannot be produced from outside, and the branch is a guard
    kind: unreachable
---

Three gaps, three reasons. The first could be written this afternoon; the second waits for a change to
the test host, not for a test; the third will never have a test, because nothing outside the handler can
make a random id collide. Before round 26 all three read the same — "no test" — and a gate counting them
could not tell the work that is simply undone from the work that cannot be done.
