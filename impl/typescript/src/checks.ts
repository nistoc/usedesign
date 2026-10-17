/**
 * The five checks. Each one has the same shape: the repository states a fact in a format it
 * already produces, and usedesign compares that statement with the cards. Nothing here parses a
 * framework, reads source code, or guesses.
 *
 *   1. no wild endpoints                design/route-conformance.md
 *   2. no unproven steps                design/step-coverage.md
 *   3. no inflated maturity             design/maturity-evidence.md
 *   4. no imagined storage              SPEC §7.4
 *   5. the form matches its contract    SPEC §7.5
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { SaxesParser } from "saxes";
import {
  Card, Config, Finding, expandGlobs, globMatches, isMap, list, loadCardFiles, map, maps, readDocument, refuseTwins, text, texts,
  whyUnreadable,
} from "./core.js";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"];

/**
 * Parameter syntaxes seen in the wild: {name} · :name · <name> · <converter:name>
 *
 * `:name` counts as a parameter ONLY after a slash. Written any other way it is a literal —
 * the AIP-136 style spells an action on a resource as `POST /progress/{id}:finish`, and treating
 * that suffix as a parameter collapses `:finish`, `:abandon`, `:resume`, `:reorder` and `:sync`
 * into one shape. The checker then reports a clean run while four operations are declared by
 * nobody, which is the worst thing a checker can do.
 */
const PARAM = /\{[^}]*\}|(?<=\/):[A-Za-z_][A-Za-z0-9_]*|<[^>]*>/g;

/**
 * Reduce a route to what identifies it: method and path *shape*.
 *
 * Parameter names are documentation, not identity — a card saying {copyId} and a framework saying
 * :id describe the same route. See design/route-conformance.md §4, including the case this
 * deliberately cannot tell apart.
 */
export function normalise(method: string, path: string): string {
  let shape = path.trim().replace(PARAM, "{}");
  if (shape.length > 1) shape = shape.replace(/\/+$/, "");
  return `${method.trim().toUpperCase()} ${shape}`;
}

export interface CheckResult {
  findings: Finding[];
  summary: Record<string, unknown>;
}

// ── check 1 — no wild endpoints ───────────────────────────────────────────────────────────────

function loadDeclared(config: Config, base: string): { declared: Map<string, string[]>; maturityById: Map<string, string>; findings: Finding[] } {
  const declared = new Map<string, string[]>();
  const dispatchOf = new Map<string, string>();
  const maturityById = new Map<string, string>();
  const { cards, findings } = loadCardFiles(config, base);

  for (const [cardId, fm] of cards) {
    maturityById.set(cardId, text(fm["maturity"]) ?? "");
    for (const [name, iface] of Object.entries<any>(map(fm["interfaces"]))) {
      if (!isMap(iface) || iface["transport"] !== "http_rest") continue;
      const method = text(iface["method"]);
      const path = text(iface["path"]);
      if (!method || !path) {
        findings.push(
          new Finding("incomplete_rest_interface", `${cardId}: interface \`${name}\` declares http_rest without method or path`),
        );
        continue;
      }
      // The key stays the route shape — that is what the inventory can be compared against.
      // Dispatch tells cards apart from each other, not routes from each other.
      const key = normalise(method, path);
      const d = map(iface["dispatch"]);
      const by = text(d["by"]);
      const value = text(d["value"]);
      declared.set(key, [...(declared.get(key) ?? []), cardId]);
      dispatchOf.set(`${key}\u0000${cardId}`, by && value ? `${by}=${value}` : "");
    }
  }

  for (const [key, owners] of byKey(declared)) {
    if (owners.length < 2) continue;
    // Several operations may legitimately share a route, told apart by a request field — a
    // widespread REST idiom, not a defect. It is only ambiguous when two cards claim the same
    // route with the same dispatch, or with none.
    const stamps = owners.map((id) => dispatchOf.get(`${key}\u0000${id}`) ?? "");
    if (new Set(stamps).size === owners.length && !stamps.includes("")) continue;
    findings.push(
      new Finding(
        "ambiguous_shape",
        `${key} is declared by ${owners.length} cards (${owners.join(", ")}) — the checker cannot tell them apart`,
        "warning",
      ),
    );
  }
  return { declared, maturityById, findings };
}

/**
 * Declared routes in the order of their `METHOD shape` (1.5.1). Sorted as pairs, they were ordered
 * by the text `GET /a,owner` — `GET /a+b` before `GET /a` — and the Python prototype by the pair
 * itself, so two routes could print in a different order in each.
 */
function byKey(declared: Map<string, string[]>): [string, string[]][] {
  return [...declared.entries()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}

interface Route {
  method?: string;
  path?: string;
  source?: string;
}

function loadInventory(config: Config, base: string): { routes: Route[]; findings: Finding[]; producedBy: string } {
  const location = config.inventory;
  if (!location) {
    return {
      routes: [],
      findings: [new Finding("inventory_missing", "no `inventory` in the config — check 1 cannot run and is NOT considered passed")],
      producedBy: "",
    };
  }

  const path = join(base, location);
  if (!existsSync(path)) {
    return { routes: [], findings: [new Finding("inventory_missing", `${location} does not exist`)], producedBy: "" };
  }

  const data = JSON.parse(readFileSync(path, "utf8"));
  const findings: Finding[] = [];
  if (data.usedesign_inventory !== 1) {
    findings.push(new Finding("inventory_malformed", `${location}: missing \`usedesign_inventory: 1\``));
  }
  if (!data.produced_by) findings.push(new Finding("inventory_malformed", `${location}: missing \`produced_by\``));

  const routes: Route[] = data.routes ?? [];
  if (routes.length === 0) {
    findings.push(
      new Finding("inventory_empty", `${location}: no routes — almost always a failed dump rather than an application with no routes`),
    );
  }
  for (const entry of routes) {
    if (!METHODS.includes(String(entry.method))) {
      findings.push(new Finding("inventory_malformed", `${location}: unknown method \`${entry.method}\``));
    }
  }
  return { routes, findings, producedBy: data.produced_by ?? "" };
}

/** The rule that hides this route, by the glob of a `cards:` segment (1.5.1), or -1. */
function excludedBy(config: Config, method: string, shape: string): number {
  const rules = config.exclude ?? [];
  for (const [index, rule] of rules.entries()) {
    if (rule.method && rule.method.toUpperCase() !== method) continue;
    if (globMatches(shape, rule.path ?? "")) return index;
  }
  return -1;
}

export function checkRoutes(config: Config, base: string): CheckResult {
  const findings: Finding[] = [];
  const { declared, maturityById, findings: cardFindings } = loadDeclared(config, base);
  findings.push(...cardFindings);
  let designedAhead = 0;

  const { routes, findings: inventoryFindings, producedBy } = loadInventory(config, base);
  findings.push(...inventoryFindings);

  const served = new Set<string>();
  const hidden = new Map<number, number>();

  for (const entry of routes) {
    const key = normalise(entry.method ?? "", entry.path ?? "");
    const [method = "", shape = ""] = [key.slice(0, key.indexOf(" ")), key.slice(key.indexOf(" ") + 1)];
    const rule = excludedBy(config, method, shape);
    if (rule !== -1) {
      hidden.set(rule, (hidden.get(rule) ?? 0) + 1);
      continue;
    }
    served.add(key);
    if (!declared.has(key)) {
      findings.push(new Finding("wild_endpoint", `${key} is served but declared by no card${entry.source ? ` (source: ${entry.source})` : ""}`));
    }
  }

  for (const [key, owners] of byKey(declared)) {
    const method = key.slice(0, key.indexOf(" "));
    const shape = key.slice(key.indexOf(" ") + 1);
    if (routes.length > 0 && !served.has(key) && excludedBy(config, method, shape) === -1) {
      // Two opposite situations used to share one diagnostic (issue #3). A route that is GONE
      // is an error; a route that is DESIGNED AND NOT BUILT YET is exactly what `conceived`
      // and `designed` exist to describe — contract-first is the format's own flow, and a
      // check that is red by construction gets ignored until the real phantom arrives unread.
      const ahead = owners.every((id) => ["conceived", "designed"].includes(maturityById.get(id) ?? ""));
      if (ahead) {
        designedAhead += 1;
        findings.push(
          new Finding("route_not_yet_served", `${key} is declared by ${owners.join(", ")} — designed ahead of the code, expected to be absent`, "warning"),
        );
      } else {
        findings.push(new Finding("phantom_route", `${key} is declared by ${owners.join(", ")} but is not served`));
      }
    }
  }

  // An exclusion that hides nothing is dead. With no routes at all every exclusion is trivially
  // dead; saying so adds noise to a run that already reported the real problem, and cascading
  // noise is how a checker teaches people to stop reading it. See the design note §5.
  const rules = routes.length > 0 ? config.exclude ?? [] : [];
  for (const [index, rule] of rules.entries()) {
    if (!hidden.has(index)) {
      findings.push(new Finding("dead_exclusion", `\`${rule.path}\` excluded nothing — remove it or fix the pattern`, "warning"));
    }
  }

  const hiddenPerRule: Record<string, number> = {};
  for (const [index, count] of [...hidden.entries()].sort((a, b) => a[0] - b[0])) {
    hiddenPerRule[String((config.exclude ?? [])[index]?.path)] = count;
  }

  return {
    findings,
    summary: {
      produced_by: producedBy,
      served: routes.length,
      excluded: [...hidden.values()].reduce((a, b) => a + b, 0),
      declared: declared.size,
      designed_ahead: designedAhead,
      hidden_per_rule: hiddenPerRule,
    },
  };
}

// ── check 2 — no unproven steps ───────────────────────────────────────────────────────────────
//
// The repository states the facts, the checker compares — the same shape as check 1, except that
// here the format already exists (JUnit XML), so nothing new is invented.

const PARAMETRISED = /[[(].*$/; // checkout[blocked] · checkout(1) → checkout

export interface TestCase {
  classname: string;
  name: string;
  status: "passed" | "failed" | "skipped";
  full: string;
}

/**
 * The test cases of a report, read as XML 1.0 reads it: a `testcase` element in no namespace, at any
 * depth, in document order; its `classname` and `name`; and its status from its own children —
 * `failure` or `error` fails it, `skipped` skips it, in any letter case, and the last of them decides.
 *
 * 1.5.1 read the report with a lenient parser: a report cut off while it was written read as far as
 * it went, so a test cut before its `<failure>` passed; past 1 000 escaped characters (`&quot;`) the
 * report was refused; `&#233;` stayed six characters. The Python prototype read all three as XML
 * reads them; both do now (1.5.2). A DOCTYPE is refused in both: JUnit reports carry none, and its
 * entities are what the expansion attacks are made of.
 */
function readReport(text: string): TestCase[] | "doctype" | "malformed" {
  class Doctype extends Error {}
  const parser = new SaxesParser({ xmlns: true });
  const cases: TestCase[] = [];
  const open: (TestCase | null)[] = [];
  parser.on("doctype", () => {
    throw new Doctype();
  });
  parser.on("opentag", (tag) => {
    const parent = open[open.length - 1];
    if (parent && tag.uri === "") {
      const local = tag.local.toLowerCase();
      if (local === "failure" || local === "error") parent.status = "failed";
      else if (local === "skipped") parent.status = "skipped";
    }
    let own: TestCase | null = null;
    if (tag.uri === "" && tag.local === "testcase") {
      const classname = tag.attributes["classname"]?.value ?? "";
      const name = tag.attributes["name"]?.value ?? "";
      own = { classname, name, status: "passed", full: classname ? `${classname}.${name}` : name };
      cases.push(own);
    }
    open.push(own);
  });
  parser.on("closetag", () => {
    open.pop();
  });
  try {
    parser.write(text).close();
  } catch (exc) {
    return exc instanceof Doctype ? "doctype" : "malformed";
  }
  return cases;
}

function loadReport(config: Config, base: string): { cases: TestCase[]; findings: Finding[] } {
  const location = config.test_report;
  if (!location) {
    return {
      cases: [],
      findings: [new Finding("report_missing", "no `test_report` in the config — check 2 cannot run and is NOT considered passed")],
    };
  }

  const path = join(base, location);
  if (!existsSync(path)) return { cases: [], findings: [new Finding("report_missing", `${location} does not exist`)] };
  // 1.5.1 named a directory here as malformed XML, and the Python prototype stopped with a traceback.
  const why = whyUnreadable(path);
  if (why) return { cases: [], findings: [new Finding("report_missing", `${location} cannot be read: ${why}`)] };

  const cases = readReport(readFileSync(path, "utf8"));
  if (cases === "doctype") {
    return { cases: [], findings: [new Finding("report_malformed", `${location}: a DOCTYPE — a JUnit report has none, and check 2 reads none`)] };
  }
  if (cases === "malformed") {
    return {
      cases: [],
      findings: [new Finding("report_malformed", `${location}: not well-formed XML — a run that stopped while writing its report leaves such a file`)],
    };
  }

  if (cases.length === 0) {
    return { cases, findings: [new Finding("report_empty", `${location}: no test cases — a failed run, not a suite without tests`)] };
  }
  return { cases, findings: [] };
}

type Index = Map<string, TestCase[]>;

/** Two indexes: by `classname.name`, and by bare name, with parametrised cases folded in. */
function indexReport(cases: TestCase[]): { byFull: Index; byName: Index } {
  const byFull: Index = new Map();
  const byName: Index = new Map();
  const push = (index: Index, key: string, value: TestCase) => index.set(key, [...(index.get(key) ?? []), value]);

  for (const item of cases) {
    push(byFull, item.full, item);
    push(byName, item.name, item);
    const base = item.name.replace(PARAMETRISED, "");
    if (base !== item.name) {
      push(byName, base, item);
      push(byFull, item.classname ? `${item.classname}.${base}` : base, item);
    }
  }
  return { byFull, byName };
}

/** Resolve a card's test id to report entries. Full-id matching only — never a substring. */
export function findCases(testId: string, byFull: Index, byName: Index): TestCase[] {
  // Exact matches first, in BOTH indexes. The "file:name" shape below is a heuristic, and a
  // heuristic consulted before the exact match ate every name containing a colon (issue #9):
  // `архив карточки > скрытие: без причины…` was split at its own colon, looked up by its tail,
  // and reported as unproven — a fully proven card, red, with the tempting "fix" of deleting
  // the proof from the card. Measured both ways on a live repository: 53 ids without a colon
  // matched, the 2 with one never did.
  if (byFull.has(testId)) return byFull.get(testId)!;
  if (byName.has(testId)) return byName.get(testId)!;
  if (testId.includes(":")) {
    // file-and-name shape — every colon is a candidate split, left to right, first hit wins:
    // the name part may itself carry colons.
    for (let at = testId.indexOf(":"); at !== -1; at = testId.indexOf(":", at + 1)) {
      const candidates = byName.get(testId.slice(at + 1)) ?? [];
      if (candidates.length === 0) continue;
      const filePart = testId.slice(0, at);
      const narrowed = candidates.filter((c) => (c.classname || "").includes(filePart));
      return narrowed.length > 0 ? narrowed : candidates;
    }
  }
  if (testId.includes(".")) {
    // runners disagree about `classname`
    return byName.get(testId.slice(testId.lastIndexOf(".") + 1)) ?? [];
  }
  return [];
}

export function checkCoverage(config: Config, base: string): CheckResult {
  const findings: Finding[] = [];
  const { cases, findings: reportFindings } = loadReport(config, base);
  findings.push(...reportFindings);
  const haveReport = cases.length > 0;
  const { byFull, byName } = indexReport(cases);

  const { cards } = loadCardFiles(config, base);
  let proven = 0;
  let unproven = 0;
  let inherited = 0;
  const gapKinds = { unwritten: 0, harness: 0, unreachable: 0 };

  // Pass 1 — every card's OWN proofs. A variant (§5.2e) reads the original's own proofs, never
  // what the original itself inherited, so credit cannot chain.
  const ownProof = new Map<string, Map<string, string[]>>();
  for (const [cardId, fm] of cards) {
    const byStep = new Map<string, string[]>();
    ownProof.set(cardId, byStep);

    for (const test of maps(fm["tests"])) {
      const refs = coversOf(test);
      const testId = text(test["id"]) ?? "";
      const matched = haveReport ? findCases(testId, byFull, byName) : [];

      if (haveReport) {
        if (matched.length === 0) {
          findings.push(new Finding("test_not_found", `${cardId}: \`${testId}\` matches nothing in the report`));
        } else {
          // Rule 4: a parametrised family proves the step only if all of it passes.
          const failed = matched.filter((c) => c.status === "failed");
          const skipped = matched.filter((c) => c.status === "skipped");
          if (failed.length > 0) {
            findings.push(
              new Finding("test_failing", `${cardId}: \`${testId}\` failed${matched.length > 1 ? ` (${failed.length} of ${matched.length} cases)` : ""}`),
            );
          } else if (skipped.length > 0) {
            findings.push(new Finding("test_skipped", `${cardId}: \`${testId}\` was skipped — a name in the report is not proof`));
          }
        }
      }

      const passing = matched.length > 0 && matched.every((c) => c.status === "passed");
      for (const ref of refs) {
        if (!byStep.has(ref)) byStep.set(ref, []);
        if (passing || !haveReport) byStep.get(ref)!.push(testId);
      }
    }
  }

  // Pass 2 — verdicts, with a variant's inherited steps credited from the original.
  const byId = new Map<string, Card>(cards);
  for (const [cardId, fm] of cards) {
    const steps = stepIdsOf(fm);
    const gaps = gapStepsOf(fm);
    const byStep = ownProof.get(cardId)!;
    const { credited, explained } = inheritance(cardId, fm, steps, byStep, byId, ownProof, haveReport, findings);
    // Round 26 ⑬: a gap says why the proof is missing — counted apart, so "not written yet" is
    // never read as "cannot be written".
    for (const entry of maps(fm["coverage_gaps"])) {
      const kind = text(entry["kind"]) || "unwritten";
      if (kind === "unwritten" || kind === "harness" || kind === "unreachable") gapKinds[kind] += 1;
    }

    for (const step of steps) {
      if (gaps.has(step)) continue;
      if ((byStep.get(step) ?? []).length > 0) {
        proven += 1;
        continue;
      }
      if (credited.has(step)) {
        proven += 1;
        inherited += 1;
        continue;
      }
      unproven += 1;
      // A step whose only tests failed or vanished is already reported above, and so is an
      // inherited step a variant finding already explains; saying it twice trains people to skim.
      if (!byStep.has(step) && !explained.has(step)) {
        findings.push(
          new Finding("step_unproven", `${cardId}: step \`${step}\` has no test and no declared gap`, haveReport ? "error" : "warning"),
        );
      }
    }
  }

  return {
    findings,
    summary: {
      report_cases: cases.length, proven, unproven, inherited,
      gaps: gapKinds.unwritten + gapKinds.harness + gapKinds.unreachable,
      gaps_harness: gapKinds.harness, gaps_unreachable: gapKinds.unreachable,
    },
  };
}

/** The steps a test covers: one id or a list of them (1.5.1: an id of another type is absent). */
function coversOf(test: Record<string, any>): string[] {
  const covers = test["covers"];
  return typeof covers === "string" ? [covers] : texts(covers);
}

/** A card's step ids, in order; a step that is not a map, or an id that is not a string, is absent. */
function stepIdsOf(fm: Card): string[] {
  return texts(maps(fm["steps"]).map((step) => step["id"]));
}

/** The steps a card declares a gap for. */
function gapStepsOf(fm: Card): Set<string> {
  return new Set(texts(maps(fm["coverage_gaps"]).map((gap) => gap["step"])));
}

/**
 * Which inherited steps of a variant (§5.2e) the original's own tests prove. `explained` holds the
 * steps whose missing credit a variant finding has already reported, so check 2 does not repeat it
 * step by step.
 */
function inheritance(
  cardId: string,
  fm: Card,
  steps: string[],
  byStep: Map<string, string[]>,
  byId: Map<string, Card>,
  ownProof: Map<string, Map<string, string[]>>,
  haveReport: boolean,
  findings: Finding[],
): { credited: Set<string>; explained: Set<string> } {
  const credited = new Set<string>();
  const explained = new Set<string>();
  const variant = fm["variant_of"];
  if (!isMap(variant)) return { credited, explained };

  const inherits = texts(variant["inherits"]);
  const originalId = text(variant["card"]) ?? "";
  const original = byId.get(originalId);
  if (!original) {
    findings.push(new Finding("variant_of_unknown", `${cardId}: \`variant_of\` names \`${originalId}\`, which no card in the set declares`));
    inherits.forEach((s) => explained.add(s));
    return { credited, explained };
  }

  const shared = (text(variant["shared"]) ?? "").trim().replace(LINE_SUFFIX, "");
  const codeShared = evidencePaths(map(original["maturity_evidence"])["implemented"]).includes(shared);
  if (!codeShared) {
    findings.push(
      new Finding("variant_code_not_shared", `${cardId}: \`${shared}\` is not in the \`implemented\` evidence of \`${originalId}\` — nothing shows the two run the same code`),
    );
  }

  // Wiring: a passing test of the variant's own that covers its last step (§5.2e, rule 4).
  const last = steps[steps.length - 1];
  const wired = last !== undefined && (byStep.get(last) ?? []).length > 0;
  if (!wired) {
    findings.push(
      new Finding(
        "variant_unwired",
        `${cardId}: no passing test of its own covers its last step \`${last ?? "(none)"}\` — ${inherits.length} inherited step(s) get no credit`,
        haveReport ? "error" : "warning",
      ),
    );
  }

  const originalSteps = new Set(stepIdsOf(original));
  const originalGaps = gapStepsOf(original);
  const originalProof = ownProof.get(originalId) ?? new Map<string, string[]>();
  for (const step of inherits) {
    if (!originalSteps.has(step)) {
      findings.push(new Finding("variant_step_unknown", `${cardId}: inherits \`${step}\`, which \`${originalId}\` has no step called`));
      explained.add(step);
      continue;
    }
    if (!codeShared || !wired) {
      explained.add(step);
      continue;
    }
    // A gap the original declares passes nothing on; the variant then answers for the step itself.
    if (!originalGaps.has(step) && (originalProof.get(step) ?? []).length > 0) credited.add(step);
  }
  return { credited, explained };
}

// ── check 3 — no inflated maturity ────────────────────────────────────────────────────────────
//
// Three claims of different natures wear one field. Only the first is verifiable against the
// repository, the second is derived from check 2, and the third can only be made to expire.

const LEVELS = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"];
const LINE_SUFFIX = /:\d+$/;
const DEFAULT_HORIZON_DAYS = 180;

/**
 * `implemented` is one path or several — one example joins two with ' + '. A value that is not a
 * string is absent (1.5.1): `true` was the path `true` here and `True` in the Python prototype.
 */
export function evidencePaths(value: unknown): string[] {
  const values = typeof value === "string" ? [value] : texts(value);
  const paths: string[] = [];
  for (const item of values) {
    for (const part of item.split("+")) {
      const trimmed = part.trim().replace(LINE_SUFFIX, "");
      if (trimmed) paths.push(trimmed);
    }
  }
  return paths;
}

function daysBetween(from: Date, to: Date): number {
  return Math.floor((to.getTime() - from.getTime()) / 86_400_000);
}

export function checkMaturity(config: Config, base: string, today = new Date()): CheckResult {
  const findings: Finding[] = [];
  const { cases } = loadReport(config, base);
  const haveReport = cases.length > 0;
  const { byFull, byName } = indexReport(cases);

  const codeRoot = config.code_root;
  const root = codeRoot ? join(base, codeRoot) : null;
  // A misspelt `code_root` otherwise reports every evidence path as missing from the repository,
  // which is both false and one error per card. Cascading noise is how a checker teaches people
  // to stop reading it — say the true thing once instead.
  if (root && !existsSync(root)) {
    return {
      findings: [new Finding("code_root_missing", `\`code_root\` points at \`${codeRoot}\`, which does not exist — check 3 cannot verify any path`)],
      summary: { cards: 0, paths_checked: 0, code_root: codeRoot ?? "", horizon: config.evidence_horizon_days ?? 180 },
    };
  }
  const horizon = config.evidence_horizon_days ?? DEFAULT_HORIZON_DAYS;

  const { cards, findings: cardFindings } = loadCardFiles(config, base);
  findings.push(...cardFindings);
  let checkedPaths = 0;

  for (const [cardId, fm] of cards as [string, Card][]) {
    const maturity = text(fm["maturity"]) ?? "";
    if (!LEVELS.includes(maturity)) continue;
    const level = LEVELS.indexOf(maturity);
    const evidence = map(fm["maturity_evidence"]);

    // Tier 1 — the code the card points at exists.
    if (level >= LEVELS.indexOf("implemented") && evidence["implemented"] && root) {
      for (const path of evidencePaths(evidence["implemented"])) {
        checkedPaths += 1;
        if (!existsSync(join(root, path))) {
          findings.push(new Finding("evidence_path_missing", `${cardId}: \`${path}\` is not in the repository`));
        }
      }
    }

    // Tier 2 — the claim is derived from the report, not from prose.
    const passing: string[] = [];
    const covered = new Set<string>();
    for (const test of maps(fm["tests"])) {
      const testId = text(test["id"]) ?? "";
      const matched = haveReport ? findCases(testId, byFull, byName) : [];
      if (matched.length > 0 && matched.every((c) => c.status === "passed")) {
        passing.push(testId);
        for (const ref of coversOf(test)) covered.add(ref);
      }
    }

    if (level >= LEVELS.indexOf("tested") && passing.length === 0) {
      findings.push(
        new Finding(
          "maturity_without_passing_test",
          `${cardId}: claims \`${maturity}\` with no test of its own passing in the report`,
          haveReport ? "error" : "warning",
        ),
      );
    }

    // Only below `implemented`. A passing test is *necessary* to claim `tested`, not sufficient
    // for it — one smoke test does not make an operation covered, and a checker cannot judge
    // which it is. Nagging every honest `implemented` card would retire this rule within a week.
    // And only when a passing test covers the LAST step — the proof §5.2e rule 4 accepts that an
    // operation goes all the way through. Tests of the door alone (sign-in, permission) pass in
    // front of an operation that answers 501; that card is honestly `designed`.
    const stepIds = stepIdsOf(fm);
    const last = stepIds.length > 0 ? stepIds[stepIds.length - 1] : undefined;
    if (haveReport && level < LEVELS.indexOf("implemented") && last !== undefined && covered.has(last)) {
      findings.push(
        new Finding(
          "maturity_understated",
          `${cardId}: claims \`${maturity}\` while a passing test of its own covers its last step \`${last}\` (${passing.length} of its tests pass)`,
          "warning",
        ),
      );
    }

    // Tier 3 — what cannot be verified must expire.
    if (level >= LEVELS.indexOf("in_production")) {
      // A dated map or a bare string (the schema's two forms); any other value is absent (1.5.1).
      const deployed = evidence["deployed"];
      if (isMap(deployed)) {
        // A day the calendar has (1.4.3): `new Date` carried 2026-02-30 over to 2 March and called it
        // stale, where the Python prototype said it is not a date. Year 0 is none either.
        const raw = typeof deployed.since === "string" ? deployed.since : "";
        const since = new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw) ? `${raw}T00:00:00Z` : NaN);
        if (Number.isNaN(since.getTime()) || since.getUTCFullYear() < 1 || since.toISOString().slice(0, 10) !== raw) {
          findings.push(new Finding("evidence_undated", `${cardId}: \`deployed.since\` is not a date`));
          continue;
        }
        const age = daysBetween(since, today);
        if (age > horizon) {
          findings.push(
            new Finding(
              "evidence_stale",
              `${cardId}: \`deployed\` was last affirmed ${age} days ago (horizon ${horizon}) — nobody has looked since`,
              "warning",
            ),
          );
        }
      } else if (typeof deployed === "string" && deployed) {
        findings.push(
          new Finding("evidence_undated", `${cardId}: \`deployed: ${deployed}\` carries no date, so it can never go stale`, "warning"),
        );
      }
    }
  }

  return { findings, summary: { cards: cards.length, paths_checked: checkedPaths, code_root: codeRoot ?? "", horizon } };
}

// ── check 4 — no imagined storage ─────────────────────────────────────────────────────────────
//
// The same shape as check 1, one layer down: the storage says what it is — which stores exist,
// what they are keyed by, which secondary indexes they carry — and the cards are compared with
// that. Nothing reads a repository class or a mapping attribute.
//
// It exists because `data.entities: [request]` was the whole of what a card said about storage:
// a logical noun, true by construction, falsifiable by nothing. Meanwhile the only human-written
// statement about tables in that repository — a comment in appsettings.json — had already gone
// stale, listing four tables while the code used at least six.
//
// What this check deliberately does NOT do: verify which ATTRIBUTES an operation writes. A
// schemaless store declares its keys and indexes and knows nothing about the rest, so a
// `fields_touched` check would be a promise the storage cannot keep. A check that cannot fail is
// not a check.
export function checkStorage(config: Config, base: string): CheckResult {
  const findings: Finding[] = [];
  const location = (config as any).storage_inventory as string | undefined;

  if (!location) {
    return {
      findings: [
        new Finding(
          "storage_inventory_missing",
          "no `storage_inventory` in the config — check 4 cannot run and is NOT considered passed",
        ),
      ],
      summary: { stores: 0, claims: 0, produced_by: "", touched: 0 },
    };
  }

  const path = join(base, location);
  if (!existsSync(path)) {
    return {
      findings: [new Finding("storage_inventory_missing", `${location} does not exist`)],
      summary: { stores: 0, claims: 0, produced_by: "", touched: 0 },
    };
  }

  const data = JSON.parse(readFileSync(path, "utf8"));
  if (data.usedesign_storage_inventory !== 1) {
    findings.push(new Finding("storage_inventory_malformed", `${location}: missing \`usedesign_storage_inventory: 1\``));
  }
  if (!data.produced_by) findings.push(new Finding("storage_inventory_malformed", `${location}: missing \`produced_by\``));

  const stores: any[] = data.stores ?? [];
  if (stores.length === 0) {
    findings.push(
      new Finding("storage_inventory_empty", `${location}: no stores — almost always a failed dump rather than a system without storage`),
    );
  }

  const { cards, findings: cardFindings } = loadCardFiles(config, base);
  findings.push(...cardFindings);

  const touched = new Set<string>();
  let claims = 0;

  for (const [cardId, fm] of cards) {
    for (const claim of maps(map(fm["data"])["storage"])) {
      claims += 1;
      const pattern = text(claim["store"]) ?? "";
      const matched = stores.filter((store) => globMatches(String(store.name), pattern));

      if (matched.length === 0) {
        findings.push(
          new Finding("unknown_store", `${cardId}: claims store \`${pattern}\`, which the storage does not have`),
        );
        continue;
      }
      for (const store of matched) touched.add(String(store.name));

      // Every environment must agree, or the card is true in one place and false in another.
      const claimedKeys = texts(claim["keyed_by"]);
      if (claimedKeys.length > 0) {
        for (const store of matched) {
          const actual: string[] = store.keyed_by ?? [];
          if (claimedKeys.join(",") !== actual.join(",")) {
            findings.push(
              new Finding(
                "store_key_mismatch",
                `${cardId}: claims \`${pattern}\` is keyed by [${claimedKeys.join(", ")}], but \`${store.name}\` is keyed by [${actual.join(", ")}]`,
              ),
            );
          }
        }
      }

      const index = text(claim["via_index"]);
      if (index) {
        for (const store of matched) {
          const names = (store.indexes ?? []).map((i: any) => String(i.name));
          if (!names.includes(index)) {
            findings.push(
              new Finding(
                "unknown_index",
                `${cardId}: depends on index \`${index}\` of \`${store.name}\`, which has ${names.length ? names.join(", ") : "no indexes"}`,
              ),
            );
          }
        }
      }
    }
  }

  // The mirror of a wild endpoint, and the question nobody asks out loud: what do we keep that
  // no description accounts for? A warning, because storage outlives the operations that filled
  // it — an abandoned store is a finding about the system, not a broken card.
  for (const store of stores) {
    if (!touched.has(String(store.name))) {
      findings.push(
        new Finding("undescribed_store", `${store.name} exists but no card says anything about it`, "warning"),
      );
    }
  }

  return {
    findings,
    summary: { stores: stores.length, claims, touched: touched.size, produced_by: data.produced_by ?? "" },
  };
}

// ── check 5 — the form matches its contract ───────────────────────────────────────────────────
//
// The one check whose reference is authored rather than measured. A form contract says what the
// owner decided the screen must show; the form inventory says what the rendered screen actually
// carries, state by state — produced by rendering the real components in a test, never by parsing
// their source. This check holds the two against each other.
//
// Contract lines the code has not caught up with are the point, not a malfunction: they are the
// product's TODO list, printed by every build until the code arrives. The reverse direction is a
// warning — an element no contract accounts for is the mirror of a wild endpoint.
//
// One rule reaches across artifacts: a control naming the operation it calls must be shown
// exactly in the states that operation departs from (`data_transition.from`). Measured twice
// before being written, zero exceptions: finish from `active`, edit from `pending`.
//
// Screen states are not data states (issue #11): a create form has `absent`, then `links_blocked`
// (a malformed URL typed, the submit greyed out with its reason) — both `absent` for the data.
// The contract's `states:` map says which data state each screen state lives in; the rule above
// compares THROUGH the map. Unmapped states map to themselves, so a contract without the map
// behaves exactly as before.

/**
 * A family pattern (issue #10): `*` matches any run of characters, everything else is literal.
 * Deliberately not a glob library — one wildcard is all a contract should ever need, and a
 * pattern must stay rare and conspicuous: "the set of names lives elsewhere, on purpose".
 */
export function familyRegex(pattern: string): RegExp {
  const escaped = pattern.split("*").map((part) => part.replace(/[.*+?^{}$()|[\]\\]/g, "\\$&"));
  return new RegExp("^" + escaped.join(".*") + "$");
}

/**
 * An element shown in a state outside its `when` (round 26 ⑫). Controls had this check from the
 * start (`control_out_of_state`); elements checked only the other direction, so a refusal caption
 * leaking into every state passed. A warning, not an error: it is a new check over a field that
 * already exists, and 1.x does not turn a clean contract red (§8).
 */
function fieldOutOfState(
  contractId: string,
  name: string,
  when: unknown,
  states: Map<string, { fields: Set<string> }>,
  present: (rendered: { fields: Set<string> }) => boolean,
  findings: Finding[],
): void {
  if (!Array.isArray(when)) return;
  for (const [state, rendered] of states) {
    if (!when.includes(state) && present(rendered)) {
      findings.push(
        new Finding("field_out_of_state", `${contractId}: \`${name}\` appears in state \`${state}\`, outside its declared \`when\``, "warning"),
      );
    }
  }
}

/**
 * The card-only half of the controls rule: every operation of a `calls` chain is described by a
 * card, and a control shown in a state its first operation cannot depart from is a conflict. It
 * reads the contract and the cards, never the inventory — so since round 29 (issue #13) it runs
 * twice over: for a rendered screen, where the conflict is an error, and for a contract designed
 * ahead of its screen, where it is a warning (a new check over existing fields, §8). The two paths
 * never meet, so no finding is reported twice.
 */
function judgeCalls(
  contractId: string,
  name: string,
  control: any,
  shownWhen: string[] | undefined,
  dataOf: (state: string) => string,
  cardById: Map<string, Card>,
  findings: Finding[],
  conflict: "error" | "warning",
): void {
  // The measured rule. Only bites when the card exists and moves lifecycle state. A chain
  // (round 27: `calls` as a list, in call order) is judged by its FIRST operation — the chain
  // departs from where that one does; every later step departs from whatever the step before
  // it left, which no screen state shows. Each operation of the chain must still have a card.
  const rawCalls = control?.calls;
  const chain: string[] =
    typeof rawCalls === "string" && rawCalls
      ? [rawCalls]
      : Array.isArray(rawCalls)
        ? rawCalls.filter((entry: unknown) => typeof entry === "string" && entry).map(String)
        : [];
  for (const [step, later] of chain.entries()) {
    if (step > 0 && !cardById.has(later)) {
      findings.push(new Finding("form_calls_undescribed", `${contractId}: control \`${name}\` calls \`${later}\` (step ${step + 1} of ${chain.length}), which no card describes`, "warning"));
    }
  }
  if (chain.length === 0) return;
  // How the first operation is named in a finding: bare for one, with its chain for several.
  const calls = chain.length > 1 ? `\`${chain[0]}\` (first of \`${chain.join(" → ")}\`)` : `\`${chain[0]}\``;
  const card = cardById.get(chain[0]!);
  if (!card) {
    findings.push(new Finding("form_calls_undescribed", `${contractId}: control \`${name}\` calls ${calls}, which no card describes`, "warning"));
    return;
  }
  if (!shownWhen) return;
  // `from` is one state or a SET of states (round 18): the control must be shown only in
  // states that belong to the set, and in at least one of them. `none` / `any` switch the
  // rule off — `any` is the honest word for an operation that does not check its origin.
  const rawFrom = map(card["data_transition"])["from"];
  const fromSet = typeof rawFrom === "string" && rawFrom ? [rawFrom] : texts(rawFrom);
  if (fromSet.length > 0 && !fromSet.includes("none") && !fromSet.includes("any")) {
    const mismatch = shownWhen.filter((state) => !fromSet.includes(dataOf(state)));
    if (mismatch.length > 0 || !shownWhen.some((state) => fromSet.includes(dataOf(state)))) {
      const mapped = shownWhen.some((state) => dataOf(state) !== state) ? ` (data states [${shownWhen.map(dataOf).join(", ")}])` : "";
      findings.push(
        new Finding(
          "shown_when_conflicts_transition",
          `${contractId}: control \`${name}\` is shown in [${shownWhen.join(", ")}]${mapped} but ${calls} departs from \`${fromSet.join(" | ")}\``,
          conflict,
        ),
      );
    }
  }
}

/** A list of state names, or undefined when the field is not a list (1.5.1: a name that is not a string is absent). */
function statesOf(value: unknown): string[] | undefined {
  return Array.isArray(value) ? texts(value) : undefined;
}

/** `at_least`, an integer, or 1. */
function floorOf(line: Record<string, any>): number {
  return Number.isInteger(line["at_least"]) ? Number(line["at_least"]) : 1;
}

export function checkForm(config: Config, base: string): CheckResult {
  const findings: Finding[] = [];
  const patterns = ((config as any).forms as string[] | undefined) ?? [];
  const location = (config as any).form_inventory as string | undefined;
  const empty = { contracts: 0, screens: 0, produced_by: "" };

  if (patterns.length === 0) {
    return {
      findings: [new Finding("form_contracts_missing", "no `forms` patterns in the config — check 5 cannot run and is NOT considered passed")],
      summary: empty,
    };
  }
  if (!location) {
    return {
      findings: [new Finding("form_inventory_missing", "no `form_inventory` in the config — check 5 cannot run and is NOT considered passed")],
      summary: empty,
    };
  }
  const inventoryPath = join(base, location);
  if (!existsSync(inventoryPath)) {
    return { findings: [new Finding("form_inventory_missing", `${location} does not exist`)], summary: empty };
  }

  const data = JSON.parse(readFileSync(inventoryPath, "utf8"));
  if (data.usedesign_form_inventory !== 1) {
    findings.push(new Finding("form_inventory_malformed", `${location}: missing \`usedesign_form_inventory: 1\``));
  }
  if (!data.produced_by) findings.push(new Finding("form_inventory_malformed", `${location}: missing \`produced_by\``));

  type RenderedState = { fields: Set<string>; controls: Set<string>; within: Map<string, Set<string>> | null };
  const byScreen = new Map<string, Map<string, RenderedState>>();
  for (const form of data.forms ?? []) {
    const states = new Map<string, RenderedState>();
    for (const s of form.states ?? []) {
      // `within` is optional: an inventory that predates container recording gets membership
      // NOT JUDGED, never failed — absence of the measurement is not evidence of misplacement.
      const within = s.within && typeof s.within === "object"
        ? new Map<string, Set<string>>(Object.entries(s.within).map(([k, v]) => [k, new Set((v as any[]).map(String))]))
        : null;
      states.set(String(s.state), { fields: new Set((s.fields ?? []).map(String)), controls: new Set((s.controls ?? []).map(String)), within });
    }
    byScreen.set(String(form.screen), states);
  }

  // Cards, for the shown_when ↔ data_transition.from rule. A frontend repository may declare
  // `cards:` pointing at a sibling checkout that is not always there (a gate without its read
  // token); then the glob matches nothing, and every `calls:` below turns into "undescribed" —
  // which reads as a fact about the cards when it is a fact about the checkout. Named once.
  const { cards, findings: cardFindings } = loadCardFiles(config, base);
  if ((config as any).cards && cardFindings.some((f) => f.code === "no_cards_found")) {
    findings.push(
      new Finding("no_cards_found", "the `cards` patterns matched nothing — every `calls:` below is unverifiable here, not undescribed", "warning"),
    );
  }
  const cardById = new Map<string, Card>(cards);

  const contracts: [string, Card][] = [];
  const read: [string, Card][] = [];
  for (const path of expandGlobs(base, patterns)) {
    const fm = readDocument(path);
    if (isMap(fm) && fm["usedesign_form"] === 1) {
      contracts.push([text(fm["id"]) ?? path, fm]);
      read.push([path, fm]);
    }
  }
  refuseTwins(read);
  if (contracts.length === 0) {
    findings.push(new Finding("form_contracts_missing", "the `forms` patterns matched no contract"));
  }

  type Claimed = { fields: Set<string>; controls: Set<string>; fieldFamilies: RegExp[]; controlFamilies: RegExp[] };
  const claimed = new Map<string, Claimed>();
  let designedAhead = 0;

  for (const [contractId, fm] of contracts) {
    const screen = text(fm["screen"]) ?? "";
    const states = byScreen.get(screen);
    // A contract may be written before its screen — the format's own recommended order of
    // work — and say so with `maturity: designed` (issue #8, the forms twin of issue #3). Then
    // an absent screen is a warning, not the same error as a screen that vanished. The flag
    // cannot go stale silently: the day the screen renders, the contract still saying
    // `designed` is reported too — the gate itself tells the owner to flip it.
    const maturity = text(fm["maturity"]) || "implemented";
    // Screen state → data state, through the contract's `states:` map; identity when unmapped.
    // Looked up among the map's own keys: `toString` is not a state.
    const stateMap = map(fm["states"]);
    const dataOf = (state: string): string => {
      const spec = Object.prototype.hasOwnProperty.call(stateMap, state) ? stateMap[state] : undefined;
      return (isMap(spec) && text(spec["data"])) || state;
    };
    if (!states) {
      if (maturity === "designed") {
        designedAhead += 1;
        findings.push(
          new Finding(
            "form_not_yet_built",
            `${contractId}: screen \`${screen}\` is absent from the inventory — designed ahead of the code (\`maturity: designed\`)`,
            "warning",
          ),
        );
        // `calls` is chosen while the contract is `designed` — the format's own order of work —
        // and comparing it with the cards needs no inventory (issue #13). Only where the config
        // declares `cards:`: a frontend-only repository has none, and stays as quiet as before.
        if ((config as any).cards) {
          for (const control of maps(fm["controls"])) {
            const name = text(control["control_pattern"]) || text(control["control"]) || "";
            judgeCalls(contractId, name, control, statesOf(control["shown_when"]), dataOf, cardById, findings, "warning");
          }
        }
      } else {
        findings.push(new Finding("form_screen_missing", `${contractId}: screen \`${screen}\` is absent from the inventory — nothing rendered it`));
      }
      continue;
    }
    if (maturity === "designed") {
      findings.push(
        new Finding(
          "form_maturity_stale",
          `${contractId}: screen \`${screen}\` is rendered but the contract still says \`maturity: designed\` — the contract is behind the code`,
          "warning",
        ),
      );
    }
    const everyState = [...states.keys()];
    const mine = claimed.get(screen) ?? { fields: new Set(), controls: new Set(), fieldFamilies: [], controlFamilies: [] };
    claimed.set(screen, mine);

    const countOf = (regex: RegExp, set: Set<string>) => [...set].filter((name) => regex.test(name)).length;

    for (const entry of maps(fm["presents"])) {
      const pattern = text(entry["field_pattern"]) ?? "";
      const when = statesOf(entry["when"]);
      if (pattern) {
        // A family: one element per item of a list that arrives at runtime. Every rendered
        // anchor matching the pattern is accounted for; `at_least` keeps the family from
        // silently becoming empty — a screen rendering NO tabs because the backend returned
        // nothing is a real failure, and without the floor nothing would notice.
        const regex = familyRegex(pattern);
        const atLeast = floorOf(entry);
        mine.fieldFamilies.push(regex);
        for (const state of when ?? everyState) {
          const rendered = states.get(state);
          if (!rendered) {
            findings.push(new Finding("form_state_missing", `${contractId}: \`${pattern}\` is required in state \`${state}\`, which the inventory never rendered`));
          } else {
            const count = countOf(regex, rendered.fields);
            if (count < atLeast) {
              findings.push(
                new Finding("element_missing", `${contractId}: \`${pattern}\` must match at least ${atLeast} element(s) in state \`${state}\` and matches ${count}`),
              );
            }
          }
        }
        fieldOutOfState(contractId, pattern, when, states, (rendered) => countOf(regex, rendered.fields) > 0, findings);
        continue;
      }
      const field = text(entry["field"]) ?? "";
      mine.fields.add(field);
      for (const state of when ?? everyState) {
        const rendered = states.get(state);
        if (!rendered) {
          findings.push(new Finding("form_state_missing", `${contractId}: \`${field}\` is required in state \`${state}\`, which the inventory never rendered`));
        } else if (!rendered.fields.has(field)) {
          findings.push(new Finding("element_missing", `${contractId}: \`${field}\` must be shown in state \`${state}\` and is not`));
        }
      }
      fieldOutOfState(contractId, field, when, states, (rendered) => rendered.fields.has(field), findings);
    }

    for (const control of maps(fm["controls"])) {
      const pattern = text(control["control_pattern"]) ?? "";
      const regex = pattern ? familyRegex(pattern) : null;
      const atLeast = floorOf(control);
      const name = pattern || (text(control["control"]) ?? "");
      if (regex) mine.controlFamilies.push(regex);
      else mine.controls.add(name);
      const shownWhen = statesOf(control["shown_when"]);
      // For a literal both questions are "is it there"; for a family they differ: enough
      // members for the floor, versus any member at all (which is what leaks out of state).
      const enough = (rendered: RenderedState) => (regex ? countOf(regex, rendered.controls) >= atLeast : rendered.controls.has(name));
      const anyOf = (rendered: RenderedState) => (regex ? countOf(regex, rendered.controls) > 0 : rendered.controls.has(name));

      if (shownWhen) {
        for (const state of shownWhen) {
          const rendered = states.get(state);
          if (!rendered) {
            findings.push(new Finding("form_state_missing", `${contractId}: control \`${name}\` is required in state \`${state}\`, which the inventory never rendered`));
          } else if (!enough(rendered)) {
            findings.push(
              new Finding(
                "control_missing",
                regex
                  ? `${contractId}: \`${name}\` must match at least ${atLeast} control(s) in state \`${state}\` and matches ${countOf(regex, rendered.controls)}`
                  : `${contractId}: control \`${name}\` must be available in state \`${state}\` and is not`,
              ),
            );
          }
        }
        for (const [state, rendered] of states) {
          if (!shownWhen.includes(state) && anyOf(rendered)) {
            findings.push(
              new Finding("control_out_of_state", `${contractId}: control \`${name}\` appears in state \`${state}\`, outside its declared \`shown_when\``),
            );
          }
        }
      } else if (atLeast > 0 && ![...states.values()].some(anyOf)) {
        // Rule-based availability: presence somewhere is all the inventory can prove.
        findings.push(new Finding("control_missing", `${contractId}: control \`${name}\` appears in no state at all`));
      }

      judgeCalls(contractId, name, control, shownWhen, dataOf, cardById, findings, "error");
    }

    for (const entry of maps(fm["removed"])) {
      const name = text(entry["control"]) ?? "";
      mine.controls.add(name);
      for (const [state, rendered] of states) {
        if (rendered.controls.has(name)) {
          findings.push(new Finding("removed_control_present", `${contractId}: control \`${name}\` was removed by the owner's decision yet appears in state \`${state}\``));
        }
      }
    }

    // A group's anchor is accounted for BY the group line: the owner named the container when
    // grouping by it. Warning about it as undescribed would ask the owner to decide what they
    // already decided — measured 19.08: three of fourteen warnings were exactly this noise.
    for (const group of maps(fm["groups"])) {
      const gname = text(group["group"]);
      if (gname) mine.fields.add(gname);
    }

    // ── group membership ───────────────────────────────────────────────────────────────────
    // The contract seats elements in groups; the inventory's `within` records which containers
    // each anchor ACTUALLY rendered inside (full ancestor chain, instances merged). Judged only
    // where the member renders and the inventory carries the measurement. The first inventory
    // with containers refuted its own contract: `add-set` was contracted into the footer and
    // measured living only in the set table — the checker's first catch was its author.
    for (const group of maps(fm["groups"])) {
      const gname = text(group["group"]) ?? "";
      if (!gname) continue;
      const anchorSeen = [...states.values()].some(
        (r) => r.fields.has(gname) || (r.within !== null && [...r.within.values()].some((chain) => chain.has(gname))),
      );
      if (!anchorSeen) {
        findings.push(new Finding("group_missing", `${contractId}: group \`${gname}\` is contracted but its anchor never renders`));
      }
      for (const member of texts(group["contains"])) {
        // A family seated in a group: every rendered member of the family must sit there.
        const regex = member.includes("*") ? familyRegex(member) : null;
        for (const [state, rendered] of states) {
          if (rendered.within === null) continue;
          const present = regex
            ? [...rendered.fields, ...rendered.controls].filter((anchor) => regex.test(anchor))
            : rendered.fields.has(member) || rendered.controls.has(member) ? [member] : [];
          const offender = present.find((anchor) => !(rendered.within!.get(anchor) ?? new Set<string>()).has(gname));
          if (offender !== undefined) {
            const chain = rendered.within.get(offender) ?? new Set<string>();
            findings.push(
              new Finding(
                "member_out_of_group",
                `${contractId}: \`${offender}\` is contracted into \`${gname}\` but in state \`${state}\` renders inside [${[...chain].sort().join(", ")}]`,
              ),
            );
            break;
          }
        }
      }
    }
  }

  // The mirror of a wild endpoint: rendered, accounted for by nobody. A family line accounts
  // for every anchor it matches — that is the whole point of declaring one.
  for (const [screen, states] of byScreen) {
    const mine = claimed.get(screen);
    if (!mine) {
      // A screen with no contract is not judged element by element — contracts are opt-in per
      // screen. But it is no longer silent (round 26 ⑭): 13 contracts against 22 rendered screens
      // gave zero signals, while the opposite drift (a typo in `screen:`) was always an error.
      // The mirror of check 1's wild endpoint, one level up; a warning unless the config opts in.
      findings.push(
        new Finding(
          "form_uncontracted_screen",
          `${screen}: rendered in ${states.size} state(s) and described by no contract`,
          config.uncontracted_screens === "error" ? "error" : "warning",
        ),
      );
      continue;
    }
    const seen = new Set<string>();
    for (const [, rendered] of states) {
      for (const field of rendered.fields) {
        if (!mine.fields.has(field) && !mine.fieldFamilies.some((r) => r.test(field)) && !seen.has(`f:${field}`)) {
          seen.add(`f:${field}`);
          findings.push(new Finding("undescribed_element", `${screen}: \`${field}\` is rendered but no contract line accounts for it`, "warning"));
        }
      }
      for (const control of rendered.controls) {
        if (!mine.controls.has(control) && !mine.controlFamilies.some((r) => r.test(control)) && !seen.has(`c:${control}`)) {
          seen.add(`c:${control}`);
          findings.push(new Finding("undescribed_element", `${screen}: control \`${control}\` is rendered but no contract line accounts for it`, "warning"));
        }
      }
    }
  }

  return {
    findings,
    summary: { contracts: contracts.length, screens: byScreen.size, designed_ahead: designedAhead, produced_by: data.produced_by ?? "" },
  };
}

export const CHECKS: Record<number, (config: Config, base: string) => CheckResult> = {
  1: checkRoutes,
  2: checkCoverage,
  3: checkMaturity,
  4: checkStorage,
  5: checkForm,
};
