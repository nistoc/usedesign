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

The clean case. Pressing each control in `draft` sent what its `calls` names, plus rereads:
`save-as-plan` reread the draft's history (an audited read, `records_only`), `start-now` reread the
list between publishing and starting, `rename` reread it after renaming, and `close` — `calls:
null` — sent only a reread. A read the contract does not name is left out of what was sent. The
reads `refresh` sends ARE its `calls`: a read the contract names stays. `tag-a` belongs to a family,
which has no one name to press, so what it sent is not compared; `published` recorded nothing.
