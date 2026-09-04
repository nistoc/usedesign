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
    shown_when: [absent, links_blocked]
---
Three screen states over two data states. `links_blocked` exists as its own screen state because
that is the only way to PROVE the reason is shown; for the data the card is still `absent`. The
`states:` map says so once, and the shown_when rule holds through it.
