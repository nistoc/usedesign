---
usedesign_form: 1
id: sample.card.create-rail
screen: CreateCardRail
entity: card
states:
  absent: { data: absent, note: "form open, nothing typed yet" }
  links_blocked: { data: absent, note: a malformed URL typed — the submit is greyed out with its reason }
  not_arrived: { data: live, note: "the create succeeded, but the backend reported fields that did not land" }
presents:
  - field: card-form
    shows: the fields of the new card
  - field: links-reason
    shows: why the submit is blocked
    when: [links_blocked]
  - field: not-arrived-notice
    shows: which typed fields did not land
    when: [not_arrived]
controls:
  - control: submit-new-card
    calls: sample.card.create
    shown_when: [absent, links_blocked, not_arrived]
---
Here the contract ALSO shows the submit in `not_arrived` — a post-write screen state. Through
the map that is data state `live`, which the create operation cannot depart from: pressing it
there would create a second record. The real defect this map made visible (issue #11).
