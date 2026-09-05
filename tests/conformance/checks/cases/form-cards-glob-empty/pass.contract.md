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
    shown_when: [abandoned]
---
A frontend contract whose `cards:` glob points at a sibling checkout that is not there. The
control still calls an operation; the checker must say ONCE that no cards were found, and then
warn about the call as undescribed — the reader learns the cause before the consequence.
