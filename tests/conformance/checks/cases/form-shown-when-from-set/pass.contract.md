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
    shown_when: [finished, partial, abandoned]
---
The resume control is offered in exactly the states the operation departs from — all three of
them. With `from` as a set the rule holds; with the old single-string `from` the card could only
say `any`, and this control would never have been checked at all.
