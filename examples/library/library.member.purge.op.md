---
id: library.member.purge
title: Permanently erase a member record
scenario: library.administration.honour-erasure-request
actors: [library_admin]

maturity: in_production
maturity_evidence:
  implemented: src/admin/MemberPurgeHandler.ts
  tested: 6 tests
  deployed: production

data_transition: { from: closed, to: erased }
since: { migration: "031", note: "erasure_receipt table" }

concurrency:
  mode: idempotency_by_header
  rationale: >
    A retried purge must not produce a second receipt. There is no revision to match against —
    the record may already be gone.
  source: src/admin/routes.ts:64

steps:
  - id: s1-role
    text: Caller holds the administrator role
    on_violation: { error: role_forbidden, http: 403 }
  - id: s2-closed
    text: Membership is already closed — an active member cannot be purged directly
    on_violation: { error: member_still_active, http: 409 }
    rationale: >
      Forcing closure first makes erasure a two-person, two-step act. A single call that both
      closes and erases would turn a misclick into an unrecoverable loss.
  - id: s3-settled
    text: No open loans, fines or holds remain
    on_violation:
      error: member_not_settled
      http: 409
      payload: [openLoanCount, outstandingFineTotal, activeHoldCount]
    rationale: >
      The refusal carries the counters, not just a verdict. An operator told only "not settled"
      goes hunting across three screens for the reason.
  - id: s4-erase
    text: Personal data is destroyed; loan history is reduced to anonymous counters
  - id: s5-receipt
    text: An erasure receipt is written, carrying no personal data — only the request reference and timestamp

interfaces:
  rest:
    transport: http_rest
    method: DELETE
    path: /v1/admin/members/{memberId}
    headers_required: [Idempotency-Key]
    responses: [204, 403, 409]
    source: src/admin/routes.ts:64
  ui:
    transport: ui
    screen: AdminMemberDetail
    control: "Erase permanently"
    covers_steps: [s1-role, s2-closed, s3-settled, s4-erase]
    note: Requires typing the member number to confirm — this is what `irreversible` buys the user
    source: web/src/pages/admin/AdminMemberDetail.tsx:301

data:
  entities: [member, loan_history, erasure_receipt]
  fields_touched: [member.*, loan_history.member_ref]
  migrations: ["031"]

provenance:
  activity_kind: member_erased
  attributed_to: the acting administrator
  on_failure: nothing is destroyed — erasure and receipt commit together or not at all

reversibility: irreversible

sensitivity:
  response_contains_secret: false
  logging_rule: >
    Neither the request nor the audit entry may retain the erased personal data — that would
    defeat the operation. Only the request reference is kept.

tests:
  - { id: PurgeTests.non_admin_is_refused, covers: s1-role, level: integration }
  - { id: PurgeTests.refuses_active_member, covers: s2-closed, level: integration }
  - { id: PurgeTests.refuses_member_with_open_loan, covers: s3-settled, level: integration }
  - { id: PurgeTests.history_survives_as_anonymous_counters, covers: s4-erase, level: integration }
  - { id: PurgeTests.receipt_carries_no_personal_data, covers: s5-receipt, level: unit }
  - { id: AdminMemberDetail.test.tsx:requires_typed_confirmation, covers: s4-erase, level: ui }
---

# Permanently erase a member record

This is the card that justifies making `reversibility` a required field.

Every other write in this example set can be undone: a checkout by a return, an import by a
rollback, a key by revocation. This one cannot, and that single fact changes four things at once
— the UI demands typed confirmation, the operation is gated behind a prior closure, the settlement
check refuses anything unsettled, and the test suite is expected to prove each refusal rather than
the happy path.

Without an explicit `irreversible`, none of that is visible from the outside. A reader would have
to open the handler and notice that the delete is physical, not a status change — the same reader
who is about to wire this endpoint into a bulk cleanup script.

Note also what `s5-receipt` guards against: an erasure that leaves no trace is indistinguishable
from data loss. The receipt proves the erasure happened, while carrying nothing that the erasure
was meant to destroy.
