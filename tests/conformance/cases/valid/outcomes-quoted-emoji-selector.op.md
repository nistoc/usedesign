---
id: sample.bookmark.save
title: Save a bookmark
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: draft, to: saved }
concurrency:
  mode: none_by_design
  rationale: One member edits one bookmark; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The bookmark still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-save
    text: The bookmark is saved

interfaces:
  rest:
    transport: http_rest
    method: PUT
    path: /bookmarks/{id}
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: BookmarkEditor
    control: button[data-action="save-bookmark"]
    covers_outcomes:
      saved: status line «Bookmark saved»
      # an escape, so that an editor dropping invisible characters cannot erase U+FE0F unnoticed
      unauthorized: "red status line «⚠\uFE0F Could not save», beside the sign-in link"
      not_found: red status line «⚠ Could not save», under the title

data:
  entities: [bookmark]
provenance: none
reversibility: irreversible
---

One status line written twice: in `unauthorized` the warning sign carries U+FE0F, the variation
selector that asks for the emoji's colour form; in `not_found` it does not. The selector is a mark
(category M), but a mark belongs to the word before it, and here it follows a symbol — so it is
read as a space, like the sign itself, and both spans read `could not save`: one warning. An
implementation that keeps every mark as a word character reads the selector as a word of its own
and stays silent; so does 1.2.0, which compared the values whole.
