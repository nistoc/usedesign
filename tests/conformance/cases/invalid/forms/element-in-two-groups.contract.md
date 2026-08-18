---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
presents:
  - field: session-head
    shows: the session's name
  - field: session-status
    shows: the session's status in words
groups:
  - group: panel-head
    role: header
    contains: [session-head, session-status]
  - group: session-foot
    role: footer
    contains: [session-status]
---

One element claimed by two groups. A rendered element sits in exactly one place; a contract
that seats it in two cannot be satisfied by any screen, so it is the contract's error — the
same family as requiring and forbidding one control.
