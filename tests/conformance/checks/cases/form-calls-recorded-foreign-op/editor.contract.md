---
usedesign_form: 1
id: sample.draft.editor
screen: DraftEditor
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
  - control: rename
    calls: sample.draft.seal
    shown_when: [draft]
  - control: close
    calls: null
  - control: refresh
    calls: [sample.draft.list, sample.pass.list]
  - control_pattern: "tag-*"
    calls: sample.draft.rename
    shown_when: [draft]
---

One operation per control, the wrong one: the contract's `rename` says `calls: sample.draft.seal`,
and pressing it sends `sample.draft.rename`. The seal departs from `draft`, where `rename` is shown,
so the shown_when rule agrees with the wrong contract.
