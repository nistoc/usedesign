#!/usr/bin/env python3
"""Prototype for check 1 — no wild endpoints.

Compares what the code registers (a route inventory, produced by the checked repository) against
what the cards declare. See design/route-conformance.md for why the comparison works this way and
why usedesign does not extract routes itself.

This is a prototype, not a package.

Usage:
    python check.py <path to usedesign.config.yaml>
    python check.py --conformance          run the check-1 conformance corpus
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import sys
from xml.etree import ElementTree

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

from validate import front_matter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CORPUS = os.path.join(REPO, "tests", "conformance", "checks")

METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

# Parameter syntaxes seen in the wild: {name} · :name · <name> · <converter:name>
PARAM = re.compile(r"\{[^}]*\}|:[A-Za-z_][A-Za-z0-9_]*|<[^>]*>")


class Finding:
    __slots__ = ("code", "detail", "severity")

    def __init__(self, code: str, detail: str, severity: str = "error"):
        self.code, self.detail, self.severity = code, detail, severity

    def __repr__(self) -> str:
        return f"{self.code}: {self.detail}"


def normalise(method: str, path: str) -> tuple[str, str]:
    """Reduce a route to what identifies it: method and path *shape*.

    Parameter names are documentation, not identity — a card saying {copyId} and a framework
    saying :id describe the same route. See design/route-conformance.md §4, including the case
    this deliberately cannot tell apart.
    """
    shape = PARAM.sub("{}", path.strip())
    if len(shape) > 1:
        shape = shape.rstrip("/")
    return method.strip().upper(), shape


def load_config(path: str) -> tuple[dict, str]:
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict) or config.get("usedesign_config") != 1:
        sys.exit(f"{path}: not a usedesign config (expected `usedesign_config: 1`)")
    return config, os.path.dirname(os.path.abspath(path))


def load_card_files(config: dict, base: str) -> tuple[list[tuple[str, dict]], list[Finding]]:
    """Return [(card id, front matter)] for every card the config points at."""
    findings: list[Finding] = []
    files: list[str] = []
    for pattern in config.get("cards") or []:
        files += glob.glob(os.path.join(base, pattern), recursive=True)

    if not files:
        findings.append(Finding("no_cards_found", "the `cards` patterns matched nothing"))

    cards: list[tuple[str, dict]] = []
    for path in sorted(set(files)):
        fm = front_matter(path)
        if fm:
            cards.append((fm.get("id", os.path.basename(path)), fm))
    return cards, findings


def load_cards(config: dict, base: str) -> tuple[dict, list[Finding]]:
    """Return {(method, shape): [card ids]} for every REST interface the cards declare."""
    declared: dict[tuple[str, str], list[str]] = {}
    cards, findings = load_card_files(config, base)

    for card_id, fm in cards:
        for name, iface in (fm.get("interfaces") or {}).items():
            if not isinstance(iface, dict) or iface.get("transport") != "http_rest":
                continue
            method, route = iface.get("method"), iface.get("path")
            if not method or not route:
                findings.append(Finding(
                    "incomplete_rest_interface",
                    f"{card_id}: interface `{name}` declares http_rest without method or path"))
                continue
            declared.setdefault(normalise(method, route), []).append(card_id)

    for key, owners in sorted(declared.items()):
        if len(owners) > 1:
            findings.append(Finding(
                "ambiguous_shape",
                f"{key[0]} {key[1]} is declared by {len(owners)} cards ({', '.join(owners)}) — "
                "the checker cannot tell them apart",
                "warning"))
    return declared, findings


def load_inventory(config: dict, base: str) -> tuple[list[dict], list[Finding], str]:
    location = config.get("inventory")
    if not location:
        return [], [Finding(
            "inventory_missing",
            "no `inventory` in the config — check 1 cannot run and is NOT considered passed")], ""

    path = os.path.join(base, location)
    if not os.path.exists(path):
        return [], [Finding("inventory_missing", f"{location} does not exist")], ""

    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    findings: list[Finding] = []
    if data.get("usedesign_inventory") != 1:
        findings.append(Finding("inventory_malformed", f"{location}: missing `usedesign_inventory: 1`"))
    if not data.get("produced_by"):
        findings.append(Finding("inventory_malformed", f"{location}: missing `produced_by`"))

    routes = data.get("routes") or []
    if not routes:
        findings.append(Finding(
            "inventory_empty",
            f"{location}: no routes — almost always a failed dump rather than an "
            "application with no routes"))
    for entry in routes:
        if entry.get("method") not in METHODS:
            findings.append(Finding(
                "inventory_malformed", f"{location}: unknown method `{entry.get('method')}`"))
    return routes, findings, data.get("produced_by", "")


def excluded_by(config: dict, method: str, shape: str):
    """Return the exclusion rule that covers this route, or None."""
    for rule in config.get("exclude") or []:
        if rule.get("method") and rule["method"].upper() != method:
            continue
        if fnmatch.fnmatch(shape, rule.get("path", "")):
            return rule
    return None


def check(config: dict, base: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    declared, card_findings = load_cards(config, base)
    findings += card_findings

    routes, inventory_findings, produced_by = load_inventory(config, base)
    findings += inventory_findings

    served: set[tuple[str, str]] = set()
    hidden: dict[int, int] = {}

    for entry in routes:
        method, shape = normalise(entry.get("method", ""), entry.get("path", ""))
        rule = excluded_by(config, method, shape)
        if rule is not None:
            index = (config.get("exclude") or []).index(rule)
            hidden[index] = hidden.get(index, 0) + 1
            continue
        served.add((method, shape))
        if (method, shape) not in declared:
            findings.append(Finding(
                "wild_endpoint",
                f"{method} {shape} is served but declared by no card"
                + (f" (source: {entry['source']})" if entry.get("source") else "")))

    for (method, shape), owners in sorted(declared.items()):
        if routes and (method, shape) not in served and not excluded_by(config, method, shape):
            findings.append(Finding(
                "phantom_route",
                f"{method} {shape} is declared by {', '.join(owners)} but is not served"))

    # An exclusion that hides nothing is dead; one that starts hiding more than it did is worth
    # seeing. Silence is what makes exclusion lists dangerous — see design note §5.
    # With no routes at all every exclusion is trivially dead; saying so adds noise to a run that
    # already reported the real problem, and cascading noise is how a checker teaches people to
    # stop reading it.
    rules = (config.get("exclude") or []) if routes else []
    for index, rule in enumerate(rules):
        if index not in hidden:
            findings.append(Finding(
                "dead_exclusion",
                f"`{rule.get('path')}` excluded nothing — remove it or fix the pattern",
                "warning"))

    summary = {
        "produced_by": produced_by,
        "served": len(routes),
        "excluded": sum(hidden.values()),
        "declared": len(declared),
        "hidden_per_rule": {(config.get("exclude") or [])[i].get("path"): n
                            for i, n in sorted(hidden.items())},
    }
    return findings, summary


def run_conformance() -> int:
    with open(os.path.join(CORPUS, "manifest.yaml"), encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    passed = failed = 0

    for case in manifest["cases"]:
        config, base = load_config(
            os.path.join(CORPUS, "cases", case["dir"], "usedesign.config.yaml"))
        findings, _ = check(config, base)
        errors = [f for f in findings if f.severity == "error"]
        verdict = "fail" if errors else "pass"
        codes = sorted({f.code for f in errors})
        warnings = sorted({f.code for f in findings if f.severity == "warning"})

        problems = []
        if verdict != case["expect"]:
            problems.append(f"expected {case['expect']}, got {verdict}")
        for code in case.get("codes", []):
            if code not in codes:
                problems.append(f"missing code `{code}`")
        for code in case.get("warnings", []):
            if code not in warnings:
                problems.append(f"missing warning `{code}`")

        if problems:
            failed += 1
            print(f"  FAIL  {case['dir']}")
            for problem in problems:
                print(f"          {problem}")
            if codes or warnings:
                print(f"          reported: {', '.join(codes + warnings)}")
        else:
            failed += 0
            passed += 1
            reported = ", ".join(codes + warnings)
            print(f"  ok    {case['dir']}" + (f"  [{reported}]" if reported else ""))

    print(f"\ncheck-1 conformance: {passed} passed, {failed} failed")
    return 1 if failed else 0


# ─────────────────────────── check 2 — no unproven steps ────────────────────────────────────────
#
# The repository states the facts, the checker compares — the same shape as check 1, except that
# here the format already exists (JUnit XML), so nothing new is invented.
# See design/step-coverage.md.

PARAMETRISED = re.compile(r"[\[(].*$")   # checkout[blocked] · checkout(1) -> checkout


class TestCase:
    __slots__ = ("classname", "name", "status")

    def __init__(self, classname: str, name: str, status: str):
        self.classname, self.name, self.status = classname, name, status

    @property
    def full(self) -> str:
        return f"{self.classname}.{self.name}" if self.classname else self.name


def load_report(config: dict, base: str) -> tuple[list[TestCase], list[Finding]]:
    location = config.get("test_report")
    if not location:
        return [], [Finding(
            "report_missing",
            "no `test_report` in the config — check 2 cannot run and is NOT considered passed")]

    path = os.path.join(base, location)
    if not os.path.exists(path):
        return [], [Finding("report_missing", f"{location} does not exist")]

    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        return [], [Finding("report_malformed", f"{location}: {exc}")]

    cases: list[TestCase] = []
    for node in root.iter("testcase"):
        status = "passed"
        for child in node:
            tag = child.tag.lower()
            if tag in ("failure", "error"):
                status = "failed"
            elif tag == "skipped":
                status = "skipped"
        cases.append(TestCase(node.get("classname", ""), node.get("name", ""), status))

    if not cases:
        return cases, [Finding(
            "report_empty",
            f"{location}: no test cases — a failed run, not a suite without tests")]
    return cases, []


def index_report(cases: list[TestCase]) -> tuple[dict, dict]:
    """Two indexes: by `classname.name`, and by bare name (with parametrised cases folded in)."""
    by_full: dict[str, list[TestCase]] = {}
    by_name: dict[str, list[TestCase]] = {}
    for case in cases:
        by_full.setdefault(case.full, []).append(case)
        by_name.setdefault(case.name, []).append(case)
        base = PARAMETRISED.sub("", case.name)
        if base != case.name:
            by_name.setdefault(base, []).append(case)
            by_full.setdefault(f"{case.classname}.{base}" if case.classname else base,
                               []).append(case)
    return by_full, by_name


def find_cases(test_id: str, by_full: dict, by_name: dict) -> list[TestCase]:
    """Resolve a card's test id to report entries. Full-id matching only — never a substring."""
    if test_id in by_full:
        return by_full[test_id]
    if ":" in test_id:                                  # file-and-name shape
        file_part, name_part = test_id.rsplit(":", 1)
        candidates = by_name.get(name_part, [])
        narrowed = [c for c in candidates if file_part in (c.classname or "")]
        return narrowed or candidates
    if test_id in by_name:
        return by_name[test_id]
    if "." in test_id:                                  # runners disagree about `classname`
        return by_name.get(test_id.rsplit(".", 1)[1], [])
    return []


def check_coverage(config: dict, base: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    cases, report_findings = load_report(config, base)
    findings += report_findings
    have_report = bool(cases)
    by_full, by_name = index_report(cases)

    cards, _ = load_card_files(config, base)
    proven = unproven = 0

    for card_id, fm in cards:
        steps = [s.get("id") for s in (fm.get("steps") or [])]
        gaps = {g.get("step") for g in (fm.get("coverage_gaps") or [])}
        by_step: dict[str, list[str]] = {}

        for test in fm.get("tests") or []:
            refs = test.get("covers")
            refs = refs if isinstance(refs, list) else [refs]
            test_id = test.get("id", "")
            matched = find_cases(test_id, by_full, by_name) if have_report else []

            if have_report:
                if not matched:
                    findings.append(Finding(
                        "test_not_found",
                        f"{card_id}: `{test_id}` matches nothing in the report"))
                else:
                    # Rule 4: a parametrised family proves the step only if all of it passes.
                    failed = [c for c in matched if c.status == "failed"]
                    skipped = [c for c in matched if c.status == "skipped"]
                    if failed:
                        findings.append(Finding(
                            "test_failing",
                            f"{card_id}: `{test_id}` failed"
                            + (f" ({len(failed)} of {len(matched)} cases)" if len(matched) > 1 else "")))
                    elif skipped:
                        findings.append(Finding(
                            "test_skipped",
                            f"{card_id}: `{test_id}` was skipped — a name in the report is not proof"))

            passing = matched and all(c.status == "passed" for c in matched)
            for ref in refs:
                by_step.setdefault(ref, [])
                if passing or not have_report:
                    by_step[ref].append(test_id)

        for step in steps:
            if step in gaps:
                continue
            if by_step.get(step):
                proven += 1
                continue
            unproven += 1
            # A step whose only tests failed or vanished is already reported above; saying it
            # twice trains people to skim.
            if step not in by_step:
                findings.append(Finding(
                    "step_unproven",
                    f"{card_id}: step `{step}` has no test and no declared gap",
                    "error" if have_report else "warning"))

    return findings, {"report_cases": len(cases), "proven": proven, "unproven": unproven}


def report(title: str, findings: list[Finding]) -> int:
    errors = [f for f in findings if f.severity == "error"]
    for finding in findings:
        marker = "ERROR  " if finding.severity == "error" else "warning"
        print(f"  {marker}  {finding}")
    print(f"  → {title}: {len(errors)} error(s), {len(findings) - len(errors)} warning(s)\n")
    return len(errors)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="checks 1 and 2 — no wild endpoints, no unproven steps")
    parser.add_argument("config", nargs="?", help="path to usedesign.config.yaml")
    parser.add_argument("--conformance", action="store_true",
                        help="run the check-1 conformance corpus")
    args = parser.parse_args()

    if args.conformance:
        return run_conformance()
    if not args.config:
        parser.print_help()
        return 2

    config, base = load_config(args.config)

    route_findings, summary = check(config, base)
    print(f"inventory:  {summary['served']} route(s) served"
          + (f", produced by {summary['produced_by']}" if summary["produced_by"] else ""))
    print(f"cards:      {summary['declared']} REST route(s) declared")
    print(f"excluded:   {summary['excluded']} route(s)")
    for pattern, count in summary["hidden_per_rule"].items():
        print(f"              {pattern} → {count}")
    print()
    errors = report("check 1 (no wild endpoints)", route_findings)

    coverage_findings, coverage = check_coverage(config, base)
    print(f"report:     {coverage['report_cases']} test case(s)")
    print(f"steps:      {coverage['proven']} proven, {coverage['unproven']} not")
    print()
    errors += report("check 2 (no unproven steps)", coverage_findings)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
