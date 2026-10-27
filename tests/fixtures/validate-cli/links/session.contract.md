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
  - control: open-totals
    calls: null
    opens: sample.session.totals-panel
  - control: open-history
    calls: null
    opens: sample.session.history
---
`open-totals` opens a contract this set describes: nothing is said. `open-history` opens
`sample.session.history`, which no contract in this set describes — `undescribed_form`, a warning.
