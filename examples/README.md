# Examples

A small fictional library system, chosen because everyone already knows the domain and nobody
has to learn a business to read a spec.

Five cards, each pulling a different part of the format into daylight:

| Card | What it demonstrates |
|---|---|
| [`library.loan.checkout`](library/library.loan.checkout.op.md) | The ordinary case: a synchronous write with optimistic locking, a lifecycle transition, an audit trail, and a `reversible_via` counterpart. Also shows why two guard steps stay separate instead of merging into one "not allowed" |
| [`library.catalog.import`](library/library.catalog.import.op.md) | Asynchronous work: the response means *accepted*, not *done*. Job states as a separate axis, a dependency on another service, and the same operation throttled **differently per transport** |
| [`library.staff.issue-api-key`](library/library.staff.issue-api-key.op.md) | `sensitivity` — a secret disclosed exactly once. One line in the card, three rules across three codebases |
| [`library.member.purge`](library/library.member.purge.op.md) | `irreversible` — and the four things that follow from it: typed confirmation, a prior-closure gate, a settlement guard, and tests that prove refusals rather than the happy path |
| [`library.member.settlement-check`](library/library.member.settlement-check.op.md) | A helper with no scenario of its own: `serves_step`, `provenance: none`, and a pure read |

## Reading order

Start with `checkout` — it is the shape everything else varies from. Then `purge` and its helper
`settlement-check` as a pair; they show how two cards reference each other. Leave `import` for
last if asynchronous work is not your problem today.

## A note on the sources

Paths like `src/loans/CheckoutHandler.ts:44` point at a codebase that does not exist. In a real
card those references are the load-bearing part: they are what makes a claim checkable, and what
turns "the card disagrees with the code" from an argument into a diff.
