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
The clean case: everything the contract requires is rendered where required, the removed
control is gone, every group member renders inside its contracted group, and rendered-but-undecided
elements (`phase-badge`, the bare containers) are accounted for by nobody — the
mirror of a wild endpoint, worth a warning and never an error.
