# Python prototype

**Status: prototype.** Not a package, not on PyPI, no stability promise. It exists for two
reasons: to keep the [conformance corpus](../../tests/conformance/) honest before the reference
implementation is written, and to demonstrate that the format is implementable on a second
runtime — a claim that is cheap to make and easy to get wrong.

## What it does

Checks the rules a JSON Schema cannot express — cross-references between steps, tests and
interfaces — plus the structural rules, so it can run the corpus end to end. Since 1.4.3 it first
validates against the published [JSON Schema](../../schema/), as the TypeScript implementation
does: `json_schema.py` reads the keywords the schemas use and reports what Ajv reports there — the
same messages, in the same order. `--no-schema` skips it.

```bash
python validate.py --conformance      # run the conformance corpus
python validate.py ../../examples     # validate real cards
```

`check.py` implements the three checks that compare cards against a repository:

- **check 1 — no wild endpoints**, against a
  [route inventory](../../schema/route-inventory.schema.json) the repository produces;
- **check 2 — no unproven steps**, against a JUnit XML report from the run being checked;
- **check 3 — no inflated maturity**: the implementation path must exist, a claim of `tested` must
  have a passing test, and a deployment claim expires.

```bash
python check.py ../../tests/fixtures/library-service/usedesign.config.yaml
python check.py --conformance
```

The fixture is expected to fail — two wild endpoints and three broken proofs; [why that is the
deliverable](../../tests/fixtures/library-service/README.md).

Requires only PyYAML.

## What it does not do

- **No general JSON Schema validator.** `json_schema.py` implements the keywords
  [`schema/`](../../schema/) uses and refuses a schema with any other, so a keyword added there
  cannot pass here unread. Since 1.4.3 the schema layer and the rules read the same front matter,
  as YAML 1.2 resolves it in the TypeScript implementation's parser — `no`, `off`, `1:20` and a
  date are text, and an explicit tag whose text does not fit it (`!!float 1`) leaves the text — and
  a key written twice is refused in both, as there. The rules read a field only in its type, as the
  TypeScript implementation does: a step id that is a number, an interface that is not a mapping,
  `steps` that is not a list count as absent, and the schema names what is wrong. Both layers are
  held to the TypeScript implementation's output, line for line, on the cards of
  [`tests/fixtures/validate-cli/schema/`](../../tests/fixtures/validate-cli/schema/) by
  [`run.sh`](../../tests/fixtures/validate-cli/run.sh) in CI. PyYAML's scanner is still PyYAML's:
  a raw U+0085, U+2028 or U+2029 and a surrogate pair read as [SPEC §5.7](../../SPEC.md#57-interfaces)
  says.
- **Does not produce route inventories.** By design — see
  [`design/route-conformance.md`](../../design/route-conformance.md) §3. The inventory comes from
  the repository being checked.
- **Does not run tests.** Check 2 consumes a report; producing it is the suite's job. A checker
  that must run the code cannot check somebody else's repository.
- **Cannot judge report freshness.** A report from an older commit will confirm a step whose code
  changed since. The rule is procedural: run the check in the same CI job as the suite.
- **Cannot verify a deployment.** Nothing here queries a deployment system; the claim is made to
  expire instead.
- **Cannot tell whether a file implements what the card says.** Check 3 confirms the file exists.
  That it is the right file is a human claim, like `covers:` on a test.

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
`inventory_malformed`, `incomplete_rest_interface`, `no_cards_found`, `test_not_found`,
`test_failing`, `test_skipped`, `report_missing`, `report_empty` and `report_malformed` as errors,
`evidence_path_missing` and `maturity_without_passing_test` as errors, and `dead_exclusion`,
`ambiguous_shape`, `evidence_undated`, `evidence_stale` and `maturity_understated` as warnings.
`step_unproven` is an error when a test report is available and a warning when it is not.

> **Removed:** `source_without_line`, which warned when a `source` reference carried no line
> number. It pushed authors toward exactly the kind of reference that rots silently — see
> [SPEC §5.7](../../SPEC.md#57-interfaces). The prototype was teaching the opposite of the format.
