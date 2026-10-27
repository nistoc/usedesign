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
    when: [active, paused]
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
The form-clean contract, with `main-progress` also required in `paused`. The test that renders
the screen renders `active` and `finished` and never `paused`, so that line cannot be judged —
and a line nobody could judge is reported, never passed over.
