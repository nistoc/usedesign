---
usedesign_form: 1
id: sample.registry.page
screen: RegistryPage
presents:
  - field: registry-head
    shows: the page title and the total count
  - field_pattern: "kind-tab-*"
    shows: one tab per project kind returned by the backend, with the card count
    when: [live, kind_empty]
controls:
  - control_pattern: "row-open-*"
    at_least: 2
    shown_when: [live]
    behaviour: opens the card of that row
groups:
  - group: kind-tabs
    role: toolbar
    contains: ["kind-tab-*"]
---
One tab per project kind, the set of kinds owned by another service and read at runtime. The
contract states the rule, not the list; every rendered tab is accounted for by the family line.
