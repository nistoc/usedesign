---
id: sample.draft.save
title: Save a draft
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: none, to: saved }
concurrency:
  mode: none_by_design
  rationale: One editor holds one draft; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-editor
    text: The caller may edit this draft
    on_violation: { error: forbidden, http: 403 }
  - id: s3-save
    text: The draft is saved

interfaces:
  rest:
    transport: http_rest
    method: PUT
    path: /drafts/{id}
    responses: [200, 401, 403]
  ui:
    transport: ui
    screen: DraftEditor
    control: button[data-action="save-draft"]
    covers_outcomes:
      saved: the row loses its draft mark
      unauthorized: pressing «Save draft» shows the red line «Could not save the draft»
      forbidden: the same red line «Could not save the draft», under the row

data:
  entities: [draft]
provenance: none
reversibility: irreversible
---

A known limit, pinned. The same message as in `outcomes-quoted-beside-a-button`, but this button's
name has two words, and a quoted span of two words of two letters is read as a message. One value
quotes the button and the line, the other quotes the line alone: two different sets, and the
refusals pass in silence although the user cannot tell them apart. SPEC §5.7 compares the kept
spans as a set and lists this among its known limits — quote only the line the user reads and name
the button without quotes. An implementation that matched one set inside another would warn here
and read the rule differently from the specification; the manifest asserts the silence
(`absent_warnings`), and a later round that changes the rule changes this case with it.
