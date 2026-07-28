# Fixture — library service

A stand-in codebase for exercising **check 1: no wild endpoints**. Nothing here runs; the files
exist so the check has something real-shaped to work against.

| File | What it is |
|---|---|
| `src/routes.ts` | Illustrative source. Shows where the inventory entries come from. |
| `route-inventory.json` | What a runtime dump of the framework's route table produces. **This is the checker's input** — see [`design/route-conformance.md`](../../../design/route-conformance.md) §3. |
| `usedesign.config.yaml` | Card locations and the exclusions for routes that are deliberately not operations. |

The cards it is checked against are the five in [`examples/library/`](../../../examples/library/).

## This fixture is expected to FAIL

Eleven routes are served. Four are excluded as infrastructure. Five are declared by the example
cards. **Two are declared by nobody:**

```
POST   /v1/admin/members
DELETE /v1/admin/api-keys/{}
```

Both were born inside the `for` loop in `src/routes.ts`, which registers create-and-delete over
two admin resources. Two of those four routes have cards; two do not. Nobody wrote them, nobody
decided them, and nobody would find them by reading the source — the loop reads as two
registrations, not four.

That is the whole argument for this design in one fixture:

- a **marker in the code** (`// usedesign: <id>`) has no line to sit on here;
- a **static parser** sees two registrations and reports no problem;
- a **runtime dump** sees all four, and the set comparison names the two nobody claimed.

The failing case is the deliverable. A fixture that passed would demonstrate only that a checker
can agree with itself.

## What passing looks like

Add cards for the two routes — or delete the routes. Both are real answers, and the check does not
prefer either one. It only refuses to let the choice go unmade.
