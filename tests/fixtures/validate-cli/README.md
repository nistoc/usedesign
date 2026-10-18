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
- The `form-card-*` cases of the checks corpus (`tests/conformance/checks/cases/`), each a contract
  and the cards it calls, read by `validate` as check 5 reads them (round 31): a card that describes
  screens and misspells the contract's screen — another letter case, two letters off or fewer
  (tools 1.7.1) — is `form_screen_not_in_card`, one whose `control` does not name the contract's
  control as a word of its own is `form_control_not_in_card` — warnings both, the step named in a
  chain. A card that describes no screen, a screen named another way (`Session`, three letters
  off), and a family of controls are not compared; the contract alone says nothing.
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
- The stale case of the checks corpus, run in the zones UTC+13 and UTC−11: both implementations
  count «N days ago» from the UTC date, as they do in UTC (1.4.3). Python counted from the local
  date, a day apart near midnight east or west of UTC.
- `schema/` holds seven cards and a contract that break thirteen of the keywords the JSON Schema
  uses (type, enum, oneOf, if/then, required, additionalProperties, minItems, uniqueItems,
  minLength, format, minimum, maximum, exclusiveMinimum) — a status of 4120, `yes` for a boolean
  (a string in YAML 1.2), a date that does not exist, a step text that is a number, among others —
  and more the rules read: `null` where a value is asked for, a key written twice, and in
  `sample.thing.typed*` fields of another type — a number where a list or a map belongs, a map
  where a list belongs, a list where a text belongs — and `!!float 1`, the text `1`. `validate`
  must print the same lines in both implementations, with the schema and with `--no-schema`
  (1.4.3): the Python prototype had no schema layer, and a card only the schema refuses passed
  there; the typed cards stopped the TypeScript reference with a stack trace, and Python wrote
  `!!float 1` as `1.0`.
- Two cards with one id, two contracts with one id (made by the script): `validate` stops with
  exit 2 and names both files (1.4.3) — kept by id, one of them left the run without a word.
  Two cards with no id are two cards.
- A card named by one character outside the BMP (U+1F600, two UTF-16 code units) is matched by
  `?` in both implementations (1.4.3); the TypeScript reference read `?` as one code unit.
- Two cards whose ids sort apart by code point and by UTF-16 code unit (U+FF5E, U+1F600) are
  printed in one order by both implementations — JavaScript's, by code unit (1.4.3).
