---
usedesign_form: 1
id: sample.draft.foot
screen: DraftFoot
entity: draft
presents:
  - field: draft-name
    shows: the name the draft will be published under
controls:
  - control: save-as-plan
    calls: [sample.draft.seal, sample.draft.publish]
    shown_when: [draft]
  - control: start-now
    calls: [sample.draft.seal, sample.draft.publish, sample.pass.start]
    shown_when: [draft]
---

The clean chain. Both controls are shown in `draft`, where the first operation departs
from; the second departs from `sealed` and the third from `absent` — states the step
before each left, which no screen state shows. An implementation holding EVERY step
of the chain against `shown_when` fails here with shown_when_conflicts_transition.
