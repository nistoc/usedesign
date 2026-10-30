# Changelog

What each release of `usedesign` changed, newest first. The format ([SPEC.md](SPEC.md)) and the
package on npm are versioned together, and one promise holds across all of them: a card with zero
errors under 1.0 has zero errors under every 1.x ([SPEC §8](SPEC.md)). `1.x.0` adds to the format,
`1.x.y` fixes the tools, `2.0.0` would break. A release that changes the format names its round
in SPEC §8, where the round-by-round record is kept.

`usedesign --version` prints both numbers: `usedesign 1.7.1 (SPEC v1.7)`. Releases before 1.0
(`0.2.0` … `0.16.0`) are tagged in this repository; the rounds that led to 1.0 are in SPEC §8.
Each date is the day the version reached npm, in UTC; the date of its tagged commit can differ by
a day.

## Unreleased

*the tools change, the format does not (SPEC v1.7)*

- `scaffold` names an `in: path` parameter it cannot use instead of passing over it. Up to 1.7.4 an
  `in: path` entry with no `name` was skipped with nothing said, and one whose `name` is not a
  string went into the draft as it stood — `5` became a parameter `5`; either way the path's own
  segment came after the declared ones, and the draft's order parted from the document's in
  silence. Now an `in: path` entry whose `name` is missing, empty or not a string — written in
  place, on the path item, or reached by `$ref` — is a warning, `openapi_path_parameter_unnamed`,
  with the route, and is not read; the draft names the segment from the path, after the declared
  ones. A query, header or cookie parameter with no name does not touch the draft and is not named
  (`scaffold-path-unnamed`).

## 1.7.4

*2026-10-30 · the tools change, the format does not (SPEC v1.7)*

Two fixes in `scaffold`, the command that drafts cards from an OpenAPI document; the format,
`validate`, `check`, `preview` and `gen` do not change.

- `scaffold` keeps a path parameter given by `$ref` where it is declared:
  `"parameters": [{ "$ref": "#/components/parameters/Y" }, { "$ref": "#/components/parameters/X" }]`
  on `/v1/a/{x}/b/{y}` reads `y, x` in the draft, as the same parameters written inline do. Up to
  1.7.3 an entry given by `$ref` had no `in`, so its name came from the path — at the end, in the
  path's order — and the draft read `x, y`: one API, written two ways, gave two drafts. A `$ref`
  inside the document is followed one level, on the path item and on the operation, the way a
  path item is. A `$ref` to another document, an empty one, one with nothing at its address, one to
  another `$ref`, or one to something that is not a parameter is a warning,
  `openapi_parameter_ref_not_read`, with the route; if it was a path parameter, the draft names it
  from the path, after the declared ones. A golden test of its own holds every case
  (`scaffold-parameter-ref`).
- `scaffold` names a `trace` operation instead of dropping it. OpenAPI 3.0 and 3.1 allow `trace` on
  a path item; the route inventory, the config's `exclude.method` and `check` take seven methods —
  a card's own `method` is any string — and `check` calls TRACE an unknown method. Up to 1.7.3 the
  route fell out of the count with nothing said, exit 0, and a `$ref` to a path item with only a
  `trace` was said to have no operation. Now each `trace` is a warning, `openapi_method_unknown`,
  with the route written as `check` writes it — `TRACE /v1/echo` — and it is still neither
  drafted nor counted (`scaffold-trace`).

## 1.7.3

*2026-10-30 · the tools change, the format does not (SPEC v1.7)*

A fix in `scaffold`, the command that drafts cards from an OpenAPI document; the format,
`validate`, `check`, `preview` and `gen` do not change.

- `scaffold` reads a path item given whole by `$ref`, as OpenAPI 3.1 allows:
  `"/v1/accounts/{account}": { "$ref": "#/components/pathItems/Account" }`. An address inside the
  document is followed one level, and the fields written beside `$ref` win over the target's; the
  routes under it are drafted and counted. Up to 1.7.2 the path item's one key, `$ref`, was not a
  verb: its routes were neither drafted nor counted, `scaffold` exited 0, and the sum it printed
  added up without them. A `$ref` to another document, to an address with nothing at it, to
  another `$ref`, or to something with no operation — an operation, the document itself — is a
  warning, `openapi_path_item_ref_not_read`, with the path; the routes at that address are still
  not counted, and the warning says so. The fields written beside such a `$ref` are read as they
  stand. A golden test of its own holds every case (`scaffold-path-item-ref`).
- Tests only, the tools do not change: the draft keeps path parameters in the order the operation
  declares them, and the route that shows it is now `/v1/loans/{loan}/rates/{rate}`, declared
  `rate, loan` — neither the path's order nor the alphabet's. Its 1.7.2 predecessor,
  `/v1/loans/{loan}/fees/{fee}` declared `fee, loan`, was in the alphabet's order, and a draft that
  sorted the names passed.

## 1.7.2

*2026-10-28 · the tools change, the format does not (SPEC v1.7)*

Fixes in `preview`, `gen` and `scaffold`, the commands that write files; the format, `validate` and
`check` do not change.

- `preview <config>` and `gen openapi <config>` without `--out` are a usage error: exit 2, and
  nothing is written. Up to 1.7.1 both took the first argument after the command for the output
  when `--out` was absent, and exited 0: `preview` wrote its page over the config, `gen` wrote the
  document into a file named `openapi`. `--out` without a value was refused already.
  `test/preview.test.mjs` and `test/gen.test.mjs` pin every form, and that no file is written.
- `scaffold` on an OpenAPI document with no routes exits 1 and writes nothing. Up to 1.7.1 it
  printed `openapi_empty` as an ERROR and exited 0, and a pipeline that read the exit code went on
  as if the routes had been drafted. An ERROR line is exit 1 in `scaffold` now, as in `validate`
  and `check`, with `--dry-run` too.
- `scaffold` creates the `--out` directory only when it has a draft to write: with every route
  declared or excluded, 1.7.1 left an empty one behind.
- `scaffold` reads the path parameters declared on the path item, for every operation under it, as
  well as the operation's own, and adds the names of the path's `{…}` segments, as `gen` writes
  them; the draft names each once. Up to 1.7.1 only inline `in: path` entries of the operation's
  own `parameters` were read: the draft of `GET /v1/loans/{loan}` named no parameter when `loan`
  was declared on the path item, given by `$ref` or not declared at all.
- `scaffold`: `parameters` that is not a list, on a path item or an operation, is a warning,
  `openapi_parameters_not_list`, with the route it stands on; it is not read, and the draft is
  written. 1.7.1 failed on it with exit 2.
- `routes_unaccounted`, the guard behind the arithmetic `scaffold` prints, words a route counted
  twice as "1 counted more than once"; 1.7.1 said "-1 vanished without a reason". No input
  reaches it.
- `gen openapi`: an operation several cards share (the dispatch idiom) is as mature as the least
  mature of them, and its `summary` names every card. Up to 1.7.1 both came from the first card by
  id, so a route a `conceived` card shares with a `tested` one could read `tested`. A `deprecated`
  card leaves the route to the others; only a route whose cards are all deprecated reads
  `deprecated`.
- Tests only, the tools do not change: 31 cases for codes that no case pinned, 8 in the card
  corpus and 23 in the checks corpus, and both implementations agree on all of them — 101 + 95
  cases, 196 (it was 93 + 72). `scaffold` and `gen` live in the reference implementation alone,
  so no corpus holds them; 13 golden tests do — the built CLI on fixtures of its own, its output,
  the drafts and the derived document byte for byte (`npm run test:unit`, a step of CI).
- Tests only, the tools do not change: the sum `scaffold` prints is checked by `unaccountedRoutes`,
  which a golden test hands a plan with a route lost and one with a route counted twice
  (`routes_unaccounted` cannot be reached from any input); `undescribed_counterpart` and
  `undescribed_form`, which the corpus cannot hold, are held by
  `tests/fixtures/validate-cli/links/`, line for line in both implementations.

## 1.7.1

*2026-10-18 · the tools change, the format does not (SPEC v1.7)*

`form_screen_not_in_card` speaks of a slip, not of another naming.

- 1.7.0 compared a card's `screen` with the contract's letter for letter. A second product names a
  screen for a person in its cards — `Account` — and by its component in its contracts —
  `AccountPage`: 1.7.0 gave 113 warnings over 70 such pairs, none of them a mistake. Now the
  warning stands only when one of the card's screens reads as a slip for the contract's: the same
  name in another letter case, or two letters off or fewer, counted by code point once letter case
  is set aside. For `SessionPanel`, `SessionPanl`, `SesionPanl` and `SESSIONPANEL` warn; `Session`
  and `SesionPnl` do not. The warning lists the slips only (SPEC §7.5).
- A card whose screens are all further off is passed over, its `control` too, and so is a `ui`
  interface without a `screen` — 1.7.0 warned on it as "screens without a name". A screen renamed
  whole on one side is not reported.
- `form_control_not_in_card` is unchanged. On that product it found two controls a card names only
  in its prose note, not in `control`.
- On the same product 1.6.0 gives 77 warnings, 1.7.0 gives 192, 1.7.1 gives 79 — the 77 and those
  two. A pilot's catalogue: no change. No new error, and no warning that 1.7.0 did not give.
- The checks corpus has six new cases — `form-card-screen-other-naming`, `-two-off`, `-three-off`,
  `-letter-case`, `-wide-letter`, a letter outside the Basic Multilingual Plane counted as one, and
  `-unnamed`, a `ui` without a screen while the contract's screen stands on the card's `rest`
  interface, where it is not a screen the card shows — and two old ones, the chain and the family,
  now misspell the screen rather than name another, so that they still tell apart an
  implementation that skips a step of a chain or compares a family.
  `validate-cli/run.sh` reads that a warning lists the slips alone. 93 + 72 cases.

## 1.7.0

*2026-10-18 · SPEC v1.7 — round 31: the card names the screen that calls it*

A form contract's `calls` says which operation a control runs, and the operation's card says, in
each `ui` interface, which screen it is called from and from which control. Until 1.6.0 nothing
compared the two: a screen misspelt by one letter in a card, or a control renamed in it, passed
`validate` over the cards and the contracts together, and `check` alike (SPEC §7.5, round 31).

- Two warnings, wherever cards and contracts meet — `validate` over both, and check 5 with
  `cards:`, for a contract designed ahead of its screen and for a rendered one:
  - `form_screen_not_in_card` — a card that describes screens describes none that a contract's
    control calls it from; the warning lists the screens the card does describe, so a misspelling
    is in view. Screens are compared letter for letter.
  - `form_control_not_in_card` — the card describes the screen, and no `control` there names the
    contract's control as a word of its own: `button[data-action="finish"]` names `finish`,
    `finish-all` and `finished` do not.
- Every operation of a chain is compared, and the warning names its step.
- Left out on purpose: a card that describes no screen (it is behind, not wrong — none of the 16
  cards of this repository's check-5 corpus describes one), a card naming a screen whose contract
  calls it from no control (a picture that loads by itself), a family of controls, and `where`.
- `control` is read as prose: the contract's control is found wherever the text names it as a word
  of its own, also where it says the control is the same as on another screen. With such a mention
  a misspelling in the other place passes.
- No new error and no new field: a card or a contract with zero errors under 1.6.0 has zero errors
  under 1.7.0. The checks corpus has seven new cases, `form-card-*`, and `validate-cli/run.sh`
  reads them with `validate`.

## 1.6.0

*2026-10-18 · SPEC v1.6 — how the text is read, written down; no round*

The two implementations read the same text alike (SPEC §6). Until 1.5.2 the Python prototype read
YAML with PyYAML, a YAML 1.1 scanner, and cut and matched text with Python's `strip()`, `\d` and
`.`, where the reference reads with `yaml` and cuts with JavaScript's: on a tab after a colon, a
raw U+2028 in a value, a file of CR line ends or a value that ends in U+FEFF, one of them passed a
card the other refused, or the two printed other lines — the defect this project exists to catch.

- The Python prototype reads YAML with `yaml12.py`, a port of the parse path of `yaml` 2.9.0, the
  version the reference now pins, and needs nothing beyond the standard library. A value is the
  same text in both, and a refusal the same words at the same line and column. PyYAML refused a
  tab after a colon, U+2028, NEL, DEL or NUL in an unquoted value and a tag it did not know, read
  a CR alone as a line break, read on past 100 aliases where the reference refused, each level
  of a nested alias ten times slower, and worded each refusal its own way.
- Four things YAML can write are refused in both as YAML that is not valid, in a card, a contract
  or a config: a collection used as a map key, an alias inside the node it names, half of a
  surrogate pair in a string, and collections nested deeper than 64 levels. The 1.5.2 reference
  wrote such a key out as YAML text, returned a value that contains itself for the alias, kept the
  half, and refused the nesting only where its stack ran out, past 700 levels; the prototype
  stopped with a traceback on the alias, and past 400 levels.
- An explicit tag outside the core schema — `!!set`, `!!binary`, `!!timestamp`, `!!omap` —
  leaves the value as it reads untagged. The 1.5.2 reference made a set, bytes, a date or a map
  of them, and its rules read each of them as a map.
- Text is cut and matched as JavaScript does it, in both. Values are trimmed of JavaScript's white
  space — U+FEFF is, U+0085 and U+001C–U+001F are not — where `outcomes_indistinguishable`
  compares them, where `tested: N tests` is read, and where routes, evidence paths and
  `variant_of.shared` are compared. A line number after `:` is the digits 0–9. An id read from a
  block scalar ends in a line feed and is malformed in both. A family pattern's `*` and the
  parameters of a test name run to no line terminator.
- `check` reads a path in the config from the config's directory, and an absolute path is that
  path; the 1.5.2 reference joined it under the directory. A `code_root` that is a file is
  `code_root_missing`, "which is not a directory": the reference took it and found no path under
  it. An evidence path that starts with `/` is read under `code_root`, where the prototype read it
  from the root of the file system. The test report is read as UTF-8, whatever it declares, a byte
  that is not UTF-8 as U+FFFD; the prototype decoded a report declared ISO-8859-1 as Latin-1, and
  refused one with a stray byte as malformed.
- What 1.6 refuses and 1.5 passed: front matter that holds one of the four refused things in a key
  no rule reads — the card schema leaves unknown keys open — and a config whose `code_root` is a
  file, where no card claims a path. None of the four is a value the format describes, and no card
  of the corpus or the examples holds one.
- `tests/fixtures/validate-cli/yaml.sh` holds 55 cases, and CI runs it beside `run.sh`; on 1.5.2
  every one of them fails but the boundary, 64 levels, which 1.5.2 read too. The corpus holds
  93 + 59 cases, as in 1.5.2.

## 1.5.2

*2026-10-17 · the tools change, the format does not (SPEC v1.5)*

`check` reads the test report as XML reads it.

- A report cut off while it was written is `report_malformed`. 1.5.1 read it as far as it went:
  a test cut right after its open tag, before its `<failure>`, passed check 2 with exit 0. A
  report that is not well-formed XML is named in one line by both implementations, without the
  parser's reason and position.
- Past 1 000 escaped characters (`&quot;` and the like) in the whole report, the 1.5.1 reference
  refused it as malformed — a suite of parametrised tests reaches that in its test names alone.
  There is no limit now, and `&#233;` is `é`, not six characters.
- A report with a DOCTYPE is refused in both: JUnit reports carry none, and its entities are what
  expansion attacks are made of. The Python prototype expanded them.
- A `test_report` that is a directory is `report_missing`, "cannot be read"; the 1.5.1 reference
  called it malformed XML, and the Python prototype stopped with a traceback.
- The reference reads the report with `saxes` in place of `fast-xml-parser`. The corpus holds
  93 + 59 cases.

## 1.5.1

*2026-10-17 · the tools change, the format does not (SPEC v1.5)*

`check` reads as `validate` reads since 1.4.3.

- A field of another type than the schema gives it — `tests: 5`, a `maturity_evidence` that is a
  text, `shown_when: 5` — is absent to the checks, as it is to the rules of `validate`, and
  `validate` names it. On such a card or contract 1.5.0 stopped `check` with a stack trace, or the
  two implementations read it differently.
- Two cards — or two contracts — with one id stop `check` with exit 2, and both files are named;
  1.5.0 judged one of them and said nothing of the other. Two cards with one id stop
  `gen openapi` and `scaffold --config` the same way, which read the cards as `check` does;
  1.5.0 `gen openapi` merged them into one route without a word.
- The config is refused with exit 2 when a key holds a value of another type — `cards: 5`, a check
  number outside 1–5, `checks: []`, which the 1.5.0 reference ran as no check at all and
  passed — and Python reads it as YAML 1.2, as the reference does: `030` is thirty days, not
  twenty-four, and a key written twice is refused, not read as its last value.
- An exclusion `path` and a card's `store` are matched as one segment of a `cards:` pattern matches
  a name: `*` and `?` stop at `/` (and at `\`), `?` is one character outside the Basic
  Multilingual Plane too, brackets are plain characters and letter case counts. The Python
  prototype matched them by the shell's rules, where `*` crossed `/`, `[1]` was a set and case did
  not count on Windows.
- The Python `check` prints its lines in the reference's order whatever `PYTHONHASHSEED` is, and
  its summary line names the routes designed ahead of the code.

## 1.5.0

*2026-10-13 · SPEC v1.5, round 30*

One spelling added to an optional field. A `covers_outcomes` value may name its line instead of
quoting it among other words: a pair `{shows, where, note}` — the line the user reads, the place
it appears, and the rest — or a list of two or more pairs for an outcome that shows several lines.
`outcomes_indistinguishable` compares the lines of `shows`, a line of one word too, beside the
quoted spans of text values, and never `where`: the same words in two places tell the user the
same thing. Text values read as before; the one new error (`malformed_outcome_pair`) is about the
new spelling only, and without the schema it also names a value that is no text, pair or null — a
number — which 1.4 passed over in silence. A card written with pairs needs 1.5: 1.4 refuses it as a
schema violation. The corpus held 93 + 56 cases.

## 1.4.4

*2026-10-13 · the tools change, the format does not (SPEC v1.4)*

Puts back one thing 1.4.3 lost. An `id` that is not text — `id: 1`, `id: true` — is a malformed id
again (`malformed_operation_id`, for a contract `malformed_form_id`), as the reference said up to
1.4.2 — the Python prototype stopped on such a card with a traceback, and now says the same. Read
only in its type, such an id had become absent to the rules: with the schema layer the schema
still named it, with `--no-schema` the card passed with no error.

## 1.4.3

*2026-10-11 · the tools change, the format does not (SPEC v1.4)*

- Two cards — or two contracts — with one id stop `validate` with exit 2, and both files are
  named: 1.4.2 kept one of them and dropped the other in silence.
- A field of another type than the schema gives it — `steps: 5`, an interface that is a text, a
  step id that is a number — no longer stops `validate` with a stack trace: the rules read it as
  absent, and the schema names what is wrong.
- In check 3, `since: 2026-02-30` is no date and is reported as `evidence_undated`; 1.4.2 carried
  it over to 2 March and called the claim stale or fresh by the clock.
- `?` in a pattern matches one character outside the Basic Multilingual Plane too, not one half of
  it. Collection lists each directory once (24 000 files: 2.6 s → 0.3 s), and `validate` collects
  once.
- The Python prototype now validates against the JSON Schema as the reference does — the same
  messages, in the same order — reads the front matter as YAML 1.2, counts days in UTC, orders
  text as JavaScript does and reads a field only in its type; the two print the same lines on the
  corpus and on the fixtures of `tests/fixtures/validate-cli/`. The corpus held 84 + 56 cases.

## 1.4.2

*2026-10-11 · the tools change, the format does not (SPEC v1.4)*

Both implementations collect the files a pattern names with one algorithm, step for step, and read
them alike. Before, the TypeScript walk and Python's glob found different files in places.

- A directory reached through a link is read, and a loop of links is walked once (the TypeScript
  tool skipped such a directory; Python's glob walked the loop to the system's depth limit).
- A card reached two ways — a link, two patterns, two paths given to `validate` — is read once.
- A name that starts with a dot is matched only by a pattern segment that starts with a dot:
  drafts in `.drafts/` and an editor's lock file beside a card are not cards (the TypeScript tool
  read them).
- `[` and `]` in a pattern are plain characters, and letter case counts (Python's glob read `[ab]`
  as a set, and ignored case on Windows).
- A directory named like a card is not a document, and `**` at the end of a `cards:` pattern
  matches files, as Python's glob does.
- An entry that cannot be opened — a link that leads nowhere, a file without read permission — is
  a card that cannot be read: `validate` counts it as `missing_required_field` and names the cause
  (SPEC §6), and `check` and `preview` stop with exit 2 and name it. A directory whose list of
  files cannot be read stops `validate`, `check` and `preview` the same way (the TypeScript tool
  stopped with a bare system error; Python's glob passed over it in silence), and so does front
  matter that is not valid YAML in `check` (the Python `check` stopped with a traceback). The 1.4.1
  tool dropped a link that leads nowhere in silence; its `validate` read a file without read
  permission as front matter that is not valid YAML, and its `check` stopped on one with a bare
  system error; the Python implementation stopped on both with a traceback.

## 1.4.1

*2026-10-10 · the tools change, the format does not (SPEC v1.4)*

- `validate` refuses a path that does not exist by name, with exit 2, as the Python implementation
  does; 1.4.0 read it as a card whose front matter is not valid YAML, counted it and exited 1
  (issue #14).
- Check 3 warns `maturity_understated` only when a passing test of the card's own covers its last
  step: tests that prove only the door — sign-in, permission — pass in front of an operation that
  is not built yet, and that card is honestly `designed` (`design/maturity-evidence.md` §4).

## 1.4.0

*2026-10-10 · SPEC v1.4, round 29*

One value added to an existing field and no new code. `concurrency.mode: server_read_version`
names a write the server guards on its own — it reads a revision, then writes only over it — where
the caller sends none; until now such a card could only say `none_by_design` and contradict itself
in `rationale`.

- Check 5 reads the `calls` of a contract written ahead of its screen, as warnings, and `validate`
  reads `calls` against the cards of the same run (issue #13).
- `validate` refuses a path with nothing to validate instead of passing it, and a card whose front
  matter cannot be read — a line above the opening `---`, no closing `---`, YAML that does not
  parse — is counted and reported as an error, not skipped in silence (issue #14).

## 1.3.0

*2026-10-03 · SPEC v1.3, round 28*

No new field and no new code.

- `outcomes_indistinguishable` compares the words the user reads — the text inside «…» or “…” — so
  context written around a message no longer hides two endings that show it, unless the context
  quotes other screen text too; every pair of outcomes 1.2 reported is still reported (a 1.2
  warning may grow, or merge with another).
- A step's `source` may name a file alone or `path#Symbol`, as SPEC §5.7 already advised
  (issue #12).

## 1.2.0

*2026-09-25 · SPEC v1.2, round 27*

One spelling added to an optional field: `calls:` may name a chain of operations in call order — a
control that renames a draft, then publishes it. The state rule reads the first operation; the one
new error (`malformed_calls`) is about the new spelling only.

## 1.1.0

*2026-09-15 · SPEC v1.1, round 26 — the first round under the 1.x promise*

Two optional fields: `variant_of` for an operation that exists twice over one handler, and
`coverage_gaps[].kind` for why a proof is missing. One optional config key, `uncontracted_screens`,
and two new warnings over fields 1.0 already had, `field_out_of_state` and
`form_uncontracted_screen`.

## 1.0.0

*2026-09-13 · SPEC v1.0*

The 1.x promise is declared: the required keys of a card are frozen, so a card with zero errors
under 1.0 has zero errors under every 1.x; new rounds add optional fields and codes, and a new
check on existing fields arrives as a warning. The criterion was *a round that changes only
optional fields, never required ones*, and it held from round 8 to round 24, seventeen consecutive
rounds on three stacks (SPEC §8).
