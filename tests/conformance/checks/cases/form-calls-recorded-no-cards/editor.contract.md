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

The config declares no `cards:`. The inventory records `start-now` sending its chain in another
order, which with cards is a `form_calls_mismatch`. Without cards a read cannot be told from a
write, so nothing is compared and the summary says NOT COMPARED; every `calls` reads as
undescribed, as it did before round 33.
