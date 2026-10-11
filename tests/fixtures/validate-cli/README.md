# validate-cli

What `validate` does with the paths it is given, and which files `validate`, `check` and
`preview` collect, checked against both implementations by [`run.sh`](run.sh) in CI.

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
- Which files both implementations collect (1.4.2), each input made by the script beside a copy of
  the card in `cards/`:
  - a directory named like a card (`y.op.md/`) is not a document; `**` at the end of a pattern
    matches files, and a file is not a directory for `**` to walk;
  - `.drafts/` and `.dot.op.md` are not matched by `*` or `**`, and `.drafts/*.op.md` matches;
    `[ab].op.md` names that one file, not `a.op.md` and `b.op.md`; `*.OP.MD` matches no
    `.op.md`;
  - front matter that does not parse stops `check` with exit 2 and the card's name;
  - where symbolic links hold (on Windows the script makes junctions): a directory reached through
    a link, by one pattern, two patterns or two paths, is read once; a loop of two links is walked
    once, within a time limit; a link that leads nowhere — a card, a contract, an editor's lock
    file `.#….op.md` — is counted and named once by `validate`, stops `check` and `preview` with
    exit 2, and is not a card when its name starts with a dot;
  - where permissions hold (not as root): a card nobody may read is counted and named, a named
    `.md` nobody may read is refused with exit 2, and a directory nobody may list stops `validate`
    with exit 2 and its name.

  In CI these cases must run: the script fails when links do not hold, and when permissions do not
  hold for a user other than root.
