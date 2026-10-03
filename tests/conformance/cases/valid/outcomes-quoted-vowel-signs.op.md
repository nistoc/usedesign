---
id: sample.list.save
title: Save a list
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: draft, to: saved }
concurrency:
  mode: none_by_design
  rationale: One member edits one list; nothing else writes it.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The list still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-save
    text: The list is saved

interfaces:
  rest:
    transport: http_rest
    method: PUT
    path: /lists/{id}
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: ListEditor
    control: button[data-action="save-list"]
    covers_outcomes:
      saved: status line «सूची सहेजी गई»
      unauthorized: red status line «सहेजा नहीं जा सका», beside the sign-in link
      not_found: red status line «सहेजी नहीं जा सकी», under the title

data:
  entities: [list]
provenance: none
reversibility: irreversible
---

Two different lines that differ only in their vowel signs: `सहेजा … सका` and `सहेजी … सकी`, the
masculine and the feminine ending. Devanagari writes most vowels as marks on a consonant (Unicode
category M), so a checker that reads every mark as a space reads both lines as the same five
fragments and warns about two endings the user can tell apart. A mark belongs to the word before
it: a word is a run of letters and numbers with the marks that follow them, and still needs two
letters (category L) to count toward the two-word floor. Silent on the published 1.2.0 box too,
which compared the values whole. The manifest asserts the silence: `absent_warnings`.
