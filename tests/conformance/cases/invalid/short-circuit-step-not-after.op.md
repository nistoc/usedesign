---
id: library.loan.renew
title: Renew a loan, safe to retry — the short path names a step that ran before it
scenario: library.borrowing.member-renews-a-loan
actors: [member]

maturity: tested
maturity_evidence:
  implemented: src/loans/RenewHandler.ts
  tested: 4 tests

data_transition: { from: on_loan, to: on_loan }

concurrency:
  mode: etag_optional
  rationale: >
    The loan's revision is honoured when sent; a stored answer is also replayed by Idempotency-Key.
  source: src/loans/RenewHandler.ts#RenewHandler

steps:
  - id: s2-precondition
    text: When If-Match is sent, it equals the loan's current revision
    on_violation: { error: revision_mismatch, http: 412 }
  - id: s1-replay
    text: A stored answer for the same Idempotency-Key, member, method and path is sent back as it was
    short_circuit:
      when: the same key from the same member on the same method and path, answered 2xx within 24 hours
      runs_again: [s2-precondition, s3-member-active]
      returns: the stored status and body, with the header Idempotent-Replay true
  - id: s3-member-active
    text: The member's card is active
    on_violation: { error: member_inactive, http: 403 }
  - id: s4-commit
    text: The due date moves by the period, and the answer is stored under the key

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/loans/{loanId}/renewals
    headers_required: [Idempotency-Key]
    responses: [200, 403, 412]

data:
  entities: [loan, member]

provenance:
  activity_kind: loan_renewed
  attributed_to: the member

reversibility:
  reversible_via: library.loan.return

tests:
  - { id: RenewTests.stale_revision_is_412, covers: s2-precondition, level: integration }
  - { id: RenewTests.same_key_returns_the_first_answer, covers: s1-replay, level: integration }
  - { id: RenewTests.blocked_card_is_refused_on_a_replay_too, covers: s3-member-active, level: integration }
  - { id: RenewTests.due_date_moves_once, covers: s4-commit, level: integration }
---

If-Match is listed before the replay, and the replay says it runs again. A step listed before the
short path has already run on every path; naming it in `runs_again` contradicts the order of the
list. Either the step belongs after the replay — on the usual path it runs only after the key is
looked up — or it does not belong in `runs_again`.
