# usedesign — TypeScript

The reference implementation: validates Operation Cards and runs the three checks against a
repository.

```bash
npx usedesign validate examples/library/
npx usedesign check usedesign.config.yaml
```

Exit status is `1` when anything reported an error, `0` otherwise, `2` on misuse. That is the
whole CI contract.

## Status

**Complete against the corpus, not yet published to npm.** Everything below runs today from a
clone; `npx usedesign` will work once the package is released, and this README will not claim it
does before then.

| | |
|---|---|
| Cards corpus | **14 / 14** |
| Repository corpus | **20 / 20** |
| Runtime | Node ≥ 20, no native modules |
| Dependencies | `ajv`, `ajv-formats`, `yaml`, `fast-xml-parser` |

```bash
npm install && npm run build
npm test                      # both corpora
node dist/cli.js check ../../tests/fixtures/library-service/usedesign.config.yaml
```

The last command is expected to report **six errors** — the fixture is deliberately rotten, and
a clean run there would mean the checks had stopped working.

## Commands

| Command | What it does |
|---|---|
| `validate <path…>` | Cards against the JSON Schema **and** the cross-card rules. `--no-schema` keeps only the latter |
| `check <config>` | The three invariants: no wild endpoints, no unproven steps, no maturity beyond its evidence |
| `conformance` | Both corpora. `--cards` / `--checks` to run one |

## What validation is, in two halves

`validate` runs the published schema and the cross-reference rules, and the split is not
cosmetic. Measured on the 10 invalid corpus cases:

- **7** are caught by the schema — a missing required field, an enum out of range, a malformed
  step id, an interface with no transport;
- **3** are invisible to it — a test covering a step that does not exist, a UI screen covering a
  step that does not exist, and the same step id used twice.

All three of the invisible ones are the same shape: *a name that points at nothing*. A schema can
say what a field looks like; only a checker holding the whole card can say whether the thing it
names is there.

That second group is the reason this tool exists rather than a bare `ajv` invocation. A schema
validates *form*; the rules validate *meaning*, and meaning is where cards rot.

The schema itself is never vendored: the compiled package carries a copy of the repository's
`schema/` made at build time, so the tool cannot drift from the schema it claims to implement.

## Notes from building it

- **Line endings are not content.** A CRLF card handed the YAML parser a dangling carriage
  return after the closing fence; scalars came back with `\r` attached, ids stopped matching
  their pattern, and one card would not parse at all. Every symptom looked like a format problem
  and none of them was. `frontMatter` normalises before parsing.
- **The three checks are ported line for line from the Python prototype**, including the noise
  suppressions — a dead exclusion is not reported when there are no routes, and a step whose only
  test failed is reported once, not twice. Two implementations that disagree about what to stay
  quiet about are two dialects.

## Layout

| File | What is in it |
|---|---|
| `src/core.ts` | Findings, front matter, config, globbing — no rules |
| `src/validate.ts` | The schema and the cross-card rules |
| `src/checks.ts` | The three checks |
| `src/conformance.ts` | The corpus runners |
| `src/cli.ts` | Argument handling and output |

Rules never live in a helper: a rule that hides inside a utility is a rule nobody reviews.
