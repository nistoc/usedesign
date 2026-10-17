# usedesign — TypeScript

The reference implementation: validates Operation Cards and form contracts, and runs the five
checks against a repository.

```bash
npx usedesign validate examples/library/
npx usedesign check usedesign.config.yaml
```

Exit status is `1` when anything reported an error, `0` otherwise, `2` on misuse or on input that
cannot be read. That is the whole CI contract.

## Status

**Complete against both corpora, published to npm as `usedesign`.** Everything below runs from a
clone as well as through `npx usedesign`.

| | |
|---|---|
| Cards corpus | every case passes (`tests/conformance/cards/`) |
| Repository corpus | every case passes (`tests/conformance/checks/`) |
| Runtime | Node ≥ 20, no native modules |
| Dependencies | `ajv`, `ajv-formats`, `yaml`, `fast-xml-parser` |

```bash
npm install && npm run build
npm test                      # both corpora
node dist/cli.js check ../../tests/fixtures/library-service/usedesign.config.yaml
```

The last command is expected to exit `1`: the fixture is deliberately rotten — two wild
endpoints, three unproven steps, one missing evidence path — and it has no storage inventory,
which check 4 reports as not run. A clean run there would mean the checks had stopped working.

## Commands

| Command | What it does |
|---|---|
| `validate <path…>` | Cards and form contracts against the JSON Schema **and** the cross-card rules. `--no-schema` keeps only the latter |
| `check <config>` | Checks 1–5: no wild endpoints, no unproven steps, no maturity beyond its evidence, no imagined storage, the form matches its contract. A config's `checks:` names the ones that apply to the repository |
| `scaffold <openapi.json> --out <dir>` | A draft card per route the cards do not declare yet, read from the application's own OpenAPI. Every draft fails validation on purpose |
| `preview <config> --out <file.html>` | Form contracts as a three-rail wireframe page |
| `gen openapi <config> --out <file.json>` | An OpenAPI contract derived from the cards — the opposite direction to `scaffold` |
| `conformance` | Both corpora. `--cards` / `--checks` to run one |

## What validation is, in two halves

`validate` runs the published schema and the cross-reference rules, and the split is not
cosmetic. The schema catches what a field looks like — a missing required field, an enum out of
range, a malformed step id, an interface with no transport. It cannot see a test covering a step
that does not exist, a screen covering a step that does not exist, or one step id used twice.

Those invisible ones are the same shape: *a name that points at nothing*. A schema can say what a
field looks like; only a checker holding the whole card — and every other card of the run — can
say whether the thing it names is there.

That second group is the reason this tool exists rather than a bare `ajv` invocation. A schema
validates *form*; the rules validate *meaning*, and meaning is where cards rot.

The schema itself is never vendored: the compiled package carries a copy of the repository's
`schema/` made at build time, so the tool cannot drift from the schema it claims to implement.

## Notes from building it

- **Line endings are not content.** A CRLF card handed the YAML parser a dangling carriage
  return after the closing fence; scalars came back with `\r` attached, ids stopped matching
  their pattern, and one card would not parse at all. Every symptom looked like a format problem
  and none of them was. `frontMatter` normalises before parsing.
- **A field is read only in its type.** A list is read as a list, a map as a map, a name as text;
  a value of another type is absent to the rules and to the checks, and the schema names it. A
  rule that trusts the shape of its input stops with a stack trace on the first card that lies.
- **The Python implementation prints what this one prints, line for line**, including the noise
  suppressions — a dead exclusion is not reported when there are no routes, and a step whose only
  test failed is reported once, not twice. Two implementations that disagree about what to stay
  quiet about are two dialects; CI compares them on the corpora and on the fixtures.

## Layout

| File | What is in it |
|---|---|
| `src/core.ts` | Findings, front matter, config, file collection, typed reads — no rules |
| `src/validate.ts` | The schema and the cross-card rules for cards and form contracts |
| `src/checks.ts` | The five checks |
| `src/conformance.ts` | The corpus runners |
| `src/scaffold.ts` | Draft cards from an OpenAPI document |
| `src/gen.ts` | `gen openapi`: an OpenAPI document from the cards |
| `src/preview.ts` | The wireframe page of form contracts |
| `src/formInventory.ts` | Helper for producing the form inventory check 5 reads |
| `src/index.ts` | Library entry point: findings, front matter, config, card collection, card validation, checks 1–3 and the `CHECKS` map of all five, the corpus runners, the form-inventory helpers |
| `src/cli.ts` | Argument handling and output |

Rules never live in a helper: a rule that hides inside a utility is a rule nobody reviews.
