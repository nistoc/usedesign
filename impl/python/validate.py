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
import errno
import os
import re
import sys
import unicodedata

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
CONCURRENCY_MODES = ["etag_required", "etag_optional", "idempotency_by_header",
                     "idempotency_by_formula", "none_by_design", "none_unexplained",
                     "server_read_version"]
TRANSPORTS = ["http_rest", "json_rpc", "in_process", "ui"]
TEST_LEVELS = ["unit", "integration", "ui", "contract"]
GAP_KINDS = ["unwritten", "harness", "unreachable"]

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
    # A byte-order mark must not decide whether a card parses, and bytes that are not UTF-8 must
    # not crash the run: read as the TypeScript twin reads (round 29).
    text = open(path, encoding="utf-8-sig", errors="replace").read()
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return yaml.safe_load(text[3:end])


def why_unreadable(path: str) -> str:
    """Why a collected path cannot be opened as a file, or "" when it can (1.4.2).

    A link that leads nowhere and a file without read permission are entries a listing finds and
    a reader cannot open. This implementation stopped on both with a traceback; the TypeScript
    twin dropped the first unseen. The words are the same in both implementations.
    """
    if not os.path.exists(path):
        return "it is a link to a path that does not exist"
    if os.path.isdir(path):
        return "it is a directory"
    try:
        with open(path, "rb"):
            pass
    except OSError as e:
        return cause_of(e)
    return ""


class CannotRead(Exception):
    """An input the run cannot go past: it stops with the input's name and exit 2 (1.4.2)."""


def cause_of(e: OSError) -> str:
    """The cause of a system error, in the words both implementations print (1.4.2).

    A file another process holds open on Windows is a permission error here and EBUSY in the
    TypeScript twin, so it is "permission denied" in both.
    """
    if isinstance(e, PermissionError) or e.errno in (errno.EACCES, errno.EPERM, errno.EBUSY):
        return "permission denied"
    return errno.errorcode.get(e.errno, str(e)) if e.errno else str(e)


# ── Which files a pattern names (1.4.2) ───────────────────────────────────────────────────────
#
# The algorithm of the TypeScript twin's expandGlob, step for step, in place of Python's glob, so
# that both implementations collect the same files. Measured before the change: glob walked a loop
# of links to the system's depth limit (exponential time with two links per level), matched `[ab]`
# as a set and letters in either case on Windows, and the twin did none of these.

def _join(directory: str, name: str) -> str:
    """A name under a directory; a name that looks like a drive does not restart the path."""
    return directory + name if directory.endswith(os.sep) else directory + os.sep + name


def is_entry(path: str) -> bool:
    """Whether anything stands at `path`, a link that leads nowhere included.

    Only "does not exist" is absence: an entry the system lists and will not describe — no
    permission, a link made by another system — goes on to the reader, which names it.
    """
    try:
        os.lstat(path)
        return True
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return True


def real_of(path: str) -> str:
    """The real path of `path`; for an entry the system will not resolve — a link that leads
    nowhere, on Windows a file without read permission — the real path of its directory and its
    own name, so that such an entry reached two ways is still one entry."""
    try:
        return os.path.realpath(path, strict=True)
    except OSError:
        pass
    try:
        return _join(os.path.realpath(os.path.dirname(path) or ".", strict=True), os.path.basename(path))
    except OSError:
        return os.path.abspath(path)


def listing(directory: str) -> list:
    """The entries of a directory a pattern walks into; one that cannot be listed stops the run
    with its name, as a file that cannot be opened does: the cards under it would go unseen."""
    try:
        with os.scandir(directory) as entries:
            return list(entries)
    except OSError as e:
        raise CannotRead(f"`{directory}` cannot be listed — {cause_of(e)}") from None


def _is_link(entry) -> bool:
    """A link as the TypeScript twin's Dirent sees one: a symbolic link, and on Windows any reparse
    point — a junction, a link made by WSL — which DirEntry.is_symlink() does not count."""
    if entry.is_symlink():
        return True
    if os.name != "nt":
        return False
    return bool(getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0) & 0x400)  # REPARSE_POINT


def _segment(segment: str):
    """One glob segment as a regular expression: `*` and `?` do not cross a separator."""
    return re.compile("".join("[^/\\\\]*" if ch == "*" else "[^/\\\\]" if ch == "?" else re.escape(ch)
                              for ch in segment), re.DOTALL)


def expand_glob(base: str, pattern: str) -> list[str]:
    """Expand a pattern relative to `base`. Supports `*`, `?` and `**`.

    Links to directories are followed, and a loop of them is walked once; a name that starts with
    a dot is matched only by a segment that starts with a dot, and `**` passes it over; `[` and `]`
    are plain characters; letter case counts. Every entry whose name matches is returned, a link
    that leads nowhere included, so that the reader names it; directories are not.
    """
    segments = [s for s in re.split(r"[\\/]+", pattern) if s]
    current = [os.path.abspath(base)]
    for index, segment in enumerate(segments):
        last = index == len(segments) - 1
        found: list[str] = []
        if segment == "**":
            for directory in current:
                if not os.path.isdir(directory):
                    continue
                # Each directory carries its real path and those of the directories above it: a
                # link back to one of them would be walked forever and is walked once. The system
                # is asked for a real path only at the start and at a link; below that, the
                # parent's real path and the name are it.
                stack = [(directory, real_of(directory), [])]
                while stack:
                    here, real, above = stack.pop()
                    found.append(here)
                    if real in above:
                        continue
                    for entry in listing(here):
                        if entry.name.startswith("."):
                            continue
                        path = _join(here, entry.name)
                        if not _is_link(entry) and entry.is_dir(follow_symlinks=False):
                            stack.append((path, _join(real, entry.name), above + [real]))
                        elif _is_link(entry) and os.path.isdir(path):
                            stack.append((path, real_of(path), above + [real]))
                        elif last:
                            found.append(path)
        elif segment in (".", ".."):
            found += [os.path.normpath(_join(directory, segment)) for directory in current]
        elif not re.search(r"[*?]", segment):
            found += [_join(directory, segment) for directory in current]
        else:
            matcher = _segment(segment)
            dotted = segment.startswith(".")
            for directory in current:
                if not os.path.isdir(directory):
                    continue
                for entry in listing(directory):
                    if (entry.name.startswith(".") and not dotted) or not matcher.fullmatch(entry.name):
                        continue
                    path = _join(directory, entry.name)
                    if last or (os.path.isdir(path) if _is_link(entry) else entry.is_dir(follow_symlinks=False)):
                        found.append(path)
        current = list(dict.fromkeys(found))
    return once_per_file([path for path in current if is_entry(path) and not os.path.isdir(path)])


# ── What the user reads (SPEC §5.7, round 28) ─────────────────────────────────────────────────
#
# A covers_outcomes value may carry context around the words the user reads — where the line
# appears, why, which code renders it — and those words go inside «…» or “…”. Round 28 measured
# authors who re-measured a screen and wrote that context into every refusal: each value became
# unique, and refusals sharing one status line stopped being reported. So the key compares the
# quoted words. It is computed from the 1.2 key (strip + lower; casefold(lower(x)) == casefold(x)
# on every code point, and NFC is a function of its input), so every pair 1.2 reported is still
# reported.

QUOTE_PAIRS = {"«": "»", "“": "”"}  # «…» and “…”
QUOTE_OPENERS = {closer: opener for opener, closer in QUOTE_PAIRS.items()}


def quoted_spans(text: str) -> list[str]:
    """Every outermost «…» or “…” span, in order.

    Quotes pair as brackets do, each kind on its own: a quote of the same kind nests and belongs
    to the outer span; a quote of the other kind inside a span is plain text. A closer with no
    opener is ignored; an opener never closed opens nothing, and the quotes after it are still
    read. One pass pairs every quote, a second takes the outermost pairs — linear in the length,
    so a value of a thousand unclosed openers costs what a value of a thousand letters does.
    """
    closer_at: dict[int, int] = {}  # where each opener that is closed closes
    open_at: dict[str, list[int]] = {opener: [] for opener in QUOTE_PAIRS}
    for pos, ch in enumerate(text):
        if ch in QUOTE_PAIRS:
            open_at[ch].append(pos)
        elif ch in QUOTE_OPENERS:
            stack = open_at[QUOTE_OPENERS[ch]]
            if stack:  # a closer with no opener is ignored
                closer_at[stack.pop()] = pos
    spans: list[str] = []
    i, n = 0, len(text)
    while i < n:
        end = closer_at.get(i)  # an opener never closed is not in the map: it opens nothing
        if end is None:
            i += 1
        else:
            spans.append(text[i + 1:end])
            i = end + 1
    return spans


def shown_words(span: str) -> list[str]:
    """Every code point that is not a letter, a mark or a number (category L, M or N) read as a
    space — a vowel sign or an accent belongs to the word before it. A mark is a word character
    only when it follows one (a letter, a number, or a mark already attached): a mark after a
    space, a glyph or the start of the span reads as a space — the U+FE0F after an emoji that is
    a symbol, such as ⚠, and a keycap after # or *. After a letter or a digit the U+FE0F stays
    in the word: ℹ (U+2139) is a letter, and a keycap on a digit keeps both its marks."""
    shown = []
    attached = False  # the code point before was read as a word character
    for ch in span:
        category = unicodedata.category(ch)[0]
        attached = category in "LN" or (category == "M" and attached)
        shown.append(ch if attached else " ")
    return "".join(shown).split()


def shown_key(value: str) -> tuple:
    """The key outcomes_indistinguishable groups by.

    The value is stripped, case-folded and NFC-normalised first — folding before NFC, in that
    order — so an accent typed as a separate mark after its letter reads as the composed letter
    (SPEC §5.7 names the few sequences that do not). Then the kept quoted spans as a set — a span
    is kept when it has two words or more of at least two letters (marks and numbers do not
    count), so a glyph or a single word, such as «!» or «OK», is not a message. With no span kept,
    the whole value, stripped, case-folded and NFC-normalised (1.2 lowercased; folding and
    normalising only add matches). A set of spans never equals a whole value: the two keys are
    tagged apart.
    """
    folded = unicodedata.normalize("NFC", value.strip().casefold())
    kept = set()
    for span in quoted_spans(folded):
        words = shown_words(span)
        long_words = [w for w in words if sum(unicodedata.category(ch)[0] == "L" for ch in w) >= 2]
        if len(long_words) >= 2:
            kept.add(" ".join(words))
    if kept:
        return ("quoted", frozenset(kept))
    return ("whole", folded)


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

    # `data_transition.from` may be a SET (round 18): an operation departing from any of several
    # states. One state is written as a string; a one-element set is that string wearing brackets.
    transition_value = fm.get("data_transition")
    from_value = transition_value.get("from") if isinstance(transition_value, dict) else None
    if isinstance(from_value, list):
        if len(from_value) < 2:
            err("malformed_transition",
                "`data_transition.from` as a set needs at least two states — one state is written as a string")
        if len({str(s) for s in from_value}) != len(from_value):
            err("malformed_transition", "`data_transition.from` lists the same state twice")

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
    # `maturity_evidence.tested` is advisory prose — but a leading number is a claim that rots by
    # hand ("5 tests" kept after the sixth was cited); the product's cards were kept in step by hand three times in one day.
    tested_prose = evidence.get("tested") if isinstance(evidence, dict) else None
    tested_match = re.match(r"\s*(\d+)", str(tested_prose)) if isinstance(tested_prose, (int, str)) else None
    if tested_match and int(tested_match.group(1)) != len(tests):
        warn("tested_count_mismatch",
             f"maturity_evidence.tested says {tested_match.group(1)}, tests[] lists {len(tests)} — the count went stale")

    # ── concurrency ──────────────────────────────────────────────────────────
    concurrency = fm.get("concurrency") or {}
    mode = concurrency.get("mode")
    if mode is not None and mode not in CONCURRENCY_MODES:
        err("invalid_enum_value", f"concurrency.mode `{mode}` is not one of {CONCURRENCY_MODES}")
    if mode and mode != "etag_required" and not concurrency.get("rationale"):
        err("relaxation_without_rationale", f"mode `{mode}` weakens protection without a rationale")
    if mode == "idempotency_by_formula" and not concurrency.get("formula"):
        err("missing_required_field", "idempotency_by_formula without `formula`")
    # Round 24: a soft delete that reads no If-Match between two neighbours that require one,
    # with nothing in the code to say why. `none_by_design` asserts an intent nobody measured;
    # this mode records the absence and keeps it visible in every run until it is explained.
    if mode == "none_unexplained":
        warn("concurrency_unexplained",
             "concurrency.mode is `none_unexplained` — no precondition is read and the code gives "
             "no reason; a measured absence, kept visible until it is explained (`none_by_design`) "
             "or closed (an `etag_*` mode)")

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
    for entry in fm.get("coverage_gaps") or []:
        kind = entry.get("kind")
        if kind is not None and kind not in GAP_KINDS:
            err("invalid_enum_value",
                f"coverage_gaps `{entry.get('step')}`: kind `{kind}` is not one of {GAP_KINDS}")

    # ── a variant of another operation (SPEC 5.2e) ──────────────────────────────────────────────
    # Only what the card itself can show: the inherited steps are its own listed steps, and the
    # shared code is its own evidence. Whether the original agrees is check 2's question.
    inherited_steps: set[str] = set()
    variant = fm.get("variant_of")
    if isinstance(variant, dict):
        for sid in variant.get("inherits") or []:
            if sid not in step_ids:
                err("variant_inherits_unlisted_step",
                    f"`variant_of.inherits` names `{sid}`, which is not one of this card's steps — "
                    "a variant lists every step it runs")
            inherited_steps.add(sid)
        implemented = evidence.get("implemented")
        shared = variant.get("shared")
        if implemented is not None and isinstance(shared, str):
            items = implemented if isinstance(implemented, list) else [implemented]
            own = [re.sub(r":\d+$", "", part.strip())
                   for item in items for part in str(item).split("+")]
            shared = re.sub(r":\d+$", "", shared.strip())
            if shared not in own:
                err("variant_shared_not_implemented",
                    f"`variant_of.shared` `{shared}` is not in this card's `maturity_evidence.implemented`")

    for sid in step_ids:
        if sid not in covered and sid not in gaps and sid not in inherited_steps:
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
    # Round 23 wrote two read cards whose screens could describe every refusal and not the one
    # ending the user came for. A read has no `data_transition.to`, and with a single ending no
    # `outcomes[]` either — the list exists only for endings that differ in shape — so the
    # vocabulary held the failures and nothing else. `ok` is the name of that default success.
    # It is in the vocabulary exactly when the operation names no success of its own; beside
    # named successes it is the residue of a template.
    named_successes = [oid for oid, where in outcome_vocabulary.items()
                       if where in ("outcomes", "data_transition.to")]
    has_default_success = not named_successes
    for name, iface in interfaces.items():
        covers = iface.get("covers_outcomes")
        if not isinstance(covers, dict):
            continue
        for key in covers:
            if key == "ok":
                if not has_default_success:
                    named = ", ".join(f"`{i}`" for i in named_successes)
                    err("ok_reserved",
                        f"interface `{name}`: `ok` is reserved for the default success, and this "
                        f"operation names its successes: {named} — write those instead")
                continue
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
        # A warning, not an error: cards written before round 23 had no way to name the success,
        # and a gate must not turn red on them for a word that did not exist when they were written.
        if has_default_success:
            if "ok" not in covers:
                warn("default_success_uncovered",
                     f"interface `{name}`: the default success has no line in covers_outcomes — "
                     "write `ok:`, even as null")
            elif covers["ok"] is None:
                warn("outcome_unshown",
                     f"interface `{name}`: outcome `ok` is declared not shown to the user")

        # Shown, but shown as the same thing. Between "the user sees it" and "the user sees
        # nothing" sits the state nobody notices: two different endings wearing one sentence.
        # Measured on a real screen — 401 and 403 both surfaced as the same «попробуйте ещё раз»,
        # so the user who must give consent is told to retry, and retrying can never work.
        # Round 28: the words compared are the quoted ones, not the whole value (shown_key).
        by_text: dict[tuple, list[str]] = {}
        for oid, shown in covers.items():
            if not isinstance(shown, str):
                continue
            by_text.setdefault(shown_key(shown), []).append(oid)
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
    # `mutates` is the format's own word for "writes without a state change" (round 21: a card
    # for logging a set — transition null, mutates seven fields — was called read-only here).
    writes_without_transition = bool(fm.get("mutates"))
    if (fm.get("data_transition", False) is None
            and not writes_without_transition
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
FORM_KEYS = {"usedesign_form", "id", "screen", "page", "entity", "maturity", "states",
             "presents", "controls", "groups", "removed"}
FORM_MATURITY = ["designed", "implemented"]
STATE_KEYS = {"data", "note"}
ELEMENT_KEYS = {"field", "field_pattern", "at_least", "shows", "when", "note"}
CONTROL_KEYS = {"control", "control_pattern", "at_least", "calls", "shown_when",
                "shown_when_rule", "opens", "behaviour", "placement", "note"}
GROUP_KEYS = {"group", "role", "contains", "note"}
GROUP_ROLES = ["header", "footer", "section", "table", "list", "toolbar", "menu"]
REMOVED_KEYS = {"control", "was", "verdict"}


def anchor_or_family(line: dict, literal_key: str, pattern_key: str, where: str, err) -> str | None:
    """One line names ONE anchor or ONE family (issue #10), never both and never neither.

    A "pattern" without a wildcard is a literal wearing the wrong key, and would silently
    match nothing the literal key would have matched.
    """
    literal = line.get(literal_key)
    pattern = line.get(pattern_key)
    if not literal and not pattern:
        err("missing_required_field", f"{where}: `{literal_key}` (or `{pattern_key}`) is absent")
    if literal and pattern:
        err("literal_and_pattern",
            f"{where}: both `{literal_key}` and `{pattern_key}` — one line names one anchor "
            "or one family, never both")
    if pattern and "*" not in str(pattern):
        err("pattern_without_wildcard",
            f"{where}: `{pattern}` has no `*` — a family without a wildcard is a literal; "
            f"write `{literal_key}:`")
    at_least = line.get("at_least")
    if at_least is not None and (isinstance(at_least, bool)
                                 or not isinstance(at_least, int) or at_least < 0):
        err("malformed_at_least",
            f"{where}: `at_least` must be a non-negative integer, got `{at_least}`")
    if at_least is not None and not pattern:
        err("malformed_at_least",
            f"{where}: `at_least` belongs to a family line (`{pattern_key}`) — a single anchor "
            "is present or it is not")
    return str(literal) if literal else (str(pattern) if pattern else None)


def validate_form(fm: dict, filename: str = "",
                  known_forms: set[str] | None = None,
                  known_cards: set[str] | None = None) -> list[Finding]:
    """Validate one form contract. `known_forms` enables the `opens` link warning, `known_cards`
    the `calls` one (round 29, issue #13)."""
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

    # `maturity: designed` marks a contract written before its screen (issue #8) — two values,
    # not the card's six: a contract has no evidence axis beyond "does the screen render".
    maturity = fm.get("maturity")
    if maturity is not None and maturity not in FORM_MATURITY:
        err("invalid_enum_value", f"maturity `{maturity}` is not one of {FORM_MATURITY}")

    # `states:` maps screen states onto data states (issue #11).
    if "states" in fm:
        state_map = fm.get("states")
        if not isinstance(state_map, dict):
            err("malformed_states", "`states` must be a map of screen state → { data: <data state> }")
        else:
            for state, spec in state_map.items():
                if not isinstance(spec, dict):
                    err("missing_required_field", f"states.{state}: `data` is absent")
                    continue
                if not spec.get("data"):
                    err("missing_required_field", f"states.{state}: `data` is absent")
                for key in spec:
                    if key not in STATE_KEYS:
                        err("unknown_field", f"states.{state}: `{key}` is not part of a state line")

    presents = fm.get("presents") if isinstance(fm.get("presents"), list) else []
    seen_fields: set[str] = set()
    for index, element in enumerate(presents):
        if not isinstance(element, dict):
            continue
        if not element.get("shows"):
            err("missing_required_field", f"presents[{index}]: `shows` is absent")
        for key in element:
            if key not in ELEMENT_KEYS:
                err("unknown_field", f"presents[{index}]: `{key}` is not part of an element line")
        field = anchor_or_family(element, "field", "field_pattern", f"presents[{index}]", err)
        if field:
            if field in seen_fields:
                err("duplicate_element", f"`{field}` appears more than once in presents")
            seen_fields.add(field)

    controls = fm.get("controls") if isinstance(fm.get("controls"), list) else []
    seen_controls: set[str] = set()
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            continue
        for key in control:
            if key not in CONTROL_KEYS:
                err("unknown_field", f"controls[{index}]: `{key}` is not part of a control line")
        name = anchor_or_family(control, "control", "control_pattern", f"controls[{index}]", err)
        if name:
            if name in seen_controls:
                err("duplicate_control", f"`{name}` appears more than once in controls")
            seen_controls.add(name)
        opens = control.get("opens")
        if opens and known_forms is not None and opens not in known_forms:
            warn("undescribed_form",
                 f"control `{name}` opens `{opens}`, which no contract in this set describes")
        # `calls` names the operation a control runs, or null for local behaviour — and since
        # round 27 the chain it runs, in call order: a draft's «save as plan» renames it, then
        # publishes it. A list of one is a string wearing brackets (the round 18 reason for
        # `from`); an empty list says nothing that `null` would not; an entry that is not an id
        # names no card at all.
        calls = control.get("calls")
        if calls is not None and not isinstance(calls, str):
            if not isinstance(calls, list):
                err("malformed_calls",
                    f"controls[{index}]: `calls` must be an operation id, a list of them in call "
                    "order, or null")
            elif len(calls) < 2:
                err("malformed_calls",
                    f"controls[{index}]: a `calls` list names a chain of two or more operations "
                    "— one is written as its id, none as null")
            elif any(not isinstance(entry, str) or not entry for entry in calls):
                err("malformed_calls",
                    f"controls[{index}]: every entry of `calls` must be an operation id")
        # Round 29 (issue #13): with cards in the validated set, every operation `calls` names is
        # looked up among them — the `opens` ↔ contracts cross-check, one kind over. `None` (no
        # cards in the set) switches it off. See the TypeScript twin.
        if known_cards is not None:
            if isinstance(calls, str) and calls:
                chain = [calls]
            elif isinstance(calls, list):
                chain = [e for e in calls if isinstance(e, str) and e]
            else:
                chain = []
            for step, op in enumerate(chain):
                if op not in known_cards:
                    where = f" (step {step + 1} of {len(chain)})" if len(chain) > 1 else ""
                    warn("form_calls_undescribed",
                         f"control `{name}` calls `{op}`{where}, which no card in this set describes")

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
            files += expand_glob(path, "**/*.op.md") + expand_glob(path, "**/*.contract.md")
        else:
            files.append(path)
    return once_per_file(files)


def once_per_file(paths: list[str]) -> list[str]:
    """Paths in order, each file once however many links or patterns lead to it (1.4.2).

    A loop of links gave the same card here once per level of glob's walk, and twice in the
    TypeScript twin; the counts disagreed. See the TypeScript twin.
    """
    seen: set[str] = set()
    out = []
    for path in sorted(set(paths)):
        key = real_of(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def is_usedesign_config(path: str, fm) -> bool:
    """A named file that is a usedesign config, not a card (issue #14) — plain or fenced."""
    if isinstance(fm, dict) and "usedesign_config" in fm:
        return True
    try:
        parsed = yaml.safe_load(open(path, encoding="utf-8-sig", errors="replace"))
    except Exception:
        return False
    return isinstance(parsed, dict) and "usedesign_config" in parsed


def read_front(path: str):
    """The front matter of a file `validate` was given, or why there is none (round 29, issue #14).

    A card or contract whose front matter cannot be read carries none of the required keys (§8),
    so it is reported with its cause, never skipped. See the TypeScript twin.
    """
    # 1.4.2: a file that cannot be opened is named as such, with its cause — not a traceback.
    why = why_unreadable(path)
    if why:
        return None, f"cannot be read — {why}"
    try:
        fm = front_matter(path)
    except yaml.YAMLError as e:
        return None, f"front matter is not valid YAML — {str(e).splitlines()[0]}"
    except OSError as e:
        return None, f"cannot be read — {cause_of(e)}"
    if isinstance(fm, list):
        return None, "front matter is a list — a card's fields are a mapping"
    if not isinstance(fm, dict):
        return None, ("no front matter — the file must open with a `---` line, carry its fields, "
                      "and close them with a second `---` line")
    return fm, ""


def run_files(paths: list[str]) -> int:
    # Round 29 (issue #14): a path that exists and yields nothing to validate is refused, as a
    # missing path is (exit 2). See the TypeScript twin.
    refusals = []
    for path in paths:
        if not os.path.exists(path):
            refusals.append(f"`{path}`: no such file or directory")
        elif os.path.isdir(path):
            if not collect([path]):
                refusals.append(f"`{path}` holds no card (*.op.md) and no form contract "
                                "(*.contract.md) — nothing to validate")
        elif not re.search(r"\.(op|contract)\.md$", path):
            fm, problem = read_front(path)
            if problem.startswith("cannot be read"):
                refusals.append(f"`{path}` {problem}")
            elif is_usedesign_config(path, fm):
                refusals.append(f"`{path}` is a usedesign config — `usedesign check {path}` reads "
                                "it; `validate` takes cards, form contracts or their directories")
            elif fm is None:
                refusals.append(f"`{path}` has no front matter — it is neither a card nor a form "
                                "contract")
    if refusals:
        for refusal in refusals:
            print(f"validate.py: {refusal}", file=sys.stderr)
        return 2
    files = collect(paths)
    cards: dict = {}
    forms: dict = {}
    # A card or contract file without front matter used to vanish from the count; it is counted
    # and named now, with its cause.
    unreadable = []
    for path in files:
        fm, problem = read_front(path)
        if fm is not None:
            target = forms if fm.get("usedesign_form") == 1 else cards
            target[fm.get("id")] = (path, fm)
        else:
            unreadable.append((path, problem))
    unreadable_forms = sum(1 for path, _ in unreadable if path.endswith(".contract.md"))
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

    for path, problem in unreadable:
        show(path, [Finding("missing_required_field", problem)])
    for _, (path, fm) in sorted(cards.items()):
        show(path, validate(fm, os.path.basename(path), known))
    for _, (path, fm) in sorted(forms.items()):
        show(path, validate_form(fm, os.path.basename(path), known_forms,
                                 known if cards else None))
    print(f"\n{len(cards) + len(unreadable) - unreadable_forms} card(s), "
          f"{len(forms) + unreadable_forms} form contract(s): {errors} error(s), {warnings} warning(s)")
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
        # And their absence (round 28): a rule that must stay quiet on a case is a rule too, and
        # `warnings:` alone could never tell a guard from a case that forgot to list a warning.
        for code in case.get("absent_warnings", []):
            if code in warned:
                problems.append(f"unexpected warning `{code}`")
        # And what a warning names: a code alone cannot tell the right group of outcomes from a
        # wrong one, so a case may also give text that one reported warning must contain.
        details = [f.detail for f in findings if f.severity == "warning"]
        for text in case.get("warning_messages", []):
            if not any(text in detail for detail in details):
                problems.append(f'no warning says "{text}"')

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
    try:
        sys.exit(main())
    except CannotRead as stop:
        print(f"validate.py: {stop}", file=sys.stderr)
        sys.exit(2)
