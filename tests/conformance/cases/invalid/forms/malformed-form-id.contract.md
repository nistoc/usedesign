---
usedesign_form: 1
id: SessionPanel
screen: SessionPanel
presents:
  - field: session-status
    shows: the session's status in words
---

The contract's id written as its screen's component name. A contract id is `<area>.<object>.<name>`,
like an operation's: `opens` in another contract points at it by that id, and a component name
is the screen, which `screen:` already says — two keys naming one thing, and no id at all.
