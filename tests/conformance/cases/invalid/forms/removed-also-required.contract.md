---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
presents:
  - field: session-head
    shows: the session's name
controls:
  - control: clear-session
    calls: null
    shown_when: [active]
removed:
  - control: clear-session
    verdict: the owner removed it
---

The contract disagreeing with itself: one document both requires `clear-session` and forbids
it. No code can satisfy this — whichever way the screen renders, half the contract reports a
finding. Self-contradiction is an error in the contract, not a TODO for the product.
