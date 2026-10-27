---
usedesign_form: 1
id: demo.registry.page
screen: RegistryPage
presents:
  - field: registry-head
    shows: the page title and the total count
    at_least: 2
---

A floor on a single anchor. `registry-head` names one element, and one element is rendered or it
is not; "at least two of it" asks the inventory a question it cannot answer. `at_least` belongs
to a family line — `field_pattern` or `control_pattern` — and is an error anywhere else.
