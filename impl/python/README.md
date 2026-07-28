# Python prototype

**Status: prototype.** Not a package, not on PyPI, no stability promise. It exists for two
reasons: to keep the [conformance corpus](../../tests/conformance/) honest before the reference
implementation is written, and to demonstrate that the format is implementable on a second
runtime — a claim that is cheap to make and easy to get wrong.

## What it does

Checks the rules a JSON Schema cannot express — cross-references between steps, tests and
interfaces — plus the structural rules, so it can run the corpus end to end.

```bash
python validate.py --conformance      # run the conformance corpus
python validate.py ../../examples     # validate real cards
```

`check.py` implements **check 1 — no wild endpoints**: it compares the routes the cards declare
against a [route inventory](../../schema/route-inventory.schema.json) produced by the checked
repository.

```bash
python check.py ../../tests/fixtures/library-service/usedesign.config.yaml
```

The fixture is expected to fail with two wild endpoints; [why that is the
deliverable](../../tests/fixtures/library-service/README.md).

Requires only PyYAML.

## What it does not do

- **No JSON Schema validation.** The rules are hand-written, which means the schema and this
  prototype could drift. They are kept aligned by the corpus, not by construction — the reference
  implementation will validate against [`schema/`](../../schema/) directly.
- **Does not produce route inventories.** By design — see
  [`design/route-conformance.md`](../../design/route-conformance.md) §3. The inventory comes from
  the repository being checked.
- **Does not confirm that tests exist or pass.** Check 2 is reported as a `step_unproven` warning
  from the cards alone; nothing here runs a test suite or looks for the named tests in a
  repository.
- **No maturity evidence verification (check 3) beyond form.** That a card claiming `tested` names
  tests is enforced; that those tests are real is not.

## Errors and warnings

Errors are corpus-defined codes; the corpus README lists them. Warnings are advisory and never
fail a run:

| Warning | Meaning |
|---|---|
| `step_unproven` | A step has no test and no declared gap — invariant two of the three checks, reported rather than enforced |
| `undescribed_counterpart` | `reversible_via` or `serves_step` points at an operation nobody has described yet. Normal in a partial catalogue |
| `filename_mismatch` | File name does not match the card's `id` |

Running it over the example cards yields three `undescribed_counterpart` warnings and no errors —
the counterpart operations are deliberately outside the example set.

`check.py` adds `wild_endpoint`, `phantom_route`, `inventory_missing`, `inventory_empty`,
`inventory_malformed`, `incomplete_rest_interface` and `no_cards_found` as errors, and
`dead_exclusion` and `ambiguous_shape` as warnings.

> **Removed:** `source_without_line`, which warned when a `source` reference carried no line
> number. It pushed authors toward exactly the kind of reference that rots silently — see
> [SPEC §5.7](../../SPEC.md#57-interfaces). The prototype was teaching the opposite of the format.
