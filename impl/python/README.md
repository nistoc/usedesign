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

Requires only PyYAML.

## What it does not do

- **No JSON Schema validation.** The rules are hand-written, which means the schema and this
  prototype could drift. They are kept aligned by the corpus, not by construction — the reference
  implementation will validate against [`schema/`](../../schema/) directly.
- **No checking against a repository.** Confirming that the listed tests exist and pass, and that
  declared routes are the routes the code registers, is check number three in
  [SPEC.md](../../SPEC.md#7-the-three-checks) and is not implemented here.

## Errors and warnings

Errors are corpus-defined codes; the corpus README lists them. Warnings are advisory and never
fail a run:

| Warning | Meaning |
|---|---|
| `step_unproven` | A step has no test and no declared gap — invariant two of the three checks, reported rather than enforced |
| `undescribed_counterpart` | `reversible_via` or `serves_step` points at an operation nobody has described yet. Normal in a partial catalogue |
| `filename_mismatch` | File name does not match the card's `id` |
| `source_without_line` | A `source` reference has no line number, so it cannot be verified |

Running it over the example cards yields three `undescribed_counterpart` warnings and no errors —
the counterpart operations are deliberately outside the example set.
