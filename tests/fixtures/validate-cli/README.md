# validate-cli

What `validate` does with the paths it is given, checked against both implementations by
[`run.sh`](run.sh) in CI.

- `usedesign.config.yaml`, `closed.config.yaml` (the same, fenced like front matter), an empty
  directory and a file of bytes that are not UTF-8 (both made by the script), `docs/` and
  `docs/notes.md` hold no card and no contract — each is refused with exit 2 (issue #14).
- `broken/` holds four cards whose front matter cannot be read — an empty line above the opening
  `---`, no closing `---`, YAML that does not parse, a list where the fields belong. Each is
  `missing_required_field` with its cause, and all four are counted: `4 card(s)`, exit 1 (issue #14).
- A card with a byte-order mark before its front matter (made by the script) is read as any other.
- `cards/` and `forms/` together: the contract calls `sample.session.finsh`, a typo no card
  describes — `form_calls_undescribed`, a warning (issue #13). `forms/` alone says nothing about it.
- `cards-empty.config.yaml` declares `cards: []` — `check` reports `no_cards_found` in both
  implementations.
