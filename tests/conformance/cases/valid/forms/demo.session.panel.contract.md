---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
page: /session
entity: session
presents:
  - field: session-head
    shows: the session's name and phase
    when: [active, finished]
  - field: session-summary
    shows: totals after the session ends
    when: [finished]
    note: the server already computes the totals; the panel does not show them yet
controls:
  - control: finish-session
    calls: demo.session.finish
    shown_when: [active]
  - control: open-settings
    calls: null
    opens: demo.session.settings
    shown_when: [active, finished]
    placement: in the ⋯ menu
    behaviour: opens the settings overlay, a contract of its own
groups:
  - group: panel-head
    role: header
    contains: [session-head, open-settings]
  - group: session-foot
    role: footer
    contains: [session-summary, finish-session]
removed:
  - control: clear-session
    was: wiped the record with no confirmation
    verdict: the owner removed it on 2026-08-18
---

A clean form contract exercising every section: elements with states, a control calling an
operation, a local control that opens another form (a flat link, not a nested tree), grouping
by purpose (a header and a footer, members in display order), and an owner's removal decision.
`opens` names a contract outside this file — with no known-forms set the link check must stay
silent, the same restraint the card corpus applies to `reversible_via`.
