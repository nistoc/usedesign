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
    calls: [sample.pass.start, sample.draft.publish]
    shown_when: [draft]
  - control: rename
    calls: sample.draft.rename
    shown_when: [draft]
  - control: close
    calls: null
  - control: refresh
    calls: [sample.draft.list, sample.pass.list]
  - control_pattern: "tag-*"
    calls: sample.draft.rename
    shown_when: [draft]
---

The planted break a pilot's frontend made on purpose: the contract's `start-now` says
`[sample.pass.start, sample.draft.publish]` — the seal dropped, the start moved first — while the
button sends seal, publish, start. `sample.pass.start` departs from `none`, which switches the
shown_when rule off, so every check before round 33 passed it.
