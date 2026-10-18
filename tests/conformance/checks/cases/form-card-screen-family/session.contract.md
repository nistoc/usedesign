---
usedesign_form: 1
id: sample.session.panel
screen: SessionPanel
maturity: designed
presents:
  - field: session-status
    shows: whether the session is running or over
controls:
  - control_pattern: finish-*
    calls: sample.session.finish
    shown_when: [active]
---
A family of controls calls the operation, and the card describes the screen misspelt. A family has
no one name for a card to write, so round 31 compares only controls named as one anchor.
