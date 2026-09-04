---
usedesign_form: 1
id: sample.workout.session-nav
screen: SessionPanel
entity: workout_progress
maturity: designed
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
---
The screen renders (this is the clean case inventory) but the contract still says `designed` —
the flag went stale on build day. Compared in full all the same; the staleness is a warning.
