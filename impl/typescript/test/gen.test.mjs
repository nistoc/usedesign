/**
 * Golden tests for `usedesign gen openapi`, black box: the built CLI is run in a fresh temporary
 * directory that holds a copy of a fixture, with relative arguments, and its stdout and the
 * document it writes are compared byte for byte with the files under test/golden/gen/.
 *
 *   npm run test:unit                    compare with the golden files (build first: npm run build)
 *   UPDATE_GOLDEN=1 npm run test:unit    rewrite the golden files from the CLI's current output —
 *                                        then READ every changed file: a golden file is a claim,
 *                                        not a recording.
 *
 * Fixtures: test/fixtures/gen/ (four cards: two on one route told apart by `dispatch`, one with
 * `outcomes[]` and a path parameter, one with a `ui` interface only) and test/fixtures/gen-no-rest/
 * (a single ui-only card).
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

/** A fresh temporary directory holding a copy of the fixture, removed when the test ends. */
function sandbox(t, fixture = "gen") {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "usedesign-gen-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.cpSync(path.join(here, "fixtures", fixture), dir, { recursive: true });
  return dir;
}

function run(cwd, ...args) {
  return spawnSync(process.execPath, [cli, ...args], { cwd, encoding: "utf8" });
}

test("gen openapi: stdout and the derived document match the golden files, and are deterministic", (t) => {
  const dir = sandbox(t);
  const first = run(dir, "gen", "openapi", "usedesign.config.yaml", "--out", "openapi.json");
  assert.equal(first.status, 0, first.stderr);
  const written = fs.readFileSync(path.join(dir, "openapi.json"), "utf8");

  golden("gen/stdout.txt", first.stdout);
  golden("gen/openapi.json", written);

  // gen.ts promises deterministic output: the same cards, byte-identical, run after run.
  const second = run(dir, "gen", "openapi", "usedesign.config.yaml", "--out", "second.json");
  assert.equal(second.status, 0, second.stderr);
  assert.ok(fs.readFileSync(path.join(dir, "second.json")).equals(fs.readFileSync(path.join(dir, "openapi.json"))), "two runs, two different documents");
  assert.equal(second.stdout, first.stdout.replace("→ openapi.json", "→ second.json"));

  // What the golden file must say, stated independently of it.
  assert.ok(first.stdout.includes("cards:      4 read, 3 REST interface(s)\n"), first.stdout);
  assert.ok(first.stdout.includes("routes:     2 path+method pair(s) → openapi.json\n"), first.stdout);
  assert.ok(first.stdout.includes("merged:     POST /v1/things:batch ← sample.batch.delete-many, sample.batch.publish-many\n"), first.stdout);
  assert.ok(written.endsWith("}\n") && !written.endsWith("\n\n"));
  const doc = JSON.parse(written);
  assert.deepEqual(Object.keys(doc.paths), ["/v1/loans/{loanId}", "/v1/things:batch"], "paths are sorted");
  const merged = doc.paths["/v1/things:batch"].post;
  assert.deepEqual(merged["x-usedesign-operations"], ["sample.batch.delete-many", "sample.batch.publish-many"]);
  assert.deepEqual(
    Object.fromEntries(Object.entries(merged.responses).map(([code, response]) => [code, response.description])),
    {
      200: "published, queued", // the sibling named none; "declared by the card" gives way to the names
      403: "forbidden, publish_not_allowed", // `forbidden` is named by both cards and listed once
      404: "thing_not_found",
      409: "thing_locked, already_published",
      422: "draft_incomplete",
    },
  );
  const loan = doc.paths["/v1/loans/{loanId}"].get;
  assert.deepEqual(loan.parameters, [{ name: "loanId", in: "path", required: true, schema: { type: "string" } }]);
  assert.equal(loan.responses["410"].description, "loan_closed", "a status named by outcomes[] alone");
  assert.equal(JSON.stringify(doc).includes("sample.loans.screen"), false, "the ui-only card adds no route");
});

test("gen openapi: cards without a REST interface derive nothing (exit 1)", (t) => {
  const dir = sandbox(t, "gen-no-rest");
  const r = run(dir, "gen", "openapi", "usedesign.config.yaml", "--out", "openapi.json");
  assert.equal(r.status, 1);
  assert.ok(r.stderr.includes("the cards declare no REST interface — nothing to derive"), r.stderr);
  assert.ok(!fs.existsSync(path.join(dir, "openapi.json")), "an output file was written");
});

// NOTE: `gen openapi <config>` with no `--out` at all is not a usage error today: the parser reads
// `rest[rest.indexOf("--out") + 1]`, which is `rest[0]` when `--out` is absent, so the word
// `openapi` becomes the output file name (cli.ts, case "gen"). That is a defect rather than a
// decision, so it is not pinned here; the two forms below are the ones that do exit 2.
test("gen openapi: a missing --out is a usage error (exit 2)", (t) => {
  const dir = sandbox(t);
  for (const args of [["gen", "openapi"], ["gen", "openapi", "usedesign.config.yaml", "--out"]]) {
    const r = run(dir, ...args);
    assert.equal(r.status, 2, `${args.join(" ")}\n${r.stdout}`);
    assert.ok(r.stderr.includes("usage"), r.stderr);
  }
  assert.deepEqual(fs.readdirSync(dir).sort(), ["cards", "usedesign.config.yaml"], "a file was written");
});

test("gen, then scaffold: the loop closes — zero drafts, every route declared", (t) => {
  const dir = sandbox(t);
  const gen = run(dir, "gen", "openapi", "usedesign.config.yaml", "--out", "openapi.json");
  assert.equal(gen.status, 0, gen.stderr);
  const routes = Object.values(JSON.parse(fs.readFileSync(path.join(dir, "openapi.json"), "utf8")).paths).reduce(
    (n, methods) => n + Object.keys(methods).length,
    0,
  );
  assert.equal(routes, 2);

  const r = run(dir, "scaffold", "openapi.json", "--out", "drafts", "--config", "usedesign.config.yaml");
  assert.equal(r.status, 0, r.stderr);
  assert.ok(r.stdout.includes(`routes:     ${routes} served, read from openapi.json\n`), r.stdout);
  assert.ok(r.stdout.includes("drafts:     0 to write"), r.stdout);
  assert.ok(r.stdout.includes(`→ 0 + ${routes} + 0 = ${routes} ✓`), r.stdout);
  assert.ok(r.stdout.includes("GET /v1/loans/{} → sample.loans.get-one\n"), r.stdout);
  assert.ok(r.stdout.includes("POST /v1/things:batch → sample.batch.delete-many, sample.batch.publish-many\n"), r.stdout);
  const drafts = path.join(dir, "drafts");
  assert.deepEqual(fs.existsSync(drafts) ? fs.readdirSync(drafts) : [], [], "a draft was written");
});
