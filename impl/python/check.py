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
from datetime import date
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
#
# `:name` is a parameter ONLY after a slash. Elsewhere it is a literal: the AIP-136 style writes
# an action as `POST /progress/{id}:finish`, and reading that suffix as a parameter collapses
# five distinct operations into one shape — after which the checker reports a clean run while
# four of them are declared by nobody.
PARAM = re.compile(r"\{[^}]*\}|(?<=/):[A-Za-z_][A-Za-z0-9_]*|<[^>]*>")


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
    dispatch_of: dict[tuple, str] = {}
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
            # The key stays the route shape — that is what the inventory can be compared against.
            # Dispatch tells cards apart from each other, not routes from each other.
            d = iface.get("dispatch") or {}
            key = normalise(method, route)
            declared.setdefault(key, []).append(card_id)
            stamp = f"{d['by']}={d['value']}" if d.get("by") and d.get("value") else ""
            dispatch_of[(key, card_id)] = stamp

    for key, owners in sorted(declared.items()):
        if len(owners) < 2:
            continue
        # Several operations may legitimately share a route, told apart by a request field — a
        # widespread REST idiom. Ambiguous only when two cards claim it the same way, or not at all.
        stamps = [dispatch_of.get((key, card_id), "") for card_id in owners]
        if len(set(stamps)) == len(owners) and "" not in stamps:
            continue
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
        runner = {1: check, 2: check_coverage, 3: check_maturity, 4: check_storage, 5: check_form}[case.get("check", 1)]
        findings, _ = runner(config, base)
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

    print(f"\nchecks conformance: {passed} passed, {failed} failed")
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


# ─────────────────────────── check 3 — no inflated maturity ─────────────────────────────────────
#
# Three claims of different natures wear one field. Only the first is verifiable against the
# repository, the second is derived from check 2, and the third can only be made to expire.
# See design/maturity-evidence.md.

LEVELS = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"]
LINE_SUFFIX = re.compile(r":\d+$")
DEFAULT_HORIZON_DAYS = 180


def evidence_paths(value) -> list[str]:
    """`implemented` is one path or several — one example joins two with ' + '."""
    values = value if isinstance(value, list) else [value]
    paths: list[str] = []
    for item in values:
        for part in str(item).split("+"):
            part = LINE_SUFFIX.sub("", part.strip())
            if part:
                paths.append(part)
    return paths


def check_maturity(config: dict, base: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    cases, _ = load_report(config, base)
    have_report = bool(cases)
    by_full, by_name = index_report(cases)

    code_root = config.get("code_root")
    root = os.path.join(base, code_root) if code_root else None
    # A misspelt `code_root` otherwise reports every evidence path as missing from the repository —
    # false, and one error per card. Say the true thing once instead.
    if root and not os.path.isdir(root):
        return ([Finding("code_root_missing",
                         f"`code_root` points at `{code_root}`, which does not exist — "
                         "check 3 cannot verify any path")],
                {"cards": 0, "paths_checked": 0, "code_root": code_root or "",
                 "horizon": config.get("evidence_horizon_days", DEFAULT_HORIZON_DAYS)})
    horizon = config.get("evidence_horizon_days", DEFAULT_HORIZON_DAYS)
    today = date.today()

    cards, card_findings = load_card_files(config, base)
    findings += card_findings
    checked_paths = 0

    for card_id, fm in cards:
        maturity = fm.get("maturity")
        if maturity not in LEVELS:
            continue
        level = LEVELS.index(maturity)
        evidence = fm.get("maturity_evidence") or {}

        # Tier 1 — the code the card points at exists.
        if level >= LEVELS.index("implemented") and evidence.get("implemented") and root:
            for path in evidence_paths(evidence["implemented"]):
                checked_paths += 1
                if not os.path.exists(os.path.join(root, path)):
                    findings.append(Finding(
                        "evidence_path_missing",
                        f"{card_id}: `{path}` is not in the repository"))

        # Tier 2 — the claim is derived from the report, not from prose.
        passing = []
        for test in fm.get("tests") or []:
            matched = find_cases(test.get("id", ""), by_full, by_name) if have_report else []
            if matched and all(c.status == "passed" for c in matched):
                passing.append(test.get("id"))

        if level >= LEVELS.index("tested") and not passing:
            findings.append(Finding(
                "maturity_without_passing_test",
                f"{card_id}: claims `{maturity}` with no test of its own passing in the report",
                "error" if have_report else "warning"))

        # Only below `implemented`. A passing test is *necessary* to claim `tested`, not
        # sufficient for it — one smoke test does not make an operation covered, and a checker
        # cannot judge which it is. Nagging every honest `implemented` card would retire this rule
        # within a week.
        if have_report and level < LEVELS.index("implemented") and passing:
            findings.append(Finding(
                "maturity_understated",
                f"{card_id}: claims `{maturity}` while {len(passing)} of its tests pass",
                "warning"))

        # Tier 3 — what cannot be verified must expire.
        if level >= LEVELS.index("in_production"):
            deployed = evidence.get("deployed")
            if isinstance(deployed, dict):
                try:
                    since = date.fromisoformat(str(deployed.get("since")))
                except ValueError:
                    findings.append(Finding(
                        "evidence_undated",
                        f"{card_id}: `deployed.since` is not a date"))
                    continue
                age = (today - since).days
                if age > horizon:
                    findings.append(Finding(
                        "evidence_stale",
                        f"{card_id}: `deployed` was last affirmed {age} days ago "
                        f"(horizon {horizon}) — nobody has looked since",
                        "warning"))
            elif deployed:
                findings.append(Finding(
                    "evidence_undated",
                    f"{card_id}: `deployed: {deployed}` carries no date, so it can never go stale",
                    "warning"))

    return findings, {
        "cards": len(cards),
        "paths_checked": checked_paths,
        "code_root": code_root or "",
        "horizon": horizon,
    }


# ─────────────────────────── check 4 — no imagined storage ──────────────────────────────────────
#
# The same shape as check 1, one layer down: the storage says what it is — which stores exist,
# what they are keyed by, which secondary indexes they carry — and the cards are compared with
# that. Nothing reads a repository class or a mapping attribute.
#
# It exists because `data.entities: [request]` was the whole of what a card said about storage: a
# logical noun, true by construction, falsifiable by nothing.
#
# What this check deliberately does NOT do: verify which ATTRIBUTES an operation writes. A
# schemaless store declares its keys and indexes and knows nothing about the rest, so a
# `fields_touched` check would be a promise the storage cannot keep.
def check_storage(config: dict, base: str) -> tuple[list[Finding], dict]:
    empty = {"stores": 0, "claims": 0, "touched": 0, "produced_by": ""}
    location = config.get("storage_inventory")
    if not location:
        return ([Finding("storage_inventory_missing",
                         "no `storage_inventory` in the config — check 4 cannot run and is NOT "
                         "considered passed")], empty)

    path = os.path.join(base, location)
    if not os.path.exists(path):
        return ([Finding("storage_inventory_missing", f"{location} does not exist")], empty)

    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    findings: list[Finding] = []
    if data.get("usedesign_storage_inventory") != 1:
        findings.append(Finding("storage_inventory_malformed",
                                f"{location}: missing `usedesign_storage_inventory: 1`"))
    if not data.get("produced_by"):
        findings.append(Finding("storage_inventory_malformed", f"{location}: missing `produced_by`"))

    stores = data.get("stores") or []
    if not stores:
        findings.append(Finding("storage_inventory_empty",
                                f"{location}: no stores — almost always a failed dump rather than "
                                "a system without storage"))

    cards, card_findings = load_card_files(config, base)
    findings += card_findings

    touched: set[str] = set()
    claims = 0

    for card_id, fm in cards:
        for claim in (fm.get("data") or {}).get("storage") or []:
            claims += 1
            pattern = claim.get("store") or ""
            matched = [s for s in stores if fnmatch.fnmatch(str(s.get("name")), pattern)]

            if not matched:
                findings.append(Finding(
                    "unknown_store",
                    f"{card_id}: claims store `{pattern}`, which the storage does not have"))
                continue
            for store in matched:
                touched.add(str(store.get("name")))

            claimed_keys = claim.get("keyed_by") or []
            if claimed_keys:
                for store in matched:
                    actual = store.get("keyed_by") or []
                    if list(claimed_keys) != list(actual):
                        findings.append(Finding(
                            "store_key_mismatch",
                            f"{card_id}: claims `{pattern}` is keyed by [{', '.join(claimed_keys)}], "
                            f"but `{store.get('name')}` is keyed by [{', '.join(actual)}]"))

            index = claim.get("via_index")
            if index:
                for store in matched:
                    names = [str(i.get("name")) for i in (store.get("indexes") or [])]
                    if index not in names:
                        findings.append(Finding(
                            "unknown_index",
                            f"{card_id}: depends on index `{index}` of `{store.get('name')}`, "
                            f"which has {', '.join(names) if names else 'no indexes'}"))

    # The mirror of a wild endpoint, and the question nobody asks out loud: what do we keep that no
    # description accounts for? A warning — storage outlives the operations that filled it.
    for store in stores:
        if str(store.get("name")) not in touched:
            findings.append(Finding(
                "undescribed_store",
                f"{store.get('name')} exists but no card says anything about it", "warning"))

    return findings, {"stores": len(stores), "claims": claims, "touched": len(touched),
                      "produced_by": data.get("produced_by", "")}


# ─────────────────────────── check 5 — the form matches its contract ────────────────────────────
#
# The one check whose reference is authored rather than measured: the contract says what the owner
# decided the screen must show; the inventory says what the rendered screen carries, state by
# state. Contract lines the code has not caught up with are the product's TODO list, printed by
# every build. See the TypeScript twin for the full commentary.
def check_form(config: dict, base: str) -> tuple[list[Finding], dict]:
    empty = {"contracts": 0, "screens": 0, "produced_by": ""}
    patterns = config.get("forms") or []
    location = config.get("form_inventory")
    if not patterns:
        return ([Finding("form_contracts_missing",
                         "no `forms` patterns in the config — check 5 cannot run and is NOT "
                         "considered passed")], empty)
    if not location:
        return ([Finding("form_inventory_missing",
                         "no `form_inventory` in the config — check 5 cannot run and is NOT "
                         "considered passed")], empty)
    inventory_path = os.path.join(base, location)
    if not os.path.exists(inventory_path):
        return ([Finding("form_inventory_missing", f"{location} does not exist")], empty)

    with open(inventory_path, encoding="utf-8") as handle:
        data = json.load(handle)

    findings: list[Finding] = []
    if data.get("usedesign_form_inventory") != 1:
        findings.append(Finding("form_inventory_malformed",
                                f"{location}: missing `usedesign_form_inventory: 1`"))
    if not data.get("produced_by"):
        findings.append(Finding("form_inventory_malformed", f"{location}: missing `produced_by`"))

    by_screen: dict[str, dict[str, dict]] = {}
    for form in data.get("forms") or []:
        states = {}
        for s in form.get("states") or []:
            # `within` is optional: an inventory that predates container recording gets
            # membership NOT JUDGED, never failed.
            raw_within = s.get("within")
            states[str(s.get("state"))] = {
                "fields": {str(x) for x in s.get("fields") or []},
                "controls": {str(x) for x in s.get("controls") or []},
                "within": ({str(k): {str(c) for c in v or []} for k, v in raw_within.items()}
                           if isinstance(raw_within, dict) else None),
            }
        by_screen[str(form.get("screen"))] = states

    cards, _ = load_card_files(config, base)
    card_by_id = dict(cards)

    contracts: list[tuple[str, dict]] = []
    files: list[str] = []
    for pattern in patterns:
        files += glob.glob(os.path.join(base, pattern), recursive=True)
    for path in sorted(set(files)):
        fm = front_matter(path)
        if fm and fm.get("usedesign_form") == 1:
            contracts.append((str(fm.get("id", path)), fm))
    if not contracts:
        findings.append(Finding("form_contracts_missing", "the `forms` patterns matched no contract"))

    claimed: dict[str, dict[str, set]] = {}

    for contract_id, fm in contracts:
        screen = str(fm.get("screen") or "")
        states = by_screen.get(screen)
        if states is None:
            findings.append(Finding("form_screen_missing",
                                    f"{contract_id}: screen `{screen}` is absent from the "
                                    "inventory — nothing rendered it"))
            continue
        every_state = list(states.keys())
        mine = claimed.setdefault(screen, {"fields": set(), "controls": set()})

        for entry in fm.get("presents") or []:
            field = str(entry.get("field") or "")
            mine["fields"].add(field)
            for state in entry.get("when") or every_state:
                rendered = states.get(state)
                if rendered is None:
                    findings.append(Finding("form_state_missing",
                                            f"{contract_id}: `{field}` is required in state "
                                            f"`{state}`, which the inventory never rendered"))
                elif field not in rendered["fields"]:
                    findings.append(Finding("element_missing",
                                            f"{contract_id}: `{field}` must be shown in state "
                                            f"`{state}` and is not"))

        for control in fm.get("controls") or []:
            name = str(control.get("control") or "")
            mine["controls"].add(name)
            shown_when = control.get("shown_when")

            if shown_when:
                for state in shown_when:
                    rendered = states.get(state)
                    if rendered is None:
                        findings.append(Finding("form_state_missing",
                                                f"{contract_id}: control `{name}` is required in "
                                                f"state `{state}`, which the inventory never rendered"))
                    elif name not in rendered["controls"]:
                        findings.append(Finding("control_missing",
                                                f"{contract_id}: control `{name}` must be "
                                                f"available in state `{state}` and is not"))
                for state, rendered in states.items():
                    if state not in shown_when and name in rendered["controls"]:
                        findings.append(Finding("control_out_of_state",
                                                f"{contract_id}: control `{name}` appears in "
                                                f"state `{state}`, outside its declared `shown_when`"))
            elif not any(name in rendered["controls"] for rendered in states.values()):
                findings.append(Finding("control_missing",
                                        f"{contract_id}: control `{name}` appears in no state at all"))

            calls = control.get("calls")
            if isinstance(calls, str) and calls:
                card = card_by_id.get(calls)
                if card is None:
                    findings.append(Finding("form_calls_undescribed",
                                            f"{contract_id}: control `{name}` calls `{calls}`, "
                                            "which no card describes", "warning"))
                elif shown_when:
                    transition = card.get("data_transition")
                    origin = str(transition.get("from") or "") if isinstance(transition, dict) else ""
                    if origin and origin not in ("none", "any"):
                        mismatch = [s for s in shown_when if s != origin]
                        if mismatch or origin not in shown_when:
                            findings.append(Finding(
                                "shown_when_conflicts_transition",
                                f"{contract_id}: control `{name}` is shown in "
                                f"[{', '.join(shown_when)}] but `{calls}` departs from `{origin}`"))

        for entry in fm.get("removed") or []:
            name = str(entry.get("control") or "")
            mine["controls"].add(name)
            for state, rendered in states.items():
                if name in rendered["controls"]:
                    findings.append(Finding("removed_control_present",
                                            f"{contract_id}: control `{name}` was removed by the "
                                            f"owner's decision yet appears in state `{state}`"))

        # A group's anchor is accounted for BY the group line: the owner named the container
        # when grouping by it. Warning about it as undescribed would ask the owner to decide
        # what they already decided — measured 19.08: three of fourteen warnings were this.
        for group in fm.get("groups") or []:
            if group.get("group"):
                mine["fields"].add(str(group.get("group")))

        # ── group membership ─────────────────────────────────────────────────
        # The contract seats elements in groups; the inventory's `within` records which
        # containers each anchor ACTUALLY rendered inside. Judged only where the member renders
        # and the inventory carries the measurement. The first inventory with containers refuted
        # its own contract: `add-set` was contracted into the footer and measured living only in
        # the set table — the checker's first catch was its author.
        for group in fm.get("groups") or []:
            gname = str(group.get("group") or "")
            if not gname:
                continue
            anchor_seen = any(
                gname in rendered["fields"]
                or (rendered["within"] is not None
                    and any(gname in chain for chain in rendered["within"].values()))
                for rendered in states.values())
            if not anchor_seen:
                findings.append(Finding("group_missing",
                                        f"{contract_id}: group `{gname}` is contracted but its "
                                        "anchor never renders"))
            for member_raw in group.get("contains") or []:
                member = str(member_raw)
                for state, rendered in states.items():
                    if rendered["within"] is None:
                        continue
                    if member not in rendered["fields"] and member not in rendered["controls"]:
                        continue
                    chain = rendered["within"].get(member) or set()
                    if gname not in chain:
                        inside = ", ".join(sorted(chain))
                        findings.append(Finding("member_out_of_group",
                                                f"{contract_id}: `{member}` is contracted into "
                                                f"`{gname}` but in state `{state}` renders "
                                                f"inside [{inside}]"))
                        break

    for screen, states in by_screen.items():
        mine = claimed.get(screen)
        if mine is None:
            continue
        seen: set[str] = set()
        for rendered in states.values():
            for field in rendered["fields"]:
                if field not in mine["fields"] and f"f:{field}" not in seen:
                    seen.add(f"f:{field}")
                    findings.append(Finding("undescribed_element",
                                            f"{screen}: `{field}` is rendered but no contract "
                                            "line accounts for it", "warning"))
            for control in rendered["controls"]:
                if control not in mine["controls"] and f"c:{control}" not in seen:
                    seen.add(f"c:{control}")
                    findings.append(Finding("undescribed_element",
                                            f"{screen}: control `{control}` is rendered but no "
                                            "contract line accounts for it", "warning"))

    return findings, {"contracts": len(contracts), "screens": len(by_screen),
                      "produced_by": data.get("produced_by", "")}


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
                        help="run the conformance corpus for checks 1 and 2")
    args = parser.parse_args()

    if args.conformance:
        return run_conformance()
    if not args.config:
        parser.print_help()
        return 2

    config, base = load_config(args.config)

    # `checks: [5]` scopes which checks apply to THIS repository — same rule as the TypeScript twin.
    scope = config.get("checks")
    def in_scope(n: int) -> bool:
        return not scope or n in scope
    errors = 0

    if in_scope(1):
        route_findings, summary = check(config, base)
        print(f"inventory:  {summary['served']} route(s) served"
              + (f", produced by {summary['produced_by']}" if summary["produced_by"] else ""))
        print(f"cards:      {summary['declared']} REST route(s) declared")
        print(f"excluded:   {summary['excluded']} route(s)")
        for pattern, count in summary["hidden_per_rule"].items():
            print(f"              {pattern} → {count}")
        print()
        errors += report("check 1 (no wild endpoints)", route_findings)

    if in_scope(2):
        coverage_findings, coverage = check_coverage(config, base)
        print(f"report:     {coverage['report_cases']} test case(s)")
        print(f"steps:      {coverage['proven']} proven, {coverage['unproven']} not")
        print()
        errors += report("check 2 (no unproven steps)", coverage_findings)

    if in_scope(3):
        maturity_findings, maturity = check_maturity(config, base)
        print(f"cards:      {maturity['cards']} card(s), {maturity['paths_checked']} evidence path(s) checked"
              + ("" if maturity["code_root"] else " — no `code_root`, path check NOT RUN"))
        print(f"horizon:    {maturity['horizon']} days")
        print()
        errors += report("check 3 (no inflated maturity)", maturity_findings)

    if in_scope(4):
        storage_findings, storage = check_storage(config, base)
        print(f"storage:    {storage['stores']} store(s)"
              + (f", produced by {storage['produced_by']}" if storage["produced_by"] else "")
              + f"; {storage['claims']} claim(s) in cards touching {storage['touched']}")
        errors += report("check 4 (no imagined storage)", storage_findings)

    # Check 5 is opt-in: naming it in `checks:` or declaring `forms:` opts in.
    if (scope and 5 in scope) or (not scope and config.get("forms")):
        form_findings, form = check_form(config, base)
        print(f"forms:      {form['contracts']} contract(s) against {form['screens']} rendered screen(s)"
              + (f", produced by {form['produced_by']}" if form["produced_by"] else ""))
        errors += report("check 5 (the form matches its contract)", form_findings)

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
