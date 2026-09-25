---
usedesign_form: 1
id: sample.draft.foot
screen: DraftFoot
entity: draft
presents:
  - field: draft-name
    shows: the name the draft will be published under
controls:
  - control: seal-and-archive
    calls: [sample.draft.seal, sample.draft.archive]
    shown_when: [draft]
---

The second step of the chain has no card. Every operation of a chain must be
described, not only the first: a warning names the step and its place in the chain.
The first step is described and departs from `draft`, so the state rule holds.
