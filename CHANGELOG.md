# Changelog

What each release of `usedesign` changed, newest first. The format ([SPEC.md](SPEC.md)) and the
package on npm are versioned together, and one promise holds across all of them: a card with zero
errors under 1.0 has zero errors under every 1.x ([SPEC §8](SPEC.md)). `1.x.0` adds to the format,
`1.x.y` fixes the tools, `2.0.0` would break. A release that changes the format names its round
in SPEC §8, where the round-by-round record is kept.

`usedesign --version` prints both numbers: `usedesign 1.5.1 (SPEC v1.5)`. Releases before 1.0
(`0.2.0` … `0.16.0`) are tagged in this repository; the rounds that led to 1.0 are in SPEC §8.
Each date is the day the version reached npm, in UTC; the date of its tagged commit can differ by
a day.

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
