# Implementations

The format itself is language-agnostic: an Operation Card is YAML front matter and Markdown, and
the schema is plain JSON Schema. Nothing about the specification requires a particular runtime.

Tooling is a different matter, and this is where implementations live. Each one sits in its own
directory and must earn the name by passing the same corpus:

| Directory | Status |
|---|---|
| `typescript/` | Reference implementation — validate and all three checks; **14/14 and 20/20**; not yet published to npm |
| `python/` | Prototype — the same rules on a second runtime, kept so the corpus is never agreed with by only one tool |

## The one rule

**Every implementation must pass [`tests/conformance`](../tests/conformance/).** Not "should" —
must. The corpus is what stops "a valid card" from quietly becoming "a card my validator happens
to accept", which is the exact disease this project exists to treat. An implementation that
cannot pass the corpus is a fork of the format wearing its name.

If a corpus case looks wrong, the fix is a pull request against the corpus, not a special case
inside one implementation.

## Why TypeScript is the reference

Chosen for reasons, not by default:

- **`ajv`** is the most complete and fastest JSON Schema implementation available, and this
  format leans on the schema heavily — including conditional rules such as *claiming
  `in_production` requires naming an environment*. Support for draft 2020-12 is noticeably
  thinner elsewhere.
- **`npx usedesign validate`** means zero installation. For a tool whose whole job is to slot
  into somebody else's CI, not having to install a runtime first is decisive.
- **Generating an OpenAPI document** from cards is on the roadmap, and no ecosystem has richer
  tooling for that.

The honest counter-argument: Go or Rust would produce a single binary with no runtime at all,
which is better *distribution*. That advantage matters once there are users to distribute to.

**What the ajv argument turned out to be worth**, now that it has been built: the schema catches
7 of the 10 invalid corpus cases, and the 3 it misses are all the same shape — a name pointing at
a step that does not exist. So the schema does the bulk of the work, and the cross-card rules do
the part that matters most. Both halves were needed; neither would have been enough.

And a result that could only appear once two implementations existed: **the schema had never been
run against the corpus** before the TypeScript port. It agreed with it completely — every case
the corpus calls valid passes the schema, and no case is called invalid by the schema alone. Two
artifacts written separately from the same specification, neither derived from the other,
agreeing on first contact — that is the strongest evidence the format has produced so far.

## Adding an implementation

1. Create `impl/<language>/` with its own README stating scope and status.
2. Add the stack's section to the root `.gitignore` — at that point, not earlier.
3. Pass every case in `tests/conformance`, including the diagnostic codes. Reporting *that* a
   card is invalid is not enough; two implementations disagreeing on *why* is how dialects start.
4. Add a row to the table above.

An implementation does not have to be complete. A validator that handles only the schema is
useful and honest, as long as its README says so.
