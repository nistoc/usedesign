# usedesign

**One description per operation. Every screen, contract, test and migration points back to it.**

[![conformance](https://github.com/nistoc/usedesign/actions/workflows/conformance.yml/badge.svg)](https://github.com/nistoc/usedesign/actions/workflows/conformance.yml)

*[Русская версия](README.ru.md)* · **Team quickstart (RU): [starter-kit/](starter-kit/)**

---

## The problem

Ask a mature system *"what can it actually do, and what state is each of those things in?"* and
there is usually no answer. Not because nobody knows — because the knowledge is split across
genres that never agree:

- the **API spec** knows endpoints, not screens, not tests, not why anything exists;
- the **decision records** know why, but not what implements them;
- the **test suite** knows what passes, never what is uncovered;
- everything else lives in code comments and in people's heads.

So the screen drifts from the API. The test suite is green while a whole branch is unproven.
A deliberate design decision survives only as a comment that one person will ever read.

## The idea

Describe each operation **once**, in a file that both a human and a machine can read, and let
every artifact point back at it.

```
Scenario   — a user goal, in human terms         "A member borrows a book"
  └─ Operation — one atomic action, stable id     library.loan.checkout
       └─ Step  — one stage inside it             s3-member-standing
```

Tests attach to steps. Screens declare which steps they cover. Migrations attach to the version
axis. Nothing is left to be inferred.

```yaml
steps:
  - id: s3-member-standing
    text: Member has no blocking holds
    on_violation: { error: member_blocked, http: 403 }

tests:
  - { id: CheckoutTests.blocked_member_cannot_borrow, covers: s3-member-standing, level: integration }

interfaces:
  ui:
    screen: CirculationDesk
    covers_steps: [s3-member-standing, s5-commit]
```

Now the question *"what proves this behaviour, and where is it shown to the user?"* has an
answer that fits on one screen — and the absence of an answer is **a visible line**, not a
silence.

## The axes

The one thing this format insists on: **stages of life are not a single field.** Six different
things change at six different speeds, and squashing them into one `stage` is why traceability
schemes rot.

| Axis | Question it answers |
|---|---|
| **Maturity** | How far is this operation built? |
| **Steps** | What happens while it runs, including the failure branches? |
| **Data lifecycle** | What does it do to the record's state? |
| **Version** | Since which migration does it behave this way? |
| **Async job** | What is the life of the background work it starts? |
| **Continuation** | Is it stopped, waiting for a person to decide? |

A test attaches to a *step* and, by existing, moves *maturity*. A migration attaches to *neither* —
which is exactly why migrations end up orphaned everywhere else.

## What it is not

- **Not a new language.** YAML front matter and Markdown. No compiler, no runtime, no lock-in.
- **Not a replacement for OpenAPI.** An API spec describes endpoints; a card describes an
  operation, which may span several endpoints, a screen, a background worker and a migration.
  Generate the spec *from* the cards.
- **Not documentation.** Documentation is optional and rots quietly. These cards are meant to be
  checked, and to fail loudly.

## Status

**The format is SPEC v1.5; the tools are 1.5.2.** Since v1.0, declared 13 September 2026, the
format has been under one promise: the required keys of a card are frozen, so a card with zero
errors under 1.0 has zero errors under every 1.x. A round adds optional fields, optional artifact
kinds and new codes, and a new check on existing fields arrives as a warning; renaming or removing
a field, changing what a required field accepts or turning a warning into an error is 2.0. The package
follows the format — `1.x.0` adds, `1.x.y` fixes, `2.0.0` breaks — and 1.5.2 fixed the tools, so
the tools are 1.5.2 while the format is still v1.5. The package is published to npm with build
provenance.

Thirty rounds of hardening stand behind it, seven of them driven by a pilot on a real product. The
format was hardened by writing cards for real operations of production systems — each line from a
measurement of the code, not from memory — and recording where it broke. The criterion for v1.0
was never "no more breakage", because untouched ground always breaks something, but *a round that
changes only optional fields, never required ones* — and it held from round 8 to round 24,
seventeen consecutive rounds on three stacks. Round 25 changed nothing in the format; rounds
26–30 ran under the promise. The
round-by-round record is [SPEC §8](SPEC.md); what each release changed is in
[CHANGELOG.md](CHANGELOG.md).

How it got there, in two findings. Rounds 7–8 broke it in five places and produced five optional
fields — one of them, `continuation`, a sixth axis — and four new checks, and one finding worth more than the
rest: `reversibility` was required and had **no honest value for a read-only operation**, so a
read-only card could only claim `reversible`. A format that demands an answer must supply one that
is true, or it manufactures the exact falsehood it exists to prevent. See
[SPEC §8.1](SPEC.md).

**Then it was pointed at a system it had never seen** — a different product, a different domain,
the same author's habits deliberately left behind. The first defect surfaced *before a single
card was written*: that API writes actions as `POST /progress/{id}:finish`, path normalisation
read the suffix as a parameter, and eight of its routes collapsed into two shapes. Declare one
and the checker calls them all declared, then reports a clean run. **A checker that has quietly
stopped checking looks exactly like a healthy repository.** Three more findings followed, and
none of it was findable on the original system — **a format tested on one codebase is partly a
description of that codebase**, and the only way to learn which part is to take it somewhere
else. See [SPEC §8.0](SPEC.md).

| | |
|---|---|
| [SPEC.md](SPEC.md) | The format: fields, rules, and why each exists |
| [schema/](schema/) | Six JSON Schemas: the card's front matter, the form contract, the config file, and the three inventories a producer writes for checks 1, 4 and 5 |
| [examples/](examples/) | Five cards over a fictional library system |
| [tests/conformance/](tests/conformance/) | Shared corpus every implementation must pass — 93 card-and-contract cases and 56 repository cases |
| [tests/fixtures/](tests/fixtures/) | `library-service`, a deliberately rotten repository that `check` must keep failing on, and `validate-cli`, command-line cases both implementations must answer alike |
| [design/](design/) | Design notes — questions worked out before they were specified |
| [impl/](impl/) | Implementations, one directory each: the TypeScript reference and the Python prototype |
| [docs/](docs/) | An animated walkthrough of all of the above — and [architecture.html](docs/architecture.html), an interactive map of how the pieces fit |
| [starter-kit/](starter-kit/) | Team quickstart (RU): config, gate, inventory tool, form-inventory recipe — copy and go |
| [CHANGELOG.md](CHANGELOG.md) | What each release changed, newest first |

## Repository layout

The format is language-agnostic — YAML front matter, Markdown, and plain JSON Schema — so what
defines it sits at the root, in no language's folder: the specification, the schemas, the examples
and the design notes. Tooling lives under `impl/`, one directory per language, and the root has no
build file of its own. Beside them are the conformance corpus and the fixtures in `tests/`, the CI
workflows in `.github/workflows/`, the walkthrough and the architecture map in `docs/`, and the
team quickstart in `starter-kit/`.

Everything under `impl/` answers to [`tests/conformance/`](tests/conformance/): a shared set of
cards with agreed verdicts **and agreed diagnostic codes**. Without it, "a valid card" quietly
becomes "a card the validator you happen to have installed accepts" — the same disease, one level
up. The corpus was written before any implementation, so that it describes the format rather than
enshrining one tool's bugs.

The reference implementation is [TypeScript](impl/typescript/), chosen for reasons set out in
[impl/](impl/) rather than by default. It validates cards and form contracts against the schemas
and the cross-card rules, runs the five checks, and passes both corpora — **93 / 93 card and
contract cases and 56 / 56 repository cases**.

```bash
npx usedesign check usedesign.config.yaml
```

The command line has six commands — `validate`, `check` (checks 1–5), `scaffold`, `preview`,
`gen openapi` and `conformance`; `usedesign --help` lists them.

Nothing to install. The package carries its own copy of the schemas, so it does not need this
repository to be anywhere nearby — which is what makes it usable inside somebody else's CI.

The Python prototype stays. It has a JSON Schema layer of its own (`json_schema.py`, no
third-party schema library) and reads YAML as 1.2, as the reference does. A corpus that only one
implementation agrees with has stopped describing the format and started describing that tool, so
CI runs both and diffs what they report about the same repository.

## Roadmap

- [x] Specification and schema
- [x] Worked examples
- [x] Conformance corpus — 93 card-and-contract cases and 56 repository cases, verdicts, codes
      **and warnings**
- [x] Check 1 designed and prototyped — [route inventory](schema/route-inventory.schema.json),
      path normalisation, exclusions that report what they hid
      ([design note](design/route-conformance.md))
- [x] Check 2 designed and prototyped — a test a card names must exist, run, pass and not be
      skipped ([design note](design/step-coverage.md))
- [x] Check 3 designed and prototyped — the implementation path must exist, and the one claim
      nobody can verify expires instead ([design note](design/maturity-evidence.md))
- [x] `usedesign validate` — cards against the schema **and** the cross-card rules
- [x] Check 4 — no imagined storage: cards' storage claims against the keys and indexes the
      live store declares about itself (SPEC §7.4)
- [x] Check 5 — the form matches its contract: the one check whose reference is **authored**,
      not measured — the owner writes what a screen must show, a test renders the real
      components, and the errors are the product's TODO list (SPEC §7.5); form contracts are
      validated with named codes, grouping by purpose included, group membership verified
      against the rendered container chains; a contract may be written ahead of its screen,
      describe a family of elements by a pattern, and map screen states onto data states
- [x] `usedesign check` — the five checks, holding the 56-case repository corpus; a repository
      declares which checks apply to it (`checks: [5]`, SPEC §7.6)
- [x] `usedesign scaffold` — a draft card per undescribed route, read from the application's own
      OpenAPI. Every draft fails validation on purpose, until a person fills it in: a shell that
      validated would look like a description while claiming maturity nobody measured
- [x] A reference implementation in TypeScript, both corpora run in CI on three Node versions,
      plus a job that insists the deliberately rotten fixture still fails
- [x] `usedesign preview` — form contracts as a three-rail wireframe page: the tree, the text,
      and a rough canvas with a verdict badge on every element
- [x] Published to npm with build provenance — `npx usedesign` needs no clone
- [x] [starter-kit/](starter-kit/) — adopt checks 1–3 in a foreign repository within an hour
      (RU), with an honest list of what is still raw
- [x] `usedesign gen openapi` — derive an API contract from the cards, the opposite direction to
      `scaffold`: every card yields its contract, a `conceived` or `designed` one BEFORE the code
      exists.
      Response codes are named by the outcomes and violated steps that declare them; the loop
      closes — fed back to `scaffold`, the generated document reports zero undescribed routes

The checker is the point: a catalogue without one becomes aspiration within months. It exists
now, on two runtimes, and CI compares what they say about the same repository — because two tools
agreeing that something is broken while disagreeing about *what* is broken is how dialects start.

## Licence

[Apache License 2.0](LICENSE) — permissive, with an explicit patent grant, which matters for a
format organisations are meant to adopt internally.
