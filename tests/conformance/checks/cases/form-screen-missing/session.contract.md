---
usedesign_form: 1
id: sample.workout.session-nav
screen: SesionPanel
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
The form-clean contract with its `screen:` misspelt. The contract carries no `maturity`, so it
is implemented, and a screen that nothing rendered is an error — the screen that does render,
`SessionPanel`, is then described by no contract.
