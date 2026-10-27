---
id: sample.loan.return
title: Return a loaned copy
scenario: sample.flow
actors: [librarian]
maturity: conceived
data_transition: { from: on_loan, to: available }
concurrency:
  mode: none_by_design
  rationale: Returning twice leaves the copy available.
  source: docs/design.md:1
steps:
  - id: s1-loan-exists
    text: The loan exists
    on_violation: { error: loan_not_found, http: 404 }
  - id: s2-loan-open
    text: The loan has not been returned yet
    on_violation: { error: loan_already_returned, http: 409 }
  - id: s3-return
    text: The copy becomes available again

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/loans/{id}/return
    responses: [200, 404, 409]

data:
  entities: [copy, loan]
provenance: none
reversibility: reversible
---

This is the fixture card that the scaffold test expects to be skipped as declared. It names the
route `POST /v1/loans/{id}/return`, which the OpenAPI document lists as
`/v1/loans/{loanId}/return`: the parameter names differ, the route does not.
