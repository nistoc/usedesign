# Design note — check 2: no unproven steps

**Status:** design, not yet specified.
**Question it answers:** what it takes for a card to *prove* a step, rather than to claim it — and
how a checker can tell the difference without becoming a test runner for every stack in existence.

---

## 1. What the check is not

The prototype already reports `step_unproven` when a step has neither a test nor a declared gap.
That reads like check 2, and it is worth being precise about how little it proves: it confirms that
**a string was written in the card**. Nothing about it says the named test exists, ran, or passed.

A card can satisfy it while naming a test that was renamed last spring, a test that has been
skipped since it started flaking, or a test that never existed. All three are ordinary, none of
them is malicious, and all three produce a catalogue that says a behaviour is proven when it is not.
That is worse than an empty catalogue: an empty one is not consulted.

So check 2 is the same shape as check 1 — a claim in the card measured against the world — and the
interesting part is where the world's answer comes from.

## 2. What "proven" has to mean

Four conditions, and the last one is the one people forget:

1. the named test **exists** in the suite;
2. it **ran** in the recorded run;
3. it **passed**;
4. it was **not skipped**.

A skipped test is the classic silent hole. It sits in the suite, it is counted in the total, and it
keeps its name in every report — so any check that matches by name and stops there will confirm a
step that has not been exercised in months. Skipped must be *louder* than absent, not quieter:
an absent test at least fails the name match.

## 3. Three ways to learn that, two of which fail

### 3.1 Run the tests

The tool would have to know how to invoke pytest, jest, xUnit, go test, JUnit, RSpec — and to
configure each of them. It would be a worse test runner than the one the project already has, it
would need the project's dependencies installed, and it would turn a checker into part of the
build. Refused, and not narrowly: a checker that must run the code cannot run in the places a
checker is most useful, such as a review of somebody else's repository.

### 3.2 Parse the test sources for test names

Cheap to start, and it repeats the mistake that check 1 already discovered. Tests are generated as
routinely as routes are: table-driven cases, parametrised fixtures, a loop over a list of inputs.
A parser sees one function where the suite has forty cases. Worse, source text cannot answer
conditions 2, 3 and 4 at all — a test that exists in the source can be excluded by a filter, marked
skip, or fail. Refused.

### 3.3 Consume the report the suite already produces

Every test runner in use can emit a machine-readable report, and one format is the lingua franca:
**JUnit XML**. pytest, jest, vitest, Go (via converters), Maven, Gradle and .NET (via a one-line
switch or a converter) all produce it, and CI systems already collect it.

This is the same conclusion as check 1, reached from the other end — the repository states the
facts, the checker compares. The difference is that here **the format already exists**, so
usedesign should consume it rather than invent a second inventory. Inventing one would mean asking
every project to produce a bespoke artifact next to the standard one it already has.

## 4. Matching a card's test id to a report entry

The same normalisation problem as paths, and the format has already committed to two id shapes —
both appear in the example cards:

```
CheckoutTests.blocked_member_cannot_borrow          class-and-method
CirculationDesk.test.tsx:shows_reason_when_blocked  file-and-name
```

A JUnit XML entry carries `classname` and `name`. Proposed rules, in order:

| # | Rule | Why |
|---|---|---|
| 1 | Compare against `classname.name`, exactly | The common case, and the only unambiguous one |
| 2 | If no match, compare against `name` alone | Runners disagree about what belongs in `classname`; jest puts the file path there, pytest puts the module |
| 3 | Match a card id of the form `file:name` against `name`, using the file part only to disambiguate | The file-and-name shape the format already permits |
| 4 | A card id matching **several** entries is satisfied only if **all** of them pass | Parametrised cases: `checkout[blocked]`, `checkout[expired]`. One green case does not prove the step |
| 5 | Matching is on the full id, never on a substring | Substring matching turns `checkout` into a match for `checkout_rollback`, and a checker that guesses is a checker that lies |

⚠️ Rule 4 is where this check earns its keep and also where it will annoy people: a card naming a
parametrised test inherits every one of its cases. That is correct — the step is proven only if
the whole family passes — but it means a single flaky case marks a step unproven. The alternative,
"proven if any case passed", is how coverage numbers become decorative.

## 5. Diagnostics

| Code | | Meaning |
|---|:--:|---|
| `test_not_found` | error | A card names a test no report entry matches. The card is describing a test that was renamed, moved, or never written |
| `test_failing` | error | The named test ran and failed. The step is not proven, whatever the card says |
| `test_skipped` | error | The named test was skipped. Louder than absent, on purpose — see §2 |
| `step_unproven` | error | A step with neither a test nor a declared gap. Today a warning from the card alone; with a report it becomes an error |
| `stale_gap` | warning | A step declared as a gap whose test now exists and passes. Not a defect in the code — a card that under-claims, and a sign nobody revisits `coverage_gaps` |
| `report_missing` | error | No report. Check 2 is then **not run**, never passed |
| `report_empty` | error | A report with zero test cases — a failed run, not a suite without tests |

`stale_gap` is deliberately included. A catalogue that is wrong in the pessimistic direction still
misleads: it sends someone to write a test that exists, and it makes the coverage picture useless
for deciding what to work on next.

## 6. The limits, stated rather than discovered

**A passing test proves that a test passed.** That it proves *this step* is a human claim, made
when someone wrote `covers: s3-member-standing`, and no checker can verify it. The check protects
against a claim going stale, not against a claim being wrong on the day it was written.

**Report freshness is outside the mechanism.** A report from three commits ago will happily confirm
a step whose code changed this morning. JUnit XML carries a timestamp but not a commit, and adding
one would mean inventing the bespoke artifact §3.3 just avoided. The workable rule is procedural:
run the check in the same CI job as the suite, on the report that job just produced. This is a real
limit, and the honest way to hold it is to say so in the spec rather than to imply the check is
stronger than it is.

**Nothing here proves the test is a good test.** A test that asserts nothing passes. That is out of
reach of any traceability format, and pretending otherwise would be the same overclaiming this
project exists to prevent.

## 7. Consequences for the format

| # | Demand | Kind of change |
|---|---|---|
| C1 | The two permitted shapes of `tests[].id` must be stated in §5.9, together with the matching rules of §4 — otherwise two implementations disagree about what a card's test id means | wording in §5.9 |
| C2 | `step_unproven` becomes an error when a report is available and a warning when it is not; the spec should say which, so implementations do not each pick | wording in §7 |
| C3 | The procedural freshness rule (§6) belongs in the spec next to check 2, because a checker cannot enforce it | wording in §7 |
| C4 | Conformance cases: not found, failing, skipped, parametrised-partial-failure, stale gap, missing report | additions to `tests/conformance/checks/` |

**Again, no required field of the card changes.** Two rounds of implementation work in a row have
now demanded only wording. That is the strongest evidence so far that the card's required set is
close to right — stronger than the card-writing rounds, because these two exercises were trying to
*use* the cards rather than to write more of them.
