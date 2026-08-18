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
import { CHECKS, checkCoverage, checkForm, checkMaturity, checkRoutes, checkStorage } from "./checks.js";
import { codesOf, collectCards, errors, Finding, frontMatter, loadConfig, warnings } from "./core.js";
import { runCardCorpus, runChecksCorpus } from "./conformance.js";
import { planScaffold, writeScaffold } from "./scaffold.js";
import { commandPreview } from "./preview.js";
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
  usedesign scaffold <openapi.json> --out <dir>
                                      draft a card shell per undescribed route
  usedesign preview <config> --out <file.html>
                                      render form contracts as a three-rail wireframe page
  usedesign conformance [--cards|--checks]
                                      run the conformance corpora
  usedesign --help | --version

Options:
  --no-schema                        validate: skip the JSON Schema, keep the cross-card rules
  --config <file>                    scaffold: skip routes already declared or excluded
  --dry-run                          scaffold: print the arithmetic, write nothing
  --force                            scaffold: overwrite drafts already on disk
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

  // `checks: [5]` scopes which checks apply to THIS repository. A frontend serves no routes and
  // owns no tables; running checks 1–4 there fails on inputs that cannot exist, and a check that
  // always fails gets ignored. The scope is declared in the config — visible in review — and
  // within it "cannot run" still means "not passed".
  const scope = (config as any).checks as number[] | undefined;
  const inScope = (n: number) => !scope || scope.includes(n);
  let errorCount = 0;

  if (inScope(1)) {
  const routes = checkRoutes(config, base);
  const s = routes.summary as Record<string, any>;
  console.log(`inventory:  ${s["served"]} route(s) served${s["produced_by"] ? `, produced by ${s["produced_by"]}` : ""}`);
  console.log(`cards:      ${s["declared"]} REST route(s) declared`);
  console.log(`excluded:   ${s["excluded"]} route(s)`);
  for (const [pattern, count] of Object.entries(s["hidden_per_rule"] as Record<string, number>)) {
    console.log(`              ${pattern} → ${count}`);
  }
  console.log();
  errorCount += summarise("check 1 (no wild endpoints)", routes.findings);
  }

  if (inScope(2)) {
  const coverage = checkCoverage(config, base);
  const c = coverage.summary as Record<string, any>;
  console.log(`report:     ${c["report_cases"]} test case(s)`);
  console.log(`steps:      ${c["proven"]} proven, ${c["unproven"]} not\n`);
  errorCount += summarise("check 2 (no unproven steps)", coverage.findings);
  }

  if (inScope(3)) {
  const maturity = checkMaturity(config, base);
  const m = maturity.summary as Record<string, any>;
  console.log(
    `cards:      ${m["cards"]} card(s), ${m["paths_checked"]} evidence path(s) checked` +
      (m["code_root"] ? "" : " — no `code_root`, path check NOT RUN"),
  );
  console.log(`horizon:    ${m["horizon"]} days\n`);
  errorCount += summarise("check 3 (no inflated maturity)", maturity.findings);
  }

  if (inScope(4)) {
  const storage = checkStorage(config, base);
  const g = storage.summary as Record<string, any>;
  console.log(
    `storage:    ${g["stores"]} store(s)${g["produced_by"] ? `, produced by ${g["produced_by"]}` : ""}` +
      `; ${g["claims"]} claim(s) in cards touching ${g["touched"]}`,
  );
  errorCount += summarise("check 4 (no imagined storage)", storage.findings);
  }

  // Check 5 is opt-in: a backend repository has no forms, and a missing section must not read
  // as a failure there. Naming it in `checks:` or declaring `forms:` opts in; then absence of
  // the inventory IS a failure.
  if (scope ? scope.includes(5) : (config as any).forms) {
    const form = checkForm(config, base);
    const f = form.summary as Record<string, any>;
    console.log(
      `forms:      ${f["contracts"]} contract(s) against ${f["screens"]} rendered screen(s)` +
        (f["produced_by"] ? `, produced by ${f["produced_by"]}` : ""),
    );
    errorCount += summarise("check 5 (the form matches its contract)", form.findings);
  }

  return errorCount > 0 ? 1 : 0;
}

/**
 * Generate draft cards for routes nobody has described yet.
 *
 * The arithmetic is printed because it is the point: generated + skipped-as-declared +
 * skipped-as-excluded must equal the routes served. A command that quietly dropped the remainder
 * would read exactly like one that covered everything.
 */
function commandScaffold(openapiPath: string, outDir: string, configPath: string | undefined, dryRun: boolean, force: boolean): number {
  let config = null;
  let base: string | null = null;
  if (configPath) ({ config, base } = loadConfig(configPath));

  const plan = planScaffold(openapiPath, outDir, config, base);
  print(plan.findings);

  console.log(`routes:     ${plan.total} served, read from ${openapiPath}`);
  console.log(`drafts:     ${plan.drafts.length} to write into ${outDir}`);
  console.log(`skipped:    ${plan.skippedDeclared.length} already declared by a card`);
  for (const skip of plan.skippedDeclared) console.log(`              ${skip.route} → ${skip.by.join(", ")}`);
  console.log(`            ${plan.skippedExcluded.length} excluded by the config`);
  for (const skip of plan.skippedExcluded) console.log(`              ${skip.route} → ${skip.reason}`);

  const accounted = plan.drafts.length + plan.skippedDeclared.length + plan.skippedExcluded.length;
  if (accounted !== plan.total) {
    console.log("");
    print([
      new Finding(
        "routes_unaccounted",
        `${plan.total} routes served but ${accounted} accounted for — ${plan.total - accounted} vanished without a reason`,
      ),
    ]);
    return 1;
  }
  console.log(`            → ${plan.drafts.length} + ${plan.skippedDeclared.length} + ${plan.skippedExcluded.length} = ${plan.total} ✓`);

  if (plan.existing.length > 0) {
    console.log(`\nexisting:   ${plan.existing.length} draft(s) already on disk — ${force ? "OVERWRITTEN (--force)" : "left untouched"}`);
  }

  if (dryRun) {
    console.log("\ndry run: nothing written.");
    return 0;
  }

  const { written, kept } = writeScaffold(plan, outDir, force);
  console.log(`\nwritten:    ${written}${kept ? `, kept ${kept} existing` : ""}`);
  console.log("Every draft fails `usedesign validate` by design. Fill it in, then MOVE it into cards/.");
  return 0;
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

    case "scaffold": {
      // `--out dir` and `--config file` take a value, so the value must not be mistaken for a
      // positional argument. Parsed explicitly rather than by filtering on a leading dash.
      const takesValue = new Set(["--out", "--config"]);
      const values = new Map<string, string>();
      const free: string[] = [];
      for (let i = 0; i < rest.length; i += 1) {
        const argument = rest[i]!;
        if (takesValue.has(argument)) {
          const value = rest[i + 1];
          if (!value || value.startsWith("--")) {
            console.error(`usedesign scaffold: ${argument} needs a value`);
            return 2;
          }
          values.set(argument, value);
          i += 1;
        } else if (!argument.startsWith("--")) {
          free.push(argument);
        }
      }
      if (free.length !== 1) {
        console.error(
          "usedesign scaffold: name exactly one OpenAPI document\n" +
            "  usedesign scaffold <openapi.json> --out <dir> [--config <usedesign.config.yaml>] [--dry-run] [--force]",
        );
        return 2;
      }
      const outDir = values.get("--out");
      if (!outDir) {
        console.error("usedesign scaffold: --out <dir> is required — drafts must not land among real cards");
        return 2;
      }
      return commandScaffold(free[0]!, outDir, values.get("--config"), flags.includes("--dry-run"), flags.includes("--force"));
    }

    case "preview": {
      const out = rest[rest.indexOf("--out") + 1];
      const free = rest.filter((a, i) => !a.startsWith("--") && rest[i - 1] !== "--out");
      if (free.length !== 1 || !out || out.startsWith("--")) {
        console.error("usedesign preview: usage — usedesign preview <usedesign.config.yaml> --out <file.html>");
        return 2;
      }
      return commandPreview(free[0]!, out, loadConfig);
    }

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
