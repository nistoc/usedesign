/**
 * Card validation: the JSON Schema for form, and the cross-reference rules for meaning.
 *
 * SPEC §7 draws the line — the schema says whether a card is *shaped* like a card, and this file
 * says whether it *means* anything. A schema cannot know that a test covers a step that does not
 * exist, and a hand-written rule should not be re-checking that `maturity` is a string.
 */
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, basename } from "node:path";
import { Ajv2020 } from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { Card, Finding } from "./core.js";

const HERE = dirname(fileURLToPath(import.meta.url));
export const REPO = join(HERE, "..", "..", "..");

const REQUIRED = ["id", "title", "actors", "maturity", "steps", "concurrency", "interfaces", "data", "provenance", "reversibility"];
export const MATURITY = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"];
const CONCURRENCY_MODES = ["etag_required", "etag_optional", "idempotency_by_header", "idempotency_by_formula", "none_by_design"];
const TRANSPORTS = ["http_rest", "json_rpc", "in_process", "ui"];
const TEST_LEVELS = ["unit", "integration", "ui", "contract"];

const OPERATION_ID = /^[a-z0-9]+(\.[a-z0-9-]+){2,}$/;
const STEP_ID = /^s[0-9]+-[a-z0-9-]+$/;

/** maturity level → the evidence key it must carry */
const EVIDENCE_FOR: Record<string, string> = {
  implemented: "implemented",
  tested: "tested",
  in_production: "deployed",
};

let compiled: ((data: unknown) => boolean) & { errors?: any[] } | null = null;
let compiledForm: ((data: unknown) => boolean) & { errors?: any[] } | null = null;

/**
 * Where the published schema is. In the repository it is `schema/` at the root; in a published
 * package it is copied next to the compiled code at build time. Both are the *same file* — the
 * tool never carries a private variant of the schema it claims to implement, because that is how
 * a schema and its implementation quietly start to disagree.
 */
export function schemaPathFor(name = "operation-card.schema.json"): string {
  const packaged = join(HERE, "schema", name);
  return existsSync(packaged) ? packaged : join(REPO, "schema", name);
}

/** Compile the published schema once. */
function schemaValidator(schemaPath = schemaPathFor()) {
  if (compiled) return compiled;
  const ajv = new Ajv2020({ allErrors: true, strict: false });
  addFormats.default ? addFormats.default(ajv as any) : (addFormats as any)(ajv as any);
  compiled = ajv.compile(JSON.parse(readFileSync(schemaPath, "utf8"))) as any;
  return compiled!;
}

/** Validate a card's *form* against the published JSON Schema. */
export function validateSchema(fm: Card): Finding[] {
  const validator = schemaValidator();
  if (validator(fm)) return [];
  return (validator.errors ?? []).map(
    (error: any) =>
      new Finding("schema_violation", `${error.instancePath || "/"} ${error.message}`.trim()),
  );
}

/** Validate a form contract against its published JSON Schema. */
export function validateFormSchema(fm: Card): Finding[] {
  if (!compiledForm) {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    addFormats.default ? addFormats.default(ajv as any) : (addFormats as any)(ajv as any);
    compiledForm = ajv.compile(
      JSON.parse(readFileSync(schemaPathFor("form-contract.schema.json"), "utf8")),
    ) as any;
  }
  if (compiledForm!(fm)) return [];
  return (compiledForm!.errors ?? []).map(
    (error: any) =>
      new Finding("schema_violation", `${error.instancePath || "/"} ${error.message}`.trim()),
  );
}

// ── form contracts ───────────────────────────────────────────────────────────────────────────
//
// Check 5 used to read contracts raw, and the measured failure is quiet in the worst way: a
// contract with `presnts` misspelled lost its whole "must show" section, and every line of it
// resurfaced as SOMEBODY ELSE'S warning — "element rendered but not described". The typo did not
// fail; it changed whose problem it looked like. Same class as the gate that ran `check` without
// `validate` and stayed green on a card with an invented maturity level.
//
// The rules are hand-rolled with named codes — not raw schema output — because the second
// implementation has no schema library, and two implementations must agree on WHAT is wrong,
// not merely that something is.

const FORM_REQUIRED = ["usedesign_form", "id", "screen", "presents"];
const FORM_KEYS = new Set(["usedesign_form", "id", "screen", "page", "entity", "maturity", "states", "presents", "controls", "groups", "removed"]);
const FORM_MATURITY = ["designed", "implemented"];
const STATE_KEYS = new Set(["data", "note"]);
const ELEMENT_KEYS = new Set(["field", "field_pattern", "at_least", "shows", "when", "note"]);
const CONTROL_KEYS = new Set(["control", "control_pattern", "at_least", "calls", "shown_when", "shown_when_rule", "opens", "behaviour", "placement", "note"]);
const GROUP_KEYS = new Set(["group", "role", "contains", "note"]);
const GROUP_ROLES = ["header", "footer", "section", "table", "list", "toolbar", "menu"];
const REMOVED_KEYS = new Set(["control", "was", "verdict"]);

/**
 * One line names ONE anchor or ONE family, never both and never neither. A family (issue #10)
 * is a pattern with `*`; a "pattern" without a wildcard is a literal wearing the wrong key,
 * and would silently match nothing the literal key would have matched.
 */
function anchorOrFamily(
  line: Record<string, any>,
  literalKey: string,
  patternKey: string,
  where: string,
  err: (code: string, detail: string) => void,
): string | undefined {
  const literal = line[literalKey];
  const pattern = line[patternKey];
  if (!literal && !pattern) err("missing_required_field", `${where}: \`${literalKey}\` (or \`${patternKey}\`) is absent`);
  if (literal && pattern) {
    err("literal_and_pattern", `${where}: both \`${literalKey}\` and \`${patternKey}\` — one line names one anchor or one family, never both`);
  }
  if (pattern && !String(pattern).includes("*")) {
    err("pattern_without_wildcard", `${where}: \`${pattern}\` has no \`*\` — a family without a wildcard is a literal; write \`${literalKey}:\``);
  }
  const atLeast = line["at_least"];
  if (atLeast !== undefined && (!Number.isInteger(atLeast) || atLeast < 0)) {
    err("malformed_at_least", `${where}: \`at_least\` must be a non-negative integer, got \`${atLeast}\``);
  }
  if (atLeast !== undefined && !pattern) {
    err("malformed_at_least", `${where}: \`at_least\` belongs to a family line (\`${patternKey}\`) — a single anchor is present or it is not`);
  }
  return literal ? String(literal) : pattern ? String(pattern) : undefined;
}

/**
 * Validate one form contract's *meaning*. `knownForms` enables the cross-contract link warning
 * (`opens` pointing at a contract that is not in the validated set); pass null for a lone file.
 */
export function validateForm(fm: Card, filename = "", knownForms: Set<string> | null = null): Finding[] {
  const out: Finding[] = [];
  const err = (code: string, detail: string) => out.push(new Finding(code, detail));
  const warn = (code: string, detail: string) => out.push(new Finding(code, detail, "warning"));

  for (const field of FORM_REQUIRED) {
    if (!(field in fm)) err("missing_required_field", `\`${field}\` is absent`);
  }
  // The typo gets its own name. Reported as an unknown key, `presnts` says what happened;
  // reported only as "presents is absent", it reads like an empty contract, not a broken one.
  for (const key of Object.keys(fm)) {
    if (!FORM_KEYS.has(key)) err("unknown_field", `\`${key}\` is not part of the form contract format`);
  }

  const formId: string = fm["id"] ?? "";
  if (formId && !OPERATION_ID.test(formId)) {
    err("malformed_form_id", `\`${formId}\` is not <area>.<object>.<name>`);
  }

  // `maturity: designed` marks a contract written before its screen (issue #8) — two values,
  // not the card's six: a contract has no evidence axis beyond "does the screen render".
  const maturity = fm["maturity"];
  if (maturity !== undefined && !FORM_MATURITY.includes(maturity)) {
    err("invalid_enum_value", `maturity \`${maturity}\` is not one of ${FORM_MATURITY}`);
  }

  // `states:` maps screen states onto data states (issue #11). A map, keyed by screen state;
  // every entry names the data state it lives in.
  const stateMap = fm["states"];
  if (stateMap !== undefined) {
    if (!stateMap || typeof stateMap !== "object" || Array.isArray(stateMap)) {
      err("malformed_states", "`states` must be a map of screen state → { data: <data state> }");
    } else {
      for (const [state, spec] of Object.entries<any>(stateMap)) {
        if (!spec || typeof spec !== "object" || Array.isArray(spec)) {
          err("missing_required_field", `states.${state}: \`data\` is absent`);
          continue;
        }
        if (!spec["data"]) err("missing_required_field", `states.${state}: \`data\` is absent`);
        for (const key of Object.keys(spec)) {
          if (!STATE_KEYS.has(key)) err("unknown_field", `states.${state}: \`${key}\` is not part of a state line`);
        }
      }
    }
  }

  const presents: any[] = Array.isArray(fm["presents"]) ? fm["presents"] : [];
  const seenFields = new Set<string>();
  for (const [index, element] of presents.entries()) {
    if (!element || typeof element !== "object") continue;
    if (!element["shows"]) err("missing_required_field", `presents[${index}]: \`shows\` is absent`);
    for (const key of Object.keys(element)) {
      if (!ELEMENT_KEYS.has(key)) err("unknown_field", `presents[${index}]: \`${key}\` is not part of an element line`);
    }
    const field = anchorOrFamily(element, "field", "field_pattern", `presents[${index}]`, err);
    if (field) {
      if (seenFields.has(field)) err("duplicate_element", `\`${field}\` appears more than once in presents`);
      seenFields.add(field);
    }
  }

  const controls: any[] = Array.isArray(fm["controls"]) ? fm["controls"] : [];
  const seenControls = new Set<string>();
  for (const [index, control] of controls.entries()) {
    if (!control || typeof control !== "object") continue;
    for (const key of Object.keys(control)) {
      if (!CONTROL_KEYS.has(key)) err("unknown_field", `controls[${index}]: \`${key}\` is not part of a control line`);
    }
    const name = anchorOrFamily(control, "control", "control_pattern", `controls[${index}]`, err);
    if (name) {
      if (seenControls.has(name)) err("duplicate_control", `\`${name}\` appears more than once in controls`);
      seenControls.add(name);
    }
    const opens = control["opens"];
    if (opens && knownForms !== null && !knownForms.has(opens)) {
      warn("undescribed_form", `control \`${name}\` opens \`${opens}\`, which no contract in this set describes`);
    }
  }

  // ── groups ─────────────────────────────────────────────────────────────────────────────────
  // Grouping by purpose: headers, footers, tables, and which controls sit where. Array order IS
  // the group order. Membership is authored, not yet verified — the inventory records anchors
  // flat — but a group naming a member the contract itself does not declare is wrong today, by
  // the contract's own text, and needs no inventory to prove it.
  const members = new Set([...seenFields, ...seenControls]);
  const seenGroups = new Set<string>();
  const claimed = new Map<string, string>();
  for (const [index, group] of (Array.isArray(fm["groups"]) ? fm["groups"] : []).entries()) {
    if (!group || typeof group !== "object") continue;
    for (const required of ["group", "role", "contains"]) {
      if (!group[required]) err("missing_required_field", `groups[${index}]: \`${required}\` is absent`);
    }
    for (const key of Object.keys(group)) {
      if (!GROUP_KEYS.has(key)) err("unknown_field", `groups[${index}]: \`${key}\` is not part of a group line`);
    }
    const name = group["group"];
    if (name) {
      if (seenGroups.has(name)) err("duplicate_group", `\`${name}\` appears more than once in groups`);
      seenGroups.add(name);
    }
    const role = group["role"];
    if (role && !GROUP_ROLES.includes(role)) {
      err("invalid_enum_value", `groups[${index}]: role \`${role}\` is not one of ${GROUP_ROLES}`);
    }
    for (const member of Array.isArray(group["contains"]) ? group["contains"] : []) {
      if (!members.has(member)) {
        err("unknown_group_member", `group \`${name}\` contains \`${member}\`, which no element or control declares`);
      }
      const already = claimed.get(member);
      if (already && already !== name) {
        err("element_in_two_groups", `\`${member}\` sits in \`${already}\` and \`${name}\` — an element renders in one place`);
      }
      if (name) claimed.set(member, name);
    }
  }

  // One document both requiring and forbidding a control is not incompleteness — it is the
  // contract disagreeing with itself, and no amount of code can satisfy it.
  for (const [index, removed] of (Array.isArray(fm["removed"]) ? fm["removed"] : []).entries()) {
    if (!removed || typeof removed !== "object") continue;
    if (!removed["control"]) err("missing_required_field", `removed[${index}]: \`control\` is absent`);
    for (const key of Object.keys(removed)) {
      if (!REMOVED_KEYS.has(key)) err("unknown_field", `removed[${index}]: \`${key}\` is not part of a removed line`);
    }
    const name = removed["control"];
    if (name && seenControls.has(name)) {
      err("removed_also_required", `\`${name}\` is listed in controls and in removed — the contract both requires and forbids it`);
    }
  }

  return out;
}

/**
 * Validate one card's *meaning*. `knownIds` enables the cross-card reference warnings; pass null
 * when validating a card on its own, so that pointing at a card outside the set is not reported
 * as if it were missing.
 */
export function validate(fm: Card, filename = "", knownIds: Set<string> | null = null): Finding[] {
  const out: Finding[] = [];
  const err = (code: string, detail: string) => out.push(new Finding(code, detail));
  const warn = (code: string, detail: string) => out.push(new Finding(code, detail, "warning"));

  for (const field of REQUIRED) {
    if (!(field in fm)) err("missing_required_field", `\`${field}\` is absent`);
  }

  const cardId: string = fm["id"] ?? "";
  if (cardId && !OPERATION_ID.test(cardId)) {
    err("malformed_operation_id", `\`${cardId}\` is not <area>.<object>.<action>`);
  }
  if (filename && cardId && basename(filename).replace(/\.md$/, "") !== `${cardId}.op`) {
    warn("filename_mismatch", `file name does not match id \`${cardId}\``);
  }

  if (!("scenario" in fm) && !("serves_step" in fm)) {
    err("no_owner", "neither `scenario` nor `serves_step` is present");
  }

  const maturity: string | undefined = fm["maturity"];
  if (maturity !== undefined && !MATURITY.includes(maturity)) {
    err("invalid_enum_value", `maturity \`${maturity}\` is not one of ${MATURITY}`);
  }

  // `data_transition.from` may be a SET (round 18): an operation that departs from any of several
  // states — resume from finished | partial | abandoned. Measured on a live service, where the only
  // honest alternative was `from: any`, which switches the shown_when rule off. One state is written
  // as a string; a one-element set is that string wearing brackets.
  const fromValue = fm["data_transition"] && typeof fm["data_transition"] === "object" ? fm["data_transition"].from : undefined;
  if (Array.isArray(fromValue)) {
    if (fromValue.length < 2) err("malformed_transition", "`data_transition.from` as a set needs at least two states — one state is written as a string");
    if (new Set(fromValue.map(String)).size !== fromValue.length) err("malformed_transition", "`data_transition.from` lists the same state twice");
  }

  // ── steps ──────────────────────────────────────────────────────────────────────────────────
  const steps: any[] = fm["steps"] ?? [];
  const stepIds = new Set<string>();
  for (const step of steps) {
    const sid: string = step?.id ?? "";
    if (!STEP_ID.test(sid)) err("malformed_step_id", `\`${sid}\` is not s<N>-<name>`);
    else if (stepIds.has(sid)) err("duplicate_step_id", `\`${sid}\` appears more than once`);
    stepIds.add(sid);
  }

  // ── maturity vs evidence ───────────────────────────────────────────────────────────────────
  const evidence: Record<string, unknown> = fm["maturity_evidence"] ?? {};
  const tests: any[] = fm["tests"] ?? [];
  if (maturity && maturity in EVIDENCE_FOR) {
    // Every level implies the ones below it.
    for (const level of ["implemented", "tested", "in_production"]) {
      if (MATURITY.indexOf(maturity) >= MATURITY.indexOf(level)) {
        const key = EVIDENCE_FOR[level]!;
        if (!(key in evidence)) {
          err("maturity_without_evidence", `\`${maturity}\` claimed without \`maturity_evidence.${key}\``);
        }
      }
    }
  }
  if (maturity && ["tested", "in_production"].includes(maturity) && tests.length === 0) {
    err("maturity_without_tests", `\`${maturity}\` claimed with an empty \`tests[]\``);
  }
  // `maturity_evidence.tested` is advisory prose — but when it opens with a number, the number is a
  // claim, and it rots by hand: cards keep "5 tests" after the sixth was cited, or after one was
  // dropped. The format's own example library was clean when this arrived; the product's cards had been kept in step by hand three times in one day.
  const testedProse = evidence["tested"];
  const testedMatch = typeof testedProse === "number" ? [null, String(testedProse)] : /^\s*(\d+)/.exec(String(testedProse ?? ""));
  if (testedMatch && Number(testedMatch[1]) !== tests.length) {
    warn("tested_count_mismatch", `maturity_evidence.tested says ${testedMatch[1]}, tests[] lists ${tests.length} — the count went stale`);
  }

  // ── concurrency ────────────────────────────────────────────────────────────────────────────
  const concurrency: Record<string, unknown> = fm["concurrency"] ?? {};
  const mode = concurrency["mode"] as string | undefined;
  if (mode !== undefined && !CONCURRENCY_MODES.includes(mode)) {
    err("invalid_enum_value", `concurrency.mode \`${mode}\` is not one of ${CONCURRENCY_MODES}`);
  }
  if (mode && mode !== "etag_required" && !concurrency["rationale"]) {
    err("relaxation_without_rationale", `mode \`${mode}\` weakens protection without a rationale`);
  }
  if (mode === "idempotency_by_formula" && !concurrency["formula"]) {
    err("missing_required_field", "idempotency_by_formula without `formula`");
  }

  // ── interfaces ─────────────────────────────────────────────────────────────────────────────
  const interfaces: Record<string, any> = fm["interfaces"] ?? {};
  if (Object.keys(interfaces).length === 0) {
    err("missing_required_field", "at least one interface is required");
  }
  for (const [name, iface] of Object.entries(interfaces)) {
    const transport = iface?.transport;
    if (!transport) err("missing_transport", `interface \`${name}\` does not declare a transport`);
    else if (!TRANSPORTS.includes(transport)) {
      err("invalid_enum_value", `interface \`${name}\`: transport \`${transport}\` is unknown`);
    }
    for (const ref of iface?.covers_steps ?? []) {
      if (!stepIds.has(ref)) err("unknown_step_reference", `interface \`${name}\` covers unknown step \`${ref}\``);
    }
  }

  // ── tests ──────────────────────────────────────────────────────────────────────────────────
  const covered = new Set<string>();
  for (const test of tests) {
    const refs: any[] = Array.isArray(test?.covers) ? test.covers : [test?.covers];
    for (const ref of refs) {
      if (!stepIds.has(ref)) err("unknown_step_reference", `test \`${test?.id}\` covers unknown step \`${ref}\``);
      covered.add(ref);
    }
    if (!TEST_LEVELS.includes(test?.level)) {
      err("invalid_enum_value", `test \`${test?.id}\`: level \`${test?.level}\` is unknown`);
    }
  }

  const gaps = new Set<string>((fm["coverage_gaps"] ?? []).map((gap: any) => gap?.step));
  for (const gap of gaps) {
    if (!stepIds.has(gap)) err("unknown_step_reference", `coverage_gaps names unknown step \`${gap}\``);
  }
  for (const sid of stepIds) {
    if (!covered.has(sid) && !gaps.has(sid)) {
      warn("step_unproven", `step \`${sid}\` has no test and no declared gap`);
    }
  }

  // ── outcomes, continuation, parameters ─────────────────────────────────────────────────────
  //
  // Three rules that need nothing but the card itself. Each one exists because the field it
  // guards is otherwise a claim nobody can be wrong about — and a claim nobody can be wrong
  // about is a claim nobody maintains.
  const outcomes: any[] = fm["outcomes"] ?? [];
  const outcomeIds = new Set<string>(outcomes.map((o: any) => o?.id));

  for (const [name, iface] of Object.entries<any>(interfaces)) {
    const declared: number[] = iface?.responses ?? [];
    if (declared.length === 0) continue; // the field is optional; absent is not a claim

    const returned = new Map<number, string>();
    for (const step of steps) {
      const code = step?.on_violation?.http;
      if (typeof code === "number") returned.set(code, `step \`${step.id}\``);
    }
    for (const outcome of outcomes) {
      if (typeof outcome?.http === "number") returned.set(outcome.http, `outcome \`${outcome.id}\``);
    }
    for (const [code, who] of returned) {
      if (!declared.includes(code)) {
        err("undeclared_response", `interface \`${name}\`: ${who} returns ${code}, absent from \`responses\``);
      }
    }
  }

  // A violated step that answers with success is either a typo or not a violation at all. The
  // second case is real: a bulk operation reports per-item failures inside a 200, and the whole
  // shape of `steps[]` — violated, therefore stopped, therefore an error code — does not fit it.
  // A warning, not an error, because the honest bulk card would otherwise be unwritable.
  const perItem = fm["per_item"];
  for (const step of steps) {
    const code = step?.on_violation?.http;
    if (typeof code === "number" && code >= 200 && code < 300) {
      if (perItem) {
        // With `per_item` declared there is a true place to write this, so writing it falsely
        // is a mistake rather than a shortage of vocabulary.
        err(
          "per_item_failure_as_violation",
          `step \`${step.id}\` answers ${code}; this card declares \`per_item\`, so a per-item failure belongs there and carries no status`,
        );
      } else {
        warn(
          "violation_with_success_status",
          `step \`${step.id}\` is violated yet answers ${code} — either a typo, or this is a per-item failure and belongs in \`per_item\``,
        );
      }
    }
  }

  // `after` may name an outcome or a job state. Axis F was designed with one example in hand —
  // an operation answering immediately and suspending on an outcome — and the rule was fitted to
  // it. A request thread suspends on `done`, a *job state*, and waits there for a person. The
  // axis survived that; its check did not.
  const continuation = fm["continuation"];
  if (continuation && typeof continuation === "object") {
    const jobStates: string[] = fm["async_execution"]?.job_states ?? [];
    if (!outcomeIds.has(continuation.after) && !jobStates.includes(continuation.after)) {
      err(
        "continuation_without_outcome",
        `\`continuation.after\` names \`${continuation.after}\`, which is neither a declared outcome nor a job state`,
      );
    }
  }

  // ── covers_outcomes ────────────────────────────────────────────────────────────────────────
  //
  // Round 10, from tracing one real button: of the four outcomes the server declares, the screen
  // showed two and swallowed two in a bodyless catch — a rollback indistinguishable from success.
  // The card had no way to say it. This map is that way. The rule is deliberately asymmetric:
  // once the map exists, a MISSING outcome is an error, while an outcome explicitly mapped to
  // null is only a warning. The field forbids silent gaps, not honest ones.
  //
  // The vocabulary is what THIS INVOCATION can end with — not everything the record will ever
  // be. Round 11 met the second card the rule had ever seen and demanded that a *create* screen
  // display `checking`, `executing`, `done`, `rejected`, `failed`, `archived`: job states the
  // call never returns, reached later and watched through `observe_via` — a different operation
  // with a screen of its own. Job states stayed in the vocabulary from the continuation rule,
  // which asks a genuinely different question. Six errors, all false, on the first honest card.
  const outcomeVocabulary = new Map<string, string>();
  for (const outcome of outcomes) {
    if (outcome?.id) outcomeVocabulary.set(outcome.id, "outcomes");
  }
  const transition = fm["data_transition"];
  if (transition && typeof transition === "object") {
    const targets: any[] = Array.isArray(transition.to) ? transition.to : transition.to ? [transition.to] : [];
    for (const target of targets) outcomeVocabulary.set(target, "data_transition.to");
  }
  for (const step of steps) {
    const error = step?.on_violation?.error;
    if (error) outcomeVocabulary.set(error, `step \`${step.id}\``);
  }
  // Per-item failures belong here and job states do not, and the line between them is not taste.
  // A per-item failure arrives in THIS call's response — the user is looking at the screen when
  // it happens. A job state is the record's later life, watched through `observe_via`. Round 11
  // measured a bulk screen that discards the response body entirely: ten items selected, three
  // rejected inside a 200, and the page says nothing at all. Without these in the vocabulary the
  // card had no way to admit it, which is the one thing this field exists to prevent.
  for (const failure of fm["per_item"]?.failures ?? []) {
    if (failure?.code) outcomeVocabulary.set(failure.code, "per_item failure");
  }
  for (const [name, iface] of Object.entries<any>(interfaces)) {
    const covers = iface?.covers_outcomes;
    if (!covers || typeof covers !== "object") continue;
    for (const key of Object.keys(covers)) {
      if (!outcomeVocabulary.has(key)) {
        err(
          "covers_unknown_outcome",
          `interface \`${name}\`: covers_outcomes names \`${key}\`, which no outcome, transition target, or violation declares`,
        );
      }
    }
    for (const [id, where] of outcomeVocabulary) {
      if (!(id in covers)) {
        err(
          "outcome_not_covered",
          `interface \`${name}\`: outcome \`${id}\` (${where}) is absent from covers_outcomes — write it, even as null`,
        );
      } else if (covers[id] === null) {
        warn("outcome_unshown", `interface \`${name}\`: outcome \`${id}\` is declared not shown to the user`);
      }
    }

    // Shown, but shown as the same thing. Between "the user sees it" and "the user sees nothing"
    // sits the state nobody notices: two different endings wearing one sentence. Measured on a
    // real screen — 401 and 403 both surfaced as «Не удалось выполнить действие. Попробуйте ещё
    // раз.», so the one user who must give consent is told to retry, and retrying can never work.
    // A warning: collapsing outcomes is sometimes a deliberate choice, and the card is the place
    // where that choice stops being invisible.
    const byText = new Map<string, string[]>();
    for (const [id, shown] of Object.entries<any>(covers)) {
      if (typeof shown !== "string") continue;
      const key = shown.trim().toLowerCase();
      byText.set(key, [...(byText.get(key) ?? []), id]);
    }
    for (const [, ids] of byText) {
      if (ids.length > 1) {
        warn(
          "outcomes_indistinguishable",
          `interface \`${name}\`: outcomes ${ids.map((i) => `\`${i}\``).join(", ")} are shown identically — the user cannot tell them apart`,
        );
      }
    }
  }

  for (const [name, iface] of Object.entries<any>(interfaces)) {
    for (const parameter of iface?.parameters ?? []) {
      if (parameter?.handling !== "decorative") continue;
      const path: string = iface?.path ?? "";
      if (!path.includes(`{${parameter.name}}`)) {
        err(
          "decorative_parameter_not_in_path",
          `interface \`${name}\`: \`${parameter.name}\` is declared decorative but does not appear in \`${path || "(no path)"}\``,
        );
      }
    }
  }

  // An operation that produces no effect has nothing to reverse. Saying `reversible` there
  // answers a different question than the one asked, and both read-only cards in this project
  // said it — because the field is required and, until round 7, had no honest value for them.
  // A warning, not an error: the reading is a judgement about the card's own claims, and a
  // checker that hard-fails on judgement gets switched off.
  // `mutates` is the format's own word for "writes without a state change" (round 21: a card
  // for logging a set — transition null, mutates seven fields — was called read-only here).
  const mutates = fm["mutates"];
  const writesWithoutTransition = Array.isArray(mutates) && mutates.length > 0;
  if (fm["data_transition"] === null && !writesWithoutTransition && fm["provenance"] === "none" && fm["reversibility"] === "reversible") {
    warn("reversibility_overstated", "read-only operation claims `reversible`; nothing was done, so nothing can be undone");
  }

  // ── effect of a write ──────────────────────────────────────────────────────────────────────
  // Three truthful forms for a null transition: `mutates` (a write that names its fields),
  // `provenance: none` (nothing recorded AND nothing changed), or `records_only: true` — the
  // audit-only read: changes no domain state, records who asked. The third arrived from issue
  // #1: a compliance read had to pick between two lies, and the smaller lie was still a lie.
  if ("data_transition" in fm && fm["data_transition"] === null) {
    const provenance = fm["provenance"];
    const recordsOnly = provenance && typeof provenance === "object" && provenance.records_only === true;
    if (!fm["mutates"] && provenance !== "none" && !recordsOnly) {
      err(
        "write_without_effect",
        "`data_transition: null` with neither `mutates`, `provenance: none`, nor `records_only: true` — the write does not say what it changes",
      );
    }
  }

  // ── cross-card references ──────────────────────────────────────────────────────────────────
  if (knownIds !== null) {
    const reversibility = fm["reversibility"];
    if (reversibility && typeof reversibility === "object") {
      const target = reversibility.reversible_via;
      if (target && !knownIds.has(target)) {
        warn("undescribed_counterpart", `\`reversible_via\` points at undescribed \`${target}\``);
      }
    }
    const serves = fm["serves_step"];
    if (serves && !knownIds.has(serves.operation)) {
      warn("undescribed_counterpart", `\`serves_step\` points at undescribed \`${serves.operation}\``);
    }
  }

  return out;
}
