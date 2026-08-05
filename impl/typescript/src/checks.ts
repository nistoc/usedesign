/**
 * The three checks. Each one has the same shape: the repository states a fact in a format it
 * already produces, and usedesign compares that statement with the cards. Nothing here parses a
 * framework, reads source code, or guesses.
 *
 *   1. no wild endpoints      design/route-conformance.md
 *   2. no unproven steps      design/step-coverage.md
 *   3. no inflated maturity   design/maturity-evidence.md
 */
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { XMLParser } from "fast-xml-parser";
import { Card, Config, Finding, loadCardFiles } from "./core.js";

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

function loadDeclared(config: Config, base: string): { declared: Map<string, string[]>; findings: Finding[] } {
  const declared = new Map<string, string[]>();
  const { cards, findings } = loadCardFiles(config, base);

  for (const [cardId, fm] of cards) {
    for (const [name, iface] of Object.entries<any>(fm["interfaces"] ?? {})) {
      if (!iface || typeof iface !== "object" || iface.transport !== "http_rest") continue;
      const { method, path } = iface;
      if (!method || !path) {
        findings.push(
          new Finding("incomplete_rest_interface", `${cardId}: interface \`${name}\` declares http_rest without method or path`),
        );
        continue;
      }
      const key = normalise(method, path);
      declared.set(key, [...(declared.get(key) ?? []), cardId]);
    }
  }

  for (const [key, owners] of [...declared.entries()].sort()) {
    if (owners.length > 1) {
      findings.push(
        new Finding(
          "ambiguous_shape",
          `${key} is declared by ${owners.length} cards (${owners.join(", ")}) — the checker cannot tell them apart`,
          "warning",
        ),
      );
    }
  }
  return { declared, findings };
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

/** Shell-style match for exclusion patterns: `*` and `?` do not cross a `/`. */
function matchesPattern(shape: string, pattern: string): boolean {
  const escaped = pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]");
  return new RegExp(`^${escaped}$`).test(shape);
}

function excludedBy(config: Config, method: string, shape: string): number {
  const rules = config.exclude ?? [];
  for (const [index, rule] of rules.entries()) {
    if (rule.method && rule.method.toUpperCase() !== method) continue;
    if (matchesPattern(shape, rule.path ?? "")) return index;
  }
  return -1;
}

export function checkRoutes(config: Config, base: string): CheckResult {
  const findings: Finding[] = [];
  const { declared, findings: cardFindings } = loadDeclared(config, base);
  findings.push(...cardFindings);

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

  for (const [key, owners] of [...declared.entries()].sort()) {
    const method = key.slice(0, key.indexOf(" "));
    const shape = key.slice(key.indexOf(" ") + 1);
    if (routes.length > 0 && !served.has(key) && excludedBy(config, method, shape) === -1) {
      findings.push(new Finding("phantom_route", `${key} is declared by ${owners.join(", ")} but is not served`));
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

  let tree: any;
  try {
    tree = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@_", isArray: (name) => name === "testcase" }).parse(
      readFileSync(path, "utf8"),
    );
  } catch (exc) {
    return { cases: [], findings: [new Finding("report_malformed", `${location}: ${(exc as Error).message}`)] };
  }

  const cases: TestCase[] = [];
  const walk = (node: any): void => {
    if (!node || typeof node !== "object") return;
    for (const [key, value] of Object.entries<any>(node)) {
      if (key === "testcase") {
        for (const item of Array.isArray(value) ? value : [value]) {
          let status: TestCase["status"] = "passed";
          for (const child of Object.keys(item ?? {})) {
            const tag = child.toLowerCase();
            if (tag === "failure" || tag === "error") status = "failed";
            else if (tag === "skipped") status = "skipped";
          }
          const classname = String(item?.["@_classname"] ?? "");
          const name = String(item?.["@_name"] ?? "");
          cases.push({ classname, name, status, full: classname ? `${classname}.${name}` : name });
        }
      } else if (typeof value === "object") {
        for (const item of Array.isArray(value) ? value : [value]) walk(item);
      }
    }
  };
  walk(tree);

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
  if (byFull.has(testId)) return byFull.get(testId)!;
  if (testId.includes(":")) {
    // file-and-name shape
    const at = testId.lastIndexOf(":");
    const filePart = testId.slice(0, at);
    const candidates = byName.get(testId.slice(at + 1)) ?? [];
    const narrowed = candidates.filter((c) => (c.classname || "").includes(filePart));
    return narrowed.length > 0 ? narrowed : candidates;
  }
  if (byName.has(testId)) return byName.get(testId)!;
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

  for (const [cardId, fm] of cards) {
    const steps: string[] = (fm["steps"] ?? []).map((s: any) => s?.id);
    const gaps = new Set<string>((fm["coverage_gaps"] ?? []).map((g: any) => g?.step));
    const byStep = new Map<string, string[]>();

    for (const test of (fm["tests"] ?? []) as any[]) {
      const refs: any[] = Array.isArray(test?.covers) ? test.covers : [test?.covers];
      const testId: string = test?.id ?? "";
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

    for (const step of steps) {
      if (gaps.has(step)) continue;
      if ((byStep.get(step) ?? []).length > 0) {
        proven += 1;
        continue;
      }
      unproven += 1;
      // A step whose only tests failed or vanished is already reported above; saying it twice
      // trains people to skim.
      if (!byStep.has(step)) {
        findings.push(
          new Finding("step_unproven", `${cardId}: step \`${step}\` has no test and no declared gap`, haveReport ? "error" : "warning"),
        );
      }
    }
  }

  return { findings, summary: { report_cases: cases.length, proven, unproven } };
}

// ── check 3 — no inflated maturity ────────────────────────────────────────────────────────────
//
// Three claims of different natures wear one field. Only the first is verifiable against the
// repository, the second is derived from check 2, and the third can only be made to expire.

const LEVELS = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"];
const LINE_SUFFIX = /:\d+$/;
const DEFAULT_HORIZON_DAYS = 180;

/** `implemented` is one path or several — one example joins two with ' + '. */
export function evidencePaths(value: unknown): string[] {
  const values = Array.isArray(value) ? value : [value];
  const paths: string[] = [];
  for (const item of values) {
    for (const part of String(item).split("+")) {
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
  const horizon = config.evidence_horizon_days ?? DEFAULT_HORIZON_DAYS;

  const { cards, findings: cardFindings } = loadCardFiles(config, base);
  findings.push(...cardFindings);
  let checkedPaths = 0;

  for (const [cardId, fm] of cards as [string, Card][]) {
    const maturity: string = fm["maturity"];
    if (!LEVELS.includes(maturity)) continue;
    const level = LEVELS.indexOf(maturity);
    const evidence: Record<string, any> = fm["maturity_evidence"] ?? {};

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
    for (const test of (fm["tests"] ?? []) as any[]) {
      const matched = haveReport ? findCases(test?.id ?? "", byFull, byName) : [];
      if (matched.length > 0 && matched.every((c) => c.status === "passed")) passing.push(test?.id);
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
    if (haveReport && level < LEVELS.indexOf("implemented") && passing.length > 0) {
      findings.push(
        new Finding("maturity_understated", `${cardId}: claims \`${maturity}\` while ${passing.length} of its tests pass`, "warning"),
      );
    }

    // Tier 3 — what cannot be verified must expire.
    if (level >= LEVELS.indexOf("in_production")) {
      const deployed = evidence["deployed"];
      if (deployed && typeof deployed === "object" && !Array.isArray(deployed)) {
        const raw = String(deployed.since ?? "");
        const since = /^\d{4}-\d{2}-\d{2}$/.test(raw) ? new Date(`${raw}T00:00:00Z`) : new Date("invalid");
        if (Number.isNaN(since.getTime())) {
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
      } else if (deployed) {
        findings.push(
          new Finding("evidence_undated", `${cardId}: \`deployed: ${deployed}\` carries no date, so it can never go stale`, "warning"),
        );
      }
    }
  }

  return { findings, summary: { cards: cards.length, paths_checked: checkedPaths, code_root: codeRoot ?? "", horizon } };
}

export const CHECKS: Record<number, (config: Config, base: string) => CheckResult> = {
  1: checkRoutes,
  2: checkCoverage,
  3: checkMaturity,
};
