# Conformance corpus

A shared set of cards with agreed verdicts. **Every implementation must reproduce them** —
including the diagnostic codes, not merely the pass/fail outcome.

## Why this exists before any implementation does

Two validators that disagree turn "a valid card" into "a card that happens to satisfy the
validator you installed". At that point the format has dialects, and a catalogue is only as
trustworthy as the tool that last checked it — which is the disease this project exists to treat.
Writing the corpus first also keeps it honest: a corpus written *after* an implementation tends
to enshrine that implementation's bugs as the standard.

Agreeing on the *code* matters as much as the verdict. Two tools that both reject a card but
disagree on why cannot be used interchangeably in a pipeline, and their messages teach users two
different mental models of the format.

## Layout

```
manifest.yaml          the list of cases with expected verdicts and codes
cases/valid/*.op.md    cards that must be accepted
cases/invalid/*.op.md  cards that must be rejected, each with its codes

checks/manifest.yaml   the same idea for the checks against a repository
checks/cases/<name>/   a config plus what the check consumes: a route
                       inventory for check 1, a JUnit XML report for check 2
```

Each case says which invariant it exercises (`check: 1` or `check: 2`) and is run through that one
only, so a missing inventory is not held against a coverage case.

Every card case is a real card, and its Markdown body explains what it is probing — read the case
before arguing with it.

The `checks/` cases all point at the same five example cards, so what varies between them is only
what the code is said to serve — which is the axis check 1 is about.

## Diagnostic codes

| Code | Meaning |
|---|---|
| `no_owner` | Neither `scenario` nor `serves_step` — nobody can say who calls this operation |
| `maturity_without_evidence` | The claimed level lacks the evidence it requires (`implemented` path, `tested` note, `deployed` environment) |
| `maturity_without_tests` | `tested` or `in_production` claimed with an empty `tests[]` |
| `relaxation_without_rationale` | A concurrency mode weaker than the strictest, with no `rationale` |
| `unknown_step_reference` | A test or an interface points at a step id that does not exist |
| `duplicate_step_id` | Two steps share an id, making every reference to it ambiguous |
| `malformed_step_id` | A step id does not match `s<N>-<name>` |
| `malformed_operation_id` | An operation id does not match `<area>.<object>.<action>` |
| `missing_required_field` | A field required by the schema is absent |
| `missing_transport` | An interface does not declare its transport |
| `write_without_effect` | `data_transition: null` with neither `mutates` nor `provenance: none` |

An implementation may report **additional** codes beyond these, and may cover only part of the
corpus — but whatever it does report must agree with the table above. Silently renaming a code is
how a fork begins.

### Check 1 — comparing cards against the code

| Code | | Meaning |
|---|:--:|---|
| `wild_endpoint` | error | A route is served and declared by no card |
| `phantom_route` | error | A card declares a route the code does not serve |
| `inventory_empty` | error | An inventory with no routes — almost always a failed dump |
| `inventory_malformed` | error | Missing `usedesign_inventory: 1`, missing `produced_by`, or an unknown method |
| `inventory_missing` | error | No inventory at all. Check 1 is then reported as **not run**, never as passed |
| `no_cards_found` | error | The card patterns matched nothing — a run with nothing to disagree with is not a passing run |
| `incomplete_rest_interface` | error | A card declares `http_rest` without a method or a path |
| `dead_exclusion` | warning | An exclusion that hid nothing |
| `ambiguous_shape` | warning | Two cards declare routes that normalise to the same shape; the checker cannot tell them apart |

### Check 2 — comparing cards against a test run

| Code | | Meaning |
|---|:--:|---|
| `test_not_found` | error | A card names a test no report entry matches — renamed, moved, or never written |
| `test_failing` | error | The named test ran and failed. For a parametrised family, one failing case is enough |
| `test_skipped` | error | The named test was skipped. Louder than absent on purpose: a skipped test keeps its name |
| `step_unproven` | error | A step with neither a test nor a declared gap. A warning when no report is available, an error when one is |
| `report_missing` | error | No report. Check 2 is then **not run**, never passed |
| `report_empty` | error | A report with zero cases — a failed run, not a suite without tests |
| `report_malformed` | error | The report is not parseable XML |

### Check 3 — comparing a maturity claim against its evidence

| Code | | Meaning |
|---|:--:|---|
| `evidence_path_missing` | error | `implemented` names a file that is not in the repository |
| `maturity_without_passing_test` | error | `tested` or above with no named test passing in the report |
| `evidence_undated` | warning | An unverifiable claim with no date — it can never go stale |
| `evidence_stale` | warning | A dated claim past the horizon. Reports silence, not absence |
| `maturity_understated` | warning | A card below `implemented` whose tests pass. Advisory, and narrowed once already |

## What the corpus deliberately does not test

**Meaning.** `tested: "soon"` satisfies the rule that a tested note exists, and the card corpus
accepts that, because a schema validates form. Confirming that the listed tests exist and pass is
the checker's job against a real repository — see
[SPEC §7](../../SPEC.md#7-the-three-checks). The corpus draws that boundary on purpose rather than
pretending it is not there.

The `checks/` cases are the first crossing of that boundary: they compare cards against a stated
route inventory. They still do not run anything — the inventory is a fixture, not a live
application — but the disagreement they detect is with the code, not within the card.

## Running it

```
python impl/python/validate.py --conformance
python impl/python/check.py    --conformance
```

The prototype implementation runs the corpus and compares its verdicts and codes against
`manifest.yaml`. Any future implementation is expected to offer an equivalent entry point.

## Adding a case

1. Write a real card that isolates **one** rule, and say in its body what it probes.
2. Add it to `manifest.yaml` with the expected verdict and, for invalid cards, the codes.
3. Confirm every existing implementation still agrees. A case that only one implementation passes
   is a bug report against the others, not a merge.

If a case turns out to be wrong, fix the case — never special-case it inside one implementation.
