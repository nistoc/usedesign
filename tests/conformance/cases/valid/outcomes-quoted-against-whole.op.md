---
id: sample.note.rename
title: Rename a note
scenario: sample.flow
actors: [author]
maturity: conceived
data_transition: { from: draft, to: renamed }
concurrency:
  mode: none_by_design
  rationale: One author edits one note; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-free
    text: No other note carries the new name
    on_violation: { error: name_taken, http: 409 }
  - id: s3-exists
    text: The note still exists
    on_violation: { error: not_found, http: 404 }
  - id: s4-open
    text: The note is not archived
    on_violation: { error: archived, http: 409 }
  - id: s5-rename
    text: The note takes the new name

interfaces:
  rest:
    transport: http_rest
    method: PATCH
    path: /notes/{id}
    responses: [200, 401, 404, 409]
  ui:
    transport: ui
    screen: NoteTitle
    control: input[data-field="note-title"]
    covers_outcomes:
      renamed: the title changes in place
      unauthorized: status line «Could not rename now»
      name_taken: could not rename now
      not_found:
      archived:

data:
  entities: [note]
provenance: none
reversibility: reversible
---

Two silences the rule specifies. A value whose quoted span is kept is compared by its set of
spans, and a value with no kept span is compared whole; the two are never equal, even when the
words match, because the unquoted value is the author's prose, not a line the user reads. And a
null — the outcome is *not shown* — is never compared: two nulls are two declared silences, each
its own `outcome_unshown`, not one sentence worn twice. An implementation that compared the span
text with the whole value, or grouped the nulls, warns here; the manifest asserts the silence
(`absent_warnings`).
