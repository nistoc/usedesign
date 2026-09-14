---
id: library.loan.checkout.on-behalf
title: Check out a copy to a member who called the desk
scenario: library.borrowing.member-borrows-a-book
actors: [librarian]

maturity: tested
maturity_evidence:
  implemented: src/loans/CheckoutOnBehalf.ts + src/loans/CheckoutHandler.ts:40
  tested: 2 tests

variant_of:
  card: library.loan.checkout
  shared: src/loans/CheckoutHandler.ts
  inherits: [s1-copy-available, s3-member-standing, s4-loan-limit, s5-commit]

data_transition: { from: available, to: on_loan }

concurrency:
  mode: none_by_design
  rationale: >
    The desk works from the shelf, not from a revision it read earlier; the shared handler's
    conditional write still refuses a copy that is no longer available.
  source: src/loans/CheckoutOnBehalf.ts:12

steps:
  - id: s8-acting-librarian
    text: The caller is a librarian acting for a named member
    on_violation: { error: forbidden, http: 403 }
  - id: s1-copy-available
    text: The physical copy is currently available
    on_violation: { error: copy_not_available, http: 409 }
  - id: s3-member-standing
    text: The member has no blocking holds
    on_violation: { error: member_blocked, http: 403 }
  - id: s4-loan-limit
    text: The member is below the concurrent loan limit for their tier
    on_violation: { error: loan_limit_reached, http: 409 }
  - id: s5-commit
    text: The copy becomes on_loan to the member
  - id: s9-audit-on-behalf
    text: The checkout is recorded with both the member and the acting librarian
    on_violation: { error: audit_write_failed, http: 500 }

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/members/{memberId}/checkouts
    responses: [200, 403, 409, 500]

data:
  entities: [copy, loan, member]

provenance:
  activity_kind: loan_checkout
  attributed_to: the acting librarian, on behalf of the member

reversibility:
  reversible_via: library.loan.return

tests:
  - { id: CheckoutOnBehalfTests.kiosk_identity_is_refused, covers: s8-acting-librarian, level: integration }
  - { id: CheckoutOnBehalfTests.desk_checkout_is_audited_with_both_names, covers: s9-audit-on-behalf, level: integration }
---
