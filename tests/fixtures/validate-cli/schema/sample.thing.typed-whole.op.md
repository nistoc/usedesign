---
id: sample.thing.typed-whole
title: Whole sections of another type
scenario: sample.flow
actors: [operator]
maturity: [designed, implemented]
data_transition: { from: active, to: finished }
mutates: [thing.state]
concurrency: { mode: none_by_design, rationale: [one, two] }
steps: 5
interfaces: { rest: x }
variant_of: { operation: sample.thing.act, inherits: [[a, b]] }
data:
  entities: [thing]
provenance: none
reversibility: reversible
---

Whole sections of another type: `steps` a number, an interface a text, a maturity a list, a
rationale a list, an inherited step a list. The rules see no steps and no interface where the
section is not a list or a map; the schema names each.
