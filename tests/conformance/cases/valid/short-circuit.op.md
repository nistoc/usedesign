---
id: library.loan.renew
title: Renew a loan, safe to retry
scenario: library.borrowing.member-renews-a-loan
actors: [member]

maturity: tested
maturity_evidence:
  implemented: src/loans/RenewHandler.ts + src/http/IdempotencyFilter.ts
  tested: 5 tests

data_transition: { from: on_loan, to: on_loan }

concurrency:
  mode: idempotency_by_header
  rationale: >
    A renewal retried after a lost response must not move the due date twice. The stored answer
    is found by the key together with the member, the method and the path, so the same key on
    another loan is a new call.
  on_duplicate: { http: 200, code: first_answer_replayed }
  source: src/http/IdempotencyFilter.ts#IdempotencyFilter

steps:
  - id: s1-replay
    text: A stored answer for the same Idempotency-Key, member, method and path is sent back as it was
    short_circuit:
      when: the same key from the same member on the same method and path, answered 2xx within 24 hours
      runs_again: [s2-member-active]
      returns: the stored status and body, with the header Idempotent-Replay true
      binds: [member, method, path]
      unbound: [body]
      on_unbound: >
        the stored answer goes out; a different period under the same key is neither checked nor
        run — a new renewal goes under a new key
  - id: s2-member-active
    text: The member's card is active
    on_violation: { error: member_inactive, http: 403 }
    rationale: >
      Checked again on a replay as well: a card blocked since the first call is not renewed by
      sending the old key.
  - id: s3-period
    text: The requested period is one the loan's tier allows
    on_violation: { error: period_not_allowed, http: 422 }
  - id: s4-not-reserved
    text: Nobody holds a reservation on the copy
    on_violation: { error: copy_reserved, http: 409 }
  - id: s5-commit
    text: The due date moves by the period, and the answer is stored under the key

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/loans/{loanId}/renewals
    headers_required: [Idempotency-Key]
    responses: [200, 403, 409, 422]

data:
  entities: [loan, member]

provenance:
  activity_kind: loan_renewed
  attributed_to: the member

reversibility:
  reversible_via: library.loan.return

tests:
  - { id: RenewTests.same_key_returns_the_first_answer_and_writes_nothing, covers: s1-replay, level: integration }
  - { id: RenewTests.blocked_card_is_refused_on_a_replay_too, covers: s2-member-active, level: integration }
  - { id: RenewTests.period_beyond_the_tier_is_refused, covers: s3-period, level: integration }
  - { id: RenewTests.reserved_copy_is_not_renewed, covers: s4-not-reserved, level: integration }
  - { id: RenewTests.due_date_moves_once, covers: s5-commit, level: integration }
---

A step where the call can end early (§5.3). On a replay the stored answer goes out after the
member's card is checked again (`runs_again`); the period, the reservation and the commit do not
run — the list of steps reads as the usual path, and the field says what the short path leaves out.
The key does not bind the body, and `on_unbound` says what a different body under the same key
receives, so `guard_bypassable` stays quiet.
