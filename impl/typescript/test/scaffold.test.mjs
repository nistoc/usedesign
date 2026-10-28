/**
 * Golden tests for `usedesign scaffold`, black box: the built CLI is run in a fresh temporary
 * directory that holds a copy of a fixture, with relative arguments, and its stdout and the drafts
 * it writes are compared byte for byte with the files under test/golden/.
 *
 *   npm run test:unit                    compare with the golden files (build first: npm run build)
 *   UPDATE_GOLDEN=1 npm run test:unit    rewrite the golden files from the CLI's current output —
 *                                        then READ every changed file: a golden file is a claim,
 *                                        not a recording.
 *
 * Fixtures: test/fixtures/scaffold/ (openapi.json, usedesign.config.yaml, cards/, and two small
 * documents for the uniform-statuses and the empty case). Goldens: the test/golden/scaffold
 * directories, one per case.
 *
 * One test is not black box: `routes_unaccounted` cannot be reached through the CLI, so the check
 * behind it, unaccountedRoutes in dist/scaffold.js, is called with plans made by hand.
 */
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const cli = path.join(here, "..", "dist", "cli.js");
assert.ok(fs.existsSync(cli), "build first: npm run build");
// The check behind `routes_unaccounted` is called directly: no input makes the CLI reach it.
const { planScaffold, unaccountedRoutes } = await import("../dist/scaffold.js");
const { loadConfig } = await import("../dist/core.js");

const UPDATE = process.env.UPDATE_GOLDEN === "1";

/** Compare `actual` with test/golden/<name>; with UPDATE_GOLDEN=1 write it there instead. */
function golden(name, actual) {
  const file = path.join(here, "golden", name);
  if (UPDATE) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, actual);
    return;
  }
  assert.ok(fs.existsSync(file), `no golden file ${name} — run once with UPDATE_GOLDEN=1, then read it`);
  assert.equal(actual, fs.readFileSync(file, "utf8"), `${name} differs from its golden file`);
}

/** Every file in `dir` against test/golden/<name>/: the same set of names, the same contents. */
function goldenTree(name, dir) {
  const written = fs.existsSync(dir) ? fs.readdirSync(dir).sort() : [];
  const goldenDir = path.join(here, "golden", name);
  if (UPDATE) fs.rmSync(goldenDir, { recursive: true, force: true });
  else assert.deepEqual(written, fs.existsSync(goldenDir) ? fs.readdirSync(goldenDir).sort() : [], `${name}: the set of files differs`);
  for (const file of written) golden(`${name}/${file}`, fs.readFileSync(path.join(dir, file), "utf8"));
  return written;
}

/** A fresh temporary directory holding a copy of the fixture, removed when the test ends. */
function sandbox(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "usedesign-scaffold-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.cpSync(path.join(here, "fixtures", "scaffold"), dir, { recursive: true });
  return dir;
}

function run(cwd, ...args) {
  return spawnSync(process.execPath, [cli, ...args], { cwd, encoding: "utf8" });
}

const DRAFT_OF_COPIES = "TODO.v1-copies.get.op.md";
const SENTINEL = "half-filled by a human — must survive a run without --force\n";

test("scaffold: drafts, stdout and the arithmetic match the golden files", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml");
  assert.equal(r.status, 0, r.stderr);

  golden("scaffold/stdout.txt", r.stdout);
  const drafts = goldenTree("scaffold/drafts", path.join(dir, "drafts"));

  // The arithmetic line `→ d + s + e = total ✓` is the observable half of the invariant behind the
  // `routes_unaccounted` finding. Every route ends in exactly one of drafts / skippedDeclared /
  // skippedExcluded (planScaffold), so no input makes the CLI print the finding; the check itself,
  // unaccountedRoutes, is handed the plans planScaffold would not make in the test below.
  assert.ok(r.stdout.includes("→ 5 + 1 + 1 = 7 ✓"), r.stdout);
  assert.ok(!r.stdout.includes("routes_unaccounted"), r.stdout);

  // Five drafts: GET and POST on one path, the AIP-136 action, and the `-2` suffix of the second
  // route that slugifies to `v1-members`; the declared route and the excluded one are absent.
  assert.deepEqual(drafts.map((f) => f.replace(/\.op\.md$/, "")).sort(), [
    "TODO.v1-copies-checkout.post",
    "TODO.v1-copies.get",
    "TODO.v1-copies.post",
    "TODO.v1-members.get",
    "TODO.v1-members.get-2",
  ]);

  // The statuses differ between routes, so the framework-default warning must NOT fire.
  assert.ok(!r.stdout.includes("statuses_uniform"), r.stdout);
  for (const file of drafts) {
    const body = fs.readFileSync(path.join(dir, "drafts", file), "utf8");
    assert.ok(!body.includes("⚠"), `${file} carries the uniform-statuses marker`);
    for (const field of ["title", "scenario", "maturity", "provenance", "reversibility"]) {
      assert.match(body, new RegExp(`^${field}: FILL_ME`, "m"), `${file}: ${field} is not FILL_ME`);
    }
    assert.match(body, /^actors: \[FILL_ME\]$/m, file);
    assert.match(body, /^data:\n {2}entities: \[FILL_ME\]$/m, file);
  }
});

test("scaffold: a route lost or counted twice is routes_unaccounted", (t) => {
  // commandScaffold prints `routes_unaccounted` and exits 1 when unaccountedRoutes (scaffold.ts)
  // returns a finding, and the ✓ line when it returns null. planScaffold never gives it a plan that
  // fails, so the plan it makes on the fixture is the one that must pass, and the two that must fail
  // are made from it by hand: one with the excluded route lost, one with a draft counted again as
  // declared. Without this test, a guard that quietly stopped guarding would pass every other one.
  const dir = sandbox(t);
  const { config, base } = loadConfig(path.join(dir, "usedesign.config.yaml"));
  const planned = planScaffold(path.join(dir, "openapi.json"), path.join(dir, "drafts"), config, base);
  assert.deepEqual([planned.drafts.length, planned.skippedDeclared.length, planned.skippedExcluded.length, planned.total], [5, 1, 1, 7]);

  const draft = planned.drafts[0];
  const plans = {
    "as planned": planned,
    lost: { ...planned, skippedExcluded: [] },
    "counted twice": {
      ...planned,
      skippedDeclared: [...planned.skippedDeclared, { route: `${draft.method} ${draft.path}`, by: ["sample.twice"] }],
    },
  };
  const verdicts = Object.entries(plans).map(([name, plan]) => [name, unaccountedRoutes(plan)]);

  // A route lost "vanished"; a route counted twice is "counted more than once" (up to 1.7.1 it
  // read "-1 vanished"). Both lines are in the golden file.
  golden(
    "scaffold-unaccounted/findings.txt",
    verdicts.map(([name, f]) => `${`${name}:`.padEnd(15)}${f ? `${f.severity} ${f}` : "null"}\n`).join(""),
  );
  const [asPlanned, lost, twice] = verdicts.map(([, f]) => f);
  assert.equal(asPlanned, null);
  for (const f of [lost, twice]) {
    assert.ok(f, "an unbalanced plan passed");
    assert.equal(f.code, "routes_unaccounted");
    assert.equal(f.severity, "error");
  }
  assert.ok(lost.detail.endsWith("— 1 vanished without a reason"), lost.detail);
  assert.ok(twice.detail.endsWith("— 1 counted more than once"), twice.detail);
  assert.ok(!twice.detail.includes("-1"), twice.detail);
});

test("scaffold: every written draft fails validate", (t) => {
  const dir = sandbox(t);
  const made = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml");
  assert.equal(made.status, 0, made.stderr);

  const r = run(dir, "validate", "drafts");
  assert.equal(r.status, 1, r.stdout);

  // Each of the five drafts is named in a schema violation and in a FILL_ME that is not a value.
  const drafts = fs.readdirSync(path.join(dir, "drafts"));
  assert.equal(drafts.length, 5);
  for (const file of drafts) {
    assert.ok(r.stdout.includes(`  ERROR    ${file}: schema_violation: `), `${file}: no schema_violation\n${r.stdout}`);
    assert.ok(r.stdout.includes(`  ERROR    ${file}: invalid_enum_value: maturity \`FILL_ME\``), `${file}: no FILL_ME maturity\n${r.stdout}`);
  }
  const summary = r.stdout.match(/^5 card\(s\), 0 form contract\(s\): (\d+) error\(s\), \d+ warning\(s\)$/m);
  assert.ok(summary, r.stdout);
  assert.ok(Number(summary[1]) >= 5, `fewer errors than drafts: ${summary[0]}`);
});

test("scaffold --dry-run: prints the arithmetic and writes nothing", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml", "--dry-run");
  assert.equal(r.status, 0, r.stderr);
  golden("scaffold-dry-run/stdout.txt", r.stdout);
  assert.ok(r.stdout.endsWith("dry run: nothing written.\n"), r.stdout);
  assert.ok(r.stdout.includes("→ 5 + 1 + 1 = 7 ✓"), r.stdout);
  assert.ok(!fs.existsSync(path.join(dir, "drafts")), "the out dir was created by a dry run");
});

test("scaffold: a draft already on disk is kept without --force", (t) => {
  const dir = sandbox(t);
  fs.mkdirSync(path.join(dir, "drafts"));
  fs.writeFileSync(path.join(dir, "drafts", DRAFT_OF_COPIES), SENTINEL);

  const r = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml");
  assert.equal(r.status, 0, r.stderr);
  golden("scaffold-existing-kept/stdout.txt", r.stdout);
  assert.ok(r.stdout.includes("existing:   1 draft(s) already on disk — left untouched"), r.stdout);
  assert.ok(r.stdout.includes("written:    4, kept 1 existing"), r.stdout);

  assert.equal(fs.readFileSync(path.join(dir, "drafts", DRAFT_OF_COPIES), "utf8"), SENTINEL);
  // The other four are the golden drafts; the kept one is the sentinel, so the tree is compared
  // without it.
  for (const file of fs.readdirSync(path.join(dir, "drafts")).filter((f) => f !== DRAFT_OF_COPIES)) {
    golden(`scaffold/drafts/${file}`, fs.readFileSync(path.join(dir, "drafts", file), "utf8"));
  }
  assert.equal(fs.readdirSync(path.join(dir, "drafts")).length, 5);
});

test("scaffold --force: a draft already on disk is overwritten", (t) => {
  const dir = sandbox(t);
  fs.mkdirSync(path.join(dir, "drafts"));
  fs.writeFileSync(path.join(dir, "drafts", DRAFT_OF_COPIES), SENTINEL);

  const r = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml", "--force");
  assert.equal(r.status, 0, r.stderr);
  golden("scaffold-existing-force/stdout.txt", r.stdout);
  assert.ok(r.stdout.includes("existing:   1 draft(s) already on disk — OVERWRITTEN (--force)"), r.stdout);
  assert.ok(r.stdout.includes("written:    5\n"), r.stdout);
  assert.ok(!r.stdout.includes("kept"), r.stdout);

  goldenTree("scaffold/drafts", path.join(dir, "drafts"));
});

test("scaffold: statuses identical across every route are flagged in stdout and in every draft", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi-uniform.json", "--out", "drafts");
  assert.equal(r.status, 0, r.stderr);

  golden("scaffold-uniform/stdout.txt", r.stdout);
  const drafts = goldenTree("scaffold-uniform/drafts", path.join(dir, "drafts"));

  assert.ok(
    r.stdout.startsWith("  warning  statuses_uniform: every one of the 3 routes declares the same statuses (200) — "),
    r.stdout,
  );
  assert.ok(r.stdout.includes("→ 3 + 0 + 0 = 3 ✓"), r.stdout);
  assert.equal(drafts.length, 3);
  for (const file of drafts) {
    const body = fs.readFileSync(path.join(dir, "drafts", file), "utf8");
    assert.match(body, /^ {4}responses: \[200\] {3}# ⚠ /m, `${file}: no ⚠ comment on the responses line`);
    assert.ok(body.includes("⚠️ `responses` СКОПИРОВАН, НО ЕМУ НЕЛЬЗЯ ВЕРИТЬ."), `${file}: no ⚠️ paragraph`);
  }
});

test("scaffold: an OpenAPI document without routes is openapi_empty, exit 1, and nothing is written", (t) => {
  // Up to 1.7.1 the ERROR line came with exit 0, and an empty `--out` directory was left behind.
  for (const extra of [[], ["--dry-run"]]) {
    const dir = sandbox(t);
    const r = run(dir, "scaffold", "openapi-empty.json", "--out", "drafts", ...extra);
    assert.equal(r.status, 1, `${extra.join(" ")}\n${r.stdout}${r.stderr}`);

    if (extra.length === 0) golden("scaffold-empty/stdout.txt", r.stdout);
    assert.ok(r.stdout.startsWith("  ERROR    openapi_empty: openapi-empty.json: no routes"), r.stdout);
    assert.ok(r.stdout.includes("routes:     0 served, read from openapi-empty.json\n"), r.stdout);
    assert.ok(r.stdout.includes("→ 0 + 0 + 0 = 0 ✓"), r.stdout);
    assert.ok(r.stdout.endsWith("nothing written: an ERROR above — fix the document, then run again.\n"), r.stdout);
    assert.ok(!fs.existsSync(path.join(dir, "drafts")), "the out dir was created");
  }
});

test("scaffold: path parameters declared on the path item reach the draft", (t) => {
  // OpenAPI lets `parameters` stand on the path item, for every operation under it. Up to 1.7.1
  // only the operation's own were read: the draft of `GET /v1/loans/{loan}` named no parameter.
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi-path-item.json", "--out", "drafts");
  assert.equal(r.status, 0, r.stdout + r.stderr);
  const drafts = goldenTree("scaffold-path-item/drafts", path.join(dir, "drafts"));
  assert.deepEqual(drafts, ["TODO.v1-loans-notes.get.op.md", "TODO.v1-loans.delete.op.md", "TODO.v1-loans.get.op.md"]);

  const said = (file) => fs.readFileSync(path.join(dir, "drafts", file), "utf8").match(/параметры пути: ([^·.]*)/)?.[1]?.trim();
  // On the path item alone; on both, named once; one on each, the path item's first.
  assert.equal(said("TODO.v1-loans.get.op.md"), "loan");
  assert.equal(said("TODO.v1-loans.delete.op.md"), "loan");
  assert.equal(said("TODO.v1-loans-notes.get.op.md"), "loan, note");
});

test("scaffold: no --out is a usage error (exit 2)", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi.json");
  assert.equal(r.status, 2);
  assert.ok(r.stderr.includes("--out <dir> is required"), r.stderr);
  assert.equal(r.stdout, "");
});

test("scaffold: two OpenAPI documents are a usage error (exit 2)", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "scaffold", "openapi.json", "openapi-uniform.json", "--out", "drafts");
  assert.equal(r.status, 2);
  assert.ok(r.stderr.includes("name exactly one OpenAPI document"), r.stderr);
  assert.equal(r.stdout, "");
  assert.ok(!fs.existsSync(path.join(dir, "drafts")));
});
