---
id: library.loan.checkout
title: Check out a copy to a member
scenario: library.borrowing.member-borrows-a-book
actors: [librarian, self_service_kiosk]

maturity: in_production
maturity_evidence:
  implemented: src/loans/CheckoutHandler.ts
  tested: 7 tests
  deployed: { env: production, since: 2026-07-02 }

data_transition: { from: available, to: on_loan }
since: { migration: "014", note: "due_date column added" }

concurrency:
  mode: etag_required
  source: src/loans/CheckoutHandler.ts:31
  on_duplicate: { http: 412, code: stale_copy_revision }

steps:
  - id: s1-copy-available
    text: The physical copy is currently available
    on_violation: { error: copy_not_available, http: 409 }
    source: src/loans/CheckoutHandler.ts:44
  - id: s2-concurrency
    text: Caller sent If-Match with the copy's current revision
    on_violation: { error: stale_copy_revision, http: 412 }
  - id: s3-member-standing
    text: Member has no blocking holds — unpaid fines above the threshold, or a suspended card
    on_violation: { error: member_blocked, http: 403 }
    rationale: >
      Checked before the loan limit so the member sees the real reason. Hitting the limit is
      recoverable by returning a book; a suspension is not, and conflating them sends people
      to the wrong desk.
  - id: s4-loan-limit
    text: Member is below the concurrent loan limit for their membership tier
    on_violation: { error: loan_limit_reached, http: 409 }
  - id: s5-commit
    text: Copy becomes on_loan, due date computed from the tier's loan period
  - id: s7-hold-fulfilled
    text: If this member was holding the title, the hold is closed and the queue moves on
    emits_notice: hold_fulfilled
    rationale: >
      Reported as a notice, not a warning: the queue moving is something the operation *did*,
      not something wrong with the request. Announced in an error channel, a successful checkout
      reads to the caller as a failed one.
      Numbered s7 although it runs before s6: step ids are identifiers, not positions. It was
      added after s6 existed, so it took the next free number instead of displacing one.
  - id: s6-audit
    text: A checkout event is recorded against the member and the copy
    on_violation: { error: audit_write_failed, http: 500 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/copies/{copyId}/checkout
    headers_required: [If-Match]
    responses: [200, 403, 409, 412]
    contract_version: application/vnd.library.loan.v2+json
    source: src/loans/routes.ts:58
  ui:
    transport: ui
    screen: CirculationDesk
    control: "Check out"
    covers_steps: [s1-copy-available, s3-member-standing, s4-loan-limit, s5-commit]
    source: web/src/pages/circulation/CirculationDesk.tsx:210

data:
  entities: [copy, loan, member, hold]
  fields_touched: [copy.status, copy.revision, loan.due_date, loan.checked_out_at]
  migrations: ["014"]

provenance:
  activity_kind: loan_checkout
  attributed_to: acting staff account, or the kiosk service identity
  on_failure: the checkout is rolled back — a loan without a recorded event is not allowed

reversibility:
  reversible_via: library.loan.return
  note: An accidental checkout is undone by an immediate return; the audit trail keeps both events.

taxonomy_refs: [concept:circulation, concept:membership-tier]

tests:
  - { id: CheckoutTests.rejects_copy_already_on_loan, covers: s1-copy-available, level: integration }
  - { id: CheckoutTests.rejects_stale_revision, covers: s2-concurrency, level: integration }
  - { id: CheckoutTests.blocked_member_cannot_borrow, covers: s3-member-standing, level: integration }
  - { id: CheckoutTests.limit_is_per_tier, covers: s4-loan-limit, level: unit }
  - { id: CheckoutTests.due_date_follows_tier_period, covers: s5-commit, level: unit }
  - { id: CirculationDesk.test.tsx:shows_reason_when_blocked, covers: s3-member-standing, level: ui }
  - { id: CheckoutTests.own_hold_is_closed_and_reported_as_notice, covers: s7-hold-fulfilled, level: integration }

coverage_gaps:
  - step: s6-audit
    gap: no test for the rollback path when the audit write fails
---

# Check out a copy to a member

Checkout is the moment a physical copy leaves the library's control. Everything before it is
reversible bookkeeping; after it, a real object is in someone's bag and the only way back is a
return.

That is why two different guards sit in front of the state change. **Member standing**
(`s3-member-standing`) asks *may this person borrow at all* — a suspended card or unpaid fines
above the threshold. **Loan limit** (`s4-loan-limit`) asks *may they borrow one more*. They are
deliberately separate steps with separate errors: the first sends the member to the front desk,
the second is fixed by returning something. A single "not allowed" error would send half of the
people to the wrong place.

The due date is not stored on the request. It is computed at `s5-commit` from the membership
tier's loan period, so that changing a tier's policy does not require rewriting open loans.
