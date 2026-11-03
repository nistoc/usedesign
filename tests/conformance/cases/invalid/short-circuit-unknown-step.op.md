---
id: library.loan.renew
title: Renew a loan, safe to retry — the short path names a step the card does not have
scenario: library.borrowing.member-renews-a-loan
actors: [member]

maturity: tested
maturity_evidence:
  implemented: src/loans/RenewHandler.ts
  tested: 3 tests

data_transition: { from: on_loan, to: on_loan }

concurrency:
  mode: idempotency_by_header
  rationale: >
    A renewal retried after a lost response must not move the due date twice.
  on_duplicate: { http: 200, code: first_answer_replayed }
  source: src/http/IdempotencyFilter.ts#IdempotencyFilter

steps:
  - id: s1-replay
    text: A stored answer for the same Idempotency-Key, member, method and path is sent back as it was
    short_circuit:
      when: the same key from the same member on the same method and path, answered 2xx within 24 hours
      runs_again: [s2-member-consent]
      returns: the stored status and body, with the header Idempotent-Replay true
  - id: s2-member-active
    text: The member's card is active
    on_violation: { error: member_inactive, http: 403 }
  - id: s3-commit
    text: The due date moves by the period, and the answer is stored under the key

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/loans/{loanId}/renewals
    headers_required: [Idempotency-Key]
    responses: [200, 403]

data:
  entities: [loan, member]

provenance:
  activity_kind: loan_renewed
  attributed_to: the member

reversibility:
  reversible_via: library.loan.return

tests:
  - { id: RenewTests.same_key_returns_the_first_answer, covers: s1-replay, level: integration }
  - { id: RenewTests.blocked_card_is_refused, covers: s2-member-active, level: integration }
  - { id: RenewTests.due_date_moves_once, covers: s3-commit, level: integration }
---

`runs_again` names `s2-member-consent`, a step this card does not have — a name from another card,
or one renamed since. What the short path still runs has to be one of the card's own steps, or the
field says nothing anyone can check.
