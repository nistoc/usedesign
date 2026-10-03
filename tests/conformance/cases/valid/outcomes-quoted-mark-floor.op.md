---
id: sample.photo.upload
title: Upload a photo
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: none, to: uploaded }
concurrency:
  mode: none_by_design
  rationale: Every upload is a new record; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The album still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-upload
    text: The photo is stored

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /albums/{id}/photos
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: AlbumView
    control: button[data-action="upload-photo"]
    covers_outcomes:
      uploaded: the photo appears at the top of the album
      unauthorized: red status line «फिर से» beside the file name, until the member signs in
      not_found: grey toast «फिर से» at the bottom, when the album was removed

data:
  entities: [photo]
provenance: none
reversibility: irreversible
---

The one quoted span is «फिर से», "again": two words, but only `फिर` has two letters (category L);
`से` is one letter and a vowel sign, a mark. Marks and numbers do not count toward the two-letter
floor, so the span is not a message, neither value keeps a span, and each is compared whole — and
the two differ. An implementation that counts marks, or code points, toward the floor keeps the
span and warns. The manifest asserts the silence: `absent_warnings`.
