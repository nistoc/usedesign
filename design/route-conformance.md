# Design note — check 1: no wild endpoints

**Status:** design, not yet specified. Written before the implementation on purpose.
**Question it answers:** how can a checker know, mechanically, that every route the code registers
is declared by some card — without becoming a per-framework parser and without producing false
alarms that train people to ignore it.

---

## 1. Why this check is the hard one

Checks 2 and 3 look only at the cards. A step without a test, a maturity level without its
evidence — both are answerable by reading the card set and the test names it claims. They need no
knowledge of the codebase.

Check 1 is different in kind: it compares **the card set against the running truth of the code**.
That comparison is where the format meets reality, and it is the only place where the format can
still be found insufficient. Everything else is bookkeeping.

It also carries the highest cost of being wrong. A checker that reports endpoints that do not exist,
or misses endpoints that do, gets switched off within a week — and a switched-off checker is worse
than none, because the catalogue keeps its authority while losing its correctness.

## 2. Three ways to link a card to code, and why two of them fail

### 2.1 By file and line — what the format does today

Cards currently carry `source: src/loans/routes.ts:58`.

**This does not survive contact with a repository.** A line number is invalidated by any insertion
above it — an import, a comment, a blank line. The reference does not break loudly; it silently
starts pointing at a different line, and a checker that trusted it would confirm a route that moved
away months ago.

This is the same failure the specification already warns about for step ids (§5.3: renumbering to
keep a list tidy silently moves every external reference). The format made the identical mistake
one field over. Line numbers are a **convenience for humans reading the card**, and must never be
load-bearing for a machine.

### 2.2 By marker in the code

Put the operation id in the code — a comment or an attribute above each route registration:

```ts
// usedesign: library.loan.checkout
router.post('/v1/copies/:copyId/checkout', checkout)
```

Attractive: it is exactly the principle the format preaches (the artifact declares what it
implements), it is language-agnostic to find, and it survives refactoring because it travels with
the code.

It fails on the case that matters most. Routes are frequently **not written one by one**. A
generic CRUD registration that loops over eleven artifact kinds produces dozens of routes from a
single statement — measured in a real system: ~180 routes from ~90–110 operations, the difference
being template expansion. There is no line above which to put a marker per route, because the
routes do not exist in the source at all. They exist only after the loop runs.

Markers stay useful as an *optional* aid. They cannot be the mechanism.

### 2.3 By comparing route sets

Cards declare method + path. Something enumerates what the code registers. The checker compares
the two sets and reports the difference in both directions:

- in the code, in no card → **wild endpoint**, check 1 fails;
- in a card, not in the code → **phantom**, the card describes something that does not exist.

No line numbers. No markers. Template expansion is invisible to the checker, because it compares
the *result* of registration, not its source text.

This is the mechanism. The rest of this note is about how the enumeration happens and how the
comparison avoids false alarms.

## 3. Where the route list comes from — and why usedesign should not produce it

Enumerating routes requires framework knowledge: Express, FastAPI, Spring, ASP.NET Minimal APIs
and Rails each register routes differently, and a tool that parses all of them is a tool that is
permanently behind. Worse, static parsing is precisely what fails on generated routes — the case
from §2.2 that made markers unworkable.

**The design decision: usedesign defines a route inventory format and consumes it. It does not
extract routes.** Producing the inventory belongs to whoever owns the codebase, by whichever of
two means suits them:

| | How | Cost | Handles generated routes |
|---|---|---|---|
| **Runtime dump** | ask the running application for its route table — most frameworks expose one (ASP.NET `EndpointDataSource`, Express router stack, FastAPI `app.routes`, Flask `url_map`, Spring `RequestMappingHandlerMapping`) | needs the app to boot | ✅ exactly — the table *is* the expansion |
| **Static extraction** | parse registration sites | no boot; CI-friendly | ❌ not without interpreting the registration code |

The runtime dump is the honest default and should be recommended: it is a few lines per framework,
it cannot disagree with what the application actually serves, and it is immune to every parsing
problem above. Static extraction is a fallback for codebases that cannot be booted in CI.

Making the inventory an explicit, boring artifact has a second benefit: it is reviewable. A human
can read it, a diff shows when routes appear, and the checker's input is inspectable when it
reports something surprising.

## 4. The comparison is not string equality

Two route lists that describe identical behaviour will not match textually. The checker must
normalise before comparing, and each normalisation rule is a decision that has to be written down
rather than discovered by the person debugging a false alarm.

| Difference | Example | Rule |
|---|---|---|
| Parameter syntax | `/copies/{copyId}` · `/copies/:copyId` · `/copies/<copy_id>` | normalise every parameter to a positional placeholder: `/copies/{}` |
| Parameter naming | card says `{copyId}`, code says `{id}` | compare **shape**, not names — names are documentation, not identity |
| Trailing slash | `/v1/loans` vs `/v1/loans/` | strip, they are the same route |
| Method case | `POST` vs `post` | upper-case |
| Mount prefix | app mounts a router at `/v1` | the inventory records the **final** path; a runtime dump gets this right for free |
| Multi-method registration | one handler for `GET` and `HEAD` | one inventory entry per method |

⚠️ **Shape comparison has a real cost, stated here rather than discovered later:** two genuinely
different routes can share a shape — `/users/{}/follow` and `/users/{}/block` do not, but
`/exports/{}` for a report id and `/exports/{}` for a job id do. Where a collision is possible the
checker cannot tell them apart, and the card must disambiguate by method or by carrying the literal
segment. This is a known limit of the mechanism, not a bug to be fixed by a cleverer matcher.

## 5. Routes that are deliberately not operations

Every real application serves routes that no card should describe: health probes, metrics, the
generated API-documentation UI, static assets, framework-internal redirects. Without a way to say
so, check 1 reports them forever and the check is abandoned.

Three candidate answers:

1. **Exclusion patterns in a config file** — simple, explicit, reviewable in one place; the risk is
   that a broad pattern (`/internal/*`) silently swallows real operations added later.
2. **A card with a dedicated maturity level** — `not_an_operation`, giving infrastructure routes the
   same shape as everything else; honest but heavy, and it puts noise in the catalogue.
3. **A marker in code** — back to §2.2, and it breaks on the same generated-route case.

**Recommendation: (1), with the mitigation that the checker reports what each pattern excluded.**
An exclusion that hides nothing is dead and should be removed; an exclusion that starts hiding
twelve routes instead of two is a change worth seeing. Silence is what makes exclusion lists
dangerous, and a count is cheap.

This is the first artifact in the project that is *configuration* rather than description, and it
should stay the only one. It needs a home: `usedesign.config.yaml` at the root of the checked
repository, holding the inventory location and the exclusions — nothing else.

## 6. Consequences for the format

This design was reached before implementation precisely so that its demands on the format arrive
now, while there are five example cards, rather than after a hundred.

| # | Demand | Kind of change |
|---|---|---|
| C1 | `source` must not be load-bearing: state in the spec that it is a human aid, that line numbers are permitted but never used by a checker, and that a file-and-symbol reference is preferred | wording in §5.7 — **no field changes** |
| C2 | Path normalisation rules (§4) must be specified, not left to each implementation — otherwise a card that passes one checker fails another, which is the disease the conformance corpus exists to prevent | new subsection in §5.7 |
| C3 | The route inventory format must be specified: a JSON array of `{method, path, source?}` | new file `schema/route-inventory.schema.json` |
| C4 | Exclusions need a defined home (§5) | new, minimal config file |
| C5 | Conformance cases for the comparison itself: shape mismatch, phantom route, wild route, excluded route | additions to `tests/conformance/` |

**None of these change a required field of the card.** By the v1.0 criterion stated in SPEC §8 —
*a round that changes only optional fields, never required ones* — this round passes. That is a
result about the format, and it is worth as much as the checker itself: the first exercise that
was not a card-writing exercise did not break the card.

## 7. What the prototype must demonstrate

To be worth anything, the first implementation has to be exercised against the case that killed the
two rejected designs:

1. a fixture whose routes are registered **individually** — the easy half;
2. a fixture whose routes are **generated from a template over a collection** — the half that
   defeats markers and static parsing, and the reason the inventory is a runtime artifact;
3. a wild route (in the inventory, in no card) → check 1 fails with a diagnostic code;
4. a phantom route (in a card, not in the inventory) → reported separately, because it is a
   different defect: not an undocumented endpoint but a card describing something that is gone;
5. an excluded route → passes, and the exclusion reports what it hid.
