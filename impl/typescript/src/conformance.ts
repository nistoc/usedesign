/**
 * The conformance corpora, run by this implementation.
 *
 * An implementation passes when, for each case, it reaches the same verdict AND reports the same
 * diagnostic codes. Agreeing that something is wrong while disagreeing on what is wrong is how
 * dialects start — so a missing code fails the case just as a wrong verdict does.
 */
import { readFileSync } from "node:fs";
import { basename, join } from "node:path";
import { parse as parseYaml } from "yaml";
import { CHECKS } from "./checks.js";
import { codesOf, errors, Finding, frontMatter, loadConfig, warnings } from "./core.js";
import { REPO, validate, validateForm, validateFormSchema, validateSchema } from "./validate.js";

export interface CorpusResult {
  passed: number;
  failed: number;
}

const CARDS = join(REPO, "tests", "conformance");
const CHECKS_CORPUS = join(CARDS, "checks");

function report(name: string, problems: string[], reported: string[]): void {
  if (problems.length > 0) {
    console.log(`  FAIL  ${name}`);
    for (const problem of problems) console.log(`          ${problem}`);
    if (reported.length > 0) console.log(`          reported: ${reported.join(", ")}`);
  } else {
    console.log(`  ok    ${name}${reported.length > 0 ? `  [${reported.join(", ")}]` : ""}`);
  }
}

/** The 14 card cases: does this card mean anything, and if not, why not. */
export function runCardCorpus(withSchema = true): CorpusResult {
  const manifest = parseYaml(readFileSync(join(CARDS, "manifest.yaml"), "utf8"));
  let passed = 0;
  let failed = 0;

  for (const testCase of manifest.cases) {
    const path = join(CARDS, "cases", ...String(testCase.file).split("/"));
    const fm = frontMatter(path);
    const findings: Finding[] = !fm
      ? [new Finding("missing_required_field", "no front matter")]
      : fm["usedesign_form"] === 1
        ? [...(withSchema ? validateFormSchema(fm) : []), ...validateForm(fm, basename(path))]
        : [...(withSchema ? validateSchema(fm) : []), ...validate(fm, basename(path))];

    const failing = errors(findings);
    const verdict = failing.length > 0 ? "invalid" : "valid";
    const reported = codesOf(failing);
    const warned = codesOf(warnings(findings));

    const problems: string[] = [];
    if (verdict !== testCase.expect) problems.push(`expected ${testCase.expect}, got ${verdict}`);
    for (const code of testCase.codes ?? []) {
      if (!reported.includes(code)) problems.push(`missing code \`${code}\``);
    }
    // Warnings are part of the contract too: a rule that only warns is still a rule two
    // implementations must agree about, and until now nothing here compared them.
    for (const code of testCase.warnings ?? []) {
      if (!warned.includes(code)) problems.push(`missing warning \`${code}\``);
    }

    report(testCase.file, problems, reported);
    problems.length > 0 ? (failed += 1) : (passed += 1);
  }

  console.log(`\ncards conformance: ${passed} passed, ${failed} failed`);
  return { passed, failed };
}

/** The 20 repository cases: do the cards still match what the repository does. */
export function runChecksCorpus(): CorpusResult {
  const manifest = parseYaml(readFileSync(join(CHECKS_CORPUS, "manifest.yaml"), "utf8"));
  let passed = 0;
  let failed = 0;

  for (const testCase of manifest.cases) {
    const { config, base } = loadConfig(join(CHECKS_CORPUS, "cases", testCase.dir, "usedesign.config.yaml"));
    const runner = CHECKS[testCase.check ?? 1]!;
    const { findings } = runner(config, base);

    const failing = errors(findings);
    const verdict = failing.length > 0 ? "fail" : "pass";
    const codes = codesOf(failing);
    const warned = codesOf(warnings(findings));

    const problems: string[] = [];
    if (verdict !== testCase.expect) problems.push(`expected ${testCase.expect}, got ${verdict}`);
    for (const code of testCase.codes ?? []) {
      if (!codes.includes(code)) problems.push(`missing code \`${code}\``);
    }
    for (const code of testCase.warnings ?? []) {
      if (!warned.includes(code)) problems.push(`missing warning \`${code}\``);
    }

    report(testCase.dir, problems, [...codes, ...warned]);
    problems.length > 0 ? (failed += 1) : (passed += 1);
  }

  console.log(`\nchecks conformance: ${passed} passed, ${failed} failed`);
  return { passed, failed };
}
