---
id: sample.card.create
title: Create a project card (designed, not built)
maturity: designed
interfaces:
  rest: { transport: http_rest, method: POST, path: /project-cards }
---
The contract-first card (issue #3): designed, not built. Its route is EXPECTED to be absent —
`route_not_yet_served`, a warning. The old single diagnostic called this a phantom, an error
nobody could fix except by deleting the design.
