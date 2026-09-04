---
usedesign_form: 1
id: demo.registry.page
screen: RegistryPage
presents:
  - field_pattern: kind-tab-all
    shows: the tab for all kinds
---

A family with no `*` is a literal wearing the wrong key. Accepted, it would match exactly one
anchor — the one `field:` would have matched — while reading as "the set lives elsewhere". The
error says which key to use instead.
