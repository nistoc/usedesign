---
usedesign_form: 1
id: demo.session.panel
screen: SessionPanel
entity: session
presnts:
  - field: session-head
    shows: the session's name and phase
controls:
  - control: finish-session
    calls: demo.session.finish
    shown_when: [active]
---

The measured hole, verbatim: `presents` misspelled as `presnts`. On usedesign 0.5.0 this
contract passed silently — the whole "must show" section vanished, and every element in it
resurfaced as somebody else's warning ("rendered but not described"). The typo must be named
as itself: an unknown key AND the required section absent. An implementation reporting only
one of the two tells half the story.
