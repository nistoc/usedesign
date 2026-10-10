# validate-cli

What `validate` does with the paths it is given, checked against both implementations by
[`run.sh`](run.sh) in CI.

- `usedesign.config.yaml`, `empty/` (created by the script), `docs/` and `docs/notes.md` hold no
  card and no contract — each is refused with exit 2 (issue #14).
- `broken/` holds a card with an empty line above its front matter — `missing_required_field`,
  exit 1 (issue #14).
- `cards/` and `forms/` together: the contract calls `sample.session.finsh`, a typo no card
  describes — `form_calls_undescribed`, a warning (issue #13). `forms/` alone says nothing about it.
