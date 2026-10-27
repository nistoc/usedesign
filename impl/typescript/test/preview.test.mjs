/**
 * Tests for `usedesign preview`, black box: the built CLI is run in a fresh temporary directory
 * that holds a copy of test/fixtures/preview/ (the form-clean case of the checks corpus: a config,
 * a contract, its card and a form inventory), with relative arguments.
 *
 *   npm run test:unit                    (build first: npm run build)
 *
 * What is pinned is what the command must never do: write anywhere it was not told to. Up to 1.7.1
 * `preview <config>` with no `--out` wrote the page over the config itself and exited 0.
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

const FIXTURE = path.join(here, "fixtures", "preview");
const CONFIG = "usedesign.config.yaml";

/** A fresh temporary directory holding a copy of the fixture, removed when the test ends. */
function sandbox(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "usedesign-preview-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  fs.cpSync(FIXTURE, dir, { recursive: true });
  return dir;
}

function run(cwd, ...args) {
  return spawnSync(process.execPath, [cli, ...args], { cwd, encoding: "utf8" });
}

/** Every file of the sandbox is still the fixture's, byte for byte, and nothing was added. */
function untouched(dir) {
  assert.deepEqual(fs.readdirSync(dir).sort(), fs.readdirSync(FIXTURE).sort(), "a file was added or removed");
  for (const file of fs.readdirSync(FIXTURE)) {
    assert.ok(fs.readFileSync(path.join(dir, file)).equals(fs.readFileSync(path.join(FIXTURE, file))), `${file} was rewritten`);
  }
}

test("preview: no --out is a usage error, and the config is left as it was", (t) => {
  const dir = sandbox(t);
  const r = run(dir, "preview", CONFIG);
  assert.equal(r.status, 2, r.stdout);
  assert.ok(r.stderr.includes("usedesign preview: usage"), r.stderr);
  assert.equal(r.stdout, "");
  untouched(dir);
});

test("preview: --out with no value is a usage error, and nothing is written", (t) => {
  const dir = sandbox(t);
  for (const args of [[CONFIG, "--out"], ["--out", CONFIG]]) {
    const r = run(dir, "preview", ...args);
    assert.equal(r.status, 2, `${args.join(" ")}\n${r.stdout}`);
    assert.ok(r.stderr.includes("usedesign preview: usage"), r.stderr);
    untouched(dir);
  }
});

test("preview: --out names the page, wherever it stands, and only the page is written", (t) => {
  for (const args of [[CONFIG, "--out", "page.html"], ["--out", "page.html", CONFIG]]) {
    const dir = sandbox(t);
    const r = run(dir, "preview", ...args);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.stdout, "preview:    1 contract(s) → page.html (с вердиктами по перечню формы)\n");
    const page = path.join(dir, "page.html");
    assert.ok(fs.readFileSync(page, "utf8").startsWith("<!doctype html>"), "the page is not HTML");
    fs.rmSync(page);
    untouched(dir);
  }
});
