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

---

## 2. Core principles

1. **One file, one operation.** The file name equals the operation `id`. No collections.
2. **Axes never merge.** Maturity, execution steps, data lifecycle, version and async job state
   are five different things. Systems that squash them into a single `stage` field fall apart.
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

## 4. The five axes of life

This is the heart of the format. Each axis changes at its own pace and is owned by different
artifacts.

| Axis | Field | What it describes | Changes |
|---|---|---|---|
| **A · Maturity** | `maturity` | How far the operation is built: conceived → … → in production | Weekly, as work lands |
| **B · Steps** | `steps[]` | What happens during execution, including failure branches | Only when behaviour changes |
| **C · Data lifecycle** | `data_transition` | What the operation does to the state of the record | Almost never — it is the domain model |
| **D · Version** | `since` | Since which migration / release the operation behaves this way | Every release |
| **E · Async job** | `async_execution.job_states` | The life of background work started by the operation | Only for async operations |

**Why they must stay apart.** A test attaches to a *step* (axis B) and by existing moves
*maturity* (axis A). A screen covers a *set of steps*. A migration attaches to *neither* — it
belongs to axis D, which is exactly why migrations end up orphaned in every traceability scheme
that has only one stage field.

**Axis B is not axis C.** Steps are states of *executing the operation*; the data transition is
the state of *the record itself*. A publish operation has its own steps **and** moves a record
from draft to published. Conflating the two is the second classic mistake.

**Axis E is neither.** A job may reach `succeeded` while the record it produced stays `draft`.

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
| `maturity_evidence` | 🔶 | `{ implemented: <path>, tested: <n tests>, deployed: <env> }`. Required from `implemented` upward — **a level may not be claimed without its evidence**. A `conceived` or `designed` operation has nothing to prove yet |
| `data_transition` | ⬜ | `{ from, to }` — axis C. `null` for read-only operations and for writes that do not change state |
| `mutates` | 🔶 | Fields changed, when `data_transition` is null but the operation still writes |
| `since` | ⬜ | `{ migration, note }` — axis D. The one place where migrations stop being orphans |

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
  ui:   { transport: ui, screen, control, covers_steps[], source }
```

At least one interface is required. Each interface declares its `transport`
(`http_rest` · `json_rpc` · `in_process` · `ui`) — without it, `on_violation.http` is meaningless
for protocols whose errors are numeric RPC codes.

`ui.covers_steps` is the mechanism that makes UI/API drift visible: if a screen claims to cover a
step that does not exist, the checker fails.

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
| `reversibility` | ⬛ | `{ reversible_via: <id> }` · `reversible` · `irreversible` |
| `sensitivity` | ⬜ | `{ response_contains_secret, disclosure, storage, logging_rule }`. `disclosure` ∈ `one_time` · `repeatable` · `never` |
| `consumer_boundary` | ⬜ | `{ owner, our_role, adr }` — when the scenario belongs to another system |
| `taxonomy_refs` | ⬜ | Links to business concepts / a controlled vocabulary |
| `adr` | ⬜ | Decision records that justify the operation. The one link from *why* to *what implements it* |

> **Why `reversibility` is required.** An irreversible operation needs different UX (confirmation),
> a different test (the guard) and often a different permission. Without an explicit field, telling
> a hard delete from a soft retire requires reading the implementation.
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
2. **No unproven steps** — every step is covered by at least one test, or appears in
   `coverage_gaps`.
3. **No inflated maturity** — the claimed level is backed by the evidence it requires.

Without check 3 in particular, cards drift into aspiration within a couple of months.

**Where the schema stops and the checker starts.** A schema validates *form*: that a field is
present, that a value is one of a set, that claiming `in_production` names an environment. It
cannot validate *meaning* — nothing stops `tested: "planned for Q3"` from satisfying the rule
that a tested note exists. That gap is not a defect to be patched in the schema; it is the
boundary. Confirming that a card's claims match reality — that its listed tests exist and pass,
that its routes are the routes the code registers — is the checker's job, and it is the reason
the checker is on the roadmap rather than the schema being made ever cleverer.

---

## 8. Maturity of this specification

v0.2 was reached by writing cards for eight real operations of a production system and recording
where the format broke:

| Round | Areas exercised | Fields the format was missing |
|---|---|---|
| 1 | CRUD, async ingestion, curation UI, read-only helper | `async_execution`, `concurrency`, `serves_step` |
| 2 | RPC protocol, security administration, cross-system boundary | `transport`, `quota`, `reversibility`, `sensitivity`, `consumer_boundary`, `contract_version` |

**Criterion for v1.0:** not "no more breakage" — untouched areas will always break something —
but *a round that changes only optional fields, never required ones*.

### A note on this document's own consistency

Before publishing, this specification was checked against its own schema and examples — the same
exercise it asks of everyone else. It failed in seven places: a field present in the schema and
in an example but described nowhere here; a rule stated in prose that the schema did not enforce;
one term spelled two ways across two files.

All seven are fixed. The point of recording it is not modesty. A specification is a description
like any other, and descriptions drift from what they describe — including this one, including
while its author is writing about drift. That is the argument for check number three.
