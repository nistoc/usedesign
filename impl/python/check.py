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


def load_cards(config: dict, base: str) -> tuple[dict, list[Finding]]:
    """Return {(method, shape): [card ids]} for every REST interface the cards declare."""
    declared: dict[tuple[str, str], list[str]] = {}
    findings: list[Finding] = []
    files: list[str] = []
    for pattern in config.get("cards") or []:
        files += glob.glob(os.path.join(base, pattern), recursive=True)

    if not files:
        findings.append(Finding("no_cards_found", "the `cards` patterns matched nothing"))

    for path in sorted(set(files)):
        fm = front_matter(path)
        if not fm:
            continue
        card_id = fm.get("id", os.path.basename(path))
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


def main() -> int:
    parser = argparse.ArgumentParser(description="check 1 — no wild endpoints")
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
    findings, summary = check(config, base)

    print(f"inventory:  {summary['served']} route(s) served"
          + (f", produced by {summary['produced_by']}" if summary["produced_by"] else ""))
    print(f"cards:      {summary['declared']} REST route(s) declared")
    print(f"excluded:   {summary['excluded']} route(s)")
    for pattern, count in summary["hidden_per_rule"].items():
        print(f"              {pattern} → {count}")
    print()

    errors = [f for f in findings if f.severity == "error"]
    for finding in findings:
        marker = "ERROR  " if finding.severity == "error" else "warning"
        print(f"  {marker}  {finding}")

    warnings = len(findings) - len(errors)
    print(f"\ncheck 1: {len(errors)} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
