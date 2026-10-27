---
usedesign_form: 1
id: demo.card.create-rail
screen: CreateCardRail
states: [absent, links_blocked]
presents:
  - field: card-form
    shows: the fields of the new card
---

The screen states listed, not mapped. `states:` is a map from each screen state to the data state
it lives in; a list names the states and maps none of them, so check 5 could only fall back to
reading every screen state as a data state of the same name — the identity the map exists to
replace.
