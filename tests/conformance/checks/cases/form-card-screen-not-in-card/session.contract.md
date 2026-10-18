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
The card describes two screens, and neither is `SessionPanel`: one is misspelt by a letter,
`SessionPanl`, the other differs in letter case, `sessionPanel` — both slips for the
contract's screen. Until round 31 both passed: nothing compared a card's `screen` with the
contract that calls the card.
