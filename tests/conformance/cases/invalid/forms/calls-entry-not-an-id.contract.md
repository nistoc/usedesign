---
usedesign_form: 1
id: demo.draft.foot
screen: DraftFoot
presents:
  - field: draft-name
    shows: the name the draft will be published under
controls:
  - control: save-as-plan
    calls: [demo.draft.seal, 7]
    shown_when: [draft]
---

An entry that is not an operation id names no card at all. Read as a chain it would be skipped
without a word, and the chain would read shorter than it is written.
