# Outcomes, continuations, and what an operation does to its own request

*Written before the schema changed, and checked against the five example cards plus the four
that broke in round 7. Two rules in this project have already died on contact with data; the
cheapest place to kill a rule is here.*

## What round 7 established

Four things could not be said honestly. Three of them are one gap seen from three sides: **the
format speaks well about what an operation does to the data, and poorly about what it does to
its own request and its own response.** The fourth is a missing axis.

This note proposes four changes, all optional fields. None of the five existing examples changes
by a character — checked, not assumed.

---

## 1. A terminal outcome is not a violated step

### The problem, in an existing card

`library.member.settlement-check` already has it, and it does not hurt there:

```yaml
- id: s2-answer
  text: Returns settled true or false, plus the counters behind the answer
```

Two outcomes, written as prose inside a step's `text`. It gets away with it because both answers
have the same *shape* — same status, same fields, only a boolean differs.

It stops getting away with it the moment the shapes diverge. An operation answering a question
against a catalogue has four terminal outcomes, three of them successful:

| Outcome | What it means | What the response carries |
|---|---|---|
| answered | the catalogue had it | context, answer, a suggested query |
| not covered | **the catalogue has nothing on this** | nothing — every field above is null |
| ambiguous | the question matches several things | a list of candidates |
| unresolvable | the request was well formed but could not be planned | an error code |

"Not covered" is not a failure. Nothing was violated, no rule was broken, the operation did
everything it was asked and answered honestly. Writing it as `on_violation` with a success status
lies twice: it is not a violation, and the field that names error codes now contains a success.

### The test that separates the two

> **Can the caller fix this by changing the request?**
> Yes → it is a violated step. No → it is an outcome.

A missing required field: fix the request. A stale revision: refetch and retry. Ambiguity: yes —
the caller picks a candidate. Nothing in the catalogue: **no.** There is no request that makes an
absent metric present.

### The proposal

```yaml
outcomes:
  - id: answered
    means: The catalogue covered the question
    http: 200
    carries: [context_pack, answer]
  - id: not_covered
    means: Nothing in the catalogue covers it — an honest empty answer, not a failure
    http: 200
    carries: []
  - id: ambiguous
    means: Several catalogue entries match the phrase
    http: 200
    carries: [candidates]
```

**Optional.** Present only when an operation has more than one terminal outcome *and they differ
in shape*. `settlement-check` keeps its prose, correctly: one shape, one outcome.

**The machinery is not new.** `async_execution` already carries `job_states` and `terminal` — the
format has always been able to say "there are several end states, these ones are final". It was
locked inside axis E, available only when the response does not mean the work is done. This
unlocks it for operations that answer immediately.

### What a checker can do with it — today, with no new input

Every `outcomes[].http` must appear in that interface's `responses[]`. A card claiming an outcome
its own interface does not list is inconsistent with itself, and nothing outside the card is
needed to see it. Diagnostic: `undeclared_response`.

### Writing this rule down found a defect in the reference example

The rule is symmetric — if outcomes must be declared, so must the codes a violated step returns.
Applied to the five examples, it fires once:

```
library.loan.checkout   responses: [200, 403, 409, 412]
                        s6-audit  on_violation: { error: audit_write_failed, http: 500 }
```

**500 is nowhere in `responses`.** The card contradicts itself, in the example the whole project
uses to explain the format, and it went unnoticed through every round because nothing compared
those two lists.

The reason it could happen is worth more than the fix: **the specification never said what
`responses` means.** The field appears in §5.7 in a one-line summary of interface keys and is
never defined — complete list, or the interesting ones? Nobody could be wrong, because nothing
was claimed. An undefined field cannot rot; it also cannot be checked, which is the same
statement from the other side.

So this note also fixes the specification: `responses[]` is **every status the operation can
return**, including those named by `on_violation` and `outcomes`. With that settled, the checker
can compare, and the example is corrected to `[200, 403, 409, 412, 500]`.

---

## 2. An operation that stops and waits for a person

The ambiguous outcome above does not end the story. The next call carries the chosen candidate
and continues where the first stopped.

This is **not** axis E, and the difference is worth stating precisely, because at a glance they
look identical — both are "the response does not mean it is over":

| | Async execution (axis E) | Continuation |
|---|---|---|
| Who moves it forward | the system, on its own | **a person** |
| What the caller does | watches (`observe_via`) | **decides** |
| If everybody walks away | it still finishes | **it never finishes** |
| What the second call is | a status query | the same operation, resumed |

`observe_via` is exactly the field that cannot be filled in here. There is nothing to observe.
The work is not slow — it is *stopped*, and no amount of waiting will move it.

```yaml
continuation:
  after: ambiguous              # the outcome that suspends the operation
  resumed_by: human             # human | caller — who can move it
  carries: selected_candidate   # what the resuming call must bring
  same_operation: true          # the resumption is this operation again, not another one
```

**Checkable today:** `after` must name an outcome declared in `outcomes[]`. Diagnostic:
`continuation_without_outcome`.

**Why this is a sixth axis and not a field on axis E.** The five axes were separated because they
change at different speeds and for different reasons. This one is separated for the same reason:
an operation can be asynchronous *and* resumable, asynchronous and not, resumable and synchronous.
Folding it into `async_execution` would force one to imply the other, which is the exact mistake
the five axes exist to prevent.

---

## 3. A target state taken from history

```yaml
data_transition: { from: retired, to: draft }   # false for half the records
```

An operation that undoes a retirement returns the record to *the state it held before* — draft
or published, depending on that record's own past. This is not a quirk of one system. **Every
undo operation has this shape:** they return the system to where it was, not to where the card
says.

`to: previous_state` names a variable where a value belongs, and nothing can check it.

### The proposal

```yaml
data_transition:
  from: retired
  to: [draft, published]
  determined_by: the state the record held before it was retired
```

`to` stays a string in the ordinary case — all five examples are untouched. When it is a list,
`determined_by` becomes required: a set of possible destinations without a rule for choosing
between them is worse than one wrong constant, because it looks complete.

The consumer gains what it actually needs: **the set of states this operation can leave a record
in.** That is enough to reason about what may follow, which a single false constant never was.

---

## 4. What an operation does to its own request

Two variants, one gap. Both are about a parameter whose declared meaning is not its real one.

**Silently clamped.** A page-size parameter above the maximum is not rejected — it is quietly
reduced. The caller who asks for 5000 and receives 100 concludes the data ran out. Nothing in the
response says otherwise. This is not a violated step (nothing was violated), not a notice
(nothing is emitted), and not a quota (`quota` is about how often you may call, not about what
happens to what you sent).

**Decorative.** A path parameter that the operation does not use — the real value is derived from
the caller's identity. Two callers substituting different values get the same answer. The card
must write the path verbatim, or route conformance reports a wild endpoint; but written verbatim,
the path promises that the parameter matters.

### The proposal — on the interface, where parameters live

```yaml
interfaces:
  rest:
    transport: http_rest
    method: GET
    path: /v1/tenants/{slug}/chunks/search
    parameters:
      - name: take
        handling: clamped
        range: [1, 100]
        note: A caller asking for more receives the maximum, and is not told
      - name: slug
        handling: decorative
        note: The real tenant comes from the caller's identity; this is for readable URLs
```

`handling` is one of `clamped` · `defaulted` · `normalised` · `decorative`. All four are the same
statement: **what you sent is not what was used.** That is the thing worth writing down, and the
reason to write it is not tidiness — it is that a caller who does not know cannot tell a truncated
answer from a complete one.

**Checkable today:** a parameter declared `decorative` must actually appear in the interface's
`path`, or the declaration describes nothing. Diagnostic: `decorative_parameter_not_in_path`.

---

## What this costs

| Change | Kind | Existing cards affected |
|---|---|---|
| `outcomes[]` | new optional top-level field | none |
| `continuation` | new optional top-level field — **axis F** | none |
| `data_transition.to` accepts a list | widened, string still valid | none |
| `interfaces.*.parameters[]` | new optional field | none |

**Required fields: unchanged.** By the v1.0 criterion — *a round that changes only optional
fields, never required ones* — this round qualifies. But the criterion is about a round that
**breaks**, not about the repair afterwards, and it would be self-serving to count a repair I
designed as evidence that the format is stable. The honest reading:

> Round 7 broke the format in four places. The repairs are additive, which is the good news.
> Whether the repairs are *right* is decided by the next round that has not seen them.

## Three rules this note deliberately does not propose

Each was considered and dropped, and saying why is cheaper than watching someone re-propose them:

- **`outcomes` required whenever `responses[]` has more than one entry.** Dies immediately on
  `checkout`: four response codes, one outcome, three violations. Response codes and outcomes are
  different things, and a rule conflating them would force noise into every honest card.
- **A checker verifying that every declared outcome actually occurs.** Would need a production
  trace, not a test report, and would make cards fail for outcomes that are simply rare. The
  format has one claim nobody can verify — deployment — and it is handled by expiry, not by
  proof. Adding a second unverifiable claim and pretending to check it is worse than admitting it.
- **`handling: validated`** as a fifth kind. It is not the same statement as the other four:
  validation *rejects*, and rejection is already a violated step with an error code. Adding it
  would blur the one distinction the field exists to draw.
