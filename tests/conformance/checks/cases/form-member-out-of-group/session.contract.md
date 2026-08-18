---
usedesign_form: 1
id: sample.workout.session-nav
screen: SessionPanel
entity: workout_progress
presents:
  - field: session-status
    shows: the pass status in words
  - field: main-progress
    shows: main sets closed N of M
groups:
  - group: session-head
    role: header
    contains: [session-status, main-progress]
  - group: phantom-rail
    role: section
    contains: [session-status]
---
Two group failures the inventory's `within` makes visible. `main-progress` is contracted into
the header but measured living in the footer — the contract's seating chart is wrong, and only
a container-aware inventory can say so. `phantom-rail` never renders at all: a group whose
anchor exists only in the contract. Both were invisible while the inventory recorded anchors
flat; the very first container-aware inventory in the parent project refuted its own contract
the same way (`add-set`, contracted into the footer, measured in the set table).
