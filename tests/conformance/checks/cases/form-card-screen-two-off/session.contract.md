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
Two letters off — an `s` and an `e` dropped from `SessionPanel`. Still a slip, and the
warning stands. The card's other screen, `ArchivePanel`, is another name, and the warning
does not list it.
