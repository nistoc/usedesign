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
A frontend-only repository: `checks: [5]` and no `cards:` key, so nothing to compare `calls`
with. Designed ahead of the screen, it stays as quiet as before round 29: one
`form_not_yet_built`, no `form_calls_undescribed` for an id it has no way to look up.
