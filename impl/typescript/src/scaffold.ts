/**
 * Draft generation — turning a served route into the *shell* of a card.
 *
 * The point is arithmetic, not authorship. Describing 113 routes from a blank page is work
 * nobody starts; filling in the meaning of 113 shells is work somebody finishes. So this module
 * writes down what the machine can read and refuses to write down anything else.
 *
 * WHY OPENAPI HERE, WHEN THE CHECKS DELIBERATELY DO NOT READ IT
 * The three checks compare cards against a route *inventory* — a flat statement the repository
 * produces about itself — precisely so that no framework is ever parsed. Scaffolding is not
 * checking: nothing here decides whether anything is true, and a draft that reads a route wrong
 * is caught the moment a human looks at it or a checker runs. Reading the richer document is
 * therefore allowed for drafts and still forbidden for verdicts.
 *
 * THE DRAFT MUST NOT PASS VALIDATION
 * Every field a machine cannot know is written as `FILL_ME`, which fails the schema on purpose.
 * A draft that validated would be the worst possible output of this command: 113 documents that
 * look complete, claim maturity nobody measured, and are wrong in a way that reads as machine
 * precision. Screaming is the feature.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { Config, Finding, loadCardFiles } from "./core.js";
import { normalise } from "./checks.js";

const VERBS = ["get", "post", "put", "patch", "delete", "head", "options"];

export interface ScaffoldPlan {
  drafts: { id: string; file: string; method: string; path: string; body: string }[];
  skippedDeclared: { route: string; by: string[] }[];
  skippedExcluded: { route: string; reason: string }[];
  existing: string[];
  total: number;
  findings: Finding[];
}

/**
 * A provisional id built from the route shape. It is deliberately not a guess at the operation's
 * name: `TODO` is upper-case, so the id fails its own pattern and the card says out loud that a
 * human has not been here yet. Uniqueness and stability matter — the same OpenAPI must always
 * produce the same filenames, or every regeneration is a diff nobody can read.
 */
function provisionalId(method: string, path: string, taken: Set<string>): string {
  // `{id}` carries no meaning for a name; `:finish` does — under AIP-136 the colon suffix is the
  // action, and the checker's own normaliser is careful never to eat it (see checks.ts PARAM).
  const slug =
    path
      .replace(/\{[^}]*\}/g, "")
      .split(/[/:]+/)
      .filter((s) => s.length > 0)
      .join("-")
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "") || "root";

  const base = `TODO.${slug}.${method.toLowerCase()}`;
  if (!taken.has(base)) return base;
  for (let n = 2; ; n += 1) {
    const candidate = `${base}-${n}`;
    if (!taken.has(candidate)) return candidate;
  }
}

/** Status codes the document itself lists. `default` and anything non-numeric are not statuses. */
function responsesOf(operation: any): number[] {
  return Object.keys(operation?.responses ?? {})
    .map((code) => Number.parseInt(code, 10))
    .filter((code) => Number.isInteger(code) && code >= 100 && code <= 599)
    .sort((a, b) => a - b);
}

/**
 * Does the document actually *say* anything about statuses, or does it merely default?
 *
 * Measured on the first repository this ran against: all 113 routes declared exactly `200` and
 * nothing else, while the code demonstrably answers 401 and 422 — the cards written by reading
 * that code say so, and the checks pass. A status list identical across every route in the
 * document is the signature of a framework filling in a blank, not of anybody describing
 * behaviour. Copying it into a draft unmarked would hand a human a falsehood wearing the clothes
 * of machine precision, which is the one output this command must never produce.
 */
function statusesAreDegenerate(routes: { operation: any }[]): boolean {
  if (routes.length < 2) return false;
  const sets = new Set(routes.map((r) => responsesOf(r.operation).join(",")));
  return sets.size === 1;
}

function draftBody(id: string, method: string, path: string, operation: any, source: string, degenerate: boolean): string {
  const responses = responsesOf(operation);
  const parameters: string[] = (operation?.parameters ?? [])
    .filter((p: any) => p?.in === "path" && p?.name)
    .map((p: any) => String(p.name));

  // What the document says about itself goes in the prose, attributed, never into a field. A
  // summary copied into `title` would fill a human's field with a machine's guess, and the next
  // reader could not tell which of the two wrote it.
  const says: string[] = [];
  if (operation?.summary) says.push(`summary: ${String(operation.summary).trim()}`);
  if (operation?.operationId) says.push(`operationId: ${String(operation.operationId).trim()}`);
  if (parameters.length) says.push(`параметры пути: ${parameters.join(", ")}`);

  const lines = [
    "---",
    "# ЗАГОТОВКА, а не карточка. Машина записала только то, что прочитала в OpenAPI;",
    "# всё остальное — FILL_ME, и пока они здесь, файл НЕ проходит `usedesign validate`.",
    "# Это сделано намеренно: заготовка, прошедшая проверку, выглядела бы описанием, не будучи им.",
    "#",
    "# Дозаполнив, ПЕРЕНЕСИТЕ файл в cards/ — переезд и есть слово «я за это отвечаю».",
    `id: ${id}`,
    "title: FILL_ME",
    "scenario: FILL_ME          # либо serves_step, если операция служит шагу другой",
    "actors: [FILL_ME]",
    "",
    "maturity: FILL_ME          # conceived | designed | implemented | tested | in_production",
    "",
    "steps:",
    "  - id: s1-FILL-ME",
    "    text: FILL_ME",
    "",
    "concurrency:",
    "  mode: FILL_ME            # etag_required | idempotency_by_header | idempotency_by_formula | none_by_design",
    "  rationale: FILL_ME",
    "  source: FILL_ME",
    "",
    "interfaces:",
    "  rest:",
    "    transport: http_rest",
    `    method: ${method.toUpperCase()}`,
    `    path: ${path}`,
    responses.length
      ? `    responses: [${responses.join(", ")}]${degenerate ? "   # ⚠ см. ниже: документ назвал ОДИН И ТОТ ЖЕ набор для всех маршрутов" : ""}`
      : "    responses: []            # документ не назвал ни одного статуса — проверить руками",
    "",
    "data:",
    "  entities: [FILL_ME]",
    "provenance: FILL_ME        # none для чтения, либо объект с activity_kind",
    "reversibility: FILL_ME     # reversible | irreversible | not_applicable | {reversible_via: …}",
    "---",
    "",
    `Заготовка для маршрута \`${method.toUpperCase()} ${path}\`, снятого из \`${source}\`.`,
    "",
    says.length ? `Документ говорит о себе: ${says.join(" · ")}.` : "Документ не сообщает о маршруте ничего сверх адреса и статусов.",
    "",
    "Машина не знает, зачем эта операция существует, какие проверки она делает и чем доказана её",
    "зрелость. Эти поля ждут человека, и до него описание не является описанием.",
    "",
    ...(degenerate
      ? [
          "⚠️ `responses` СКОПИРОВАН, НО ЕМУ НЕЛЬЗЯ ВЕРИТЬ. Документ назвал один и тот же набор",
          "статусов для КАЖДОГО маршрута приложения — так выглядит не описание поведения, а",
          "умолчание фреймворка. Реальные коды ошибок ищите в коде: заполнив `steps[]` с",
          "`on_violation.http`, вы почти наверняка обнаружите статусы, которых здесь нет, и",
          "проверка `undeclared_response` это покажет.",
          "",
        ]
      : []),
  ];
  return lines.join("\n");
}

/**
 * Work out what would be written, without writing it. The counts are the product: generated plus
 * skipped-because-declared plus skipped-because-excluded must equal the number of routes served,
 * and a command that quietly drops the difference is indistinguishable from one that covered
 * everything.
 */
export function planScaffold(
  openapiPath: string,
  outDir: string,
  config: Config | null,
  base: string | null,
): ScaffoldPlan {
  const findings: Finding[] = [];
  const doc = JSON.parse(readFileSync(openapiPath, "utf8"));

  const declared = new Map<string, string[]>();
  if (config && base) {
    const { cards, findings: cardFindings } = loadCardFiles(config, base);
    findings.push(...cardFindings.filter((f) => f.code !== "no_cards_found"));
    for (const [cardId, fm] of cards) {
      for (const iface of Object.values<any>(fm["interfaces"] ?? {})) {
        if (iface?.transport !== "http_rest" || !iface.method || !iface.path) continue;
        // One route may be declared by several cards (dispatch). It is still ONE covered route:
        // counting cards here would make the arithmetic add up for the wrong reason.
        const key = normalise(iface.method, iface.path);
        declared.set(key, [...(declared.get(key) ?? []), cardId]);
      }
    }
  }

  const routes: { method: string; path: string; operation: any }[] = [];
  for (const [path, operations] of Object.entries<any>(doc.paths ?? {})) {
    for (const [verb, operation] of Object.entries<any>(operations ?? {})) {
      if (VERBS.includes(verb.toLowerCase())) routes.push({ method: verb.toUpperCase(), path, operation });
    }
  }
  routes.sort((a, b) => (a.path === b.path ? a.method.localeCompare(b.method) : a.path.localeCompare(b.path)));

  if (routes.length === 0) {
    findings.push(
      new Finding("openapi_empty", `${openapiPath}: no routes — almost always a failed dump rather than an application with no routes`),
    );
  }

  const plan: ScaffoldPlan = {
    drafts: [],
    skippedDeclared: [],
    skippedExcluded: [],
    existing: [],
    total: routes.length,
    findings,
  };
  const taken = new Set<string>();
  const source = openapiPath.split(/[\\/]/).pop() ?? openapiPath;
  const degenerate = statusesAreDegenerate(routes);
  if (degenerate) {
    findings.push(
      new Finding(
        "statuses_uniform",
        `every one of the ${routes.length} routes declares the same statuses (${responsesOf(routes[0]!.operation).join(", ") || "none"}) — a framework default rather than a description; each draft says so`,
        "warning",
      ),
    );
  }

  for (const { method, path, operation } of routes) {
    const key = normalise(method, path);
    const shape = key.slice(key.indexOf(" ") + 1);

    const rule = (config?.exclude ?? []).find((r) => {
      if (r.method && r.method.toUpperCase() !== method) return false;
      const escaped = (r.path ?? "").replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]");
      return new RegExp(`^${escaped}$`).test(shape);
    });
    if (rule) {
      plan.skippedExcluded.push({ route: key, reason: rule.reason ?? "(без причины в конфиге)" });
      continue;
    }

    const owners = declared.get(key);
    if (owners) {
      plan.skippedDeclared.push({ route: key, by: owners });
      continue;
    }

    const id = provisionalId(method, path, taken);
    taken.add(id);
    const file = join(outDir, `${id}.op.md`);
    if (existsSync(file)) plan.existing.push(file);
    plan.drafts.push({ id, file, method, path, body: draftBody(id, method, path, operation, source, degenerate) });
  }

  return plan;
}

/** Write the planned drafts. Existing files are left alone unless `force` — a half-filled draft
 * is somebody's work, and silently replacing it is the one failure this command could cause that
 * nobody would notice until the writing was gone. */
export function writeScaffold(plan: ScaffoldPlan, outDir: string, force: boolean): { written: number; kept: number } {
  mkdirSync(outDir, { recursive: true });
  let written = 0;
  let kept = 0;
  for (const draft of plan.drafts) {
    if (existsSync(draft.file) && !force) {
      kept += 1;
      continue;
    }
    writeFileSync(draft.file, draft.body, { encoding: "utf8" });
    written += 1;
  }
  return { written, kept };
}
