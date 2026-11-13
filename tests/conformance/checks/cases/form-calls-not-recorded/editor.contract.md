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

The same contract against an inventory that records no `calls` — every inventory before round 33.
Nothing is compared and nothing is reported: absence of the measurement is not evidence. The
summary says "compared for 0 of 5", so the silence is visible.
