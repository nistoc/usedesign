/**
 * YAML as both implementations read it (1.6.0): front matter, configs and manifests.
 *
 * The `yaml` package reads the text — YAML 1.2, the core schema, no known tags beyond it — and
 * the Python prototype runs a port of the same parser (`impl/python/yaml12.py`), line for line,
 * so that a card one implementation reads and the other refuses cannot exist. The port is of
 * 2.9.0, the version `package.json` pins; a new version of the package is a new port.
 *
 * Four things the package lets through are refused here, in the same words in both:
 *  - collections nested deeper than `MAX_DEPTH` levels. The package recurses on them and runs
 *    out of stack, somewhere else in each runtime, with a message that names no file;
 *  - a collection as a map key. The package writes it as YAML text, `[a, b]` as "- a\n- b\n",
 *    and the key a reader sees is not the key the card wrote;
 *  - an alias inside the node it names, `&a [*a]`. The package returns a value that contains
 *    itself, which every rule that walks it follows forever;
 *  - half of a surrogate pair in a string, which only an escape writes (`"\ud800"`). JavaScript
 *    keeps it and prints U+FFFD; Python cannot hold it in a printable string, and two keys or
 *    ids that differ only there would be two here and one there.
 * Warnings — an unknown tag, an anchor ending in a colon — are not printed, as before.
 */
import { isAlias, isCollection, isScalar, LineCounter, parseDocument, Parser, visit } from "yaml";
import type { CST, Document, Node } from "yaml";

export const MAX_DEPTH = 64;
const DEEP = `Collections are nested deeper than ${MAX_DEPTH} levels`;

/** The value of a YAML document, or the first error in it, the line and column in its message. */
export function readYaml(text: string): any {
  let tokens: CST.Token[];
  try {
    tokens = [...new Parser().parse(text)];
  } catch (e) {
    // The parser closes nested collections by recursion: past some thousands of levels, the stack.
    if (e instanceof RangeError) throw new Error(DEEP);
    throw e;
  }
  if (tokens.some(tooDeep)) throw new Error(DEEP);
  const lineCounter = new LineCounter();
  const doc = parseDocument(text, { schema: "core", resolveKnownTags: false, logLevel: "error", lineCounter });
  if (doc.errors.length > 0) throw doc.errors[0];
  rules(doc, text, lineCounter);
  return doc.toJS();
}

/** Collections nested deeper than MAX_DEPTH in a document of the syntax tree. */
function tooDeep(token: CST.Token): boolean {
  if (token.type !== "document" || !token.value) return false;
  const stack: [CST.Token, number][] = [[token.value, 0]];
  while (stack.length > 0) {
    const [node, depth] = stack.pop()!;
    if (!("items" in node)) continue;
    if (depth + 1 > MAX_DEPTH) return true;
    for (const item of node.items as CST.CollectionItem[]) {
      if (item.key) stack.push([item.key, depth + 1]);
      if (item.value) stack.push([item.value, depth + 1]);
    }
  }
  return false;
}

/** Half of a surrogate pair, which only an escape (`"\ud800"`) can write. */
const LONE_SURROGATE = /\p{Cs}/u;

/**
 * A collection as a map key, an alias inside the node it names, and a string with half of a
 * character in it, in the order `visit` meets them. The last is a string JavaScript keeps and
 * Python cannot print: two such keys are two here and one there.
 */
function rules(doc: Document, text: string, lineCounter: LineCounter): void {
  const anchors = new Map<string, Node>();
  visit(doc, {
    Node(_, node, path) {
      if (isAlias(node)) {
        const target = anchors.get(node.source);
        if (target && path.includes(target)) {
          throw located(text, lineCounter, `Alias *${node.source} is inside the node it refers to`, node.range![0]);
        }
        return;
      }
      if (node.anchor) anchors.set(node.anchor, node);
      if (isScalar(node) && typeof node.value === "string" && LONE_SURROGATE.test(node.value)) {
        throw located(text, lineCounter, "A string holds half of a surrogate pair, which is not a character", node.range![0]);
      }
    },
    Pair(_, pair) {
      const key = isAlias(pair.key) ? anchors.get(pair.key.source) : pair.key;
      if (isCollection(key)) {
        throw located(text, lineCounter, "Map keys must be scalars", (pair.key as Node).range![0]);
      }
    },
  });
}

/** An error at `offset`, its line and column written as the package writes them for its own. */
function located(src: string, lc: LineCounter, message: string, offset: number): Error {
  const { line, col } = lc.linePos(offset);
  const end = lc.linePos(offset + 1);
  message += ` at line ${line}, column ${col}`;
  let ci = col - 1;
  let lineStr = src.substring(lc.lineStarts[line - 1]!, lc.lineStarts[line]!).replace(/[\n\r]+$/, "");
  if (ci >= 60 && lineStr.length > 80) {
    const trimStart = Math.min(ci - 39, lineStr.length - 79);
    lineStr = "…" + lineStr.substring(trimStart);
    ci -= trimStart - 1;
  }
  if (lineStr.length > 80) lineStr = lineStr.substring(0, 79) + "…";
  if (line > 1 && /^ *$/.test(lineStr.substring(0, ci))) {
    let prev = src.substring(lc.lineStarts[line - 2]!, lc.lineStarts[line - 1]!);
    if (prev.length > 80) prev = prev.substring(0, 79) + "…\n";
    lineStr = prev + lineStr;
  }
  if (/[^ ]/.test(lineStr)) {
    let count = 1;
    if (end.line === line && end.col > col) count = Math.max(1, Math.min(end.col - col, 80 - ci));
    message += `:\n\n${lineStr}\n${" ".repeat(ci)}${"^".repeat(count)}\n`;
  }
  return new Error(message);
}
