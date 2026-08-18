/**
 * Shared machinery: findings, front matter, config, and the small amount of path globbing the
 * tool needs. Nothing here decides anything about a card — the rules live in `validate.ts` and
 * `checks.ts`, so that a change to a rule never hides inside a helper.
 */
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { parse as parseYaml } from "yaml";

export type Severity = "error" | "warning";

export class Finding {
  constructor(
    readonly code: string,
    readonly detail: string,
    readonly severity: Severity = "error",
  ) {}

  toString(): string {
    return `${this.code}: ${this.detail}`;
  }
}

export const errors = (findings: Finding[]): Finding[] => findings.filter((f) => f.severity === "error");
export const warnings = (findings: Finding[]): Finding[] => findings.filter((f) => f.severity === "warning");
export const codesOf = (findings: Finding[]): string[] => [...new Set(findings.map((f) => f.code))].sort();

/** A card's front matter, as parsed. Deliberately loose: the schema is what judges its shape. */
export type Card = Record<string, any>;

export interface Config {
  usedesign_config?: number;
  cards?: string[];
  inventory?: string;
  test_report?: string;
  code_root?: string;
  evidence_horizon_days?: number;
  exclude?: { path?: string; method?: string; reason?: string }[];
  [key: string]: unknown;
}

/**
 * Return the parsed YAML front matter, or null if the file has none.
 *
 * The delimiter search matches the Python prototype exactly — `\n---` after the opening fence —
 * because two implementations disagreeing about where a card ends is the same class of defect
 * this project exists to catch.
 */
export function frontMatter(path: string): Card | null {
  // Line endings and a byte-order mark must never decide whether a card parses. Left alone, a
  // CRLF file hands the YAML parser a dangling carriage return after the closing fence, and a
  // card written on Windows fails on a rule that has nothing to do with its content.
  const text = readFileSync(path, "utf8").replace(/^﻿/, "").replace(/\r\n/g, "\n");
  if (!text.startsWith("---")) return null;
  const end = text.indexOf("\n---", 3);
  if (end === -1) return null;
  const parsed = parseYaml(text.slice(3, end));
  return parsed && typeof parsed === "object" ? (parsed as Card) : null;
}

export function loadConfig(path: string): { config: Config; base: string } {
  const config = parseYaml(readFileSync(path, "utf8")) as Config;
  if (!config || typeof config !== "object" || config.usedesign_config !== 1) {
    throw new Error(`${path}: not a usedesign config (expected \`usedesign_config: 1\`)`);
  }
  return { config, base: dirname(resolve(path)) };
}

/** Translate one glob segment into a regular expression. `*` and `?` do not cross a separator. */
function segmentToRegExp(segment: string): RegExp {
  const escaped = segment.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/\\\\]*").replace(/\?/g, "[^/\\\\]");
  return new RegExp(`^${escaped}$`);
}

/**
 * Expand a glob relative to `base`. Supports `*`, `?` and `**`; enough for `cards:` patterns and
 * small enough to keep the tool dependency-light, which matters for something meant to be run
 * with `npx` inside somebody else's CI.
 */
export function expandGlob(base: string, pattern: string): string[] {
  const segments = pattern.split(/[\\/]+/).filter((s) => s.length > 0);
  let current = [resolve(base)];

  for (const [index, segment] of segments.entries()) {
    const last = index === segments.length - 1;
    const next: string[] = [];

    if (segment === "**") {
      for (const dir of current) {
        const stack = [dir];
        while (stack.length) {
          const here = stack.pop()!;
          next.push(here);
          if (!existsSync(here)) continue;
          for (const entry of readdirSync(here, { withFileTypes: true })) {
            if (entry.isDirectory()) stack.push(join(here, entry.name));
          }
        }
      }
    } else if (segment === "." || segment === "..") {
      next.push(...current.map((dir) => resolve(dir, segment)));
    } else if (!/[*?]/.test(segment)) {
      next.push(...current.map((dir) => join(dir, segment)));
    } else {
      const matcher = segmentToRegExp(segment);
      for (const dir of current) {
        if (!existsSync(dir) || !statSync(dir).isDirectory()) continue;
        for (const entry of readdirSync(dir, { withFileTypes: true })) {
          if (matcher.test(entry.name) && (last || entry.isDirectory())) next.push(join(dir, entry.name));
        }
      }
    }
    current = [...new Set(next)];
  }

  return current.filter((path) => existsSync(path) && statSync(path).isFile()).sort();
}

/** Every card the config points at, as [id, front matter]. */
export function loadCardFiles(config: Config, base: string): { cards: [string, Card][]; findings: Finding[] } {
  const findings: Finding[] = [];
  const files = new Set<string>();
  for (const pattern of config.cards ?? []) {
    for (const file of expandGlob(base, pattern)) files.add(file);
  }
  if (files.size === 0) findings.push(new Finding("no_cards_found", "the `cards` patterns matched nothing"));

  const cards: [string, Card][] = [];
  for (const path of [...files].sort()) {
    const fm = frontMatter(path);
    if (fm) cards.push([String(fm["id"] ?? path.split(sep).pop()), fm]);
  }
  return { cards, findings };
}

/** Collect `*.op.md` and `*.contract.md` under the given files or directories. */
export function collectCards(paths: string[]): string[] {
  const files: string[] = [];
  for (const path of paths) {
    if (existsSync(path) && statSync(path).isDirectory()) {
      // Both document kinds, deliberately: `validate forms/` used to collect nothing and print
      // "0 card(s): 0 error(s)" — a green verdict on a directory it had not read.
      files.push(...expandGlob(path, "**/*.op.md"), ...expandGlob(path, "**/*.contract.md"));
    } else files.push(path);
  }
  return [...new Set(files)].sort();
}
