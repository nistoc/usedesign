---
usedesign_form: 1
id: demo.registry.page
screen: RegistryPage
page: /registry
entity: card
maturity: designed
states:
  live: { data: live }
  kind_empty: { data: live, note: "a kind with no cards yet — the tab still renders, the list is empty" }
  not_arrived: { data: live, note: "the create succeeded, but the backend reported fields that did not land" }
presents:
  - field: registry-head
    shows: the page title and the total count
  - field_pattern: 'kind-tab-*'
    shows: one tab per project kind returned by /bff/project-kinds, with the card count
    when: [live, kind_empty]
    at_least: 1
  - field: not-arrived-notice
    shows: which typed fields did not land
    when: [not_arrived]
controls:
  - control_pattern: 'row-open-*'
    at_least: 0
    shown_when: [live]
    behaviour: opens the card of that row; a kind with no cards has no rows, honestly
  - control: new-card
    calls: null
    opens: demo.card.create-rail
groups:
  - group: kind-tabs
    role: toolbar
    contains: ['kind-tab-*', new-card]
---

Round 17, three optional fields at once. `maturity: designed` says the contract was written before
the screen (issue #8). `states:` maps the screen's states onto the data's (issue #11) — three
screen states, one data state. `field_pattern` / `control_pattern` declare a FAMILY of anchors
whose names come from runtime data (issue #10): one tab per project kind owned by another
service; listing them literally would make the contract a second, silently stale copy of that
list. `at_least: 0` on the rows is the honest floor — a kind with no cards has no rows. A family
may be seated in a group verbatim.
