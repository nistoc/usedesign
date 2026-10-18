---
usedesign_form: 1
id: sample.session.panel
screen: SessionPanel
maturity: designed
presents:
  - field: session-status
    shows: whether the session is running or over
controls:
  - control: finish
    calls: sample.session.finish
    shown_when: [active]
---
The card's `ui` names no screen at all. There is nothing to be a slip of, so nothing is
compared. 1.7.0 warned here that the card «describes screens without a name» — true, and
not the mistake this check exists for.

`SessionPanel` does stand in the card, on its `rest` interface. That is not a screen the card
shows: only a `ui` interface describes one, so the name is not read.
