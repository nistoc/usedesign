# Operations over many items, and routes that carry more than one operation

*Round 9 met a repository the format had never seen and broke in two ways that share a root: the
format assumes **one call, one record, one ending**. Written before the schema changed, and
checked against the nine cards that exist.*

## What broke

A bulk endpoint takes a list of ids and an `op`, and answers **200 regardless**, with
`{id, ok, error?}` per item. The honest card passes validation and is false three times over:

```yaml
steps:
  - id: s1-item-exists
    text: Each named item exists
    on_violation: { error: not_found, http: 200 }   # ← a violation answering with success
```

`steps[]` has one shape built into it: **violated → stopped → error code.** A per-item failure
inside a success fits none of the three. There is nowhere else to put it, so it goes there, and
the card lies quietly.

The second break is next to it: `op` in the body decides whether the call publishes, archives,
duplicates or deletes. Those are four operations with different reversibility, different data
transitions and different permissions — on one route. A card is an operation, so the author must
choose between one card that lies about four, and four cards that trip `ambiguous_shape`, a
warning that treats a widespread REST idiom as a defect.

## 1. `per_item` — the failure that does not stop the operation

```yaml
per_item:
  applies_to: ids                    # the list the caller sends
  independent: true                  # one item failing does not stop the others
  reported_in: results               # where the per-item verdicts live in the response
  failures:
    - { code: not_found,          means: the item does not exist }
    - { code: invalid_transition, means: the item cannot make that move }
    - { code: id_conflict,        means: the generated id was taken }
```

The point is the **absence of `http`**. A per-item failure has no status of its own; it is data
inside somebody else's success. Giving it an `http` field would rebuild the same lie one level
down.

With `per_item` present, the per-item conditions leave `steps[]` entirely — they were never steps
of the operation. What remains in `steps[]` is what genuinely stops the call: authentication, a
malformed body, an empty list.

**Checked:** with `per_item` declared, an `on_violation` answering 2xx is no longer a warning but
an **error** — there is now a true place to write it, so writing it falsely is a mistake rather
than a shortage of vocabulary. Diagnostic: `per_item_failure_as_violation`.

## 2. `dispatch` — several operations on one route

```yaml
interfaces:
  rest:
    transport: http_rest
    method: POST
    path: /v1/things:batch
    dispatch: { by: op, value: publish }
```

Four cards, one path, four values. Each says what it does, what it reverses, what it touches —
truthfully, because each is one operation.

`ambiguous_shape` stays, and gets sharper: cards sharing a shape are ambiguous **unless** they
declare distinct `dispatch.value` on the same `by`. Two cards claiming `by: op, value: publish`
are still ambiguous, and now for a real reason.

**Checked:** cards sharing a route shape must either declare `dispatch` with different values, or
be reported. Same diagnostic, better question.

## 3. `continuation.after` may name a job state

Round 8 added axis F with one example in hand: an operation that answers immediately and suspends
on one of its **outcomes**. So `after` was required to name an entry in `outcomes[]`.

Round 9 found the other half. A request thread runs `pending → checking → executing → done`, and
**`done` is where it waits for a person** — the next message pushes it back to `pending`. The
suspension happens on a **job state**, not on an outcome, and the rule rejected the card.

The axis survived contact; its check did not. A rule written from a single example is fitted to
that example — which is the same defect the format exists to catch, one level up.

`after` may now name either an `outcomes[].id` or an `async_execution.job_states` entry. It must
still name something: an operation that claims it can suspend on a state it never declares is
back to unverifiable prose.

This also settles a question raised when axis F was introduced. Axes E and F were kept separate
on the argument that an operation could be asynchronous *and* resumable. That was reasoning; the
request thread is the evidence — machine work runs by itself between turns, and between those
runs nothing moves until a human writes.

## What this costs

| Change | Kind | Existing cards affected |
|---|---|---|
| `per_item` | new optional top-level field | none |
| `interfaces.*.dispatch` | new optional field | none |
| `continuation.after` may name a job state | widened, previous form still valid | none |

Required fields unchanged, so nine cards — five library examples plus four written against an
unfamiliar repository — keep validating without a character changed.

## Two rules considered and dropped

- **`per_item.failures[].http`.** Rejected above: a per-item failure has no status. Adding the
  field would let authors write `http: 200` again, in a new place.
- **Inferring `dispatch` from the request body.** The checker would have to read the handler,
  which it does not do anywhere else. The whole design rests on the repository stating facts and
  the checker comparing them; a single exception is how that principle stops being one.
