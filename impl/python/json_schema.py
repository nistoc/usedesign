"""The JSON Schema layer of `validate`, as the TypeScript twin runs it (1.4.3).

The twin validates a card's front matter against `schema/` with Ajv — draft 2020-12, every error
reported — before its own rules; this prototype did not, and a card the schema refuses, an id that
is not an operation id or a key the schema does not know, passed here and failed there. This module
reads the published schemas as Ajv does: the same messages, in the same order, as many of them.
It implements the keywords the schemas use and refuses a schema with any other, so that a keyword
added to `schema/` cannot pass here unread.

The front matter is read for it as the twin reads it, as YAML 1.2: `yes` is a string and
`2026-10-11` a string the schema's `format` judges, where PyYAML (YAML 1.1) makes a boolean and
a date of them.
"""
from __future__ import annotations

import json
import math
from decimal import Decimal
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(HERE, "..", "..", "schema")


class SchemaRefused(Exception):
    """A schema that uses what this module does not implement."""


# ── YAML as the twin reads it ─────────────────────────────────────────────────────────────────
#
# The `yaml` package's core schema (YAML 1.2): these scalars are null, booleans and numbers, every
# other plain scalar is a string — no `yes`, no dates, no `012` as octal, no `<<` merge.

class _Core(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        # The twin's parser refuses a key written twice — two scalars of one value, `1` and `0x1`
        # alike, `1` and `"1"` not; PyYAML keeps the last of them.
        seen = set()
        for key_node, _ in node.value:
            if isinstance(key_node, yaml.ScalarNode):
                key = self.construct_object(key_node)
                kind = "null" if key is None else "bool" if isinstance(key, bool) else (
                    "number" if isinstance(key, (int, float)) else "string")
                if kind == "number" and math.isnan(key):
                    continue
                if (kind, key) in seen:
                    mark = key_node.start_mark
                    raise yaml.constructor.ConstructorError(
                        None, None, f"Map keys must be unique at line {mark.line + 1}, column {mark.column + 1}:")
                seen.add((kind, key))
        return super().construct_mapping(node, deep)


_Core.yaml_implicit_resolvers = {}
for _tag, _pattern, _first in [
    ("null", r"^(?:~|[Nn]ull|NULL)?$", ["~", "n", "N", ""]),
    ("bool", r"^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$", list("tTfF")),
    ("int", r"^(?:0o[0-7]+|[-+]?[0-9]+|0x[0-9a-fA-F]+)$", list("-+0123456789")),
    ("float", r"^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN"
              r"|[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+"
              r"|[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*))$", list("-+.0123456789")),
]:
    _Core.add_implicit_resolver(f"tag:yaml.org,2002:{_tag}", re.compile(_pattern), _first)


def _int(loader, node):
    text = loader.construct_scalar(node)
    value = int(text[2:], 8) if text.startswith("0o") else int(text[2:], 16) if text.startswith("0x") else int(text)
    if abs(value) <= 2 ** 53:
        return value
    # A JavaScript number is a double: past 2^53 an integer is rounded, past ~1.8e308 it is Infinity.
    try:
        return float(value)
    except OverflowError:
        return -math.inf if value < 0 else math.inf


def _float(loader, node):
    text = loader.construct_scalar(node)
    if text.lstrip("+-").lower() == ".inf":
        return -math.inf if text.startswith("-") else math.inf
    return math.nan if text.lower() == ".nan" else float(text)


_Core.add_constructor("tag:yaml.org,2002:int", _int)
_Core.add_constructor("tag:yaml.org,2002:float", _float)
_Core.add_constructor("tag:yaml.org,2002:bool", lambda loader, node: loader.construct_scalar(node).lower() == "true")


def js_string(value) -> str:
    """A value as JavaScript's String() writes it: an object key, a uniqueItems index, a value in a
    message."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and abs(value) <= 2 ** 53:
        return str(value)
    if isinstance(value, (int, float)):
        return _js_number(float(value))
    if isinstance(value, list):
        # Array.prototype.join: null is empty there.
        return ",".join("" if item is None else js_string(item) for item in value)
    if isinstance(value, dict):
        return "[object Object]"
    return str(value)


def _js_number(value: float) -> str:
    """Number.prototype.toString: the shortest digits that read back, which Python's repr finds
    too, laid out by ECMAScript's rule — plainly from 1e-6 to below 1e21, with an exponent outside."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    _, digits, exponent = Decimal(repr(abs(value))).normalize().as_tuple()
    digits = "".join(map(str, digits))
    k, n = len(digits), len(digits) + exponent  # the value is 0.<digits> × 10^n
    sign = "-" if value < 0 else ""
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * -n + digits
    return sign + digits[0] + ("." + digits[1:] if k > 1 else "") + f"e{'+' if n > 0 else '-'}{abs(n - 1)}"


def _plain(value):
    """Mappings with string keys, as a JavaScript object has them."""
    if isinstance(value, dict):
        return {("" if key is None else js_string(key)): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def load(text: str):
    """The front matter as the twin's YAML parser gives it."""
    return _plain(yaml.load(text, Loader=_Core))


# ── The schema ────────────────────────────────────────────────────────────────────────────────
#
# Ajv's order (8.x, lib/compile/validate): the type, unless a group below carries it; the keywords
# that apply to any value; then those of numbers, strings, arrays and objects, each group in the
# order Ajv registers its keywords — `items` before `uniqueItems`, `additionalProperties` before
# `properties`.

ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "default", "examples"}
ANY = ["const", "enum", "not", "anyOf", "oneOf", "allOf", "if"]
GROUPS = {
    "number": ["maximum", "minimum", "exclusiveMaximum", "exclusiveMinimum", "format"],
    "string": ["maxLength", "minLength", "pattern", "format"],
    "array": ["maxItems", "minItems", "items", "uniqueItems"],
    "object": ["maxProperties", "minProperties", "required", "additionalProperties", "properties"],
}
KNOWN = ANNOTATIONS | {"type", "then", "else"} | set(ANY) | {k for group in GROUPS.values() for k in group}
LIMITS = {  # keyword: (what holds, whether a value breaks it)
    "maximum": ("<=", lambda value, limit: value > limit),
    "minimum": (">=", lambda value, limit: value < limit),
    "exclusiveMaximum": ("<", lambda value, limit: value >= limit),
    "exclusiveMinimum": (">", lambda value, limit: value <= limit),
}
DAYS = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})\Z")
_INDEX = re.compile(r"0|[1-9][0-9]*")
_schemas: dict = {}
_patterns: dict = {}


def messages(name: str, data) -> list[str]:
    """What `schema/<name>` says of `data`, one message per Ajv error: `<instance path> <message>`."""
    if name not in _schemas:
        with open(os.path.join(SCHEMA_DIR, name), encoding="utf-8") as f:
            schema = json.load(f)
        _refuse_unknown(schema, name)
        _schemas[name] = schema
    out: list = []
    _check(_schemas[name], data, "", out)
    return [f"{path or '/'} {message}" for path, message in out]


def _refuse_unknown(schema, where: str) -> None:
    if isinstance(schema, bool):
        return
    for key, value in schema.items():
        if key not in KNOWN:
            raise SchemaRefused(f"{where}: `{key}` is a keyword this prototype does not implement")
        if key == "properties":
            for name, sub in value.items():
                _refuse_unknown(sub, f"{where}/properties/{name}")
        elif key in ("items", "additionalProperties", "not", "if", "then", "else"):
            _refuse_unknown(value, f"{where}/{key}")
        elif key in ("anyOf", "oneOf", "allOf"):
            for index, sub in enumerate(value):
                _refuse_unknown(sub, f"{where}/{key}/{index}")
        elif key == "format" and value != "date":
            raise SchemaRefused(f"{where}: format `{value}` is not implemented")
        elif key == "pattern":
            _regex(value)
        elif key == "type" and not set([value] if isinstance(value, str) else value) <= set(GROUPS) | {"integer", "boolean", "null"}:
            raise SchemaRefused(f"{where}: type `{value}` is not a JSON type")


def _regex(source: str):
    """A schema pattern read as JavaScript reads it: `$` ends the text, where Python's `$` also
    matches before a final line break. Classes that differ between the two are refused."""
    if source not in _patterns:
        if re.search(r"\\[dDwWsSbBpPuk]|\(\?<|\[\^?\]", source):
            raise SchemaRefused(f"pattern `{source}` uses a class this prototype does not translate")
        out, index, in_class = [], 0, False
        while index < len(source):
            ch = source[index]
            if ch == "\\":
                out.append(source[index:index + 2])
                index += 2
                continue
            if in_class:
                in_class = ch != "]"
            elif ch == "[":
                in_class = True
            elif ch == "$":
                ch = r"\Z"
            out.append(ch)
            index += 1
        _patterns[source] = re.compile("".join(out))
    return _patterns[source]


def _is(kind: str, value) -> bool:
    """JavaScript's view of a value's type, as Ajv tests it."""
    if kind == "null":
        return value is None
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str)
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, dict)
    number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "number":
        return number
    # `!(x % 1) && !isNaN(x)`: Infinity % 1 is NaN, so Infinity counts as an integer there.
    return number and not math.isnan(value) and (math.isinf(value) or value % 1 == 0)


def _number(value) -> str:
    """A number from the schema, as Ajv's message writes it."""
    return js_string(value)


def _equal(a, b) -> bool:
    """Equality as Ajv's deep equal has it: a boolean is not a number, NaN equals NaN."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if a is None or b is None:
        return a is None and b is None
    if _is("number", a) or _is("number", b):
        return _is("number", a) and _is("number", b) and (a == b or (a != a and b != b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return len(a) == len(b) and all(key in b and _equal(item, b[key]) for key, item in a.items())
    return type(a) is type(b) and a == b


def _keys(data: dict) -> list[str]:
    """An object's keys in JavaScript's order: array indices first, ascending, then the rest."""
    indices = sorted((key for key in data if _INDEX.fullmatch(key) and int(key) < 2**32 - 1), key=int)
    taken = set(indices)
    return indices + [key for key in data if key not in taken]


def _at(path: str, key) -> str:
    return f"{path}/{str(key).replace('~', '~0').replace('/', '~1')}"


def _types(schema: dict) -> list[str]:
    declared = schema.get("type")
    return [] if declared is None else [declared] if isinstance(declared, str) else list(declared)


def _type_error(schema: dict) -> str:
    declared = schema["type"]
    return f"must be {declared if isinstance(declared, str) else ','.join(declared)}"


def _check(schema, data, path: str, out: list) -> None:
    if schema is True:
        return
    if schema is False:
        out.append((path, "boolean schema is false"))
        return
    types = _types(schema)
    # One type whose group has keywords here is checked with that group; any other type first.
    deferred = len(types) == 1 and types[0] in GROUPS and any(k in schema for k in GROUPS[types[0]])
    if types and not deferred and not any(_is(kind, data) for kind in types):
        out.append((path, _type_error(schema)))
    for keyword in ANY:
        if keyword in schema:
            KEYWORDS[keyword](schema, data, path, out)
    for group, keywords in GROUPS.items():
        present = [keyword for keyword in keywords if keyword in schema]
        if not present:
            continue
        if _is(group, data):
            for keyword in present:
                KEYWORDS[keyword](schema, data, path, out)
        elif deferred and types[0] == group:
            out.append((path, _type_error(schema)))


def _valid(schema, data, path: str) -> bool:
    found: list = []
    _check(schema, data, path, found)
    return not found


def _union(schemas: list, data, path: str, out: list, holds, message: str, stop: int) -> None:
    """anyOf and oneOf: the branches' errors stay only if the keyword fails. oneOf stops at its
    second passing branch, as Ajv's code does (each branch runs in the `else` of the one before);
    anyOf stops at its first, which errs only when none passes."""
    start = len(out)
    passing = 0
    for sub in schemas:
        before = len(out)
        _check(sub, data, path, out)
        passing += len(out) == before
        if passing == stop:
            break
    if holds(passing):
        del out[start:]
    else:
        out.append((path, message))


def _if(schema, data, path, out):
    clause = "then" if _valid(schema["if"], data, path) else "else"
    if clause in schema:
        before = len(out)
        _check(schema[clause], data, path, out)
        if len(out) > before:
            out.append((path, f'must match "{clause}" schema'))


def _limit(keyword):
    holds, breaks = LIMITS[keyword]
    # `x > limit || isNaN(x)`: NaN breaks every limit there, where every comparison with it is false.
    return lambda schema, data, path, out: (breaks(data, schema[keyword]) or isinstance(data, float) and math.isnan(data)) and out.append(
        (path, f"must be {holds} {_number(schema[keyword])}"))


def _count(keyword, measure, noun):
    more = keyword.startswith("max")
    def check(schema, data, path, out):
        size, limit = measure(data), schema[keyword]
        if size > limit if more else size < limit:
            out.append((path, f"must NOT have {'more' if more else 'fewer'} than {_number(limit)} {noun}"))
    return check


def _pattern(schema, data, path, out):
    if not _regex(schema["pattern"]).search(data):
        out.append((path, f'must match pattern "{schema["pattern"]}"'))


def _format(schema, data, path, out):
    if not isinstance(data, str):
        return  # `date` is a format of strings; Ajv leaves numbers to it alone
    match = _DATE.match(data)
    if match:
        year, month, day = map(int, match.groups())
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        if 1 <= month <= 12 and 1 <= day <= (29 if month == 2 and leap else DAYS[month]):
            return
    out.append((path, f'must match format "{schema["format"]}"'))


def _items(schema, data, path, out):
    for index, item in enumerate(data):
        _check(schema["items"], item, _at(path, index), out)


def _unique(schema, data, path, out):
    """The first pair Ajv finds, walking from the end: by key when the items have a simple type,
    by deep equality otherwise — and the two walks name the pair in different orders."""
    if schema["uniqueItems"] is not True or len(data) <= 1:
        return
    items = schema.get("items")
    kinds = _types(items) if isinstance(items, dict) else []
    if kinds and not {"object", "array"} & set(kinds):
        seen: dict = {}
        for i in range(len(data) - 1, -1, -1):
            item = data[i]
            if not any(_is(kind, item) for kind in kinds):
                continue
            key = js_string(item) + ("_" if len(kinds) > 1 and isinstance(item, str) else "")
            if key == "__proto__":
                continue  # an object's prototype, never a number there
            if key in seen:
                out.append((path, f"must NOT have duplicate items (items ## {seen[key]} and {i} are identical)"))
                return
            seen[key] = i
        return
    for i in range(len(data) - 1, -1, -1):
        for j in range(i - 1, -1, -1):
            if _equal(data[i], data[j]):
                out.append((path, f"must NOT have duplicate items (items ## {j} and {i} are identical)"))
                return


def _required(schema, data, path, out):
    for name in schema["required"]:
        if name not in data:
            out.append((path, f"must have required property '{name}'"))


def _additional(schema, data, path, out):
    extra = schema["additionalProperties"]
    if extra is True:
        return
    named = schema.get("properties") or {}
    for key in _keys(data):
        if key in named and key != "__proto__":
            continue
        if extra is False:
            out.append((path, "must NOT have additional properties"))
        else:
            _check(extra, data[key], _at(path, key), out)


def _properties(schema, data, path, out):
    for name, sub in schema["properties"].items():
        if name in data and name != "__proto__":
            _check(sub, data[name], _at(path, name), out)


KEYWORDS = {
    "const": lambda s, d, p, out: _equal(d, s["const"]) or out.append((p, "must be equal to constant")),
    "enum": lambda s, d, p, out: any(_equal(d, v) for v in s["enum"]) or out.append(
        (p, "must be equal to one of the allowed values")),
    "not": lambda s, d, p, out: _valid(s["not"], d, p) and out.append((p, "must NOT be valid")),
    "anyOf": lambda s, d, p, out: _union(s["anyOf"], d, p, out, lambda n: n > 0, "must match a schema in anyOf", 1),
    "oneOf": lambda s, d, p, out: _union(s["oneOf"], d, p, out, lambda n: n == 1,
                                         "must match exactly one schema in oneOf", 2),
    "allOf": lambda s, d, p, out: [_check(sub, d, p, out) for sub in s["allOf"]],
    "if": _if,
    **{keyword: _limit(keyword) for keyword in LIMITS},
    "format": _format,
    "maxLength": _count("maxLength", len, "characters"),
    "minLength": _count("minLength", len, "characters"),
    "pattern": _pattern,
    "maxItems": _count("maxItems", len, "items"),
    "minItems": _count("minItems", len, "items"),
    "items": _items,
    "uniqueItems": _unique,
    "maxProperties": _count("maxProperties", len, "properties"),
    "minProperties": _count("minProperties", len, "properties"),
    "required": _required,
    "additionalProperties": _additional,
    "properties": _properties,
}
