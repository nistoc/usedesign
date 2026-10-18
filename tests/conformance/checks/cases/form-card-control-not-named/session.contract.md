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
The card describes the right screen, and its `control` holds `finish` only inside longer
words — `finish-all` and `finished`. A name counts only as a word of its own: no letter, mark,
number, `-` or `_` may touch it.
