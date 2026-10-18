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
The card's screen has a mathematical bold italic `𝒊` pasted for the `i` and the last `l`
dropped: two letters off `SessionPanel`, a slip. The bold italic letter lies outside the Basic
Multilingual Plane, one letter and two UTF-16 code units.
