---
id: sample.plan.copy
title: Copy a plan into my list
scenario: sample.flow
actors: [member]
maturity: conceived
data_transition: { from: none, to: copied }
concurrency:
  mode: none_by_design
  rationale: Every copy is a new plan; nothing collides.
  source: docs/design.md:1
steps:
  - id: s1-authenticated
    text: The token is recognised
    on_violation: { error: unauthorized, http: 401 }
  - id: s2-exists
    text: The plan still exists
    on_violation: { error: not_found, http: 404 }
  - id: s3-copy
    text: The copy joins the member's list

interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /plans/{id}/copy
    responses: [200, 401, 404]
  ui:
    transport: ui
    screen: PlanList
    control: button[data-action="copy-plan"]
    covers_outcomes:
      copied: the copy appears in «Mine»
      unauthorized: 'toast «! Copy to «Mine»: failed» with a red «!»'
      not_found: '» a stray closer and an unclosed « before the same toast “COPY TO “MINE”: FAILED”'

data:
  entities: [plan]
provenance: none
reversibility: irreversible
---

One toast, written two ways, and every rule of reading the quotes on the path between them. A
quote of the same kind nests and belongs to the outer span — «Copy to «Mine»: failed» is one span;
a glyph is not a word, so «!» and the leading `!` fall away; “…” counts as «…» does; a closer with
no opener is ignored, and an opener never closed opens nothing, so the “…” after it is still read;
case is folded. Both values come to the one span `copy to mine failed`, and the two implementations
must agree that they do — the warning is the proof.
