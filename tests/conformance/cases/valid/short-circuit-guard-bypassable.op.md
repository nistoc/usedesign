---
id: library.loan.extend-on-behalf
title: Extend a member's loan from the desk, safe to retry
scenario: library.borrowing.member-calls-the-desk
actors: [librarian]

maturity: tested
maturity_evidence:
  implemented: src/desk/ExtendOnBehalf.ts + src/http/IdempotencyFilter.ts
  tested: 4 tests

data_transition: { from: on_loan, to: on_loan }

concurrency:
  mode: etag_optional
  rationale: >
    The loan's revision is honoured when sent. A second mechanism the mode does not say: a stored
    answer is replayed by Idempotency-Key.
  source: src/desk/ExtendOnBehalf.ts#ExtendOnBehalf

steps:
  - id: s1-replay
    text: A stored answer for the same Idempotency-Key, desk, method and path is sent back as it was
    short_circuit:
      when: the same key from the same desk on the same method and path, answered 2xx within 24 hours
      returns: the stored status and body, with the header Idempotent-Replay true
      binds: [desk, method, path]
      unbound: [body, "header:If-Match"]
  - id: s2-precondition
    text: When If-Match is sent, it equals the loan's current revision
    on_violation: { error: revision_mismatch, http: 412 }
  - id: s3-days
    text: The requested days are within the desk's limit
    on_violation: { error: days_over_limit, http: 422 }
  - id: s4-commit
    text: The due date moves, and the answer is stored under the key

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/desk/members/{memberId}/loans/{loanId}/extensions
    headers_required: [Idempotency-Key]
    responses: [200, 412, 422]

data:
  entities: [loan]

provenance:
  activity_kind: loan_extended_on_behalf
  attributed_to: the acting librarian, on behalf of the member

reversibility:
  reversible_via: library.loan.return

tests:
  - { id: ExtendOnBehalfTests.same_key_returns_the_first_answer, covers: s1-replay, level: integration }
  - { id: ExtendOnBehalfTests.stale_revision_is_412, covers: s2-precondition, level: integration }
  - { id: ExtendOnBehalfTests.days_over_limit_are_refused, covers: s3-days, level: integration }
  - { id: ExtendOnBehalfTests.due_date_moves, covers: s4-commit, level: integration }
---

The short path does not bind the body or If-Match, and the card does not say what a call that
differs there receives: a call the day limit or a stale revision would refuse gets the first call's
200 instead. `guard_bypassable` is a warning, not an error — the card is valid, and the gap stays in
view until `on_unbound` names it.
