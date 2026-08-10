#!/usr/bin/env node
/**
 * usedesign — the command line.
 *
 *   usedesign validate <path…>     cards against the schema and the cross-card rules
 *   usedesign check <config>       the three invariants against the repository
 *   usedesign conformance          the corpora this implementation must pass
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { CHECKS, checkCoverage, checkMaturity, checkRoutes } from "./checks.js";
import { codesOf, collectCards, errors, Finding, frontMatter, loadConfig, warnings } from "./core.js";
import { runCardCorpus, runChecksCorpus } from "./conformance.js";
import { validate, validateSchema } from "./validate.js";

/**
 * The version is read from package.json, never written here. It was written here once, and the
 * published 0.3.0 introduced itself as 0.2.0 — the tool that checks other people's claims against
 * their code was making a claim about itself that nothing compared to anything. Found by asking
 * the published box its version while watching it run a rule only the new version has.
 */
function version(): string {
  const path = join(dirname(fileURLToPath(import.meta.url)), "..", "package.json");
  return JSON.parse(readFileSync(path, "utf8")).version;
}

const USAGE = `usedesign — one description per operation, checked against the repository

Usage:
  usedesign validate <path…>          validate cards (files or directories)
  usedesign check <config>            run the three checks against a usedesign.config.yaml
  usedesign conformance [--cards|--checks]
                                      run the conformance corpora
  usedesign --help | --version

Options:
  --no-schema                        validate: skip the JSON Schema, keep the cross-card rules
`;

function print(findings: Finding[], prefix = ""): void {
  for (const finding of findings) {
    console.log(`  ${finding.severity === "error" ? "ERROR  " : "warning"}  ${prefix}${finding}`);
  }
}

function summarise(title: string, findings: Finding[]): number {
  print(findings);
  console.log(`  → ${title}: ${errors(findings).length} error(s), ${warnings(findings).length} warning(s)\n`);
  return errors(findings).length;
}

function commandValidate(paths: string[], withSchema: boolean): number {
  const files = collectCards(paths);
  const cards = new Map<string, { path: string; fm: Record<string, any> }>();
  for (const path of files) {
    const fm = frontMatter(path);
    if (fm) cards.set(String(fm["id"]), { path, fm });
  }
  const known = new Set(cards.keys());

  let errorCount = 0;
  let warningCount = 0;
  for (const [, { path, fm }] of [...cards.entries()].sort()) {
    const findings = [...(withSchema ? validateSchema(fm) : []), ...validate(fm, path, known)];
    const name = path.split(/[\\/]/).pop();
    print(findings, `${name}: `);
    errorCount += errors(findings).length;
    warningCount += warnings(findings).length;
  }
  console.log(`\n${cards.size} card(s): ${errorCount} error(s), ${warningCount} warning(s)`);
  return errorCount > 0 ? 1 : 0;
}

function commandCheck(configPath: string): number {
  const { config, base } = loadConfig(configPath);

  const routes = checkRoutes(config, base);
  const s = routes.summary as Record<string, any>;
  console.log(`inventory:  ${s["served"]} route(s) served${s["produced_by"] ? `, produced by ${s["produced_by"]}` : ""}`);
  console.log(`cards:      ${s["declared"]} REST route(s) declared`);
  console.log(`excluded:   ${s["excluded"]} route(s)`);
  for (const [pattern, count] of Object.entries(s["hidden_per_rule"] as Record<string, number>)) {
    console.log(`              ${pattern} → ${count}`);
  }
  console.log();
  let errorCount = summarise("check 1 (no wild endpoints)", routes.findings);

  const coverage = checkCoverage(config, base);
  const c = coverage.summary as Record<string, any>;
  console.log(`report:     ${c["report_cases"]} test case(s)`);
  console.log(`steps:      ${c["proven"]} proven, ${c["unproven"]} not\n`);
  errorCount += summarise("check 2 (no unproven steps)", coverage.findings);

  const maturity = checkMaturity(config, base);
  const m = maturity.summary as Record<string, any>;
  console.log(
    `cards:      ${m["cards"]} card(s), ${m["paths_checked"]} evidence path(s) checked` +
      (m["code_root"] ? "" : " — no `code_root`, path check NOT RUN"),
  );
  console.log(`horizon:    ${m["horizon"]} days\n`);
  errorCount += summarise("check 3 (no inflated maturity)", maturity.findings);

  return errorCount > 0 ? 1 : 0;
}

function main(argv: string[]): number {
  const args = argv.slice(2);
  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    console.log(USAGE);
    return args.length === 0 ? 2 : 0;
  }
  if (args.includes("--version") || args.includes("-v")) {
    console.log(`usedesign ${version()} (SPEC v0.2)`);
    return 0;
  }

  const [command, ...rest] = args;
  const flags = rest.filter((a) => a.startsWith("--"));
  const positional = rest.filter((a) => !a.startsWith("--"));

  switch (command) {
    case "validate":
      if (positional.length === 0) {
        console.error("usedesign validate: name at least one card or directory");
        return 2;
      }
      return commandValidate(positional, !flags.includes("--no-schema"));

    case "check":
      if (positional.length !== 1) {
        console.error("usedesign check: name exactly one usedesign.config.yaml");
        return 2;
      }
      return commandCheck(positional[0]!);

    case "conformance": {
      const cardsOnly = flags.includes("--cards");
      const checksOnly = flags.includes("--checks");
      let failed = 0;
      if (!checksOnly) failed += runCardCorpus(!flags.includes("--no-schema")).failed;
      if (!cardsOnly) failed += runChecksCorpus().failed;
      return failed > 0 ? 1 : 0;
    }

    default:
      console.error(`usedesign: unknown command \`${command}\`\n`);
      console.log(USAGE);
      return 2;
  }
}

try {
  process.exit(main(process.argv));
} catch (exc) {
  console.error(`usedesign: ${(exc as Error).message}`);
  process.exit(2);
}

export { CHECKS, codesOf };
