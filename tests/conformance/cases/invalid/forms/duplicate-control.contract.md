---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
presents:
  - field: session-head
    shows: the session's name
controls:
  - control: finish-session
    calls: demo.session.finish
    shown_when: [active]
  - control: finish-session
    calls: demo.session.finish
    shown_when: [finished]
---

The same control declared twice with different availability. Measured side effect on 0.5.0:
nothing flagged the duplicate, and every downstream finding about the control simply appeared
twice — the defect multiplied instead of being named.
