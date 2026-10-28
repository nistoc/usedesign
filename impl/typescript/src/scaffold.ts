/**
 * Draft generation — turning a served route into the *shell* of a card.
 *
 * The point is arithmetic, not authorship. Describing 113 routes from a blank page is work
 * nobody starts; filling in the meaning of 113 shells is work somebody finishes. So this module
 * writes down what the machine can read and refuses to write down anything else.
 *
 * WHY OPENAPI HERE, WHEN THE CHECKS DELIBERATELY DO NOT READ IT
 * The checks compare cards against an *inventory* — a flat statement the repository
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
import { Config, Finding, globMatches, loadCardFiles } from "./core.js";
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

/**
 * Path parameters a route takes: the inline `in: path` entries declared on the path item, for every
 * operation under it, then the operation's own, then the names of the path's `{…}` segments not
 * declared inline, as `gen` writes them — each once. Up to 1.7.1 only the operation's inline entries
 * were read, and a draft named nothing for a parameter declared on the path item, given by `$ref`,
 * or not declared at all. `parameters` that is not a list is not read; `parametersNotList` says so.
 */
function pathParameterNames(path: string, shared: any, own: any): string[] {
  const names: string[] = [];
  for (const p of [...(Array.isArray(shared) ? shared : []), ...(Array.isArray(own) ? own : [])]) {
    if (p?.in === "path" && p?.name && !names.includes(String(p.name))) names.push(String(p.name));
  }
  for (const match of path.matchAll(/\{([^}]+)\}/g)) {
    if (!names.includes(match[1]!)) names.push(match[1]!);
  }
  return names;
}

/**
 * `parameters` that is not a list, on a path item or an operation, is a broken document: 1.7.1
 * failed on it with exit 2. It is not read, and the draft still names the path's `{…}` segments, so
 * this is a warning rather than an ERROR — every route still gets its draft.
 */
function parametersNotList(where: string, parameters: any): Finding | null {
  if (parameters == null || Array.isArray(parameters)) return null;
  return new Finding(
    "openapi_parameters_not_list",
    `${where}: \`parameters\` is not a list — not read; the draft names the path parameters from the path itself`,
    "warning",
  );
}

/**
 * A path item given whole by `$ref` — `"/v1/x/{id}": { "$ref": "#/components/pathItems/X" }`, as
 * OpenAPI 3.1 allows. Up to 1.7.2 its one key, `$ref`, was not a verb, so the route was neither
 * drafted nor counted and nothing said so: the sum still added up, without it. An address inside
 * this document is followed one level, and the fields written beside `$ref` win over the target's.
 * Anything else — another document, an address with nothing at it, a target that is itself a
 * `$ref`, a target with no operation, such as an operation or the document itself — is not read,
 * and `openapi_path_item_ref_not_read` names the path, so that a route the server answers is never
 * dropped from the count unseen. The fields written beside a `$ref` not read are still read.
 */
function resolvePathItem(doc: any, path: string, item: any): { item: any; notRead: Finding | null } {
  const ref = item?.$ref;
  if (ref === undefined) return { item, notRead: null };
  const { $ref: _ref, ...own } = item;
  const notRead = (why: string) => ({
    item: own,
    notRead: new Finding(
      "openapi_path_item_ref_not_read",
      `${path}: the path item is given by \`$ref\` ${JSON.stringify(ref)} — ${why}; not read, so the routes at that address are neither drafted nor counted`,
      "warning",
    ),
  });
  if (typeof ref !== "string" || !(ref === "#" || ref.startsWith("#/"))) return notRead("not an address inside this document");
  let target: any = doc;
  for (const token of ref === "#" ? [] : ref.slice(2).split("/")) {
    let key: string;
    try {
      // A JSON Pointer in a URI fragment: percent-decoding first, then `~1` → `/` and `~0` → `~`.
      key = decodeURIComponent(token).replace(/~1/g, "/").replace(/~0/g, "~");
    } catch {
      return notRead("not a valid address");
    }
    if (target === null || typeof target !== "object" || !Object.prototype.hasOwnProperty.call(target, key)) {
      return notRead("nothing at that address");
    }
    target = target[key];
  }
  if (target === null || typeof target !== "object" || Array.isArray(target)) return notRead("what stands there is not a path item");
  if (target.$ref !== undefined) return notRead("what stands there is another `$ref`, and only one level is followed");
  // An operation (`…/X/get`) or the document itself is an object too, and taken for a path item it
  // would drop its route as silently as 1.7.2 did. A path item written in place with no operation
  // is lawful and stays as it was; one given by `$ref` names an address that holds no route.
  if (!Object.keys(target).some((key) => VERBS.includes(key.toLowerCase()))) return notRead("what stands there has no operation");
  return { item: { ...target, ...own }, notRead: null };
}

function draftBody(id: string, method: string, path: string, operation: any, shared: any, source: string, degenerate: boolean): string {
  const responses = responsesOf(operation);
  const parameters = pathParameterNames(path, shared, operation?.parameters);

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

  const routes: { method: string; path: string; operation: any; shared: any }[] = [];
  for (const [path, given] of Object.entries<any>(doc.paths ?? {})) {
    const { item: operations, notRead } = resolvePathItem(doc, path, given);
    if (notRead) findings.push(notRead);
    const onPathItem = parametersNotList(`${path} (the path item)`, operations?.parameters);
    if (onPathItem) findings.push(onPathItem);
    for (const [verb, operation] of Object.entries<any>(operations ?? {})) {
      if (!VERBS.includes(verb.toLowerCase())) continue;
      const onOperation = parametersNotList(`${verb.toUpperCase()} ${path}`, operation?.parameters);
      if (onOperation) findings.push(onOperation);
      routes.push({ method: verb.toUpperCase(), path, operation, shared: operations?.parameters });
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

  for (const { method, path, operation, shared } of routes) {
    const key = normalise(method, path);
    const shape = key.slice(key.indexOf(" ") + 1);

    // The glob `check` matches an exclusion with (1.5.1), so the two never disagree on a route.
    const rule = (config?.exclude ?? []).find((r) => {
      if (r.method && r.method.toUpperCase() !== method) return false;
      return globMatches(shape, r.path ?? "");
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
    plan.drafts.push({ id, file, method, path, body: draftBody(id, method, path, operation, shared, source, degenerate) });
  }

  return plan;
}

/**
 * The arithmetic `scaffold` prints, checked: drafts + skipped-as-declared + skipped-as-excluded
 * must equal the routes served. `planScaffold` puts every route in exactly one of the three lists,
 * so on its own plans this never fires — it is the guard that a later change to `planScaffold`,
 * dropping a route or counting one twice, does not print a sum that merely looks right. It takes
 * the plan rather than recomputing one, so a test can hand it a plan `planScaffold` would not make.
 */
export function unaccountedRoutes(plan: Pick<ScaffoldPlan, "drafts" | "skippedDeclared" | "skippedExcluded" | "total">): Finding | null {
  const accounted = plan.drafts.length + plan.skippedDeclared.length + plan.skippedExcluded.length;
  if (accounted === plan.total) return null;
  // Up to 1.7.1 a route counted twice read "-1 vanished without a reason": the surplus has its own words.
  const gap =
    accounted < plan.total
      ? `${plan.total - accounted} vanished without a reason`
      : `${accounted - plan.total} counted more than once`;
  return new Finding("routes_unaccounted", `${plan.total} routes served but ${accounted} accounted for — ${gap}`);
}

/** Write the planned drafts. Existing files are left alone unless `force` — a half-filled draft
 * is somebody's work, and silently replacing it is the one failure this command could cause that
 * nobody would notice until the writing was gone. With no draft to write, `outDir` is not created:
 * up to 1.7.1 an empty one was left behind. */
export function writeScaffold(plan: ScaffoldPlan, outDir: string, force: boolean): { written: number; kept: number } {
  if (plan.drafts.length > 0) mkdirSync(outDir, { recursive: true });
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
