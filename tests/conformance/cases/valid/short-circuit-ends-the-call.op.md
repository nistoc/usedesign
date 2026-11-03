---
id: library.loan.return
title: Return a copy, once or again
scenario: library.borrowing.member-returns-a-book
actors: [librarian]

maturity: tested
maturity_evidence:
  implemented: src/loans/ReturnHandler.ts
  tested: 3 tests

data_transition: { from: on_loan, to: available }

concurrency:
  mode: none_by_design
  rationale: >
    Returning a copy already back on the shelf changes nothing: the second scan answers with the
    loan as it stands and writes nothing.
  source: src/loans/ReturnHandler.ts#ReturnHandler

steps:
  - id: s1-loan-exists
    text: The loan exists
    on_violation: { error: loan_not_found, http: 404 }
  - id: s2-already-returned
    text: A loan already closed is answered as it stands
    short_circuit:
      when: the loan was closed by an earlier return
      returns: 200 with the closed loan; nothing is written
  - id: s3-commit
    text: The loan is closed and the copy becomes available

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/loans/{loanId}/return
    responses: [200, 404]

data:
  entities: [copy, loan]

provenance:
  activity_kind: loan_returned
  attributed_to: the librarian at the desk

reversibility:
  reversible_via: library.loan.checkout

tests:
  - { id: ReturnTests.unknown_loan_is_404, covers: s1-loan-exists, level: integration }
  - { id: ReturnTests.second_scan_writes_nothing, covers: s2-already-returned, level: integration }
  - { id: ReturnTests.copy_is_back_on_the_shelf, covers: s3-commit, level: integration }
---

A short path with nothing after it: no `runs_again`, so on that path no later step runs, and no
`unbound`, so `guard_bypassable` has nothing to say. "Already done — answer, write nothing" is the
other early exit the round's measurement named besides a replay.
