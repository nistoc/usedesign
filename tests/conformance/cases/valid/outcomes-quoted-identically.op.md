---
id: sample.note.save
title: Save a note
scenario: sample.flow
actors: [author]
maturity: conceived
data_transition: { from: draft, to: saved }
concurrency:
  mode: none_by_design
  rationale: One author edits one note; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The note still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-save
    text: The note is saved

interfaces:
  rest:
    transport: http_rest
    method: PUT
    path: /notes/{id}
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: NoteEditor
    control: button[data-action="save-note"]
    covers_outcomes:
      saved: status line «Saved» (Editor.tsx:40)
      unauthorized: red status line «Could not save — try again»; the editor stays open (Editor.tsx:48)
      not_found: the same «Could not save — try again», reached when the note was deleted elsewhere (Editor.tsx:61)

data:
  entities: [note]
provenance: none
reversibility: irreversible
---

Two refusals, one status line, and every word around it different. An author who re-measures a
screen writes where the line appears, why, and which code renders it — and each value becomes a
unique string. Compared whole, as 1.2 compared them, the two refusals pass in silence: the user
who must sign in again is told to retry, and so is the user whose note is gone. The words the user
reads are inside «…», and those are what the checker compares.
