---
usedesign_form: 1
id: sample.session.panel
screen: SessionPanel
maturity: designed
presents:
  - field: session-status
    shows: whether the session is running or over
controls:
  - control: finish
    calls: sample.session.finish
    shown_when: [finished]
---
Written before the screen: `finish` is shown in `finished`, but the card departs from
`active`. The rule needs the contract and the card only, so it runs before the screen exists —
as a warning on this path (a new check over existing fields, §8); a rendered screen keeps the
error.
