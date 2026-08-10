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
    for state in (fm.get("async_execution") or {}).get("job_states") or []:
        outcome_vocabulary[state] = "job state"
    for name, iface in interfaces.items():
        covers = iface.get("covers_outcomes")
        if not isinstance(covers, dict):
            continue
        for key in covers:
            if key not in outcome_vocabulary:
                err("covers_unknown_outcome",
                    f"interface `{name}`: covers_outcomes names `{key}`, which no outcome, "
                    "transition target, violation, or job state declares")
        for oid, where in outcome_vocabulary.items():
            if oid not in covers:
                err("outcome_not_covered",
                    f"interface `{name}`: outcome `{oid}` ({where}) is absent from "
                    "covers_outcomes — write it, even as null")
            elif covers[oid] is None:
                warn("outcome_unshown",
                     f"interface `{name}`: outcome `{oid}` is declared not shown to the user")

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
        if not fm.get("mutates") and fm.get("provenance") != "none":
            err("write_without_effect",
                "`data_transition: null` with neither `mutates` nor `provenance: none`")

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


def collect(paths: list[str]) -> list[str]:
    files: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            files += glob.glob(os.path.join(path, "**", "*.op.md"), recursive=True)
        else:
            files.append(path)
    return sorted(files)


def run_files(paths: list[str]) -> int:
    files = collect(paths)
    cards = {}
    for path in files:
        fm = front_matter(path)
        if fm:
            cards[fm.get("id")] = (path, fm)
    known = set(cards)

    errors = warnings = 0
    for card_id, (path, fm) in sorted(cards.items()):
        for finding in validate(fm, os.path.basename(path), known):
            marker = "ERROR  " if finding.severity == "error" else "warning"
            print(f"  {marker}  {os.path.basename(path)}: {finding}")
            errors += finding.severity == "error"
            warnings += finding.severity == "warning"
    print(f"\n{len(cards)} card(s): {errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


def run_conformance() -> int:
    manifest = yaml.safe_load(open(os.path.join(CORPUS, "manifest.yaml"), encoding="utf-8"))
    passed = failed = 0

    for case in manifest["cases"]:
        path = os.path.join(CORPUS, "cases", *case["file"].split("/"))
        fm = front_matter(path)
        findings = validate(fm, os.path.basename(path)) if fm else [
            Finding("missing_required_field", "no front matter")]
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
