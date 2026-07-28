# Design note — check 3: no inflated maturity

**Status:** design, not yet specified.
**Question it answers:** which parts of a maturity claim a checker can actually confirm, which it
cannot, and what to do about the second group instead of pretending it belongs to the first.

---

## 1. What the format asks for today, and what it gets

`maturity` runs `conceived → designed → implemented → tested → in_production → deprecated`, and
each level from `implemented` upwards requires an entry in `maturity_evidence`. The schema enforces
that the entry is **present**. Here is what those entries actually look like across every card in
this repository:

| Key | What it holds today | Verifiable? |
|---|---|---|
| `implemented` | `src/loans/CheckoutHandler.ts` — usually a path, sometimes two joined by `" + "` | partly: a path can be checked to exist |
| `tested` | `7 tests`, `5 tests`, and in one deliberate corpus case `soon` | no — and it duplicates what check 2 computes exactly |
| `deployed` | `production` | no |

All three are prose. The schema cannot tell `7 tests` from `soon`; that is the documented boundary
between form and meaning, and the corpus has a case (`sample.thing.untested`) whose entire purpose
is to prove the boundary is real.

So check 3 is not one check. It is three claims of very different natures wearing one field.

## 2. The three tiers

### Tier 1 — verifiable against the repository

`implemented` names code. A checker can confirm the file exists. That is a weak proof — a file can
exist and contain nothing relevant — but it catches the common decay exactly: a card written when
the handler lived at `src/loans/CheckoutHandler.ts`, and a repository where it was moved to
`src/circulation/` eight months ago.

Two things this must get right, both learned from data rather than assumed:

- **The value is not always one path.** `src/catalog/ImportEndpoint.ts + src/workers/ImportWorker.ts`
  appears in the example set. A checker that treats the value as a single path reports a false
  alarm on a card that is telling the truth in a slightly inconvenient way.
- **Line numbers must be stripped, not honoured** — SPEC §5.7 already says a line number is a
  human aid. `src/loans/CheckoutHandler.ts:42` means the file, and the `:42` is discarded.

### Tier 2 — verifiable against another check

`tested` is the odd one. The card asserts `7 tests` in prose, while `tests[]` lists the tests by
name and check 2 confirms which of them exist and pass. **The prose is a second, worse copy of
something already known exactly.** Two records of the same fact, one of which is not checked, is
the shape of every rotting catalogue in this project's motivation section.

The rule that replaces it: *a card may claim `tested` or above only if at least one test it names
exists and passes in the report.* No parsing of the prose, no counting — the claim is derived from
the same evidence check 2 already reads. When no report is available, the claim cannot be judged
and the finding degrades to a warning, exactly as check 2 does.

### Tier 3 — not verifiable at all

`deployed: production` cannot be confirmed from a repository, a test report, or anything else the
checker is willing to consume. Verifying it would mean querying a deployment system — different in
every organisation, frequently not reachable from CI, and a dependency that turns a checker into
infrastructure.

The honest options are to drop the claim, to trust it forever, or to **make it expire**.

## 3. What cannot be verified must expire

Trusting a claim forever is how a catalogue becomes decorative: `deployed: production` written in
2024 still reads as true in 2027, and nothing in the world will ever contradict it. The claim is
not wrong — it is simply unexamined, and unexamined claims accumulate until the catalogue is a
museum.

So: an unverifiable claim carries a date, and goes stale.

```yaml
maturity_evidence:
  deployed: { env: production, since: 2026-07-12 }
```

A checker compares `since` against a horizon (default: 180 days, configurable) and warns when the
claim is older. The warning does not mean the operation left production; it means **nobody has
re-affirmed it in six months**, which is a different and useful statement. Clearing it costs one
edit, and that edit is the moment somebody looks.

This is deliberately a *warning*, not an error. An error would make every long-stable operation
fail its build, and a checker that fails builds for being old is a checker that gets disabled.

⚠️ The obvious objection: a date that must be refreshed by hand will be refreshed carelessly, in
bulk, without checking. True — and it still beats a claim that never asks. The format cannot
prevent someone from lying; it can only prevent a claim from quietly outliving its evidence.

## 4. The reverse defect

A card claiming *less* than it can prove is also wrong, and cheap to detect: `maturity: designed`
while the tests it names pass in the report. It sends people to build what exists.

Checked against the data before proposing it, per the lesson from check 2: in this repository no
card under-claims, so there is no evidence either way. The code is `maturity_understated` and its
severity is advisory.

**It was narrowed the first time it ran.** The initial rule fired whenever a card below `tested`
had a passing test — and it immediately flagged two corpus cards that claim `implemented` and
carry one passing test each. That is not under-claiming. A passing test is *necessary* to claim
`tested`; it is not *sufficient* for it. One smoke test does not make an operation covered, and no
checker can judge which case it is looking at. The rule now applies only below `implemented`,
where the claim is unambiguously behind the evidence: a card saying `designed` while its tests
pass.

The general shape of the mistake is worth keeping: **a necessary condition read as a sufficient
one**. It produces a rule that is right in the direction it was designed for and wrong in the
mirror, and it is the second time in three checks that a rule survived the design note and died in
contact with the corpus.

## 5. Diagnostics

| Code | | Meaning |
|---|:--:|---|
| `evidence_path_missing` | error | `implemented` names a file that is not in the repository |
| `maturity_without_passing_test` | error | `tested` or above, and no test the card names passes in the report |
| `evidence_undated` | warning | An unverifiable claim (`deployed`) with no `since` |
| `evidence_stale` | warning | An unverifiable claim older than the horizon — nobody has re-affirmed it |
| `maturity_understated` | warning | The card claims less than its evidence supports |
| `code_root_unset` | — | Not a finding: without a `code_root` the path check is **not run**, and says so |

## 6. Limits

**A file that exists proves a file exists.** Nothing here confirms that the named file implements
the operation, and nothing can: that link is a human claim, like `covers:` on a test.

**Dates are self-reported.** `since: 2026-07-12` is as trustworthy as the person who typed it. The
mechanism does not detect lying; it detects *silence*, which is the far more common failure.

**The horizon is a guess.** 180 days is a default, not a fact about software. A team shipping
weekly may want 30; a stable internal service may want a year. It is configurable for that reason,
and any number chosen will be wrong for somebody.

## 7. Consequences for the format

| # | Demand | Kind of change |
|---|---|---|
| C1 | `maturity_evidence.implemented` accepts a string **or a list of strings** — the multi-path case already exists in the examples | additive: `oneOf` in the schema |
| C2 | `maturity_evidence.deployed` accepts `{ env, since }` as well as a bare string; a bare string draws `evidence_undated` | additive |
| C3 | `maturity_evidence.tested` becomes advisory prose; the enforced rule moves to *a named test passes* | wording in §5.2 and §7 |
| C4 | `code_root` in the config, so paths resolve; absent means the path check is not run | new optional config key |
| C5 | Conformance cases: missing path, multi-path, no passing test, undated claim, stale claim | additions to the corpus |

C1 and C2 widen what the schema accepts and reject nothing that was previously valid. **No required
field changes, for the third exercise running.**
