---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
presents:
  - field: session-head
    shows: the session's name
groups:
  - group: panel-head
    role: header
    contains: [session-head, sesion-status]
---

A group naming a member the contract itself never declares — here a misspelled
`sesion-status`. Membership against the CODE is not verifiable yet (the inventory records
anchors flat), but this line is wrong by the contract's own text, and needs no inventory to
prove it.
