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

**v0.2, draft.** The format was hardened by writing cards for real operations of a production
system and recording where it broke — three times now, in twelve places. The criterion for v1.0
is not "no more breakage" but *a round that changes only optional fields, never required ones*.

The most recent round broke it in five places and produced a sixth axis (`continuation`), three
new optional fields, four new checks — and one finding worth more than the rest: `reversibility`
was required and had **no honest value for a read-only operation**, so both read-only cards in
this repository claimed `reversible`. A format that demands an answer must supply one that is
true, or it manufactures the exact falsehood it exists to prevent. See [SPEC §8.1](SPEC.md).

**Then it was pointed at a system it had never seen** — a different product, a different domain,
the same author's habits deliberately left behind. The first defect surfaced *before a single
card was written*: that API writes actions as `POST /progress/{id}:finish`, path normalisation
read the suffix as a parameter, and eight of its routes collapsed into two shapes. Declare one
and the checker calls them all declared, then reports a clean run. **A checker that has quietly
stopped checking looks exactly like a healthy repository.**

Three more followed: a bulk operation reporting per-item failures inside a success could not be
written truthfully; one route carrying several operations was treated as a defect rather than an
ordinary REST idiom; and a rule from the previous round turned out to be fitted to its single
example. Two things held that had only been argued for. None of it was findable on the original
system — **a format tested on one codebase is partly a description of that codebase**, and the
only way to learn which part is to take it somewhere else. See [SPEC §8.0](SPEC.md).

Earlier, the specification was checked against its own schema and examples, and failed in seven
places of a different kind: a field the schema accepted but the spec never described, a rule
stated in prose that nothing enforced, one term spelled two ways in two files. All fixed before
publication — and recorded, because it is the honest argument for check number three below. A
specification is a description like any other, and descriptions drift from what they describe.

| | |
|---|---|
| [SPEC.md](SPEC.md) | The format: fields, rules, and why each exists |
| [schema/](schema/operation-card.schema.json) | JSON Schema for the front matter |
| [examples/](examples/) | Five cards over a fictional library system |
| [tests/conformance/](tests/conformance/) | Shared corpus every implementation must pass |
| [design/](design/) | Design notes — questions worked out before they are specified |
| [impl/](impl/) | Implementations, one directory each |
| [docs/](docs/) | An animated walkthrough of all of the above |
| [starter-kit/](starter-kit/) | Team quickstart (RU): config, gate, inventory tool — copy and go |

## Repository layout

The format is language-agnostic — YAML front matter, Markdown, and plain JSON Schema — so the
root of this repository holds the specification and nothing else. Tooling lives under `impl/`,
one directory per language, and the root has no build file of its own.

Everything under `impl/` answers to [`tests/conformance/`](tests/conformance/): a shared set of
cards with agreed verdicts **and agreed diagnostic codes**. Without it, "a valid card" quietly
becomes "a card the validator you happen to have installed accepts" — the same disease, one level
up. The corpus was written before any implementation, so that it describes the format rather than
enshrining one tool's bugs.

The reference implementation is [TypeScript](impl/typescript/), chosen for reasons set out in
[impl/](impl/) rather than by default. It validates cards against the schema and the cross-card
rules, runs all three checks, and passes both corpora — **24 / 24 cards and 23 / 23 repository cases**.

```bash
npx usedesign check usedesign.config.yaml
```

Nothing to install. The package carries its own copy of the schema, so it does not need this
repository to be anywhere nearby — which is what makes it usable inside somebody else's CI.

The Python prototype stays. A corpus that only one implementation agrees with has stopped
describing the format and started describing that tool, so CI runs both and diffs what they
report about the same repository.

## Roadmap

- [x] Specification and schema
- [x] Worked examples
- [x] Conformance corpus — 47 card cases and 39 repository cases, verdicts, codes **and warnings**
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
      against the rendered container chains
- [x] `usedesign check` — the five checks, holding the 29-case repository corpus; a repository
      declares which checks apply to it (`checks: [5]`, SPEC §7.6)
- [x] `usedesign scaffold` — a draft card per undescribed route, read from the application's own
      OpenAPI. Every draft fails validation on purpose: a shell that validated would look like a
      description while claiming maturity nobody measured
- [x] A reference implementation in TypeScript, both corpora run in CI on three Node versions,
      plus a job that insists the deliberately rotten fixture still fails
- [x] `usedesign preview` — form contracts as a three-rail wireframe page: the tree, the text,
      and a rough canvas with a verdict badge on every element
- [x] Published to npm with build provenance — `npx usedesign` needs no clone
- [x] [starter-kit/](starter-kit/) — adopt checks 1–3 in a foreign repository within an hour
      (RU), with an honest list of what is still raw
- [x] `usedesign gen openapi` — derive an API contract from the cards, the opposite direction to
      `scaffold`: a `designed` card yields its contract BEFORE the code exists. Response codes are
      named by the outcomes and violated steps that declare them; the closed loop is checked by
      feeding the generated document back to `scaffold`, which must report zero undescribed routes

The checker is the point: a catalogue without one becomes aspiration within months. It exists
now, on two runtimes, and CI compares what they say about the same repository — because two tools
agreeing that something is broken while disagreeing about *what* is broken is how dialects start.

## Licence

[Apache License 2.0](LICENSE) — permissive, with an explicit patent grant, which matters for a
format organisations are meant to adopt internally.
