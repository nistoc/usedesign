#!/usr/bin/env python3
"""Prototype validator for the Operation Card format.

Checks the rules that a JSON Schema cannot express — cross-references between steps, tests and
interfaces — plus the structural rules, so that it can run the conformance corpus end to end.

This is a prototype, not a package: it exists to prove the format is implementable on a second
runtime and to keep the corpus honest before the reference implementation is written.

Usage:
    python validate.py --conformance          run the conformance corpus
    python validate.py <path> [<path> ...]    validate cards (files or directories)
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CORPUS = os.path.join(REPO, "tests", "conformance")

REQUIRED = ["id", "title", "actors", "maturity", "steps",
            "concurrency", "interfaces", "data", "provenance", "reversibility"]
MATURITY = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"]
CONCURRENCY_MODES = ["etag_required", "idempotency_by_header",
                     "idempotency_by_formula", "none_by_design"]
TRANSPORTS = ["http_rest", "json_rpc", "in_process", "ui"]
TEST_LEVELS = ["unit", "integration", "ui", "contract"]

OPERATION_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+){2,}$")
STEP_ID = re.compile(r"^s[0-9]+-[a-z0-9-]+$")

EVIDENCE_FOR = {  # maturity level -> evidence key it must carry
    "implemented": "implemented",
    "tested": "tested",
    "in_production": "deployed",
}


class Finding:
    __slots__ = ("code", "detail", "severity")

    def __init__(self, code: str, detail: str, severity: str = "error"):
        self.code, self.detail, self.severity = code, detail, severity

    def __repr__(self) -> str:
        return f"{self.code}: {self.detail}"


def front_matter(path: str):
    """Return the parsed YAML front matter, or None if the file has none."""
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return yaml.safe_load(text[3:end])


def validate(fm: dict, filename: str = "", known_ids: set[str] | None = None) -> list[Finding]:
    """Validate one card. `known_ids` enables cross-card reference warnings."""
    out: list[Finding] = []

    def err(code: str, detail: str):
        out.append(Finding(code, detail))

    def warn(code: str, detail: str):
        out.append(Finding(code, detail, "warning"))

    for field in REQUIRED:
        if field not in fm:
            err("missing_required_field", f"`{field}` is absent")

    card_id = fm.get("id", "")
    if card_id and not OPERATION_ID.match(card_id):
        err("malformed_operation_id", f"`{card_id}` is not <area>.<object>.<action>")
    if filename and card_id and os.path.splitext(filename)[0] != f"{card_id}.op":
        warn("filename_mismatch", f"file name does not match id `{card_id}`")

    if "scenario" not in fm and "serves_step" not in fm:
        err("no_owner", "neither `scenario` nor `serves_step` is present")

    maturity = fm.get("maturity")
    if maturity is not None and maturity not in MATURITY:
        err("invalid_enum_value", f"maturity `{maturity}` is not one of {MATURITY}")

    # ── steps ────────────────────────────────────────────────────────────────
    steps = fm.get("steps") or []
    step_ids: set[str] = set()
    for step in steps:
        sid = step.get("id", "")
        if not STEP_ID.match(sid):
            err("malformed_step_id", f"`{sid}` is not s<N>-<name>")
        elif sid in step_ids:
            err("duplicate_step_id", f"`{sid}` appears more than once")
        step_ids.add(sid)

    # ── maturity vs evidence ─────────────────────────────────────────────────
    evidence = fm.get("maturity_evidence") or {}
    tests = fm.get("tests") or []
    if maturity in EVIDENCE_FOR:
        # Every level implies the ones below it.
        for level in ("implemented", "tested", "in_production"):
            if MATURITY.index(maturity) >= MATURITY.index(level):
                key = EVIDENCE_FOR[level]
                if key not in evidence:
                    err("maturity_without_evidence",
                        f"`{maturity}` claimed without `maturity_evidence.{key}`")
    if maturity in ("tested", "in_production") and not tests:
        err("maturity_without_tests", f"`{maturity}` claimed with an empty `tests[]`")

    # ── concurrency ──────────────────────────────────────────────────────────
    concurrency = fm.get("concurrency") or {}
    mode = concurrency.get("mode")
    if mode is not None and mode not in CONCURRENCY_MODES:
        err("invalid_enum_value", f"concurrency.mode `{mode}` is not one of {CONCURRENCY_MODES}")
    if mode and mode != "etag_required" and not concurrency.get("rationale"):
        err("relaxation_without_rationale", f"mode `{mode}` weakens protection without a rationale")
    if mode == "idempotency_by_formula" and not concurrency.get("formula"):
        err("missing_required_field", "idempotency_by_formula without `formula`")

    # ── interfaces ───────────────────────────────────────────────────────────
    interfaces = fm.get("interfaces") or {}
    if not interfaces:
        err("missing_required_field", "at least one interface is required")
    for name, iface in interfaces.items():
        transport = iface.get("transport")
        if not transport:
            err("missing_transport", f"interface `{name}` does not declare a transport")
        elif transport not in TRANSPORTS:
            err("invalid_enum_value", f"interface `{name}`: transport `{transport}` is unknown")
        for ref in iface.get("covers_steps") or []:
            if ref not in step_ids:
                err("unknown_step_reference", f"interface `{name}` covers unknown step `{ref}`")

    # ── tests ────────────────────────────────────────────────────────────────
    covered: set[str] = set()
    for test in tests:
        refs = test.get("covers")
        refs = refs if isinstance(refs, list) else [refs]
        for ref in refs:
            if ref not in step_ids:
                err("unknown_step_reference", f"test `{test.get('id')}` covers unknown step `{ref}`")
            covered.add(ref)
        if test.get("level") not in TEST_LEVELS:
            err("invalid_enum_value", f"test `{test.get('id')}`: level `{test.get('level')}` is unknown")

    gaps = {gap.get("step") for gap in (fm.get("coverage_gaps") or [])}
    for gap in gaps:
        if gap not in step_ids:
            err("unknown_step_reference", f"coverage_gaps names unknown step `{gap}`")
    for sid in step_ids:
        if sid not in covered and sid not in gaps:
            warn("step_unproven", f"step `{sid}` has no test and no declared gap")

    # ── outcomes, continuation, parameters ───────────────────────────────────
    #
    # Three rules that need nothing but the card itself. Each guards a field that would
    # otherwise be a claim nobody can be wrong about — and nobody maintains those.
    outcomes = fm.get("outcomes") or []
    outcome_ids = {o.get("id") for o in outcomes}

    for name, iface in interfaces.items():
        declared = iface.get("responses") or []
        if not declared:            # the field is optional; absent is not a claim
            continue
        returned: dict[int, str] = {}
        for step in steps:
            code = (step.get("on_violation") or {}).get("http")
            if isinstance(code, int):
                returned[code] = f"step `{step.get('id')}`"
        for outcome in outcomes:
            if isinstance(outcome.get("http"), int):
                returned[outcome["http"]] = f"outcome `{outcome.get('id')}`"
        for code, who in returned.items():
            if code not in declared:
                err("undeclared_response",
                    f"interface `{name}`: {who} returns {code}, absent from `responses`")

    # A violated step that answers with success is either a typo or not a violation at all. The
    # second case is real: a bulk operation reports per-item failures inside a 200, and the shape
    # of `steps[]` — violated, therefore stopped, therefore an error code — does not fit it.
    per_item = fm.get("per_item")
    for step in steps:
        code = (step.get("on_violation") or {}).get("http")
        if isinstance(code, int) and 200 <= code < 300:
            if per_item:
                # With `per_item` there is a true place for this, so writing it falsely is a
                # mistake rather than a shortage of vocabulary.
                err("per_item_failure_as_violation",
                    f"step `{step.get('id')}` answers {code}; this card declares `per_item`, so a "
                    "per-item failure belongs there and carries no status")
            else:
                warn("violation_with_success_status",
                     f"step `{step.get('id')}` is violated yet answers {code} — either a typo, or "
                     "this is a per-item failure and belongs in `per_item`")

    # `after` may name an outcome or a job state. Axis F was designed from one example and its
    # rule was fitted to it; a request thread suspends on `done`, a job state, and waits there
    # for a person.
    continuation = fm.get("continuation")
    if isinstance(continuation, dict):
        job_states = (fm.get("async_execution") or {}).get("job_states") or []
        if continuation.get("after") not in outcome_ids and continuation.get("after") not in job_states:
            err("continuation_without_outcome",
                f"`continuation.after` names `{continuation.get('after')}`, "
                "which is neither a declared outcome nor a job state")

    # ── covers_outcomes ──────────────────────────────────────────────────────
    #
    # Round 10, from tracing one real button: of the four outcomes the server declares, the
    # screen showed two and swallowed two in a bodyless catch — a rollback indistinguishable
    # from success. The card had no way to say it. This map is that way. The rule is
    # deliberately asymmetric: once the map exists, a MISSING outcome is an error, while an
    # outcome explicitly mapped to null is only a warning. It forbids silent gaps, not honest ones.
    #
    # The vocabulary is what THIS INVOCATION can end with — not everything the record will ever
    # be. Round 11: the rule demanded that a *create* screen display `checking`, `executing`,
    # `done`, `rejected`, `failed`, `archived` — job states the call never returns, reached later
    # and watched through `observe_via`, a different operation with a screen of its own.
    outcome_vocabulary: dict[str, str] = {}
    for outcome in outcomes:
        if outcome.get("id"):
            outcome_vocabulary[outcome["id"]] = "outcomes"
    transition = fm.get("data_transition")
    if isinstance(transition, dict):
        raw_to = transition.get("to")
        targets = raw_to if isinstance(raw_to, list) else ([raw_to] if raw_to else [])
        for target in targets:
            outcome_vocabulary[target] = "data_transition.to"
    for step in steps:
        error_id = (step.get("on_violation") or {}).get("error")
        if error_id:
            outcome_vocabulary[error_id] = f"step `{step.get('id')}`"
    # Per-item failures belong here and job states do not. A per-item failure arrives in THIS
    # call's response — the user is watching the screen when it happens; a job state is the
    # record's later life, seen through `observe_via`. Round 11 measured a bulk screen that
    # discards the response body: ten selected, three rejected inside a 200, nothing shown.
    for failure in (fm.get("per_item") or {}).get("failures") or []:
        if failure.get("code"):
            outcome_vocabulary[failure["code"]] = "per_item failure"
    for name, iface in interfaces.items():
        covers = iface.get("covers_outcomes")
        if not isinstance(covers, dict):
            continue
        for key in covers:
            if key not in outcome_vocabulary:
                err("covers_unknown_outcome",
                    f"interface `{name}`: covers_outcomes names `{key}`, which no outcome, "
                    "transition target, or violation declares")
        for oid, where in outcome_vocabulary.items():
            if oid not in covers:
                err("outcome_not_covered",
                    f"interface `{name}`: outcome `{oid}` ({where}) is absent from "
                    "covers_outcomes — write it, even as null")
            elif covers[oid] is None:
                warn("outcome_unshown",
                     f"interface `{name}`: outcome `{oid}` is declared not shown to the user")

        # Shown, but shown as the same thing. Between "the user sees it" and "the user sees
        # nothing" sits the state nobody notices: two different endings wearing one sentence.
        # Measured on a real screen — 401 and 403 both surfaced as the same «попробуйте ещё раз»,
        # so the user who must give consent is told to retry, and retrying can never work.
        by_text: dict[str, list[str]] = {}
        for oid, shown in covers.items():
            if not isinstance(shown, str):
                continue
            by_text.setdefault(shown.strip().lower(), []).append(oid)
        for ids in by_text.values():
            if len(ids) > 1:
                shown_ids = ", ".join(f"`{i}`" for i in ids)
                warn("outcomes_indistinguishable",
                     f"interface `{name}`: outcomes {shown_ids} are shown identically — "
                     "the user cannot tell them apart")

    for name, iface in interfaces.items():
        for parameter in iface.get("parameters") or []:
            if parameter.get("handling") != "decorative":
                continue
            path = iface.get("path") or ""
            if "{" + str(parameter.get("name")) + "}" not in path:
                err("decorative_parameter_not_in_path",
                    f"interface `{name}`: `{parameter.get('name')}` is declared decorative "
                    f"but does not appear in `{path or '(no path)'}`")

    # An operation that produces no effect has nothing to reverse. Saying `reversible` there
    # answers a different question than the one asked, and both read-only cards in this project
    # said it — the field is required and, until round 7, had no honest value for them.
    if (fm.get("data_transition", False) is None
            and fm.get("provenance") == "none"
            and fm.get("reversibility") == "reversible"):
        warn("reversibility_overstated",
             "read-only operation claims `reversible`; nothing was done, so nothing can be undone")

    # ── effect of a write ────────────────────────────────────────────────────
    if "data_transition" in fm and fm["data_transition"] is None:
        provenance = fm.get("provenance")
        records_only = isinstance(provenance, dict) and provenance.get("records_only") is True
        if not fm.get("mutates") and provenance != "none" and not records_only:
            err("write_without_effect",
                "`data_transition: null` with neither `mutates`, `provenance: none`, "
                "nor `records_only: true` — the write does not say what it changes")

    # ── cross-card references ────────────────────────────────────────────────
    if known_ids is not None:
        reversibility = fm.get("reversibility")
        if isinstance(reversibility, dict):
            target = reversibility.get("reversible_via")
            if target and target not in known_ids:
                warn("undescribed_counterpart", f"`reversible_via` points at undescribed `{target}`")
        serves = fm.get("serves_step")
        if serves and serves.get("operation") not in known_ids:
            warn("undescribed_counterpart",
                 f"`serves_step` points at undescribed `{serves.get('operation')}`")

    return out


# ── form contracts ───────────────────────────────────────────────────────────
#
# Check 5 used to read contracts raw, and the measured failure is quiet in the worst way: a
# contract with `presnts` misspelled lost its whole "must show" section, and every line of it
# resurfaced as SOMEBODY ELSE'S warning — "element rendered but not described". The rules are
# hand-rolled with named codes so both implementations agree on WHAT is wrong.

FORM_REQUIRED = ["usedesign_form", "id", "screen", "presents"]
FORM_KEYS = {"usedesign_form", "id", "screen", "page", "entity", "presents", "controls",
             "groups", "removed"}
ELEMENT_KEYS = {"field", "shows", "when", "note"}
CONTROL_KEYS = {"control", "calls", "shown_when", "shown_when_rule", "opens",
                "behaviour", "placement", "note"}
GROUP_KEYS = {"group", "role", "contains", "note"}
GROUP_ROLES = ["header", "footer", "section", "table", "list", "toolbar", "menu"]
REMOVED_KEYS = {"control", "was", "verdict"}


def validate_form(fm: dict, filename: str = "",
                  known_forms: set[str] | None = None) -> list[Finding]:
    """Validate one form contract. `known_forms` enables the `opens` link warning."""
    out: list[Finding] = []

    def err(code: str, detail: str):
        out.append(Finding(code, detail))

    def warn(code: str, detail: str):
        out.append(Finding(code, detail, "warning"))

    for field in FORM_REQUIRED:
        if field not in fm:
            err("missing_required_field", f"`{field}` is absent")
    # The typo gets its own name: reported as an unknown key, `presnts` says what happened.
    for key in fm:
        if key not in FORM_KEYS:
            err("unknown_field", f"`{key}` is not part of the form contract format")

    form_id = fm.get("id") or ""
    if form_id and not OPERATION_ID.match(str(form_id)):
        err("malformed_form_id", f"`{form_id}` is not <area>.<object>.<name>")

    presents = fm.get("presents") if isinstance(fm.get("presents"), list) else []
    seen_fields: set[str] = set()
    for index, element in enumerate(presents):
        if not isinstance(element, dict):
            continue
        for required in ("field", "shows"):
            if not element.get(required):
                err("missing_required_field", f"presents[{index}]: `{required}` is absent")
        for key in element:
            if key not in ELEMENT_KEYS:
                err("unknown_field", f"presents[{index}]: `{key}` is not part of an element line")
        field = element.get("field")
        if field:
            if field in seen_fields:
                err("duplicate_element", f"`{field}` appears more than once in presents")
            seen_fields.add(field)

    controls = fm.get("controls") if isinstance(fm.get("controls"), list) else []
    seen_controls: set[str] = set()
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            continue
        if not control.get("control"):
            err("missing_required_field", f"controls[{index}]: `control` is absent")
        for key in control:
            if key not in CONTROL_KEYS:
                err("unknown_field", f"controls[{index}]: `{key}` is not part of a control line")
        name = control.get("control")
        if name:
            if name in seen_controls:
                err("duplicate_control", f"`{name}` appears more than once in controls")
            seen_controls.add(name)
        opens = control.get("opens")
        if opens and known_forms is not None and opens not in known_forms:
            warn("undescribed_form",
                 f"control `{name}` opens `{opens}`, which no contract in this set describes")

    # ── groups ───────────────────────────────────────────────────────────────
    # Grouping by purpose: headers, footers, tables, and which controls sit where. Array order
    # IS the group order. Membership is authored, not yet verified — the inventory records
    # anchors flat — but a group naming a member the contract itself does not declare is wrong
    # today, by the contract's own text, and needs no inventory to prove it.
    members = seen_fields | seen_controls
    seen_groups: set[str] = set()
    claimed: dict[str, str] = {}
    groups = fm.get("groups") if isinstance(fm.get("groups"), list) else []
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            continue
        for required in ("group", "role", "contains"):
            if not group.get(required):
                err("missing_required_field", f"groups[{index}]: `{required}` is absent")
        for key in group:
            if key not in GROUP_KEYS:
                err("unknown_field", f"groups[{index}]: `{key}` is not part of a group line")
        name = group.get("group")
        if name:
            if name in seen_groups:
                err("duplicate_group", f"`{name}` appears more than once in groups")
            seen_groups.add(name)
        role = group.get("role")
        if role and role not in GROUP_ROLES:
            err("invalid_enum_value", f"groups[{index}]: role `{role}` is not one of {GROUP_ROLES}")
        contains = group.get("contains") if isinstance(group.get("contains"), list) else []
        for member in contains:
            if member not in members:
                err("unknown_group_member",
                    f"group `{name}` contains `{member}`, which no element or control declares")
            already = claimed.get(member)
            if already and already != name:
                err("element_in_two_groups",
                    f"`{member}` sits in `{already}` and `{name}` — an element renders in one place")
            if name:
                claimed[member] = name

    # One document both requiring and forbidding a control is not incompleteness — it is the
    # contract disagreeing with itself, and no amount of code can satisfy it.
    removed = fm.get("removed") if isinstance(fm.get("removed"), list) else []
    for index, entry in enumerate(removed):
        if not isinstance(entry, dict):
            continue
        if not entry.get("control"):
            err("missing_required_field", f"removed[{index}]: `control` is absent")
        for key in entry:
            if key not in REMOVED_KEYS:
                err("unknown_field", f"removed[{index}]: `{key}` is not part of a removed line")
        name = entry.get("control")
        if name and name in seen_controls:
            err("removed_also_required",
                f"`{name}` is listed in controls and in removed — "
                "the contract both requires and forbids it")

    return out


def collect(paths: list[str]) -> list[str]:
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            # Both document kinds, deliberately: `validate forms/` used to collect nothing and
            # print "0 card(s): 0 error(s)" — a green verdict on a directory it had not read.
            files += glob.glob(os.path.join(path, "**", "*.op.md"), recursive=True)
            files += glob.glob(os.path.join(path, "**", "*.contract.md"), recursive=True)
        else:
            files.append(path)
    return sorted(files)


def run_files(paths: list[str]) -> int:
    files = collect(paths)
    cards: dict = {}
    forms: dict = {}
    for path in files:
        fm = front_matter(path)
        if fm:
            target = forms if fm.get("usedesign_form") == 1 else cards
            target[fm.get("id")] = (path, fm)
    known = set(cards)
    known_forms = set(forms)

    errors = warnings = 0

    def show(path: str, findings: list[Finding]):
        nonlocal errors, warnings
        for finding in findings:
            marker = "ERROR  " if finding.severity == "error" else "warning"
            print(f"  {marker}  {os.path.basename(path)}: {finding}")
            errors += finding.severity == "error"
            warnings += finding.severity == "warning"

    for _, (path, fm) in sorted(cards.items()):
        show(path, validate(fm, os.path.basename(path), known))
    for _, (path, fm) in sorted(forms.items()):
        show(path, validate_form(fm, os.path.basename(path), known_forms))
    print(f"\n{len(cards)} card(s), {len(forms)} form contract(s): "
          f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def run_conformance() -> int:
    manifest = yaml.safe_load(open(os.path.join(CORPUS, "manifest.yaml"), encoding="utf-8"))
    passed = failed = 0

    for case in manifest["cases"]:
        path = os.path.join(CORPUS, "cases", *case["file"].split("/"))
        fm = front_matter(path)
        if not fm:
            findings = [Finding("missing_required_field", "no front matter")]
        elif fm.get("usedesign_form") == 1:
            findings = validate_form(fm, os.path.basename(path))
        else:
            findings = validate(fm, os.path.basename(path))
        errors = [f for f in findings if f.severity == "error"]
        verdict = "invalid" if errors else "valid"
        codes = sorted({f.code for f in errors})

        warned = sorted({f.code for f in findings if f.severity == "warning"})

        problems = []
        if verdict != case["expect"]:
            problems.append(f"expected {case['expect']}, got {verdict}")
        for code in case.get("codes", []):
            if code not in codes:
                problems.append(f"missing code `{code}`")
        # Warnings are part of the contract too: a rule that only warns is still a rule two
        # implementations must agree about.
        for code in case.get("warnings", []):
            if code not in warned:
                problems.append(f"missing warning `{code}`")

        if problems:
            failed += 1
            print(f"  FAIL  {case['file']}")
            for problem in problems:
                print(f"          {problem}")
            if codes:
                print(f"          reported: {', '.join(codes)}")
        else:
            passed += 1
            print(f"  ok    {case['file']}" + (f"  [{', '.join(codes)}]" if codes else ""))

    print(f"\nconformance: {passed} passed, {failed} failed")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Operation Cards.")
    parser.add_argument("paths", nargs="*", help="card files or directories")
    parser.add_argument("--conformance", action="store_true", help="run the conformance corpus")
    args = parser.parse_args()

    if args.conformance:
        return run_conformance()
    if not args.paths:
        parser.print_help()
        return 2
    return run_files(args.paths)


if __name__ == "__main__":
    sys.exit(main())
