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
```

Every case is a real card, and its Markdown body explains what it is probing — read the case
before arguing with it.

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

## What the corpus deliberately does not test

**Meaning.** `tested: "soon"` satisfies the rule that a tested note exists, and the corpus accepts
that, because a schema validates form. Confirming that the listed tests exist and pass, and that
the declared routes are the routes the code registers, is the checker's job against a real
repository — see check number three in [SPEC.md](../../SPEC.md#7-the-three-checks). The corpus
draws that boundary on purpose rather than pretending it is not there.

## Running it

```
python impl/python/validate.py --conformance
```

The prototype implementation runs the corpus and compares its verdicts and codes against
`manifest.yaml`. Any future implementation is expected to offer an equivalent entry point.

## Adding a case

1. Write a real card that isolates **one** rule, and say in its body what it probes.
2. Add it to `manifest.yaml` with the expected verdict and, for invalid cards, the codes.
3. Confirm every existing implementation still agrees. A case that only one implementation passes
   is a bug report against the others, not a merge.

If a case turns out to be wrong, fix the case — never special-case it inside one implementation.
