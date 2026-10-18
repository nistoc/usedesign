---
usedesign_form: 1
id: sample.session.panel
screen: SessionPanel
maturity: designed
presents:
  - field: session-status
    shows: whether the session is running or over
controls:
  - control: start-now
    calls: [sample.session.finish, sample.session.archive]
    shown_when: [active]
---
One control runs a chain of two operations. The first card describes this screen and names
the control; the second describes it misspelt, `SesionPanel` — one warning, at step 2 of 2.
