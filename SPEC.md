# Operation Card — Specification v0.2

> **Status:** draft. This document defines the Operation Card format: a single description of
> one operation that several consumers — UI, data model, external contracts, service-to-service
> contracts, tests and database migrations — all read from and point back to.
>
> The format is deliberately boring: YAML front matter for machines, Markdown body for humans.
> No new language, no compiler, no runtime.

---

## 1. The problem this format exists for

In most systems the answer to *"what can this platform do?"* is scattered across four genres
that never agree with each other:

| Genre | Answers | Cannot answer |
|---|---|---|
| API specification (OpenAPI, …) | Which endpoints exist | Which screens use them, what is tested, why it exists |
| Architecture decision records | Why a decision was made | What implements the decision |
| Test suite | What currently passes | Which behaviour is *not* covered |
| Tribal knowledge & code comments | Everything else | Anything, to anyone who has not read that file |

None of them is a catalogue of operations, and none of them lets an artifact — a test, a screen,
a contract, a migration — declare **what it implements** and **which stage of life it belongs to**.

An Operation Card is that missing unit.

### 1.1 Where collaborative modelling fits

Event Storming and Domain Storytelling are the nearest neighbours, and they are **not
competitors**. They are the half that comes before: a room agreeing on what happens, using the
same unit this format uses — the thing that happens, not the layer it lives in. Steps here are
close relatives of commands and policies there; `data_transition` is the aggregate's move.

Three differences decide the division of labour:

| | Collaborative modelling | Operation Cards |
|---|---|---|
| **When** | before the code exists | against code that runs |
| **What counts as true** | the agreement of the room | what the system states about itself — its own route list, its own test report, the keys of its own live store |
| **What survives the session** | a wall of stickies, then a photograph in a wiki that ages silently | a file the next build compares with reality |

They chain without strain: the workshop yields the vocabulary and the boundaries, the cards turn
that result into files that cannot lie for long. A sticky reading "request rejected" becomes an
outcome named `rejected` — and from then on, if the code stops producing it or the screen stops
showing it, somebody learns the same day rather than the following year.

What this format adds on top is not a better picture but a worse one to fake: maturity that must
name its evidence (§7.3), outcomes that must say what the user sees (§5.7), storage that must
match the live store (§7.4), and gaps that must be written as lines rather than left as silence.

---

## 2. Core principles

1. **One file, one operation.** The file name equals the operation `id`. No collections.
2. **Axes never merge.** Maturity, execution steps, data lifecycle, version, async job state and
   suspension are six different things. Systems that squash them into a single `stage` field fall
   apart.
3. **Every weakening is explained.** Any relaxation — no optimistic locking, no audit trail,
   no owning scenario — must carry a `rationale`. A silent relaxation is a spec bug.
4. **Claims cite source.** Anything asserted about the implementation carries `source:
   path:line`. An unsourced claim is treated as unverified.
5. **Gaps are written down as lines.** `coverage_gaps` is a tool, not an admission: a missing
   line is invisible, a present line is reviewable.

---

## 3. Three levels

```
Scenario   — a user goal, told in human terms          ("A member borrows a book")
  └─ Operation — one atomic action with a stable id     (library.loan.checkout)
       └─ Step  — one stage inside that action          (s3-member-standing)
```

Only the operation is a file. A scenario is a name shared by several cards; a step is a section
inside one. That is deliberate: the catalogue has exactly one kind of file in it.

Humans read scenarios. Tests, screens and contracts attach to operations and steps.
An operation that belongs to no scenario must declare whom it serves (`serves_step`) —
otherwise nobody knows who calls it, and it is probably a forgotten endpoint.

---

## 4. The axes of life

This is the heart of the format. Each axis changes at its own pace and is owned by different
artifacts.

| Axis | Field | What it describes | Changes |
|---|---|---|---|
| **A · Maturity** | `maturity` | How far the operation is built: conceived → … → in production | Weekly, as work lands |
| **B · Steps** | `steps[]` | What happens during execution, including failure branches | Only when behaviour changes |
| **C · Data lifecycle** | `data_transition` | What the operation does to the state of the record | Almost never — it is the domain model |
| **D · Version** | `since` | Since which migration / release the operation behaves this way | Every release |
| **E · Async job** | `async_execution.job_states` | The life of background work started by the operation | Only for async operations |
| **F · Continuation** | `continuation` | The operation stopped and cannot proceed until a person decides | Only for operations that can suspend |

**Why they must stay apart.** A test attaches to a *step* (axis B) and by existing moves
*maturity* (axis A). A screen covers a *set of steps*. A migration attaches to *neither* — it
belongs to axis D, which is exactly why migrations end up orphaned in every traceability scheme
that has only one stage field.

**Axis B is not axis C.** Steps are states of *executing the operation*; the data transition is
the state of *the record itself*. A publish operation has its own steps **and** moves a record
from draft to published. Conflating the two is the second classic mistake.

**Axis E is neither.** A job may reach `succeeded` while the record it produced stays `draft`.

**Axis F is not axis E**, though both mean *"the response does not tell you it is over"*. An async
job progresses on its own and you watch it; a suspended operation progresses **not at all** until
somebody decides. If everyone walks away, the first still finishes and the second never does.
Axis F arrived in round 7 — the format was published with five axes, and the sixth is the reason
this section is no longer called "the five axes".

---

## 5. Fields

Legend: ⬛ required · ⬜ optional · 🔶 conditionally required

### 5.1 Identity

| Field | | Meaning |
|---|:--:|---|
| `id` | ⬛ | Stable identifier, `<area>.<object>.<action>` — three segments, more allowed when a domain needs them. **Never changes**: tests and code point at it |
| `title` | ⬛ | Human-readable name |
| `scenario` | 🔶 | The user goal this operation is part of. Required unless `serves_step` is present |
| `serves_step` | 🔶 | `{ operation, step, purpose }` — this operation is a helper serving a step of another one |
| `actors` | ⬛ | Who invokes it: roles, service identities, agents |

### 5.2 Axes

| Field | | Meaning |
|---|:--:|---|
| `maturity` | ⬛ | `conceived` · `designed` · `implemented` · `tested` · `in_production` · `deprecated` |
| `maturity_evidence` | 🔶 | Required from `implemented` upward — **a level may not be claimed without its evidence**. A `conceived` or `designed` operation has nothing to prove yet. The three keys are not the same kind of claim; see below |
| `data_transition` | ⬜ | `{ from, to }` — axis C. `null` for read-only operations and for writes that do not change state. `to` may be **a set of states** with `determined_by`, for operations whose destination comes from the record's own history |
| `mutates` | 🔶 | Fields changed, when `data_transition` is null but the operation still writes |
| `since` | ⬜ | `{ migration, note }` — axis D. The one place where migrations stop being orphans |

```yaml
maturity_evidence:
  implemented: src/loans/CheckoutHandler.ts        # or a list, for an operation spanning files
  tested: 7 tests                                  # advisory prose — not the enforced evidence
  deployed: { env: production, since: 2026-07-12 }  # or a bare env name, which never expires
```

**The three keys differ in what a checker can do with them, and the format should not pretend
otherwise:**

- `implemented` names code and **can be verified** — the file must exist. A trailing `:line` is
  discarded (§5.7). One operation may span an endpoint and a worker, so a list is permitted.
- `tested` is **advisory prose**. The enforced rule is not this text but the report: a card
  claiming `tested` or above must name a test that exists and passes. Counting in prose what
  `tests[]` already lists exactly is a second, unchecked copy of a known fact.
- `deployed` **cannot be verified by any checker** worth building. Give it a `since` date and it
  can go stale — a bare environment name never can, and a claim that never asks to be re-examined
  is how a catalogue becomes a museum. Staleness is a warning, never a build failure.

**Undo operations, and why `to` may be a set.** An operation that reverses a lifecycle change
returns the record to *the state it held before* — which differs from record to record. A single
constant is false for half of them, and naming a variable (`to: previous_state`) puts a word
where a value belongs and can be checked by nothing. So:

```yaml
data_transition:
  from: retired
  to: [draft, published]
  determined_by: the state the record held before it was retired
```

`determined_by` is required whenever `to` is a set: a list of destinations with no rule for
choosing between them is worse than one wrong constant, because it looks complete. The rule may
be anything the destination actually depends on — the record's history for an undo, its
completeness for a finish, a request field for a bulk dispatch. Round 8 wrote this field for undo
operations and said so; round 9 found the other cases, and the field fitted them unchanged. What the
consumer gains is the thing it actually needs — **the set of states this operation can leave a
record in**, which a single false constant never gave it.

### 5.2c Operations over many items

An operation may process a list, and a failure on one item may not stop the others. `steps[]`
cannot say this: its shape is **violated → stopped → error code**, and a per-item failure inside
a success fits none of the three.

```yaml
per_item:
  applies_to: ids
  independent: true
  reported_in: results
  failures:
    - { code: not_found,          means: the item does not exist }
    - { code: invalid_transition, means: the item cannot make that move }
```

**Note the absence of `http`.** A per-item failure has no status of its own — it is data inside
somebody else's success. Giving it one would rebuild the same falsehood one level down.

With `per_item` present, per-item conditions leave `steps[]`, which then holds only what stops
the whole call: authentication, a malformed body, an empty list.

**Checked:** an `on_violation` answering 2xx is a warning normally
(`violation_with_success_status`) and an **error** when `per_item` is declared
(`per_item_failure_as_violation`) — the rule tightens exactly when the vocabulary to say it
truthfully exists.

### 5.2d Several operations on one route

`POST /things:batch` with `op` in the body may publish, archive, duplicate or delete. Those are
different operations — different reversibility, different transitions, different permissions —
and a card is one operation.

```yaml
interfaces:
  rest:
    path: /v1/things:batch
    dispatch: { by: op, value: publish }
```

One card each, all truthful. `ambiguous_shape` no longer fires on cards sharing a route when
their `dispatch.value` differ; it still fires when two cards claim the same route the same way,
or with no dispatch at all — which is the case it was always meant to catch.

The route shape itself is unchanged by `dispatch`: the inventory knows nothing about request
bodies, and the comparison in check 1 must stay a comparison of routes.

### 5.2a Outcomes

Not every ending is a success-as-usual or a violated step. An operation that searches, resolves a
name or answers a question can **reach the end and honestly return nothing** — no rule broken,
nothing to fix, the work done.

```yaml
outcomes:
  - id: answered
    means: The catalogue covered the question
    http: 200
    carries: [context, answer]
  - id: not_covered
    means: Nothing in the catalogue covers it — an honest empty answer, not a failure
    http: 200
    carries: []
```

**The test that separates an outcome from a violated step:**

> *Can the caller fix this by changing the request?*
> Yes → it is a violated step. No → it is an outcome.

A missing field: fix the request. A stale revision: refetch. Nothing in the catalogue: **no
request makes an absent record present.** Writing that as `on_violation` with a success status
lies twice — it was not a violation, and the field naming error codes now holds a success.

`outcomes` is optional, and belongs only where an operation has more than one terminal ending
*and they differ in shape*. One ending, or several sharing a shape, stays prose in a step's text.

The machinery is not new: `async_execution` has always carried `job_states` and `terminal`. The
format could always say *"there are several end states, these are final"* — it was locked inside
axis E, available only when the response did not mean the work was done. This unlocks it for
operations that answer immediately.

**Checked:** every `outcomes[].http` must appear in that interface's `responses[]`
(`undeclared_response`).

### 5.2b Continuation (axis F)

An operation can stop and be unable to continue until **somebody decides**. The next call carries
the decision and resumes where the first stopped.

```yaml
continuation:
  after: ambiguous              # the outcome that suspends the operation
  resumed_by: human             # human | caller
  carries: selected_candidate   # what the resuming call must bring
  same_operation: true
```

At a glance this looks like axis E — both are *"the response does not mean it is over"*. The
difference decides whether anyone should wait:

| | Async execution (axis E) | Continuation (axis F) |
|---|---|---|
| Who moves it forward | the system, on its own | **a person** |
| What the caller does | watches (`observe_via`) | **decides** |
| If everybody walks away | it still finishes | **it never finishes** |
| What the second call is | a status query | this operation, resumed |

`observe_via` is precisely the field that cannot be filled in here: there is nothing to observe.
The work is not slow, it is *stopped*.

It is a separate axis for the same reason the other five are separate — an operation can be
asynchronous and resumable, one, the other, or neither. Folding this into `async_execution` would
make one imply the other, which is the mistake the axes exist to prevent.

**Checked:** `continuation.after` must name a declared outcome **or a job state**
(`continuation_without_outcome`). Round 8 required an outcome, because its single example
suspended on one; a request thread suspends on `done`, a *job state*, and waits there for a
person. The axis survived that contact — its check did not, which is what a rule written from one
example does.

### 5.3 Steps (axis B)

```yaml
steps:
  - id: s<N>-<short-name>          # ⬛ stable — tests attach to it
    text: <what happens>           # ⬛ plain language
    on_violation:                  # ⬜ present on steps that can refuse the call
      error: <error code>
      http: <status>               # for HTTP transports
      jsonrpc_code: <code>         # for JSON-RPC transports
      payload: [<field>, …]        # ⬜ what the refusal returns, so the caller can act on it
    emits_notice: <code>           # ⬜ a side effect reported on success, not a violation
    rationale: <why it works this way>   # ⬜ required when non-obvious
    source: <path:line>            # 🔶 when asserting a fact about code
```

`on_violation` describes a refusal; `emits_notice` describes something the operation *did* and
reports. Keeping them apart matters: a side effect announced in an error channel reads to the
caller as a failed call.

Step ids are **never renumbered or reused**. A step inserted in the middle takes the next free
number and sits wherever it belongs in the list — so `s7` running before `s6` is normal and
correct. **Ids are identifiers, not positions**; the order of the list is the order of execution.

This rule looks fussy until it is broken. Renumbering to keep the list tidy silently moves every
external reference — a test that covered `s6-audit` now claims to cover whatever took that
number. The tidiness is visible; the damage is not.

### 5.4 Concurrency

```yaml
concurrency:
  mode: <one of the four below>    # ⬛
  rationale: <why>                 # 🔶 required for every mode except the strictest
  formula: <…>                     # 🔶 for idempotency_by_formula
  on_duplicate: <…>                # 🔶 for both idempotency modes; allowed for etag_required
  source: <path:line>              # ⬛
```

| Mode | Meaning |
|---|---|
| `etag_required` | Caller must send the current revision; mismatch is rejected |
| `idempotency_by_header` | Caller supplies an idempotency key |
| `idempotency_by_formula` | The server derives the key from the payload |
| `none_by_design` | No protection needed — the operation is idempotent by construction |

`on_duplicate` is required for the two idempotency modes, and **permitted for `etag_required`**:
a stale revision is a collision outcome the caller must handle, and stating it is more useful
than leaving it to be inferred from the status code.

> This field exists because real systems mix all four, and the reasoning usually survives only
> in a code comment next to one of them.

### 5.5 Quota

Required when call frequency is limited.

```yaml
quota:
  scheme: <how it is counted>            # e.g. per_credential_per_minute
  categories: { <name>: { bucket: <n>, window_min: <m> } }
  applies_to: <whom>                     # ⚠️ see below — the field that surprises integrators
  on_exceeded: { error, http?, jsonrpc_code?, retry_after }
  storage: <where counters live>
```

**`applies_to` is free text on purpose** — real limiters are scoped by whatever the system
authenticates with, and no fixed vocabulary survives contact with that. But it must be spelled
**identically across every card in one catalogue**: `api_key_callers_only` in one card and
`api_token_callers_only` in another describe the same rule in two words, and nothing will catch
it. Pick the wording once, alongside your credential names, and treat it as a term.

> Quota is **neither** a role **nor** concurrency. A role answers *who may*; concurrency answers
> *what happens on collision*; quota answers *how often*. For an external consumer, the difference
> between "10 writes per minute" and "unlimited" is part of the promised contract — and it is
> frequently invisible because it depends on **how the caller authenticated**.

### 5.6 Async execution (axis E)

Required when the response does not mean the work is done.

```yaml
async_execution:
  job_states: [queued, running, succeeded, failed, cancel_requested, cancelled]   # ⬛
  terminal:   [succeeded, failed, cancelled]                                      # ⬛
  worker:      <path to the worker>                                               # ⬛
  observe_via: <status endpoint>                                                  # ⬛
  cancel_via:  <cancel endpoint + required role>                                  # ⬜
  s2s_dependency:                                                                 # 🔶
    service: <whose service>
    purpose: <what for>
    failure_mode: <what happens when it fails>
```

### 5.7 Interfaces

```yaml
interfaces:
  rest: { transport: http_rest, method, path, headers_required[], responses[],
          contract_version: <media type>, source }
  rpc:  { transport: json_rpc, tool, scope_required, source }
  ui:   { transport: ui, screen, control, covers_steps[], covers_outcomes{}, source }
```

At least one interface is required. Each interface declares its `transport`
(`http_rest` · `json_rpc` · `in_process` · `ui`) — without it, `on_violation.http` is meaningless
for protocols whose errors are numeric RPC codes.

`ui.covers_steps` is the mechanism that makes UI/API drift visible: if a screen claims to cover a
step that does not exist, the checker fails.

**`covers_outcomes{}` — what the user of this interface sees for each declared outcome.** Round 10
traced one real button through its screen, its store, and back: of the four outcomes the server
declared, the screen showed two and swallowed both errors in a bodyless `catch` — a rollback
indistinguishable from success in the user's eyes. The card had no way to say it. This map is
that way:

```yaml
ui:
  transport: ui
  screen: SessionNavPanel
  control: button[data-action="finish-progress"]
  covers_outcomes:
    finished: footer label «Завершено»
    partial: footer label «Частично»
    unauthorized:          # null — declared NOT shown; a warning, never an error
    invalid_time_range:
```

Keys must name declared outcomes — an entry of `outcomes[]`, a `data_transition.to` value, a
step's `on_violation.error`, or a `per_item.failures[].code`; anything else is
`covers_unknown_outcome`, the residue of a rename. Once the map exists, **every** declared
outcome must appear in it: a missing one is `outcome_not_covered` (an error), while one
explicitly mapped to null is `outcome_unshown` (a warning). The asymmetry is the point — the
field forbids **silent** gaps, not honest ones.

**The vocabulary is what this invocation can end with.** Job states are *not* in it, and the
line is not taste: a per-item failure arrives in this call's response while the user is looking
at the screen, whereas a job state is the record's later life, watched through `observe_via` by
another operation with a screen of its own. Round 10 wrote the rule with job states included —
they had been in hand for the continuation rule, which asks a different question — and the second
card the rule ever met failed six times, every error false: a *create* screen was required to
display `checking`, `executing`, `done`, `rejected`, `failed`, `archived`. Per-item failures went
the other way: they carry no status, so nothing named them, and a bulk screen that silently drops
them had no way to admit it.

**Values are what the user reads, verbatim — not a description of it.** Writing "the same
sentence as above" hides the collapse from the checker, which compares strings. When two outcomes
carry identical text, `outcomes_indistinguishable` warns: between *shown* and *not shown* sits a
third state nobody notices — two endings wearing one sentence. Measured on a real screen where
`401` and `403` both surfaced as "something went wrong, try again", so the one user who must give
consent is told to do the only thing that cannot help.

What the round rejected matters as much as what it added. The measurement showed outcome handling
is not located in "the screen": the control sat in one component, the error policy in a shared
store, and the success label was rendered from a state field computed offline as well. So there is
no screen-card to write and no page→forms→api hierarchy to model — a screen is an *interface of an
operation*, and a page with ten forms is ten cards each naming its own control. The page is an
address, not an entity.

**`responses[]` is every status the operation can return** — success, each outcome, and every
code named by an `on_violation`. Not "the interesting ones": a list that is allowed to be partial
cannot be compared with anything, and a field nobody can be wrong about is a field nobody
maintains.

This definition was missing until round 7, and its absence had already cost something. The
reference example in `examples/library/` declared `responses: [200, 403, 409, 412]` while one of
its own steps returned `500`. The card contradicted itself, in the document used to teach the
format, and nothing noticed because nothing compared the two lists. Undefined fields do not rot —
they also cannot be checked, which is the same statement seen from the other side.

**`parameters[]` — what the operation does to what it was sent.** Not every parameter means what
it appears to mean, and the gap is invisible in the response:

```yaml
parameters:
  - name: take
    handling: clamped
    range: [1, 100]
    note: A caller asking for more receives the maximum, and is not told
  - name: tenant
    handling: decorative
    note: The real tenant comes from the caller's identity; this is for readable URLs
```

`handling` is one of `clamped` · `defaulted` · `normalised` · `decorative`, and all four make the
same statement: **what you sent is not what was used.** The reason to write it down is not
tidiness. A caller who asks for 5000 records, receives 100, and is told nothing will conclude the
data ran out — and a card that stayed silent let it happen.

`quota` does not cover this: it is about how often you may call, not about what happens to what
you sent. Validation is not one of the four kinds, because validation *rejects*, and a rejection
is already a violated step with an error code.

**Checked:** a parameter declared `decorative` must appear in the interface's `path`, or the
declaration describes nothing (`decorative_parameter_not_in_path`).

**`source` is a human aid and must never be load-bearing.** It may carry a line number — a reader
opening the file is glad of one — but no checker may rely on it. A line number is invalidated by
any insertion above it, and it fails *silently*: the reference keeps resolving, to the wrong line.
This is the same failure as renumbering steps (§5.3), one field over. Where a durable reference is
wanted, name a file and a symbol rather than a position.

#### Comparing paths

Two lists of routes that describe identical behaviour will not match textually, so a checker
normalises before comparing. These rules are specified rather than left to each implementation —
otherwise a card that passes one checker fails another, which is the disease the conformance
corpus exists to prevent.

| Difference | Rule |
|---|---|
| Parameter syntax — `{copyId}` · `:copyId` · `<copy_id>` | every parameter becomes a positional placeholder: `/copies/{}` |
| Parameter naming — card says `{copyId}`, code says `{id}` | compare **shape**, not names; names are documentation, not identity |
| Trailing slash | stripped |
| Method case | upper-cased |
| Mount prefix | the compared path is the final one, as served |
| One handler, several methods | one entry per method |

⚠️ Shape comparison has a cost, stated here rather than discovered during a debugging session:
two genuinely different routes can share a shape — `/exports/{}` for a report and `/exports/{}`
for a job. Where that happens the checker cannot tell them apart, and the card must disambiguate
by method or by carrying the literal segment. This is a limit of the mechanism, not a defect in it.

**Per-transport overrides.** When an operation is reachable through more than one transport, the
rules may differ — the same write may be unthrottled over REST and rate-limited over RPC.
`quota`, `concurrency` and `actors` may be overridden inside a specific interface; the top-level
value is the default.

`contract_version` records what is promised outward. When versioning lives in a media type rather
than in the path, this field is the only place it is visible.

### 5.8 Data, provenance, reversibility

| Field | | Meaning |
|---|:--:|---|
| `data.entities` | ⬛ | Tables / entities the operation touches |
| `data.fields_touched` | ⬜ | Specific fields |
| `data.migrations` | ⬜ | Migrations the operation depends on |
| `provenance` | ⬛ | `{ activity_kind: <kind> }` or `none`. Explicit — otherwise the checker demands an audit test where nothing is recorded |
| `reversibility` | ⬛ | `{ reversible_via: <id> }` · `reversible` · `irreversible` · `not_applicable` |
| `sensitivity` | ⬜ | `{ response_contains_secret, disclosure, storage, logging_rule }`. `disclosure` ∈ `one_time` · `repeatable` · `never` |
| `consumer_boundary` | ⬜ | `{ owner, our_role, adr }` — when the scenario belongs to another system |
| `taxonomy_refs` | ⬜ | Links to business concepts / a controlled vocabulary |
| `adr` | ⬜ | Decision records that justify the operation. The one link from *why* to *what implements it* |

> **Why `reversibility` is required.** An irreversible operation needs different UX (confirmation),
> a different test (the guard) and often a different permission. Without an explicit field, telling
> a hard delete from a soft retire requires reading the implementation.
>
> **And why `not_applicable` had to exist.** An operation that produces no effect has nothing to
> reverse. Until round 7 the enum offered no true answer for a read, so both read-only cards in
> this project said `reversible` — which answers a different question than the one asked. Neither
> author was careless; the field is required, and the format supplied nothing true to put in it.
> **A format that demands an answer must offer one that is true**, or it manufactures the exact
> falsehood it exists to prevent. Claiming `reversible` on an operation that writes nothing is now
> a warning (`reversibility_overstated`).
>
> **Why `sensitivity` matters.** An operation that returns a secret once states one rule for three
> consumers at the same time: the UI must not show it twice, the gateway must not log it, the test
> must not print it.

### 5.9 Tests and gaps

```yaml
tests:
  - id: <TestClass.TestName>        # ⬛ a real name, not an aspiration
    covers: <step-id | [step-id,…]> # ⬛
    level: unit|integration|ui|contract   # ⬛

coverage_gaps:
  - step: <step-id>
    gap:  <what is missing>
```

`coverage_gaps` starts as a human judgement and later becomes automatic: a step with no entry in
`tests[]` becomes a gap line.

**What a gap means.** A gap names a *specific* missing proof, not the absence of all proof. A step
may legitimately carry both a passing test and a gap — "there is a UI test, but nothing asserts the
secret stays out of the logs" is one sentence describing both. A checker therefore cannot decide
whether a gap is still true; the text is prose, and prose is for the reader.

**Two shapes of `tests[].id` are permitted**, because test runners disagree about what identifies
a test:

```
CheckoutTests.blocked_member_cannot_borrow          class-and-method
CirculationDesk.test.tsx:shows_reason_when_blocked  file-and-name
```

A checker resolves an id against a test report by matching, in order: `classname.name` exactly;
then the bare name; then, for the file-and-name shape, the name with the file part used only to
disambiguate. Matching is always on the whole id, never a substring — a checker that guesses is a
checker that lies. **An id matching several report entries — a parametrised family — is satisfied
only if every one of them passes.** One green case out of five is how coverage becomes decorative.

---

## 6. Keeping cards honest

1. **Cards are written from measurement, not memory.** Every `source` is verified by opening the
   file. A card written from recollection is the artifact that teaches falsehood.
2. **`id` and step ids are immutable.** Renaming means a new operation plus `deprecated` on the old.
3. **`maturity` never outruns evidence.** `tested` requires a non-empty `tests[]`; `in_production`
   requires a recorded environment.
4. **A card disagreeing with the code is a defect of the card** until proven otherwise. Even when
   the workflow is specification-first, a card must describe what the system *is*, and mark the
   intended difference explicitly.
5. **Withdrawn decisions get a tombstone on the line**, not a deletion.

---

## 7. The three checks

The format only pays for itself with an automated checker. Three invariants:

1. **No wild endpoints** — every route in the code is declared by some card.
   The checker does not read the code to learn this. The checked repository states what it
   registers, in a **route inventory** ([`schema/route-inventory.schema.json`](schema/route-inventory.schema.json)),
   and the checker compares sets. A runtime dump of the framework's own route table is the honest
   way to produce one: it cannot disagree with what the application serves, and it is immune to
   routes generated from a template — which is where the two obvious designs, a marker in the code
   and a static parser, both fail. The reasoning is in
   [`design/route-conformance.md`](design/route-conformance.md).
   Routes that are deliberately not operations — health probes, metrics, generated documentation —
   are excluded in [`usedesign.config.yaml`](schema/config.schema.json), and every exclusion states
   a reason and reports what it hid. An exclusion nobody had to justify is one nobody revisits.
2. **No unproven steps** — every step is covered by at least one test that **exists, ran, passed
   and was not skipped**, or appears in `coverage_gaps`.
   A card naming a test proves nothing on its own: the test may have been renamed last spring, or
   skipped since it started flaking. The checker consumes a **JUnit XML report** from the run being
   checked — the format already exists, so unlike the route inventory nothing new is invented, and
   nothing is executed by the checker itself. A skipped test is an error and a *louder* one than an
   absent test: it keeps its name in every report, so name-matching alone would confirm a step
   nobody has exercised in months. Without a report, this check is reported as **not run**, never
   as passed, and the step-level finding degrades to a warning.
   ⚠️ **Freshness is procedural, not mechanical.** A report from three commits ago will happily
   confirm a step whose code changed this morning. Run the check in the same CI job as the suite,
   on the report that job just produced. No checker can enforce this, which is exactly why it is
   written down. Reasoning: [`design/step-coverage.md`](design/step-coverage.md).
3. **No inflated maturity** — the claimed level is backed by the evidence it requires.
   Three claims of different natures (§5.2), checked differently: the `implemented` path must
   exist in the repository; `tested` and above must have a named test that passes in the report;
   `deployed` cannot be verified at all, so it **expires** — dated, it goes stale after a horizon;
   undated, it is reported as a claim that can never be re-examined. Both are warnings: a checker
   that fails a build for a claim being *old* is a checker somebody switches off.
   Reasoning: [`design/maturity-evidence.md`](design/maturity-evidence.md).

Without check 3 in particular, cards drift into aspiration within a couple of months.

**Where the schema stops and the checker starts.** A schema validates *form*: that a field is
present, that a value is one of a set, that claiming `in_production` names an environment. It
cannot validate *meaning* — nothing stops `tested: "planned for Q3"` from satisfying the rule
that a tested note exists. That gap is not a defect to be patched in the schema; it is the
boundary. Confirming that a card's claims match reality — that its listed tests exist and pass,
that its routes are the routes the code registers — is the checker's job, and it is the reason
the checker is on the roadmap rather than the schema being made ever cleverer.

---

### 7.4 Check 4 — no imagined storage

The same shape as check 1, one layer down. The storage says what it is — which stores exist, what
they are keyed by, which secondary indexes they carry — and the cards are compared with that.
Nothing reads a repository class, an ORM mapping, or a migration file.

```yaml
data:
  entities: [request]          # the logical noun, unchanged
  storage:
    - store: abdominal-requests-*   # a PATTERN, never a literal name
      keyed_by: [RequestId]
      via_index: gsi-owner-status   # naming one promises that removing it breaks this operation
```

**`store` is a pattern because store names carry their environment.** A card naming
`…-dev` is true in one place and false in every other, and the checker would either bless the lie
or fail the honest card, depending on which dump it was handed.

| Finding | Means |
|---|---|
| `unknown_store` | the card names a store the storage does not have |
| `store_key_mismatch` | the claimed key is not the store's key |
| `unknown_index` | the index the operation depends on is gone — the ordinary failure, since dropping an index is a cost decision taken far from the card |
| `undescribed_store` (warning) | a store no card accounts for — the mirror of a wild endpoint |
| `storage_inventory_missing` | the check **cannot run and is not considered passed** |

**What this check deliberately does not do: verify which fields an operation writes.** A
schemaless store declares its keys and indexes and knows nothing about the rest, so checking
`fields_touched` against it would be a promise the storage cannot keep — and a check that cannot
fail is not a check. This is stated rather than left implicit because `fields_touched` and
`migrations` sat in the format for eleven rounds, unfilled and unchecked: fields nobody could be
wrong about, which §5.7 says nobody maintains. They remain prose.

The measurement that produced this check is worth recording. Before it, `data.entities: [request]`
was the whole of what a card said about storage — one logical noun, true by construction. The
first run against a real system found nine stores of which **none** was accounted for by any card,
and writing four honest claims immediately revealed that publishing an item touches **two** stores,
not the one the card had named for months.

### 7.5 Check 5 — the form matches its contract

The first check whose reference is **authored rather than measured**. A *form contract*
(`usedesign_form: 1`, schema `form-contract.schema.json`) states what the owner decided a screen
must show, per entity state; a *form inventory* (`form-inventory.schema.json`) states what the
rendered screen actually carries — produced by rendering the real components in a test, never by
parsing their source. Check 5 holds the two against each other, both ways.

```yaml
usedesign_form: 1
id: abdominal.workout.session-nav
screen: SessionNavPanel
entity: workout_progress        # the state vocabulary is the entity's, computed from its cards
presents:
  - field: session-summary      # the machine anchor: a data-* marker the rendered screen carries
    shows: итог — статус, подходы, тоннаж
    when: [finished, partial, abandoned]
controls:
  - control: finish-progress
    calls: abdominal.progress.finish
    shown_when: [active]
removed:
  - control: clear-progress     # a decision is only real while something enforces it
```

| Finding | Means |
|---|---|
| `element_missing` / `control_missing` | the contract is ahead of the code — the product's TODO list, printed by every build |
| `control_out_of_state` | a control leaked outside its `shown_when` |
| `removed_control_present` | a control the owner removed came back |
| `shown_when_conflicts_transition` | the contract shows a control in a state its operation cannot depart from — the reference here is the **card**, so the form and the screen can drift together and still be caught |
| `undescribed_element` (warning) | rendered, accounted for by nobody — the mirror of a wild endpoint, and the queue of decisions the owner has not made yet |
| `form_inventory_missing` | cannot run, **NOT considered passed** |

Check 5 is opt-in through `forms:` in the config: a backend repository has no forms and its
silence is not a failure. What it deliberately cannot see, stated rather than discovered:
**content** (that the summary includes tonnage — the anchor is visible, the text is not) and
**behaviour** (that "next" opens strictly the next one) — both belong to ordinary tests, and the
contract carries them as prose for the human who writes those tests.

The measured rule behind `shown_when`: a control is available exactly in the states of the called
operation's `data_transition.from`. Two screens, zero exceptions, before it was written down.

**Grouping by purpose.** A contract may carry `groups:` — how the owner groups the screen:
headers, footers, tables, toolbars, menus, and which elements and controls sit in each. Array
order **is** the group order (a separate order key would be a duplicate that drifts); membership
is to the **nearest** group — a flat model, not a tree, twice refuted by measurement. A group's
anchor may coincide with a `presents` field: a container that itself shows content, which is how
real headers measure. Membership against the code is **authored, not yet verified** — the
inventory records anchors flat, so check 5 proves a group's anchor exists but not who sits
inside it; a declared limit, like `shown_when_rule`.

```yaml
groups:
  - group: session-foot
    role: footer            # header | footer | section | table | list | toolbar | menu
    contains: [main-progress, finish-progress, finish-error]
```

**Validating the contract itself.** Form contracts pass through `validate` like cards do, told
apart by the `usedesign_form: 1` marker. Measured on 0.5.0, which had no such validation: a
contract with `presents` misspelled as `presnts` lost its whole "must show" section silently,
and every line of it resurfaced as somebody else's `undescribed_element` warning — the typo did
not fail, it changed whose problem it looked like. The rules are hand-rolled with named codes,
in both implementations, so the two agree on *what* is wrong:

| Finding | Means |
|---|---|
| `unknown_field` | a key the format does not know — the typo named as itself |
| `missing_required_field` | `usedesign_form` / `id` / `screen` / `presents`, or a required key inside a line |
| `malformed_form_id` | the id is not `<area>.<object>.<name>` |
| `duplicate_element` / `duplicate_control` / `duplicate_group` | one anchor, two lines — the inventory can prove it only once |
| `removed_also_required` | one document both requires and forbids a control — self-contradiction, not a TODO |
| `unknown_group_member` | a group names a member the contract never declares |
| `element_in_two_groups` | an element renders in one place; two claims cannot both hold |
| `invalid_enum_value` | a group `role` outside the vocabulary |
| `undescribed_form` (warning) | `opens` points at a contract outside the validated set — honest incompleteness, the counterpart of `undescribed_counterpart` |

### 7.6 Scoping the checks per repository

`checks: [5]` in the config limits which checks run. A frontend repository serves no routes and
owns no tables; running checks 1–4 there would fail on inputs that cannot exist, and a check that
always fails gets ignored — the report-mode lesson one level up. Scoping is declared in the
config, visible in review; **within the declared scope, "cannot run" still means "not passed"**.

## 8. Maturity of this specification

v0.2 was reached by writing cards for eight real operations of a production system and recording
where the format broke:

| Round | Areas exercised | Fields the format was missing |
|---|---|---|
| 1 | CRUD, async ingestion, curation UI, read-only helper | `async_execution`, `concurrency`, `serves_step` |
| 2 | RPC protocol, security administration, cross-system boundary | `transport`, `quota`, `reversibility`, `sensitivity`, `consumer_boundary`, `contract_version` |
| 3–5 | Building the three checks — *using* cards instead of writing more of them | None |
| 6 | A second implementation, written from this document and the schema | None |
| 7 | Natural-language question answering, undo of a lifecycle change, paged search, attachments | **Four, listed below. `steps[]` is affected, so v1.0 is not reached** |
| 8 | Repairing round 7 — the four gaps closed, cards rewritten against the repairs | **Five**, all optional: `outcomes[]`, `continuation`, `parameters[]`, `to` as a set, `not_applicable` |
| 9 | **A different system entirely** — first round on a repository the format had never seen | Three optional fields, one normalisation bug, one rule fitted to its own example |
| 10 | **A screen against a described operation** — one real button traced from control to pixel | One, optional: `covers_outcomes{}` (§5.7) |
| 11 | **Four more screens** — a form, a service operation, and a bulk pair | None new. Round 10's own rule corrected twice: job states out of the vocabulary, per-item failures in; plus `outcomes_indistinguishable` |
| 12 | **The layer below** — cards against a live schemaless store | One, optional: `data.storage[]`, plus check 4 (§7.4) |
| 13 | **The layer above, inverted** — the owner authors form contracts first; the rendered screens answer | Two optional artifact kinds: the form contract and the form inventory, plus check 5 (§7.5) |
| 14 | **The contract's own shape** — a planted `presnts` typo passed 0.5.0 silently; plus grouping by purpose (headers, footers, tables) | One optional field: `groups[]`; validation of form contracts with named codes (§7.5) |

**Criterion for v1.0:** not "no more breakage" — untouched areas will always break something —
but *a round that changes only optional fields, never required ones*. Rounds 9, 10 and 11 all
meet it; three consecutive qualifying rounds on foreign ground is when the claim starts to mean
something.

⚠️ Round 11 is the first round whose findings were mostly about **the previous round's rule**
rather than the format. A rule written from one measurement fits that measurement: `covers_outcomes`
was built from a button that ends immediately, and it failed the first card whose operation keeps
living afterwards. Worth stating plainly, because it is the same failure as axis F in round 9 —
the second occurrence of a pattern, not a one-off.

### 8.0 What a different system found

Rounds 1–8 all ran against one system. Round 9 pointed the tool at an unrelated codebase, and the
first defect surfaced **before a single card was written**:

- **The checker was silently wrong, not merely limited.** That API writes actions the AIP-136 way,
  `POST /progress/{id}:finish`, and path normalisation read the suffix as a parameter. Eight of its
  routes collapsed into two shapes; declare one and the checker calls all of them declared, then
  reports a clean run. See `design/route-conformance.md` §4a.
- **A rule written from one example was fitted to that example.** Axis F required
  `continuation.after` to name an outcome, because the single case in hand suspended on one. A
  request thread suspends on a *job state* and waits there for a person — the axis held, its check
  did not.
- **Two assumptions failed together**: one call, one record, one ending. A bulk endpoint reports
  per-item failures inside a success, and one route carries several operations chosen by a request
  field. Both are ordinary REST; the format called the first unwritable and the second a defect.
  See `design/bulk-and-dispatch.md`.

And two things held that had been argued for rather than demonstrated: `data_transition.to` as a
set fitted an operation whose destination comes from *completeness* rather than history, and the
separation of axes E and F stopped being an argument the moment one record needed both.

None of this was findable on the original system. **A format tested on one codebase is partly a
description of that codebase**, and the only way to learn which part is to take it somewhere else.

### 8.0a What building a gate proved

Round 9 checked an unfamiliar system by hand. Wiring the same checks into that repository's CI
produced four findings that no amount of design could have supplied:

**Cards cannot live apart from the code.** The specification has always said so; CI made it a
fact. Both repositories were private, and a CI job's token reaches only its own repository —
cards kept elsewhere need a cross-repository secret, and a secret that exists for documentation
is the first thing removed when permissions are tightened. The check would then go quiet, which
is the failure mode this project exists to prevent.

**A tool that cannot be installed cannot be adopted.** With no published package, the gate clones
the tool and builds it from source on every run: three extra steps and a dependency on somebody
else's `main`. Publishing stops being roadmap decoration and becomes a precondition.

**The report format is a real barrier.** .NET emits TRX, not JUnit. A one-line package
(`JunitXml.TestLogger`) closes it — but it is a change to the checked repository, and every
ecosystem will have its own version of that line.

**A gate on a partly-described system must not fail the build.** 108 of 113 routes were described
by nobody. A strict gate would fail every build over honestly-acknowledged incompleteness, and be
switched off within a day — teaching people to hide incompleteness rather than declare it. Report
mode is the honest setting, with the cost that **report mode is what everybody ignores**; the
condition for switching to strict belongs in the file itself, so it cannot be quietly forgotten.

A fifth thing was confirmed rather than found: cards name tests in short form, the native JUnit
logger writes them fully qualified, and the matching rules held across a change of report
generator — until then they had only ever been tested against output the same author produced.

### 8.1 What round 7 broke, and what round 8 did about it

**All four gaps are closed, and a fifth was found while closing them.** The repairs are below;
the original failures are kept because a specification that hides what it once could not say
teaches people to trust it further than they should.

| Gap | Repair | Section |
|---|---|---|
| A terminal outcome that is neither success-as-usual nor a violation | `outcomes[]` — the `job_states` machinery, unlocked from axis E | §5.2a |
| An operation that stops and waits for a person | `continuation` — **axis F** | §5.2b |
| A target state taken from the record's history | `data_transition.to` may be a set, with `determined_by` | §5.2 |
| What an operation does to its own request | `interfaces.*.parameters[]` with `handling` | §5.7 |
| **Found while repairing:** no honest `reversibility` for a read | `not_applicable` added to the enum | §5.8 |

Four new checks came with them, and all four need nothing but the card itself:
`undeclared_response` · `continuation_without_outcome` · `decorative_parameter_not_in_path` ·
`reversibility_overstated`.

**What repairing cost the existing corpus: nothing.** No required field changed, and every card
written before round 7 still validates. By the v1.0 criterion this round qualifies — but it would
be self-serving to count a repair against a criterion about *breakage*. The honest reading:

> Round 7 broke the format in five places. The repairs are additive, which is the good news.
> Whether they are *right* is decided by the next round that has not seen them.

### 8.2 The original failures, as recorded

Round 7 wrote cards for four areas no earlier round had touched, and four things could not be
said honestly. They are listed here rather than quietly fixed, because a specification that hides
what it cannot express teaches people to write cards that lie.

**① A terminal outcome that is neither success-as-usual nor a violation.** A question-answering
operation returns *"the catalogue has nothing on this"* — with a success status, having done
everything it was asked. It is not a violated step: no rule was broken. It is not a notice: the
whole shape of the response changes. Writing it as `on_violation` with a success HTTP code lies
twice.

The machinery already exists: `async_execution` carries `job_states` and `terminal`. It is
**locked inside axis E**, available only when the response does not mean the work is done. What
is missing is the same idea for an operation that answers immediately.

**② An operation that stops and waits for a person.** The same operation can answer *"your
question is ambiguous, here are the candidates"*; the next call carries the chosen candidate and
continues where the first stopped. This is not axis E: an async job progresses on its own and
`observe_via` says where to watch it. Here nothing progresses. **A human decides, or nothing
happens.** No existing field expresses this, not even badly.

**③ A target state taken from history rather than from a rule.** An operation that undoes a
retirement returns the record to *the state it was in before* — which may be draft or published,
depending on that record's own past. `data_transition` requires `{from, to}` as two constant
strings. `to: draft` is false for half the records; `to: previous_state` names a variable where a
value belongs, and nothing can check it.

Undo operations as a class have this shape: **they return the system to where it was, not to
where the card says.**

**④ What an operation does to its own request.** Two variants, one gap:

- a paging parameter above the maximum is **silently clamped**, not rejected. The caller who
  asked for 5000 and received 100 will conclude the data ran out;
- a path parameter is **decorative** — the real value is derived from the caller's identity, and
  substituting anything else changes nothing.

Both must be written down, and there is nowhere to write them. `quota` is about call frequency,
not about substituting a parameter.

Three of them — ① and both halves of ④ — are one gap seen from three sides: **the format speaks
well about what an operation does to the data, and poorly about what it does to its own request
and its own response.** One decision closes all three, and it probably looks like `job_states`
generalised out of axis E.

Nothing here is scheduled. A specification that promises fixes on a date is making the claim
check 3 exists to refuse.

### A note on this document's own consistency

Before publishing, this specification was checked against its own schema and examples — the same
exercise it asks of everyone else. It failed in seven places: a field present in the schema and
in an example but described nowhere here; a rule stated in prose that the schema did not enforce;
one term spelled two ways across two files.

All seven are fixed. The point of recording it is not modesty. A specification is a description
like any other, and descriptions drift from what they describe — including this one, including
while its author is writing about drift. That is the argument for check number three.
