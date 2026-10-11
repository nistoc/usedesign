---
usedesign_form: 1
id: sample.session.shapes
screen: ""
maturity: drafted
presents:
  - field: session-status
    shows: whether the session is running or over
    extra: true
  - shows: a field with no name
controls:
  - control: finish
    calls: [sample.session.finish]
    shown_when: active
---
A form contract the schema refuses in several places: an empty screen name, a maturity level no
contract has, an unknown key, a presented field without its name, a `calls` list of one operation
(a chain needs two), `shown_when` written as one state instead of a list.
