#!/usr/bin/env python3
"""Checks 1–5 (SPEC §7) — the Python implementation of `usedesign check`.

Each check compares what the checked repository states about itself — a route inventory, a test
report, the paths of its code, a storage inventory, a form inventory — against what the cards and
form contracts declare. See design/route-conformance.md for why the comparison works this way and
why usedesign does not extract routes itself.

This is a prototype, not a package: it prints what the TypeScript reference prints, line for line.

Usage:
    python check.py <path to usedesign.config.yaml>
    python check.py --conformance          run the checks conformance corpus
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from typing import Any
from xml.parsers import expat

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

import json_schema
from validate import (CannotRead, _list, _map, _segment, _text, cause_of, expand_globs, front_matter,
                      is_contract, utf16_order, why_unreadable)

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


# Every key the config may carry. Enforced at load, not merely published in the schema:
# measured on issue #4 — `cheks:` was accepted silently, the scoping vanished, and the check it
# was meant to skip failed pointing at a completely different cause. Named in the TypeScript
# twin's order (1.5.1): sorted here, the refusal listed them otherwise.
CONFIG_KEYS = ["usedesign_config", "checks", "cards", "inventory", "test_report", "code_root",
               "evidence_horizon_days", "exclude", "forms", "form_inventory", "storage_inventory",
               "uncontracted_screens"]


# ── reading a field in its type (1.5.1) ──────────────────────────────────────
#
# As `validate` reads since 1.4.3: a list as a list, a map as a map, a name as a string; any other
# value is absent to the rules. Before, a number where a list belongs stopped this prototype with a
# traceback in some fifty places, and `true` was printed `True` where the twin printed `true`.

def _maps(value) -> list:
    """The maps of a list of maps; an item of another type is absent."""
    return [item for item in _list(value) if isinstance(item, dict)]


def _texts(value) -> list:
    """The strings of a list of strings; an item of another type is absent."""
    return [item for item in _list(value) if isinstance(item, str)]


def _is_integer(value) -> bool:
    """An integer as Number.isInteger has it: `2.0` is one, `true` is not."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and float(value).is_integer())


def _integer(value):
    """An integer value as JavaScript holds it: `2.0` is 2."""
    return int(value) if isinstance(value, float) and abs(value) <= 2 ** 53 else value


def js_entries(data: dict) -> list:
    """A map's entries in the order Object.entries gives them, each name as String() writes it:
    names that are array indices first, ascending, then the rest as written (1.5.1). Interfaces
    named `b`, `2`, `a`, `10` were reported here in that order, and as 2, 10, b, a by the twin."""
    named = [(json_schema.js_string(key), value) for key, value in data.items()]
    index = [pair for pair in named if json_schema._INDEX.fullmatch(pair[0]) and int(pair[0]) < 2 ** 32 - 1]
    taken = {id(pair) for pair in index}
    return sorted(index, key=lambda pair: int(pair[0])) + [pair for pair in named if id(pair) not in taken]


def glob_matches(name: str, pattern: str) -> bool:
    """`name` against `pattern` as one segment of a `cards:` glob matches a file name (1.5.1).

    `*` and `?` do not cross a separator, `?` is one character, `[` and `]` are plain, letter case
    counts. An exclusion and a store name are matched so; fnmatch made `*` cross `/`, `[a]` a set,
    and on Windows let case go. See the TypeScript twin."""
    return _segment(pattern).fullmatch(name) is not None


# The type each config key is read in (1.5.1); `null` is an absent key. See the TypeScript twin.
CONFIG_TYPES = [
    ("checks", "a list of check numbers, 1 to 5",
     lambda v: isinstance(v, list) and len(v) > 0 and all(_is_integer(n) and 1 <= n <= 5 for n in v)),
    ("cards", "a list of strings", lambda v: isinstance(v, list) and all(isinstance(s, str) for s in v)),
    ("forms", "a list of strings", lambda v: isinstance(v, list) and all(isinstance(s, str) for s in v)),
    ("inventory", "a string", lambda v: isinstance(v, str)),
    ("test_report", "a string", lambda v: isinstance(v, str)),
    ("code_root", "a string", lambda v: isinstance(v, str)),
    ("form_inventory", "a string", lambda v: isinstance(v, str)),
    ("storage_inventory", "a string", lambda v: isinstance(v, str)),
    ("uncontracted_screens", "a string", lambda v: isinstance(v, str)),
    ("evidence_horizon_days", "an integer", _is_integer),
    ("exclude", "a list of rules, each a map with `path` a string and `method`, if written, a string",
     lambda v: isinstance(v, list) and all(
         isinstance(rule, dict) and isinstance(rule.get("path"), str)
         and (rule.get("method") is None or isinstance(rule.get("method"), str)) for rule in v)),
]


def family_regex(pattern: str) -> re.Pattern:
    """A family pattern (issue #10): `*` matches any run of characters, the rest is literal."""
    return re.compile("^" + ".*".join(re.escape(part) for part in pattern.split("*")) + "$")


def _field_out_of_state(contract_id: str, name: str, when, states: dict, present, findings: list) -> None:
    """An element shown in a state outside its `when` (round 26 ⑫).

    Controls had this check from the start (`control_out_of_state`); elements checked only the
    other direction, so a refusal caption leaking into every state passed. A warning, not an
    error: it is a new check over a field that already exists, and 1.x does not turn a clean
    contract red (SPEC §8)."""
    if not isinstance(when, list):
        return
    for state, rendered in states.items():
        if state not in when and present(rendered):
            findings.append(Finding("field_out_of_state",
                                    f"{contract_id}: `{name}` appears in state `{state}`, "
                                    "outside its declared `when`", "warning"))


def load_config(path: str) -> tuple[dict, str]:
    """The config, read as the TypeScript twin reads it (1.5.1): YAML 1.2, a key written twice
    refused, and a refusal stops the run with exit 2. PyYAML read `030` as 24 and `1e2` as text,
    took the last of two keys, and the refusals ended with exit 1."""
    why = why_unreadable(path)
    if why:
        raise CannotRead(f"`{path}` cannot be read — {why}")
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as handle:
            config = json_schema.load(handle.read())
    except yaml.YAMLError as e:
        raise CannotRead(f"{path}: config is not valid YAML — {str(e).splitlines()[0]}") from None
    except RecursionError:
        # Nesting deeper than the reader's stack: the twin stops on the same file with exit 2 in
        # these words. Here it was a traceback and exit 1 (1.5.1).
        raise CannotRead(f"{path}: config is not valid YAML — Maximum call stack size exceeded") from None
    except OSError as e:
        raise CannotRead(f"`{path}` cannot be read — {cause_of(e)}") from None
    if not isinstance(config, dict) or not (_is_integer(config.get("usedesign_config"))
                                            and config.get("usedesign_config") == 1):
        raise CannotRead(f"{path}: not a usedesign config (expected `usedesign_config: 1`)")
    for key in json_schema._keys(config):
        if key not in CONFIG_KEYS:
            raise CannotRead(f"{path}: `{key}` is not a config key — a typo here silently changes "
                             f"what is checked. Known keys: {', '.join(CONFIG_KEYS)}")
    for key, need, holds in CONFIG_TYPES:
        if config.get(key) is not None and not holds(config[key]):
            raise CannotRead(f"{path}: `{key}` in the config must be {need} — a value of another "
                             "type silently changes what is checked")
    return config, os.path.dirname(os.path.abspath(path))


def load_card_files(config: dict, base: str) -> tuple[list[tuple[str, dict]], list[Finding]]:
    """Return [(card id, front matter)] for every card the config points at."""
    findings: list[Finding] = []
    files = expand_globs(base, config.get("cards") or [])

    if not files:
        findings.append(Finding("no_cards_found", "the `cards` patterns matched nothing"))

    cards: list[tuple[str, dict]] = []
    read: list[tuple[str, dict]] = []
    for path in files:
        fm = read_document(path)
        if fm is None or not isinstance(fm, (dict, list)):
            continue
        # Front matter that is a list is a card with no fields (1.5.1), as the twin reads it.
        fm = _map(fm)
        card_id = _text(fm.get("id"))
        cards.append((card_id if card_id is not None else os.path.basename(path), fm))
        read.append((path, fm))
    refuse_twins(read)
    return cards, findings


def refuse_twins(documents: list) -> None:
    """One id, one document (1.5.1), as `validate` has it since 1.4.3: kept by id, the second card
    of an id replaced the first, and `check` judged one of the two without a word. The run stops
    and names both. Cards and contracts keep two spaces of ids, as in `validate`: a card and a
    contract may share one. See the TypeScript twin."""
    first: dict[tuple, str] = {}
    for path, fm in documents:
        doc_id = fm.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            continue
        key = (is_contract(fm), doc_id)
        if key in first:
            raise CannotRead(f"`{first[key]}` and `{path}` carry the same id `{doc_id}` — an id "
                             "names one document, and the others point at it by that id")
        first[key] = path


def read_document(path: str):
    """The front matter of a document a config's patterns matched, as the TypeScript twin reads it.

    A file nobody can open — a link that leads nowhere, no read permission — and front matter that
    is not valid YAML stop the run with exit 2 and the file's name: no check can pass over a card
    it did not read. Before, each ended in a traceback (1.4.2).
    """
    why = why_unreadable(path)
    if why:
        raise CannotRead(f"`{path}` cannot be read — {why}")
    try:
        return front_matter(path)
    except yaml.YAMLError as e:
        raise CannotRead(f"`{path}` front matter is not valid YAML — {str(e).splitlines()[0]}") from None
    except OSError as e:
        raise CannotRead(f"`{path}` cannot be read — {cause_of(e)}") from None


def load_cards(config: dict, base: str) -> tuple[dict, dict, list[Finding]]:
    """Return declared routes, each card's maturity, and findings."""
    declared: dict[tuple[str, str], list[str]] = {}
    dispatch_of: dict[tuple, str] = {}
    maturity_by_id: dict[str, str] = {}
    cards, findings = load_card_files(config, base)

    for card_id, fm in cards:
        maturity_by_id[card_id] = _text(fm.get("maturity")) or ""
        for name, iface in js_entries(_map(fm.get("interfaces"))):
            if not isinstance(iface, dict) or iface.get("transport") != "http_rest":
                continue
            method, route = _text(iface.get("method")), _text(iface.get("path"))
            if not method or not route:
                findings.append(Finding(
                    "incomplete_rest_interface",
                    f"{card_id}: interface `{name}` declares http_rest without method or path"))
                continue
            # The key stays the route shape — that is what the inventory can be compared against.
            # Dispatch tells cards apart from each other, not routes from each other.
            d = _map(iface.get("dispatch"))
            by, value = _text(d.get("by")), _text(d.get("value"))
            key = normalise(method, route)
            declared.setdefault(key, []).append(card_id)
            dispatch_of[(key, card_id)] = f"{by}={value}" if by and value else ""

    for key, owners in by_key(declared):
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
    return declared, maturity_by_id, findings


def by_key(declared: dict) -> list:
    """Declared routes in the order of their `METHOD shape`, as JavaScript orders text (1.5.1)."""
    return sorted(declared.items(), key=lambda item: utf16_order(f"{item[0][0]} {item[0][1]}"))


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
    """Return the exclusion rule that covers this route, or None — by the glob of a `cards:`
    segment (1.5.1)."""
    for rule in config.get("exclude") or []:
        if rule.get("method") and rule["method"].upper() != method:
            continue
        if glob_matches(shape, rule.get("path") or ""):
            return rule
    return None


def check(config: dict, base: str) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    declared, maturity_by_id, card_findings = load_cards(config, base)
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

    designed_ahead = 0
    for (method, shape), owners in by_key(declared):
        if routes and (method, shape) not in served and not excluded_by(config, method, shape):
            # Two opposite situations used to share one diagnostic (issue #3): a route that is
            # GONE is an error; a route DESIGNED AND NOT BUILT YET is what `conceived` and
            # `designed` exist to describe — contract-first is the format's own flow.
            ahead = all(maturity_by_id.get(o_, "") in ("conceived", "designed") for o_ in owners)
            if ahead:
                designed_ahead += 1
                findings.append(Finding(
                    "route_not_yet_served",
                    f"{method} {shape} is declared by {', '.join(owners)} — designed ahead of "
                    "the code, expected to be absent", "warning"))
            else:
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
        "designed_ahead": designed_ahead,
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
        # Round 29, as the card corpus did in round 28: a check that must stay quiet is pinned too.
        for code in case.get("absent_warnings", []):
            if code in warnings:
                problems.append(f"unexpected warning `{code}`")

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


class _Doctype(Exception):
    pass


def read_report(data: bytes) -> list[TestCase] | str:
    """The test cases of a report, as the reference reads them: a `testcase` element in no namespace,
    at any depth, in document order; its `classname` and `name`; and its status from its own
    children — `failure` or `error` fails it, `skipped` skips it, in any letter case, and the last of
    them decides. A DOCTYPE is refused, as the reference refuses it (1.5.2): JUnit reports carry
    none, and the ElementTree reader of 1.5.1 expanded its entities. The message no longer names
    expat's reason and position, which the reference's parser words differently."""
    parser = expat.ParserCreate(namespace_separator=" ")
    cases: list[TestCase] = []
    open_: list[TestCase | None] = []

    def start(tag, attributes):
        parent = open_[-1] if open_ else None
        if parent is not None:
            local = tag.lower()
            if local in ("failure", "error"):
                parent.status = "failed"
            elif local == "skipped":
                parent.status = "skipped"
        own = None
        if tag == "testcase":
            own = TestCase(attributes.get("classname", ""), attributes.get("name", ""), "passed")
            cases.append(own)
        open_.append(own)

    def doctype(*_):
        raise _Doctype

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda tag: open_.pop()
    parser.StartDoctypeDeclHandler = doctype
    try:
        parser.Parse(data, True)
    except _Doctype:
        return "doctype"
    except expat.ExpatError:
        return "malformed"
    return cases


def load_report(config: dict, base: str) -> tuple[list[TestCase], list[Finding]]:
    location = config.get("test_report")
    if not location:
        return [], [Finding(
            "report_missing",
            "no `test_report` in the config — check 2 cannot run and is NOT considered passed")]

    path = os.path.join(base, location)
    if not os.path.exists(path):
        return [], [Finding("report_missing", f"{location} does not exist")]
    # A directory or a file without read permission stopped this run with a traceback (1.5.1).
    why = why_unreadable(path)
    if why:
        return [], [Finding("report_missing", f"{location} cannot be read: {why}")]

    with open(path, "rb") as handle:
        cases = read_report(handle.read())
    if cases == "doctype":
        return [], [Finding("report_malformed", f"{location}: a DOCTYPE — a JUnit report has none, and check 2 reads none")]
    if cases == "malformed":
        return [], [Finding(
            "report_malformed",
            f"{location}: not well-formed XML — a run that stopped while writing its report leaves such a file")]

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
    # Exact matches first, in BOTH indexes. The "file:name" shape is a heuristic, and a
    # heuristic consulted before the exact match ate every name containing a colon (issue #9):
    # the id was split at its own colon, looked up by its tail, and reported as unproven.
    if test_id in by_full:
        return by_full[test_id]
    if test_id in by_name:
        return by_name[test_id]
    if ":" in test_id:                                  # file-and-name shape
        # Every colon is a candidate split, left to right, first hit wins: the name part may
        # itself carry colons.
        at = test_id.find(":")
        while at != -1:
            candidates = by_name.get(test_id[at + 1:], [])
            if candidates:
                file_part = test_id[:at]
                narrowed = [c for c in candidates if file_part in (c.classname or "")]
                return narrowed or candidates
            at = test_id.find(":", at + 1)
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
    proven = unproven = inherited = 0
    gap_kinds = {"unwritten": 0, "harness": 0, "unreachable": 0}

    # Pass 1 — every card's OWN proofs. A variant (SPEC 5.2e) reads the original's own proofs,
    # never what the original itself inherited, so credit cannot chain.
    own_proof: dict[str, dict[str, list[str]]] = {}
    for card_id, fm in cards:
        by_step: dict[str, list[str]] = {}
        own_proof[card_id] = by_step

        for test in _maps(fm.get("tests")):
            refs = covers_of(test)
            test_id = _text(test.get("id")) or ""
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

    # Pass 2 — verdicts, with a variant's inherited steps credited from the original.
    by_id = dict(cards)
    for card_id, fm in cards:
        steps = step_ids_of(fm)
        gaps = gap_steps_of(fm)
        by_step = own_proof[card_id]
        credited, explained = _inheritance(card_id, fm, steps, by_step, by_id, own_proof,
                                           have_report, findings)
        # Round 26 ⑬: a gap says why the proof is missing — counted apart, so "not written yet"
        # is never read as "cannot be written".
        for entry in _maps(fm.get("coverage_gaps")):
            kind = _text(entry.get("kind")) or "unwritten"
            if kind in gap_kinds:
                gap_kinds[kind] += 1

        for step in steps:
            if step in gaps:
                continue
            if by_step.get(step):
                proven += 1
                continue
            if step in credited:
                proven += 1
                inherited += 1
                continue
            unproven += 1
            # A step whose only tests failed or vanished is already reported above, and so is an
            # inherited step a variant finding already explains; saying it twice trains people
            # to skim.
            if step not in by_step and step not in explained:
                findings.append(Finding(
                    "step_unproven",
                    f"{card_id}: step `{step}` has no test and no declared gap",
                    "error" if have_report else "warning"))

    return findings, {"report_cases": len(cases), "proven": proven, "unproven": unproven,
                      "inherited": inherited, "gaps": sum(gap_kinds.values()),
                      "gaps_harness": gap_kinds["harness"], "gaps_unreachable": gap_kinds["unreachable"]}


def covers_of(test: dict) -> list:
    """The steps a test covers: one id or a list of them (1.5.1: an id of another type is absent)."""
    covers = test.get("covers")
    return [covers] if isinstance(covers, str) else _texts(covers)


def step_ids_of(fm: dict) -> list:
    """A card's step ids, in order; a step that is not a map, or an id that is not a string, is absent."""
    return _texts([step.get("id") for step in _maps(fm.get("steps"))])


def gap_steps_of(fm: dict) -> set:
    """The steps a card declares a gap for."""
    return set(_texts([gap.get("step") for gap in _maps(fm.get("coverage_gaps"))]))


def _inheritance(card_id: str, fm: dict, steps: list, by_step: dict, by_id: dict,
                 own_proof: dict, have_report: bool, findings: list) -> tuple[set, set]:
    """Which inherited steps of a variant (SPEC 5.2e) the original's own tests prove.

    `explained` holds the steps whose missing credit a variant finding has already reported, so
    check 2 does not repeat it step by step."""
    credited: set[str] = set()
    explained: set[str] = set()
    variant = fm.get("variant_of")
    if not isinstance(variant, dict):
        return credited, explained

    inherits = _texts(variant.get("inherits"))
    original_id = _text(variant.get("card")) or ""
    original = by_id.get(original_id)
    if original is None:
        findings.append(Finding(
            "variant_of_unknown",
            f"{card_id}: `variant_of` names `{original_id}`, which no card in the set declares"))
        explained.update(inherits)
        return credited, explained

    shared = LINE_SUFFIX.sub("", (_text(variant.get("shared")) or "").strip())
    code_shared = shared in evidence_paths(_map(original.get("maturity_evidence")).get("implemented"))
    if not code_shared:
        findings.append(Finding(
            "variant_code_not_shared",
            f"{card_id}: `{shared}` is not in the `implemented` evidence of `{original_id}` — "
            "nothing shows the two run the same code"))

    # Wiring: a passing test of the variant's own that covers its last step (SPEC 5.2e, rule 4).
    last = steps[-1] if steps else None
    wired = last is not None and bool(by_step.get(last))
    if not wired:
        findings.append(Finding(
            "variant_unwired",
            f"{card_id}: no passing test of its own covers its last step "
            f"`{last if last is not None else '(none)'}` — "
            f"{len(inherits)} inherited step(s) get no credit",
            "error" if have_report else "warning"))

    original_steps = set(step_ids_of(original))
    original_gaps = gap_steps_of(original)
    original_proof = own_proof.get(original_id) or {}
    for step in inherits:
        if step not in original_steps:
            findings.append(Finding(
                "variant_step_unknown",
                f"{card_id}: inherits `{step}`, which `{original_id}` has no step called"))
            explained.add(step)
            continue
        if not code_shared or not wired:
            explained.add(step)
            continue
        # A gap the original declares passes nothing on; the variant then answers for the step.
        if step not in original_gaps and original_proof.get(step):
            credited.add(step)
    return credited, explained


# ─────────────────────────── check 3 — no inflated maturity ─────────────────────────────────────
#
# Three claims of different natures wear one field. Only the first is verifiable against the
# repository, the second is derived from check 2, and the third can only be made to expire.
# See design/maturity-evidence.md.

LEVELS = ["conceived", "designed", "implemented", "tested", "in_production", "deprecated"]
LINE_SUFFIX = re.compile(r":\d+$")
DEFAULT_HORIZON_DAYS = 180


def evidence_paths(value) -> list[str]:
    """`implemented` is one path or several — one example joins two with ' + '. A value that is
    not a string is absent (1.5.1)."""
    values = [value] if isinstance(value, str) else _texts(value)
    paths: list[str] = []
    for item in values:
        for part in item.split("+"):
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
    # `null` is an absent key, and `180.0` is 180, as the twin holds it (1.5.1).
    horizon = config.get("evidence_horizon_days")
    horizon = DEFAULT_HORIZON_DAYS if horizon is None else _integer(horizon)
    # A misspelt `code_root` otherwise reports every evidence path as missing from the repository —
    # false, and one error per card. Say the true thing once instead.
    if root and not os.path.isdir(root):
        return ([Finding("code_root_missing",
                         f"`code_root` points at `{code_root}`, which does not exist — "
                         "check 3 cannot verify any path")],
                {"cards": 0, "paths_checked": 0, "code_root": code_root or "", "horizon": horizon})
    # Today in UTC, as the TypeScript twin counts it (1.4.3). The local date put «N days ago» one
    # day apart near midnight east or west of UTC; CI runs in UTC and compares codes, so it never saw.
    today = datetime.now(timezone.utc).date()

    cards, card_findings = load_card_files(config, base)
    findings += card_findings
    checked_paths = 0

    for card_id, fm in cards:
        maturity = _text(fm.get("maturity")) or ""
        if maturity not in LEVELS:
            continue
        level = LEVELS.index(maturity)
        evidence = _map(fm.get("maturity_evidence"))

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
        covered = set()
        for test in _maps(fm.get("tests")):
            test_id = _text(test.get("id")) or ""
            matched = find_cases(test_id, by_full, by_name) if have_report else []
            if matched and all(c.status == "passed" for c in matched):
                passing.append(test_id)
                covered.update(covers_of(test))

        if level >= LEVELS.index("tested") and not passing:
            findings.append(Finding(
                "maturity_without_passing_test",
                f"{card_id}: claims `{maturity}` with no test of its own passing in the report",
                "error" if have_report else "warning"))

        # Only below `implemented`. A passing test is *necessary* to claim `tested`, not
        # sufficient for it — one smoke test does not make an operation covered, and a checker
        # cannot judge which it is. Nagging every honest `implemented` card would retire this rule
        # within a week.
        # And only when a passing test covers the LAST step — the proof §5.2e rule 4 accepts that
        # an operation goes all the way through. Tests of the door alone (sign-in, permission) pass
        # in front of an operation that answers 501; that card is honestly `designed`.
        steps = step_ids_of(fm)
        last = steps[-1] if steps else None
        if have_report and level < LEVELS.index("implemented") and last is not None and last in covered:
            findings.append(Finding(
                "maturity_understated",
                f"{card_id}: claims `{maturity}` while a passing test of its own covers its last step "
                f"`{last}` ({len(passing)} of its tests pass)",
                "warning"))

        # Tier 3 — what cannot be verified must expire.
        if level >= LEVELS.index("in_production"):
            deployed = evidence.get("deployed")
            if isinstance(deployed, dict):
                # Text of the form YYYY-MM-DD naming a day the calendar has, as the twin reads it
                # (1.4.3): fromisoformat also took 20260101 and 2026-W01-1 since Python 3.11.
                raw = deployed.get("since")
                try:
                    if not (isinstance(raw, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", raw)):
                        raise ValueError(raw)
                    since = date.fromisoformat(raw)
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
                        f"(horizon {json_schema.js_string(horizon)}) — nobody has looked since",
                        "warning"))
            # A dated map or a bare string (the schema's two forms); any other value is absent (1.5.1).
            elif isinstance(deployed, str) and deployed:
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
        for claim in _maps(_map(fm.get("data")).get("storage")):
            claims += 1
            pattern = _text(claim.get("store")) or ""
            matched = [s for s in stores if glob_matches(str(s.get("name")), pattern)]

            if not matched:
                findings.append(Finding(
                    "unknown_store",
                    f"{card_id}: claims store `{pattern}`, which the storage does not have"))
                continue
            for store in matched:
                touched.add(str(store.get("name")))

            claimed_keys = _texts(claim.get("keyed_by"))
            if claimed_keys:
                for store in matched:
                    actual = store.get("keyed_by") or []
                    # Compared as the twin compares them, joined (1.5.1).
                    if ",".join(claimed_keys) != ",".join(actual):
                        findings.append(Finding(
                            "store_key_mismatch",
                            f"{card_id}: claims `{pattern}` is keyed by [{', '.join(claimed_keys)}], "
                            f"but `{store.get('name')}` is keyed by [{', '.join(actual)}]"))

            index = _text(claim.get("via_index"))
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


# The card-only half of the controls rule: every operation of a `calls` chain is described by a
# card, and a control shown in a state its first operation cannot depart from is a conflict. It
# reads the contract and the cards, never the inventory — so since round 29 (issue #13) it runs for
# a rendered screen (the conflict an error) and for a contract designed ahead of its screen (a
# warning: a new check over existing fields, §8). See the TypeScript twin.
def judge_calls(contract_id: str, name: str, control: dict, shown_when, data_of, card_by_id: dict,
                findings: list, conflict: str) -> None:
    # A chain (round 27: `calls` as a list, in call order) is judged by its FIRST operation
    # — the chain departs from where that one does; every later step departs from
    # whatever the step before it left, which no screen state shows. Each operation of
    # the chain must still have a card.
    raw_calls = control.get("calls")
    if isinstance(raw_calls, str) and raw_calls:
        chain = [raw_calls]
    elif isinstance(raw_calls, list):
        chain = [str(entry) for entry in raw_calls if isinstance(entry, str) and entry]
    else:
        chain = []
    for step, later in enumerate(chain):
        if step > 0 and later not in card_by_id:
            findings.append(Finding("form_calls_undescribed",
                                    f"{contract_id}: control `{name}` calls `{later}` "
                                    f"(step {step + 1} of {len(chain)}), "
                                    "which no card describes", "warning"))
    if not chain:
        return
    # How the first operation is named in a finding: bare for one, with its chain for several.
    calls = (f"`{chain[0]}` (first of `{' → '.join(chain)}`)" if len(chain) > 1
             else f"`{chain[0]}`")
    card = card_by_id.get(chain[0])
    if card is None:
        findings.append(Finding("form_calls_undescribed",
                                f"{contract_id}: control `{name}` calls {calls}, "
                                "which no card describes", "warning"))
        return
    # A list, empty too, is a declared set of states, as the twin reads it (1.5.1).
    if shown_when is None:
        return
    # `from` is one state or a SET of states (round 18): the control must be shown
    # only in states that belong to the set, and in at least one of them.
    raw_from = _map(card.get("data_transition")).get("from")
    from_set = [raw_from] if isinstance(raw_from, str) and raw_from else _texts(raw_from)
    if from_set and "none" not in from_set and "any" not in from_set:
        mismatch = [s for s in shown_when if data_of(s) not in from_set]
        if mismatch or not any(data_of(s) in from_set for s in shown_when):
            mapped = ""
            if any(data_of(s) != s for s in shown_when):
                mapped = f" (data states [{', '.join(data_of(s) for s in shown_when)}])"
            findings.append(Finding(
                "shown_when_conflicts_transition",
                f"{contract_id}: control `{name}` is shown in "
                f"[{', '.join(shown_when)}]{mapped} but {calls} departs from "
                f"`{' | '.join(from_set)}`", conflict))


# ─────────────────────────── check 5 — the form matches its contract ────────────────────────────
#
# The one check whose reference is authored rather than measured: the contract says what the owner
# decided the screen must show; the inventory says what the rendered screen carries, state by
# state. Contract lines the code has not caught up with are the product's TODO list, printed by
# every build. See the TypeScript twin for the full commentary.
def states_of(value):
    """A list of state names, or None when the field is not a list (1.5.1: a name that is not a
    string is absent). An empty list is a list: `when: []` names no state, as the twin reads it."""
    return _texts(value) if isinstance(value, list) else None


def floor_of(line: dict) -> int:
    """`at_least`, an integer as Number.isInteger has it (`2.0` too), or 1. A message writes it
    with js_string: past 2^53 it is a double, and Python wrote `2e+19` where the twin writes
    20000000000000000000 (1.5.1)."""
    value = line.get("at_least")
    return _integer(value) if _is_integer(value) else 1


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

    # Names in the order the inventory gives them, as the twin's Set keeps them (1.5.1): a set here
    # put the undescribed elements of one screen in an order PYTHONHASHSEED chose, run by run.
    by_screen: dict[str, dict[str, dict]] = {}
    for form in data.get("forms") or []:
        states = {}
        for s in form.get("states") or []:
            # `within` is optional: an inventory that predates container recording gets
            # membership NOT JUDGED, never failed.
            raw_within = s.get("within")
            states[str(s.get("state"))] = {
                "fields": dict.fromkeys(str(x) for x in s.get("fields") or []),
                "controls": dict.fromkeys(str(x) for x in s.get("controls") or []),
                "within": ({str(k): dict.fromkeys(str(c) for c in v or []) for k, v in raw_within.items()}
                           if isinstance(raw_within, dict) else None),
            }
        by_screen[str(form.get("screen"))] = states

    # A frontend repository may declare `cards:` pointing at a sibling checkout that is not
    # always there; then the glob matches nothing and every `calls:` reads as "undescribed" —
    # a fact about the checkout, not the cards. Named once.
    cards, card_findings = load_card_files(config, base)
    # `cards: []` is declared, as in the TypeScript twin (an empty list is not an absent key).
    if config.get("cards") is not None and any(f.code == "no_cards_found" for f in card_findings):
        findings.append(Finding("no_cards_found",
                                "the `cards` patterns matched nothing — every `calls:` below is "
                                "unverifiable here, not undescribed", "warning"))
    card_by_id = dict(cards)

    contracts: list[tuple[str, dict]] = []
    read: list[tuple[str, dict]] = []
    for path in expand_globs(base, patterns):
        fm = read_document(path)
        if isinstance(fm, dict) and is_contract(fm):
            contract_id = _text(fm.get("id"))
            contracts.append((contract_id if contract_id is not None else path, fm))
            read.append((path, fm))
    refuse_twins(read)
    if not contracts:
        findings.append(Finding("form_contracts_missing", "the `forms` patterns matched no contract"))

    claimed: dict[str, dict[str, Any]] = {}
    designed_ahead = 0

    for contract_id, fm in contracts:
        screen = _text(fm.get("screen")) or ""
        states = by_screen.get(screen)
        # A contract may be written before its screen and say so with `maturity: designed`
        # (issue #8): then an absent screen is a warning, not the error a vanished screen earns.
        # The flag cannot go stale silently — a screen that renders while the contract still
        # says designed is reported too.
        maturity = _text(fm.get("maturity")) or "implemented"
        # Screen state → data state through the contract's `states:` map (issue #11);
        # identity when unmapped.
        state_map = _map(fm.get("states"))

        def data_of(state: str, _states=state_map) -> str:
            spec = _states.get(state)
            return (_text(spec.get("data")) if isinstance(spec, dict) else None) or state

        if states is None:
            if maturity == "designed":
                designed_ahead += 1
                findings.append(Finding("form_not_yet_built",
                                        f"{contract_id}: screen `{screen}` is absent from the "
                                        "inventory — designed ahead of the code "
                                        "(`maturity: designed`)", "warning"))
                # `calls` is chosen while the contract is `designed`, and comparing it with the
                # cards needs no inventory (issue #13). Only where the config declares `cards:`.
                if config.get("cards") is not None:
                    for control in _maps(fm.get("controls")):
                        name = (_text(control.get("control_pattern")) or _text(control.get("control"))
                                or "")
                        judge_calls(contract_id, name, control, states_of(control.get("shown_when")),
                                    data_of, card_by_id, findings, "warning")
            else:
                findings.append(Finding("form_screen_missing",
                                        f"{contract_id}: screen `{screen}` is absent from the "
                                        "inventory — nothing rendered it"))
            continue
        if maturity == "designed":
            findings.append(Finding("form_maturity_stale",
                                    f"{contract_id}: screen `{screen}` is rendered but the "
                                    "contract still says `maturity: designed` — the contract "
                                    "is behind the code", "warning"))
        every_state = list(states.keys())
        mine = claimed.setdefault(screen, {"fields": set(), "controls": set(),
                                           "field_families": [], "control_families": []})

        def count_of(regex: re.Pattern, names) -> int:
            return sum(1 for n in names if regex.match(n))

        for entry in _maps(fm.get("presents")):
            pattern = _text(entry.get("field_pattern")) or ""
            when = states_of(entry.get("when"))
            if pattern:
                # A family (issue #10): every matching anchor is accounted for; `at_least`
                # keeps the family from silently becoming empty.
                regex = family_regex(pattern)
                at_least = floor_of(entry)
                mine["field_families"].append(regex)
                for state in when if when is not None else every_state:
                    rendered = states.get(state)
                    if rendered is None:
                        findings.append(Finding("form_state_missing",
                                                f"{contract_id}: `{pattern}` is required in state "
                                                f"`{state}`, which the inventory never rendered"))
                    else:
                        count = count_of(regex, rendered["fields"])
                        if count < at_least:
                            findings.append(Finding("element_missing",
                                                    f"{contract_id}: `{pattern}` must match at least "
                                                    f"{json_schema.js_string(at_least)} element(s) in state `{state}` and "
                                                    f"matches {count}"))
                _field_out_of_state(contract_id, pattern, when, states,
                                    lambda r, rx=regex: count_of(rx, r["fields"]) > 0, findings)
                continue
            field = _text(entry.get("field")) or ""
            mine["fields"].add(field)
            for state in when if when is not None else every_state:
                rendered = states.get(state)
                if rendered is None:
                    findings.append(Finding("form_state_missing",
                                            f"{contract_id}: `{field}` is required in state "
                                            f"`{state}`, which the inventory never rendered"))
                elif field not in rendered["fields"]:
                    findings.append(Finding("element_missing",
                                            f"{contract_id}: `{field}` must be shown in state "
                                            f"`{state}` and is not"))
            _field_out_of_state(contract_id, field, when, states,
                                lambda r, f=field: f in r["fields"], findings)

        for control in _maps(fm.get("controls")):
            pattern = _text(control.get("control_pattern")) or ""
            regex = family_regex(pattern) if pattern else None
            at_least = floor_of(control)
            name = pattern or _text(control.get("control")) or ""
            if regex is not None:
                mine["control_families"].append(regex)
            else:
                mine["controls"].add(name)
            shown_when = states_of(control.get("shown_when"))

            # For a literal both questions are "is it there"; for a family they differ: enough
            # members for the floor, versus any member at all (which is what leaks out of state).
            def enough(rendered: dict, _regex=regex, _name=name, _floor=at_least) -> bool:
                if _regex is None:
                    return _name in rendered["controls"]
                return count_of(_regex, rendered["controls"]) >= _floor

            def any_of(rendered: dict, _regex=regex, _name=name) -> bool:
                if _regex is None:
                    return _name in rendered["controls"]
                return count_of(_regex, rendered["controls"]) > 0

            if shown_when is not None:
                for state in shown_when:
                    rendered = states.get(state)
                    if rendered is None:
                        findings.append(Finding("form_state_missing",
                                                f"{contract_id}: control `{name}` is required in "
                                                f"state `{state}`, which the inventory never rendered"))
                    elif not enough(rendered):
                        if regex is not None:
                            detail = (f"{contract_id}: `{name}` must match at least {json_schema.js_string(at_least)} "
                                      f"control(s) in state `{state}` and matches "
                                      f"{count_of(regex, rendered['controls'])}")
                        else:
                            detail = (f"{contract_id}: control `{name}` must be "
                                      f"available in state `{state}` and is not")
                        findings.append(Finding("control_missing", detail))
                for state, rendered in states.items():
                    if state not in shown_when and any_of(rendered):
                        findings.append(Finding("control_out_of_state",
                                                f"{contract_id}: control `{name}` appears in "
                                                f"state `{state}`, outside its declared `shown_when`"))
            elif at_least > 0 and not any(any_of(rendered) for rendered in states.values()):
                findings.append(Finding("control_missing",
                                        f"{contract_id}: control `{name}` appears in no state at all"))

            judge_calls(contract_id, name, control, shown_when, data_of, card_by_id,
                        findings, "error")

        for entry in _maps(fm.get("removed")):
            name = _text(entry.get("control")) or ""
            mine["controls"].add(name)
            for state, rendered in states.items():
                if name in rendered["controls"]:
                    findings.append(Finding("removed_control_present",
                                            f"{contract_id}: control `{name}` was removed by the "
                                            f"owner's decision yet appears in state `{state}`"))

        # A group's anchor is accounted for BY the group line: the owner named the container
        # when grouping by it. Warning about it as undescribed would ask the owner to decide
        # what they already decided — measured 19.08: three of fourteen warnings were this.
        for group in _maps(fm.get("groups")):
            if _text(group.get("group")):
                mine["fields"].add(group["group"])

        # ── group membership ─────────────────────────────────────────────────
        # The contract seats elements in groups; the inventory's `within` records which
        # containers each anchor ACTUALLY rendered inside. Judged only where the member renders
        # and the inventory carries the measurement. The first inventory with containers refuted
        # its own contract: `add-set` was contracted into the footer and measured living only in
        # the set table — the checker's first catch was its author.
        for group in _maps(fm.get("groups")):
            gname = _text(group.get("group")) or ""
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
            for member in _texts(group.get("contains")):
                # A family seated in a group: every rendered member of the family must sit there.
                regex = family_regex(member) if "*" in member else None
                for state, rendered in states.items():
                    if rendered["within"] is None:
                        continue
                    if regex is not None:
                        # Fields, then controls, each in the inventory's order, as the twin walks
                        # them (1.5.1): sorted here, another member of the family was named.
                        present = [a for a in [*rendered["fields"], *rendered["controls"]]
                                   if regex.match(a)]
                    elif member in rendered["fields"] or member in rendered["controls"]:
                        present = [member]
                    else:
                        present = []
                    offender = next((a for a in present
                                     if gname not in (rendered["within"].get(a) or set())), None)
                    if offender is not None:
                        chain = rendered["within"].get(offender) or {}
                        inside = ", ".join(sorted(chain, key=utf16_order))
                        findings.append(Finding("member_out_of_group",
                                                f"{contract_id}: `{offender}` is contracted into "
                                                f"`{gname}` but in state `{state}` renders "
                                                f"inside [{inside}]"))
                        break

    # The mirror of a wild endpoint: rendered, accounted for by nobody. A family line accounts
    # for every anchor it matches — that is the whole point of declaring one.
    for screen, states in by_screen.items():
        mine = claimed.get(screen)
        if mine is None:
            # A screen with no contract is not judged element by element — contracts are opt-in
            # per screen. But it is no longer silent (round 26 ⑭): the mirror of check 1's wild
            # endpoint, one level up; a warning unless the config opts in.
            findings.append(Finding(
                "form_uncontracted_screen",
                f"{screen}: rendered in {len(states)} state(s) and described by no contract",
                "error" if config.get("uncontracted_screens") == "error" else "warning"))
            continue
        seen: set[str] = set()
        for rendered in states.values():
            for field in rendered["fields"]:
                if (field not in mine["fields"] and f"f:{field}" not in seen
                        and not any(r.match(field) for r in mine["field_families"])):
                    seen.add(f"f:{field}")
                    findings.append(Finding("undescribed_element",
                                            f"{screen}: `{field}` is rendered but no contract "
                                            "line accounts for it", "warning"))
            for control in rendered["controls"]:
                if (control not in mine["controls"] and f"c:{control}" not in seen
                        and not any(r.match(control) for r in mine["control_families"])):
                    seen.add(f"c:{control}")
                    findings.append(Finding("undescribed_element",
                                            f"{screen}: control `{control}` is rendered but no "
                                            "contract line accounts for it", "warning"))

    return findings, {"contracts": len(contracts), "screens": len(by_screen),
                      "designed_ahead": designed_ahead,
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
        description="checks 1–5 — no wild endpoints, no unproven steps, no inflated maturity, "
                    "no imagined storage, the form matches its contract")
    parser.add_argument("config", nargs="?", help="path to usedesign.config.yaml")
    parser.add_argument("--conformance", action="store_true",
                        help="run the checks conformance corpus")
    args = parser.parse_args()

    if args.conformance:
        return run_conformance()
    if not args.config:
        parser.print_help()
        return 2

    config, base = load_config(args.config)

    # `checks: [5]` scopes which checks apply to THIS repository — same rule as the TypeScript twin.
    # The config holds a non-empty list of check numbers or nothing (1.5.1).
    scope = config.get("checks")
    def in_scope(n: int) -> bool:
        return scope is None or n in scope
    errors = 0

    if in_scope(1):
        route_findings, summary = check(config, base)
        print(f"inventory:  {summary['served']} route(s) served"
              + (f", produced by {summary['produced_by']}" if summary["produced_by"] else ""))
        # The routes designed ahead are counted here as in the twin (1.5.1); this line had lost them.
        print(f"cards:      {summary['declared']} REST route(s) declared"
              + (f", {summary['designed_ahead']} designed ahead of the code"
                 if summary["designed_ahead"] else ""))
        print(f"excluded:   {summary['excluded']} route(s)")
        for pattern, count in js_entries(summary["hidden_per_rule"]):
            print(f"              {pattern} → {count}")
        print()
        errors += report("check 1 (no wild endpoints)", route_findings)

    if in_scope(2):
        coverage_findings, coverage = check_coverage(config, base)
        print(f"report:     {coverage['report_cases']} test case(s)")
        by_inheritance = f" ({coverage['inherited']} by inheritance)" if coverage.get("inherited") else ""
        print(f"steps:      {coverage['proven']} proven{by_inheritance}, {coverage['unproven']} not")
        kinds = [k for k in (
            f"{coverage['gaps_harness']} need a harness change" if coverage.get("gaps_harness") else "",
            f"{coverage['gaps_unreachable']} unreachable" if coverage.get("gaps_unreachable") else "") if k]
        print(f"gaps:       {coverage['gaps']} declared" + (f" ({', '.join(kinds)})" if kinds else ""))
        print()
        errors += report("check 2 (no unproven steps)", coverage_findings)

    if in_scope(3):
        maturity_findings, maturity = check_maturity(config, base)
        print(f"cards:      {maturity['cards']} card(s), {maturity['paths_checked']} evidence path(s) checked"
              + ("" if maturity["code_root"] else " — no `code_root`, path check NOT RUN"))
        print(f"horizon:    {json_schema.js_string(maturity['horizon'])} days")
        print()
        errors += report("check 3 (no inflated maturity)", maturity_findings)

    if in_scope(4):
        storage_findings, storage = check_storage(config, base)
        print(f"storage:    {storage['stores']} store(s)"
              + (f", produced by {storage['produced_by']}" if storage["produced_by"] else "")
              + f"; {storage['claims']} claim(s) in cards touching {storage['touched']}")
        errors += report("check 4 (no imagined storage)", storage_findings)

    # Check 5 is opt-in: naming it in `checks:` or declaring `forms:` opts in — `forms: []` too, as
    # in the twin (1.5.1), where it then reports that no pattern is given.
    if (5 in scope) if scope is not None else (config.get("forms") is not None):
        form_findings, form = check_form(config, base)
        print(f"forms:      {form['contracts']} contract(s) against {form['screens']} rendered screen(s)"
              + (f", {form['designed_ahead']} designed ahead of the code" if form.get("designed_ahead") else "")
              + (f", produced by {form['produced_by']}" if form["produced_by"] else ""))
        errors += report("check 5 (the form matches its contract)", form_findings)

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CannotRead as stop:
        print(f"check.py: {stop}", file=sys.stderr)
        sys.exit(2)
