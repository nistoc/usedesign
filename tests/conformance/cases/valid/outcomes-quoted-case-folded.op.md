---
id: sample.profile.save
title: Save a profile
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: draft, to: saved }
concurrency:
  mode: none_by_design
  rationale: One member edits one profile; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The profile still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-save
    text: The profile is saved

interfaces:
  rest:
    transport: http_rest
    method: PUT
    path: /profiles/{id}
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: ProfileForm
    control: button[data-action="store-profile"]
    covers_outcomes:
      saved: status line «Profil gespeichert»
      unauthorized: status line «Größe nicht gespeichert»
      not_found: the same line in capitals, «GRÖSSE NICHT GESPEICHERT»

data:
  entities: [profile]
provenance: none
reversibility: irreversible
---

Case-folded, not lowercased: in a case-insensitive comparison `ß` matches `SS`, and lowercasing
keeps them apart — `größe` is not `grösse`. Python has `str.casefold()`; JavaScript has no case folding, so
an implementation there must build it — lowercasing alone reads two different lines here and stays
silent. Measured with Python 3.14 and Node 26, the two implementations agree on every character
both runtimes' Unicode tables assign.
