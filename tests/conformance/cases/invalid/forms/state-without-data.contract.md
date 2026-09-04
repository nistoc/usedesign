---
usedesign_form: 1
id: demo.card.create-rail
screen: CreateCardRail
states:
  absent: { data: absent }
  links_blocked: { note: a malformed URL typed }
presents:
  - field: card-form
    shows: the fields of the new card
---

Every entry of the `states:` map must name the data state it lives in — that is the map's whole
purpose. An entry with only a note maps nowhere, and check 5 would silently fall back to
identity for it.
