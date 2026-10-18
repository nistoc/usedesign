---
usedesign_form: 1
id: sample.workout.session-nav
screen: SessionPanel
entity: workout_progress
presents:
  - field: session-status
    shows: the pass status in words
  - field: main-progress
    shows: main sets closed N of M
    when: [active]
controls:
  - control: finish
    calls: sample.session.finish
    shown_when: [active]
groups:
  - group: session-head
    role: header
    contains: [session-status]
  - group: session-foot
    role: footer
    contains: [main-progress, finish]
removed:
  - control: clear
    was: the dismiss button
---
The clean case, with the card's one screen misspelt — `SessionPanl`. The screen renders and
the contract holds; the card is what drifted, and round 31 says so as a warning.
