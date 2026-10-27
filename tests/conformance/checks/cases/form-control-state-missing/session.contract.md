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
  - control: resume
    shown_when: [paused]
    behaviour: resumes a paused pass
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
The form-clean contract, with a `resume` control shown only in `paused`. The inventory never
rendered `paused`, so whether the control is there cannot be said — the state is missing, and
that is reported, never passed over.
