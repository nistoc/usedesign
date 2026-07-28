# usedesign

**One description per operation. Every screen, contract, test and migration points back to it.**

*[Русская версия](README.ru.md)*

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

## The five axes

The one thing this format insists on: **stages of life are not a single field.** Five different
things change at five different speeds, and squashing them into one `stage` is why traceability
schemes rot.

| Axis | Question it answers |
|---|---|
| **Maturity** | How far is this operation built? |
| **Steps** | What happens while it runs, including the failure branches? |
| **Data lifecycle** | What does it do to the record's state? |
| **Version** | Since which migration does it behave this way? |
| **Async job** | What is the life of the background work it starts? |

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

**v0.2, draft.** The format was hardened by writing cards for eight operations of a real
production system and recording where it broke — twice, in seven places. The criterion for v1.0
is not "no more breakage" but *a round that changes only optional fields, never required ones*.

Then the specification was checked against its own schema and examples, and failed in seven
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

## Repository layout

The format is language-agnostic — YAML front matter, Markdown, and plain JSON Schema — so the
root of this repository holds the specification and nothing else. Tooling lives under `impl/`,
one directory per language, and the root has no build file of its own.

Everything under `impl/` answers to [`tests/conformance/`](tests/conformance/): a shared set of
cards with agreed verdicts **and agreed diagnostic codes**. Without it, "a valid card" quietly
becomes "a card the validator you happen to have installed accepts" — the same disease, one level
up. The corpus was written before any implementation, so that it describes the format rather than
enshrining one tool's bugs.

TypeScript is to be the reference implementation, chosen for reasons set out in [impl/](impl/)
rather than by default. **It is not written yet** — today the repository ships a Python prototype
that keeps the corpus honest. Saying otherwise would be a claim ahead of its evidence, which is
the one thing this format refuses to let a card do.

## Roadmap

- [x] Specification and schema
- [x] Worked examples
- [x] Conformance corpus — 14 cases, verdicts and codes
- [x] Check 1 designed and prototyped — [route inventory](schema/route-inventory.schema.json),
      path normalisation, exclusions that report what they hid
      ([design note](design/route-conformance.md))
- [x] Check 2 designed and prototyped — a test a card names must exist, run, pass and not be
      skipped ([design note](design/step-coverage.md))
- [x] Check 3 designed and prototyped — the implementation path must exist, and the one claim
      nobody can verify expires instead ([design note](design/maturity-evidence.md))
- [~] `usedesign validate` — the cross-card rules run in [`impl/python/validate.py`](impl/python/validate.py);
      what is missing is a tool a stranger can run
- [~] `usedesign check` — all three invariants run in [`impl/python/check.py`](impl/python/check.py)
      and hold the 20-case repository corpus; same caveat
- [ ] `usedesign gen openapi` — derive an API contract from the cards. Not started
- [ ] A reference implementation — `npx usedesign` in TypeScript, the corpus run in CI. This is
      what the two half-marks above are missing

The checker is the point: a catalogue without one becomes aspiration within months. Its logic
exists and the corpus holds it — but a prototype only its author can run is not a delivered tool,
and a full tick here would be exactly the claim check 3 refuses on a card.

## Licence

[Apache License 2.0](LICENSE) — permissive, with an explicit patent grant, which matters for a
format organisations are meant to adopt internally.
