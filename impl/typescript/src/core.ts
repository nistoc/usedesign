/**
 * Shared machinery: findings, front matter, config, and the small amount of path globbing the
 * tool needs. Nothing here decides anything about a card — the rules live in `validate.ts` and
 * `checks.ts`, so that a change to a rule never hides inside a helper.
 */
import { closeSync, openSync, readFileSync, existsSync, lstatSync, readdirSync, realpathSync, statSync } from "node:fs";
import type { Dirent } from "node:fs";
import { basename, dirname, join, resolve, sep } from "node:path";
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

/**
 * Why a collected path cannot be opened as a file, or "" when it can (1.4.2). A link that leads
 * nowhere and a file without read permission are entries a listing finds and a reader cannot
 * open. Before, this implementation dropped the first unseen and called the second "front matter
 * is not valid YAML", and the Python prototype stopped on both with a traceback. The words are
 * the same in both implementations.
 */
export function whyUnreadable(path: string): string {
  if (!existsSync(path)) return "it is a link to a path that does not exist";
  if (isDirectory(path)) return "it is a directory";
  try {
    closeSync(openSync(path, "r"));
  } catch (e) {
    return causeOf(e);
  }
  return "";
}

/**
 * The cause of a system error, in the words both implementations print (1.4.2). A file another
 * process holds open on Windows is EBUSY here and a permission error in Python, so it is
 * "permission denied" in both.
 */
export function causeOf(e: unknown): string {
  const code = (e as NodeJS.ErrnoException).code ?? "";
  return ["EACCES", "EPERM", "EBUSY"].includes(code) ? "permission denied" : code || String((e as Error).message);
}

/**
 * The front matter of a document a config's patterns matched (1.4.2). A file nobody can open and
 * front matter that is not valid YAML stop the run with the file's name: no check can pass over a
 * card it did not read. Before, the second stopped it with the parser's words alone.
 */
export function readDocument(path: string): Card | null {
  const why = whyUnreadable(path);
  if (why) throw new Error(`\`${path}\` cannot be read — ${why}`);
  try {
    return frontMatter(path);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).syscall) throw new Error(`\`${path}\` cannot be read — ${causeOf(e)}`);
    throw new Error(`\`${path}\` front matter is not valid YAML — ${String((e as Error).message).split("\n")[0]}`);
  }
}

/**
 * Every key the config may carry. Enforced at load, not merely published in the schema: measured
 * on issue #4 — `cheks:` was accepted silently, the scoping vanished, and the check it was meant
 * to skip failed pointing at a completely different cause. A config typo must stop the run with
 * its own name, because everything downstream inherits its damage.
 */
const CONFIG_KEYS = new Set([
  "usedesign_config", "checks", "cards", "inventory", "test_report", "code_root",
  "evidence_horizon_days", "exclude", "forms", "form_inventory", "storage_inventory",
  "uncontracted_screens",
]);

export function loadConfig(path: string): { config: Config; base: string } {
  const config = parseYaml(readFileSync(path, "utf8")) as Config;
  if (!config || typeof config !== "object" || config.usedesign_config !== 1) {
    throw new Error(`${path}: not a usedesign config (expected \`usedesign_config: 1\`)`);
  }
  for (const key of Object.keys(config)) {
    if (!CONFIG_KEYS.has(key)) {
      throw new Error(
        `${path}: \`${key}\` is not a config key — a typo here silently changes what is checked. Known keys: ${[...CONFIG_KEYS].join(", ")}`,
      );
    }
  }
  return { config, base: dirname(resolve(path)) };
}

/** Translate one glob segment into a regular expression. `*` and `?` do not cross a separator. */
function segmentToRegExp(segment: string): RegExp {
  const escaped = segment.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/\\\\]*").replace(/\?/g, "[^/\\\\]");
  return new RegExp(`^${escaped}$`);
}

/** Whether `path` leads to a directory, through a link too; false where nothing can be read. */
function isDirectory(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

/**
 * Whether anything stands at `path`, a link that leads nowhere included (1.4.2). Only "does not
 * exist" is absence: an entry the system lists and will not describe — no permission, a link made
 * by another system — goes on to the reader, which names it.
 */
function isEntry(path: string): boolean {
  try {
    lstatSync(path);
    return true;
  } catch (e) {
    const code = (e as NodeJS.ErrnoException).code;
    return code !== "ENOENT" && code !== "ENOTDIR";
  }
}

/**
 * The real path of `path` (1.4.2). For an entry the system will not resolve — a link that leads
 * nowhere, on Windows a file without read permission — the real path of its directory and its own
 * name, so that such an entry reached two ways is still one entry.
 */
function realOf(path: string): string {
  try {
    return realpathSync.native(path);
  } catch {
    try {
      return join(realpathSync.native(dirname(path)), basename(path));
    } catch {
      return resolve(path);
    }
  }
}

/**
 * The entries of a directory a pattern walks into (1.4.2). One that cannot be listed stops the run
 * with its name, as a file that cannot be opened does: the cards under it would go unseen.
 */
function listing(dir: string): Dirent[] {
  try {
    return readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    throw new Error(`\`${dir}\` cannot be listed — ${causeOf(e)}`);
  }
}

/**
 * Expand a glob relative to `base`. Supports `*`, `?` and `**`; enough for `cards:` patterns and
 * small enough to keep the tool dependency-light, which matters for something meant to be run
 * with `npx` inside somebody else's CI.
 *
 * The Python implementation walks with the same algorithm, step for step, so that both collect the
 * same files (1.4.2): links to directories are followed, and a loop of them is walked once; a name
 * that starts with a dot is matched only by a segment that starts with a dot, and `**` passes it
 * over; `[` and `]` are plain characters; letter case counts. Every entry whose name matches is
 * returned, a link that leads nowhere included, so that the reader names it; directories are not.
 */
export function expandGlob(base: string, pattern: string): string[] {
  return once(expandKeyed(base, pattern));
}

/** Every file the patterns match, once however many of them reach it (1.4.3). */
export function expandGlobs(base: string, patterns: string[]): string[] {
  const keyed = new Map<string, string>();
  for (const pattern of patterns) for (const [path, real] of expandKeyed(base, pattern)) put(keyed, path, real);
  return once(keyed);
}

/** What is known of a path the walk stands at: a directory or a file with its real path, or null — to be asked of the system. */
type Known = readonly ["dir" | "file", string] | null;

function put<T>(map: Map<string, T>, path: string, value: T): void {
  if (!map.has(path)) map.set(path, value);
}

/**
 * What a directory listing says an entry is: "dir", "file", or null for a link, which only the
 * system can follow, and for an entry whose type the listing did not give.
 */
function kindOf(entry: Dirent): "dir" | "file" | null {
  if (entry.isSymbolicLink()) return null;
  if (entry.isDirectory()) return "dir";
  if (entry.isFile() || entry.isFIFO() || entry.isSocket() || entry.isBlockDevice() || entry.isCharacterDevice()) return "file";
  return null;
}

/** Whether the walk can go into `path`: a directory, by what is known or by asking. */
function walkable(path: string, known: Known): boolean {
  return known === null ? isDirectory(path) : known[0] === "dir";
}

/**
 * Every file `pattern` matches under `base`, with its real path — not yet once per file.
 *
 * What a directory listing told is not asked of the system again (1.4.3): an entry that is not a
 * link is a file or a directory, and its real path is its directory's real path and its name. Only
 * links and the names a pattern spells out are asked. `**` and a wildcard segment after it read
 * each directory once: the segment is matched in the listing `**` walks with. Measured on 24 000
 * files before the change: the listing read twice, and a real path, a type and an existence asked
 * per file. See the Python twin.
 */
function expandKeyed(base: string, pattern: string): Map<string, string> {
  const segments = pattern.split(/[\\/]+/).filter((s) => s.length > 0);
  let current = new Map<string, Known>([[resolve(base), null]]);

  for (let index = 0; index < segments.length; index++) {
    const segment = segments[index]!;
    let last = index === segments.length - 1;
    const found = new Map<string, Known>();

    if (segment === "**") {
      const after = last ? "" : segments[index + 1]!;
      const fused = after !== "" && after !== "**" && after !== "." && after !== ".." && /[*?]/.test(after);
      const matcher = fused ? segmentToRegExp(after) : null;
      const dotted = after.startsWith(".");
      if (fused) last = ++index === segments.length - 1;
      for (const [dir, known] of current) {
        if (!walkable(dir, known)) continue;
        // Each directory carries its real path and those of the directories above it: a link back
        // to one of them would be walked forever and is walked once. The system is asked for a real
        // path only at the start and at a link; below that, the parent's real path and the name are it.
        const stack = [{ here: dir, real: realOf(dir), above: [] as string[] }];
        while (stack.length) {
          const { here, real, above } = stack.pop()!;
          const looped = above.includes(real);
          if (!fused) {
            put<Known>(found, here, ["dir", real]);
            if (looped) continue;
          }
          for (const entry of listing(here)) {
            const name = entry.name;
            const path = join(here, name);
            const kind = kindOf(entry);
            let linkedDir: boolean | undefined; // whether a link leads to a directory, asked once
            if (matcher && !(name.startsWith(".") && !dotted) && matcher.test(name)) {
              if (kind === null) linkedDir = isDirectory(path);
              if (last || kind === "dir" || linkedDir) put<Known>(found, path, kind ? [kind, join(real, name)] : null);
            }
            // A directory a link leads back to is matched in, not walked again.
            if (looped || name.startsWith(".")) continue;
            if (kind === "dir") stack.push({ here: path, real: join(real, name), above: [...above, real] });
            // `Dirent.isDirectory()` is false for a link and for a Windows junction (1.4.2).
            else if (kind === null && (linkedDir ?? isDirectory(path))) stack.push({ here: path, real: realOf(path), above: [...above, real] });
            // `**` at the end matches files as well (1.4.2): `cards/**` found nothing here.
            else if (last && !fused) put<Known>(found, path, kind ? [kind, join(real, name)] : null);
          }
        }
      }
    } else if (segment === "." || segment === "..") {
      for (const dir of current.keys()) put<Known>(found, resolve(dir, segment), null);
    } else if (!/[*?]/.test(segment)) {
      for (const dir of current.keys()) put<Known>(found, join(dir, segment), null);
    } else {
      const matcher = segmentToRegExp(segment);
      const dotted = segment.startsWith(".");
      for (const [dir, known] of current) {
        if (!walkable(dir, known)) continue;
        let real = ""; // the directory's real path, asked once and only if a match needs it
        for (const entry of listing(dir)) {
          if ((entry.name.startsWith(".") && !dotted) || !matcher.test(entry.name)) continue;
          const path = join(dir, entry.name);
          const kind = kindOf(entry);
          if (last || kind === "dir" || (kind === null && isDirectory(path))) {
            if (kind && !real) real = realOf(dir);
            put<Known>(found, path, kind ? [kind, join(real, entry.name)] : null);
          }
        }
      }
    }
    current = found;
  }

  const keyed = new Map<string, string>();
  for (const [path, known] of current) {
    if (known === null) {
      if (isEntry(path) && !isDirectory(path)) keyed.set(path, realOf(path));
    } else if (known[0] === "file") keyed.set(path, known[1]);
  }
  return keyed;
}

/**
 * Paths in order, each file once however many links or patterns lead to it (1.4.2). A loop of
 * links gave the same card here twice and in Python's glob once per level, and two patterns that
 * reach one card through a link gave it here twice.
 */
export function oncePerFile(paths: string[]): string[] {
  return once(new Map(paths.map((path) => [path, realOf(path)])));
}

/** Paths in order, each real path once — the first path in that order stands for it. */
export function once(keyed: Map<string, string>): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const path of [...keyed.keys()].sort()) {
    const key = keyed.get(path)!;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(path);
  }
  return out;
}

/** Every card the config points at, as [id, front matter]. */
export function loadCardFiles(config: Config, base: string): { cards: [string, Card][]; findings: Finding[] } {
  const findings: Finding[] = [];
  const files = expandGlobs(base, config.cards ?? []);
  if (files.length === 0) findings.push(new Finding("no_cards_found", "the `cards` patterns matched nothing"));

  const cards: [string, Card][] = [];
  for (const path of files) {
    const fm = readDocument(path);
    if (fm) cards.push([String(fm["id"] ?? path.split(sep).pop()), fm]);
  }
  return { cards, findings };
}

/** Collect `*.op.md` and `*.contract.md` under the given files or directories. */
export function collectCards(paths: string[]): string[] {
  return once(collectKeyed(paths));
}

/** The cards and contracts under the given files or directories, each with its real path (1.4.3). */
export function collectKeyed(paths: string[]): Map<string, string> {
  const keyed = new Map<string, string>();
  for (const path of paths) {
    if (isDirectory(path)) {
      // Both document kinds, deliberately: `validate forms/` used to collect nothing and print
      // "0 card(s): 0 error(s)" — a green verdict on a directory it had not read.
      for (const pattern of ["**/*.op.md", "**/*.contract.md"]) {
        for (const [found, real] of expandKeyed(path, pattern)) put(keyed, found, real);
      }
    } else put(keyed, path, realOf(path));
  }
  return keyed;
}
