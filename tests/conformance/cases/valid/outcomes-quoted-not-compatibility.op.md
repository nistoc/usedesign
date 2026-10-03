---
id: sample.export.run
title: Run an export
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: none, to: exported }
concurrency:
  mode: none_by_design
  rationale: Every export is a new file; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The report still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-export
    text: The file is written

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /reports/{id}/exports
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: ReportView
    control: button[data-action="run-export"]
    covers_outcomes:
      exported: the file downloads
      unauthorized: red status line «Save failed now»
      not_found: red status line «Ｓave failed now», its first letter full-width

data:
  entities: [report]
provenance: none
reversibility: irreversible
---

The same words, but `not_found` begins with a full-width `Ｓ` (U+FF33). The value is NFC-normalised
— canonical composition only — and a full-width letter is a compatibility character, not a
canonical one: case folding makes it `ｓ`, never `s`, so the two spans differ and there is no
warning. An implementation that normalises to NFKC reads both as `save failed now` and warns. The
manifest asserts the silence: `absent_warnings`.
