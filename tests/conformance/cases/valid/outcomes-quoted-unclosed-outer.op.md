---
id: sample.draft.submit
title: Submit a draft
scenario: sample.flow
actors: [editor]
maturity: conceived
data_transition: { from: draft, to: submitted }
concurrency:
  mode: none_by_design
  rationale: Submitting twice leaves the draft submitted.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-editor
    text: The caller may submit this draft
    on_violation: { error: forbidden, http: 403 }
  - id: s3-submit
    text: The draft moves to `submitted`

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /drafts/{id}/submit
    responses: [200, 401, 403]
  ui:
    transport: ui
    screen: DraftEditor
    control: button[data-action="submit-draft"]
    covers_outcomes:
      submitted: the draft leaves the editor
      unauthorized: 'the banner «Session over, then the line «Sign in to submit the draft»'
      forbidden: the line «Sign in to submit the draft» under the title

data:
  entities: [draft]
provenance: none
reversibility: irreversible
---

Quotes pair as brackets do. The first value opens «…» twice and closes it once: the inner pair is
a span, `sign in to submit the draft`, and the outer opener, never closed, opens nothing. Both
values come to that one span, and the manifest pins which outcomes the warning groups
(`warning_messages`). An implementation that paired the outer opener with the first closer reads
`session over then the line sign in to submit the draft`; one that let an unclosed opener swallow
the rest reads everything after it as one span. Either stays silent here.
