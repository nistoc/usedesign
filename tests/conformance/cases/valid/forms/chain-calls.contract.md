---
usedesign_form: 1
id: demo.draft.foot
screen: DraftFoot
entity: draft
presents:
  - field: draft-name
    shows: the name the draft will be published under
controls:
  - control: save-as-plan
    calls: [demo.draft.seal, demo.draft.publish]
    shown_when: [draft]
    behaviour: seals the draft under the typed name, then publishes it
  - control: start-now
    calls: [demo.draft.seal, demo.draft.publish, demo.pass.start]
    shown_when: [draft]
    behaviour: the same two steps, then starts a pass over the published plan
  - control: discard
    calls: demo.draft.discard
    shown_when: [draft]
---

Round 27: two controls that each run more than one operation, named as a chain in call order.
Before 1.2 the schema accepted one operation per control, so a chain could be written only as
one of its steps plus prose — and the two sides of the same screen (the contract and the cards)
picked different steps. A single operation is still written as its id (`discard`).
