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
    calls: sample.session.finsh
    shown_when: [active]
---
Written before the screen, with a typo in `calls`: `finsh` for `finish`. No screen rendered
yet, and the comparison with the cards needs none — the typo is reported now, not on the day
the screen renders (issue #13).
