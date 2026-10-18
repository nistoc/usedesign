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
The card names the screen for a person, `Session`; the contract names the component,
`SessionPanel`. Two namings, not a slip — 1.7.0 gave 113 such warnings on a second
product, none of them a mistake. Five letters apart, nothing is compared.
