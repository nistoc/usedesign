---
usedesign_form: 1
id: sample.draft.foot
screen: DraftFoot
entity: draft
presents:
  - field: draft-name
    shows: the name the draft will be published under
controls:
  - control: start-now
    calls: [sample.draft.seal, sample.draft.publish, sample.pass.start]
    shown_when: [draft, sealed]
---

The chain is also offered in `sealed`. Its second step departs from there, its first
does not — and the chain starts with the first, so pressing it in `sealed` fails at
step one. An implementation accepting a state that ANY step departs from passes here;
1.1.0 skipped a list entirely and passed here too.
