# Fixture — library service

A stand-in codebase for exercising **check 1: no wild endpoints**. Nothing here runs; the files
exist so the check has something real-shaped to work against.

| File | What it is |
|---|---|
| `src/routes.ts` | Illustrative source. Shows where the inventory entries come from. |
| `route-inventory.json` | What a runtime dump of the framework's route table produces. **This is the checker's input** — see [`design/route-conformance.md`](../../../design/route-conformance.md) §3. |
| `test-report.xml` | A JUnit XML report from a run of the suite. **The input for check 2.** |
| `usedesign.config.yaml` | Card locations and the exclusions for routes that are deliberately not operations. |

The cards it is checked against are the five in [`examples/library/`](../../../examples/library/).

## This fixture is expected to FAIL

Eleven routes are served. Four are excluded as infrastructure. Five are declared by the example
cards. **Two are declared by nobody:**

```
POST   /v1/admin/members
DELETE /v1/admin/api-keys/{}
```

Both were born inside the `for` loop in `src/routes.ts`, which registers create-and-delete over
two admin resources. Two of those four routes have cards; two do not. Nobody wrote them, nobody
decided them, and nobody would find them by reading the source — the loop reads as two
registrations, not four.

That is the whole argument for this design in one fixture:

- a **marker in the code** (`// usedesign: <id>`) has no line to sit on here;
- a **static parser** sees two registrations and reports no problem;
- a **runtime dump** sees all four, and the set comparison names the two nobody claimed.

The failing case is the deliverable. A fixture that passed would demonstrate only that a checker
can agree with itself.

## Check 2 fails here too, in three different ways

The test report contains 28 cases. Three of them break a card's proof, and each breaks it
differently:

| What the report says | What the card says | Code |
|---|---|---|
| `CheckoutTests.limit_is_per_membership_tier` passes | it names `CheckoutTests.limit_is_per_tier` | `test_not_found` |
| `PurgeTests.receipt_carries_no_personal_data` is skipped, "flaky since 2026-05" | the step is proven | `test_skipped` |
| `closed_loans_do_not_count[open_loan]` passes, `[closed_loan]` fails | the step is proven | `test_failing` |

None of these is a broken build. The suite is green apart from one case, the renamed test still
runs, and the skipped one is a decision somebody made deliberately six weeks ago. All three are
invisible to a test report read by a human, and all three mean a card is claiming a proof it does
not have.

## And check 3 catches the most ordinary decay of all

`src/` holds stubs for the handlers the cards name. Five of the six are where the cards say. The
sixth moved:

```
card:       maturity_evidence.implemented: src/admin/ApiKeyHandler.ts
repository: src/security/ApiKeyHandler.ts
```

Nobody did anything wrong. The file was moved during a refactor in June, every test still passes,
and the card has been quietly false ever since. This is the failure mode the whole format exists
for, and it takes a checker one line to report.

## What passing looks like

Add cards for the two routes — or delete the routes. Both are real answers, and the check does not
prefer either one. It only refuses to let the choice go unmade.
