---
id: sample.message.send
title: Send a message
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: draft, to: sent }
concurrency:
  mode: none_by_design
  rationale: Every message is a new record; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The conversation still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-send
    text: The message is sent

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /conversations/{id}/messages
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: ConversationView
    control: button[data-action="send-message"]
    covers_outcomes:
      sent: the message appears at the bottom of the conversation
      # escapes, so that an editor that changes this file's normal form cannot make the two one
      unauthorized: "red status line «\u03b1\u0345\u0301 ab cd», beside the sign-in link"
      not_found: "grey toast «\u1fb4 ab cd», when the conversation was removed"

data:
  entities: [message]
provenance: none
reversibility: irreversible
---

One quoted line, its first word written two ways. In `unauthorized` it is `α` followed by U+0345
COMBINING GREEK YPOGEGRAMMENI and U+0301 COMBINING ACUTE ACCENT; in `not_found` it is the composed
`ᾴ` (U+1FB4) — canonically equivalent, the same letter on screen. Rule 1 folds case first and
then NFC-normalises: folding turns U+0345 into the letter `ι`, which NFC cannot move past the
accent, so the first span reads `αί ab cd`; folding `ᾴ` gives `άι`, and the second reads
`άι ab cd`. The spans differ, and there is no warning. This is the known limit §5.7 names,
pinned so that the order of rule 1 cannot change unnoticed: an implementation that decomposes
first — NFD, then folding, then NFC — or normalises before folding reads both spans as
`άι ab cd` and warns. The manifest asserts the silence: `absent_warnings`.
