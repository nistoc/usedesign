---
id: library.member.settlement-check
title: Is this member settled — any open loans, fines or holds?
serves_step:
  operation: library.member.purge
  step: s3-settled
  purpose: >
    Let the operator see the obstacle before attempting an irreversible action, instead of
    discovering it as a rejection. The point is not to report the conflict afterwards — it is
    to prevent the attempt.
actors: [library_admin, front_desk]

maturity: in_production
maturity_evidence:
  implemented: src/members/SettlementQuery.ts
  tested: 3 tests
  deployed: { env: production, since: 2026-04-11 }

data_transition: null

concurrency:
  mode: none_by_design
  rationale: Read-only query; nothing to collide with.
  source: src/members/SettlementQuery.ts:12

steps:
  - id: s1-member-exists
    text: Member reference resolves
    on_violation: { error: member_not_found, http: 404 }
  - id: s2-answer
    text: Returns settled true or false, plus the counters behind the answer
    rationale: >
      The counters ship with the answer on purpose. "Not settled" alone sends the operator
      hunting through three screens to find out why.

interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/members/{memberId}/settlement
    responses: [200, 404]
    source: src/members/routes.ts:41
  ui:
    transport: ui
    screen: AdminMemberDetail
    control: settlement badge
    covers_steps: [s2-answer]
    source: web/src/pages/admin/AdminMemberDetail.tsx:150

data:
  entities: [loan, fine, hold]

provenance: none

reversibility: reversible

tests:
  - { id: SettlementTests.unknown_member_is_404, covers: s1-member-exists, level: integration }
  - { id: SettlementTests.counters_accompany_the_verdict, covers: s2-answer, level: unit }
  - { id: SettlementTests.closed_loans_do_not_count, covers: s2-answer, level: unit }
---

# Is this member settled?

A helper operation. It has no scenario of its own — nobody wakes up wanting to check settlement —
so it declares `serves_step` instead, pointing at the step of
[`library.member.purge`](library.member.purge.op.md) that it exists to protect.

That link is what keeps it from looking like an orphaned endpoint in the catalogue. It also gives
the checker a rule: an operation with neither `scenario` nor `serves_step` is suspicious, because
nobody can say who calls it.

Two smaller things this card demonstrates:

- `provenance: none` is stated explicitly. A read-only query records nothing, and saying so keeps
  the checker from demanding an audit test that should not exist.
- `data_transition: null` with no `mutates` — the combination that identifies a pure read.
