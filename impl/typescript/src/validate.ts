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
const CONCURRENCY_MODES = ["etag_required", "idempotency_by_header", "idempotency_by_formula", "none_by_design"];
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
  for (const state of fm["async_execution"]?.job_states ?? []) {
    outcomeVocabulary.set(state, "job state");
  }
  for (const [name, iface] of Object.entries<any>(interfaces)) {
    const covers = iface?.covers_outcomes;
    if (!covers || typeof covers !== "object") continue;
    for (const key of Object.keys(covers)) {
      if (!outcomeVocabulary.has(key)) {
        err(
          "covers_unknown_outcome",
          `interface \`${name}\`: covers_outcomes names \`${key}\`, which no outcome, transition target, violation, or job state declares`,
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
  if (fm["data_transition"] === null && fm["provenance"] === "none" && fm["reversibility"] === "reversible") {
    warn("reversibility_overstated", "read-only operation claims `reversible`; nothing was done, so nothing can be undone");
  }

  // ── effect of a write ──────────────────────────────────────────────────────────────────────
  if ("data_transition" in fm && fm["data_transition"] === null) {
    if (!fm["mutates"] && fm["provenance"] !== "none") {
      err("write_without_effect", "`data_transition: null` with neither `mutates` nor `provenance: none`");
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
