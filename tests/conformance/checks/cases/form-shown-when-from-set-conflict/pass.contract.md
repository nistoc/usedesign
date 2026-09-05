---
usedesign_form: 1
id: sample.pass.panel
screen: PassPanel
entity: pass
presents:
  - field: pass-status
    shows: the pass status in words
controls:
  - control: resume-pass
    calls: sample.pass.resume
    shown_when: [active, finished, partial, abandoned]
---
The resume control is also offered in `active`, which the operation does not depart from — a
conflict against a set, judged member by member.
