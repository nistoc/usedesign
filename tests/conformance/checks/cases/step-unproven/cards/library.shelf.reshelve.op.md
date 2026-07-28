---
id: library.shelf.reshelve
title: Return a copy to its shelf position
scenario: A returned book goes back where readers can find it
actors: [staff]
maturity: implemented
maturity_evidence:
  implemented: src/shelving/ReshelveHandler.ts

steps:
  - id: s1-copy-returned
    text: The copy is in the returned state
    on_violation: { error: copy_not_returned, http: 409 }
  - id: s2-position-known
    text: The copy has a shelf position on record
    on_violation: { error: position_unknown, http: 422 }
  - id: s3-commit
    text: The copy is marked as shelved

concurrency:
  mode: none_by_design
  rationale: Two staff members shelving the same copy converge on the same end state.

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/copies/{copyId}/reshelve

data:
  entities: [copy]
data_transition: { from: returned, to: on_shelf }
provenance: { activity_kind: shelving }
reversibility: reversible

tests:
  - { id: ReshelveTests.refuses_copy_not_returned, covers: s1-copy-returned, level: integration }
  - { id: ReshelveTests.marks_copy_as_shelved, covers: s3-commit, level: integration }
---

# Return a copy to its shelf position

A conformance case, not an example to imitate.

Step `s2-position-known` has **no test and no entry in `coverage_gaps`** — the ordinary way a
branch goes unproven. Nobody decided to leave it untested; it simply was never written, and
nothing in the repository says so out loud.

Check 2 exists to turn that silence into a line of output.
