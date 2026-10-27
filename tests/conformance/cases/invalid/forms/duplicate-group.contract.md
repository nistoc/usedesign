---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
presents:
  - field: session-status
    shows: the session's status in words
  - field: main-progress
    shows: main sets closed N of M
controls:
  - control: finish
    calls: demo.session.finish
    shown_when: [active]
groups:
  - group: session-foot
    role: footer
    contains: [main-progress]
  - group: session-foot
    role: footer
    contains: [finish]
---

One container named by two group lines, each seating a different member. Read into a map by
name, one line replaces the other and its member leaves the group without a word; read as a list,
the footer stands in two places of the group order the array states. One name, one group: its
members belong on one line.
