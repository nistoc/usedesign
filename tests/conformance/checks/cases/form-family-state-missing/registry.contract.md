---
usedesign_form: 1
id: sample.registry.page
screen: RegistryPage
presents:
  - field: registry-head
    shows: the page title and the total count
  - field_pattern: "kind-tab-*"
    shows: one tab per project kind returned by the backend, with the card count
    when: [live, kind_empty, loading]
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
The form-family contract, with the tab family also required while the list loads. The inventory
renders `live` and `kind_empty` and never `loading`: the family's floor cannot be counted in a
state nobody rendered, and that is reported, never passed over.
