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
    shown_when: [active]
---
The card describes no screen at all — its only interface is `rest`. A card that has not
reached its screens yet is behind, not wrong, and round 31 holds it to nothing.
