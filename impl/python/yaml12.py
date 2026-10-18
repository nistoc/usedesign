"""YAML as the TypeScript twin reads it: the parse path of the `yaml` package, 2.9.0, in Python (1.6.0).

The twin reads front matter, configs and manifests with `yaml` (YAML 1.2, core schema); this
prototype read them with PyYAML, a YAML 1.1 parser with a 1.2 schema laid over it. The two
parsers disagree on the text itself: a tab after a colon, U+2028 and NEL inside a plain scalar,
an empty line inside double quotes, a file whose lines end in CR alone — one of them reads what
the other refuses — and where both refuse, they say it in different words. Each disagreement is
a card one implementation passes and the other does not, the defect this project exists to catch.

So this module is not a YAML parser of its own: it is the twin's, line for line — the lexer, the
parser of the concrete syntax tree, the composer, the conversion to plain values, the error
messages with their line and column. Positions count UTF-16 code units, as JavaScript does: the
text is taken apart into them on the way in and put back together on the way out. The twin pins
`yaml` to 2.9.0, the version ported here; a new version is a new port, read against this one.

What both implementations add to the package, in the same words (`readYaml.ts` in the twin):
collections nested deeper than `MAX_DEPTH` levels, a collection used as a map key, an alias
inside the node it names and a string with half of a surrogate pair in it are refused. The
package itself overflows the stack on the first, where the stack runs out — a different place in
each runtime — writes the second as YAML text, returns a value that contains itself for the
third, and keeps the fourth, which JavaScript prints as U+FFFD and Python cannot hold in a string
it prints.

Ported from yaml 2.9.0 (https://github.com/eemeli/yaml), under the ISC License:

    Copyright Eemeli Aro <eemeli@gmail.com>

    Permission to use, copy, modify, and/or distribute this software for any purpose
    with or without fee is hereby granted, provided that the above copyright notice
    and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
    REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
    FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
    INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
    OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
    TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
    THIS SOFTWARE.
"""
from __future__ import annotations

import math
import re

from json_schema import js_string

MAX_DEPTH = 64
DEEP = f"Collections are nested deeper than {MAX_DEPTH} levels"


class YAMLError(Exception):
    """What the twin's parser throws: its message, the first line of which both implementations
    print. A position of `None` is an error the package throws without one (an alias)."""

    def __init__(self, pos, code, message):
        super().__init__(message)
        self.pos = pos
        self.code = code
        self.message = message

    def __str__(self):
        return self.message


def first_line(error) -> str:
    """The first line of an error's message, as the twin cuts it: at a line feed only, where
    `splitlines()` also cuts at CR, U+2028, NEL and others a message can quote."""
    return str(error).split("\n")[0]


def load(text: str):
    """The value of a YAML document, as the twin's `readYaml` returns it, in Python's types: a map
    is a dict with text keys in the order a JavaScript object keeps them, an integer an int up to
    2^53 and a float past it, every other number a float."""
    doc, src, lc = _document(text)
    if doc.errors:
        raise doc.errors[0]
    _rules(doc, src, lc)
    return _to_js(doc.contents, _ToJS(doc))


# ── JavaScript strings ────────────────────────────────────────────────────────────────────────
#
# Inside this module a string is a JavaScript string: a sequence of UTF-16 code units, a
# character outside the BMP two of them. Offsets, columns, lengths and slices then count what the
# twin counts.

_ASTRAL = re.compile("[\U00010000-\U0010FFFF]")
_SURROGATE = re.compile("[\ud800-\udfff]")


def _to16(text: str) -> str:
    def pair(match):
        code = ord(match.group()) - 0x10000
        return chr(0xD800 + (code >> 10)) + chr(0xDC00 + (code & 0x3FF))
    return _ASTRAL.sub(pair, text)


def _from16(text: str) -> str:
    """Characters again: a surrogate pair is one, a lone surrogate U+FFFD, as Node writes it out."""
    if not _SURROGATE.search(text):
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _at(s, i):
    """`s[i]` as JavaScript reads it: `undefined` (None) outside the string, on either side."""
    return s[i] if 0 <= i < len(s) else None


def _substring(s, start, end=None):
    """`String.prototype.substring`: bounds clamped to the string, swapped when reversed."""
    n = len(s)
    a = 0 if start is None else min(max(start, 0), n)
    b = n if end is None else min(max(end, 0), n)
    return s[a:b] if a <= b else s[b:a]


JS_SPACE = ("\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008"
             "\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff")


def js_trim(s: str) -> str:
    """`String.prototype.trim`: JavaScript's white space and line terminators, not Python's."""
    return s.strip(JS_SPACE)


_JSON_ESCAPES = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def _json_string(s: str) -> str:
    """`JSON.stringify` of a string of code units, a lone surrogate escaped."""
    out = ['"']
    n = len(s)
    for i, ch in enumerate(s):
        c = ord(ch)
        if ch in _JSON_ESCAPES:
            out.append(_JSON_ESCAPES[ch])
        elif c < 0x20:
            out.append("\\u%04x" % c)
        elif 0xD800 <= c <= 0xDBFF:
            out.append(ch if i + 1 < n and 0xDC00 <= ord(s[i + 1]) <= 0xDFFF else "\\u%04x" % c)
        elif 0xDC00 <= c <= 0xDFFF:
            out.append(ch if i > 0 and 0xD800 <= ord(s[i - 1]) <= 0xDBFF else "\\u%04x" % c)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _from_code_point(code: int) -> str:
    if code > 0xFFFF:
        code -= 0x10000
        return chr(0xD800 + (code >> 10)) + chr(0xDC00 + (code & 0x3FF))
    return chr(code)


class _URIError(Exception):
    pass


_HEX = set("0123456789abcdefABCDEF")


def _decode_uri_component(s: str) -> str:
    """`decodeURIComponent`, the twin's reading of a tag's suffix: every %XX escape, UTF-8 checked."""
    out = []
    k = 0
    n = len(s)
    while k < n:
        c = s[k]
        if c != "%":
            out.append(c)
            k += 1
            continue
        if k + 2 >= n or s[k + 1] not in _HEX or s[k + 2] not in _HEX:
            raise _URIError()
        b = int(s[k + 1:k + 3], 16)
        k += 2
        if b & 0x80 == 0:
            out.append(chr(b))
        else:
            count = 0
            while (b << count) & 0x80:
                count += 1
            if count == 1 or count > 4:
                raise _URIError()
            octets = [b]
            if k + 3 * (count - 1) >= n:
                raise _URIError()
            for _ in range(count - 1):
                k += 1
                if s[k] != "%" or s[k + 1] not in _HEX or s[k + 2] not in _HEX:
                    raise _URIError()
                b = int(s[k + 1:k + 3], 16)
                if b & 0xC0 != 0x80:
                    raise _URIError()
                k += 2
                octets.append(b)
            try:
                out.append(_to16(bytes(octets).decode("utf-8")))
            except UnicodeDecodeError:
                raise _URIError() from None
        k += 1
    return "".join(out)


# ── Lexer (parse/lexer.js) ────────────────────────────────────────────────────────────────────
#
# Always run on the whole input at once (`incomplete` false): the branches that wait for more
# input never fire and are left out.

BOM = "\ufeff"
DOCUMENT = "\x02"
FLOW_END = "\x18"
SCALAR = "\x1f"

_FLOW_INDICATORS = set(",[]{}")
_INVALID_ANCHOR = set(" ,[]{}\n\r\t")
_TAG_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-#;/?:@&=+$_.!~*'()")


def _is_empty(ch):
    return ch is None or ch in (" ", "\n", "\r", "\t")


def _is_not_anchor_char(ch):
    return not ch or ch in _INVALID_ANCHOR


class _Lexer:
    def __init__(self):
        self.block_scalar_indent = -1
        self.block_scalar_keep = False
        self.buffer = ""
        self.flow_key = False
        self.flow_level = 0
        self.indent_next = 0
        self.indent_value = 0
        self.line_end_pos = None
        self.pos = 0
        self.out = []

    def lex(self, source):
        self.buffer = source
        state = "stream"
        while state and self.pos + 1 <= len(self.buffer):
            state = self.parse_next(state)
        return self.out

    def at_line_end(self):
        b = self.buffer
        i = self.pos
        ch = _at(b, i)
        while ch == " " or ch == "\t":
            i += 1
            ch = _at(b, i)
        if not ch or ch == "#" or ch == "\n":
            return True
        if ch == "\r":
            return _at(b, i + 1) == "\n"
        return False

    def char_at(self, n):
        return _at(self.buffer, self.pos + n)

    def continue_scalar(self, offset):
        b = self.buffer
        ch = _at(b, offset)
        if self.indent_next > 0:
            indent = 0
            while ch == " ":
                indent += 1
                ch = _at(b, indent + offset)
            if ch == "\r":
                nxt = _at(b, indent + offset + 1)
                if nxt == "\n":
                    return offset + indent + 1
            return offset + indent if (ch == "\n" or indent >= self.indent_next) else -1
        if ch == "-" or ch == ".":
            dt = b[offset:offset + 3]
            if (dt == "---" or dt == "...") and _is_empty(_at(b, offset + 3)):
                return -1
        return offset

    def get_line(self):
        end = self.line_end_pos
        if end is None or (end != -1 and end < self.pos):
            end = self.buffer.find("\n", self.pos)
            self.line_end_pos = end
        if end == -1:
            return self.buffer[self.pos:]
        if _at(self.buffer, end - 1) == "\r":
            end -= 1
        return _substring(self.buffer, self.pos, end)

    def peek(self, n):
        return self.buffer[self.pos:self.pos + n]

    def parse_next(self, state):
        if state == "stream":
            return self.parse_stream()
        if state == "line-start":
            return self.parse_line_start()
        if state == "block-start":
            return self.parse_block_start()
        if state == "doc":
            return self.parse_document()
        if state == "flow":
            return self.parse_flow_collection()
        if state == "quoted-scalar":
            return self.parse_quoted_scalar()
        if state == "block-scalar":
            return self.parse_block_scalar()
        if state == "plain-scalar":
            return self.parse_plain_scalar()
        return None

    def parse_stream(self):
        line = self.get_line()
        if line[:1] == BOM:
            self.push_count(1)
            line = line[1:]
        if line[:1] == "%":
            dir_end = len(line)
            cs = line.find("#")
            while cs != -1:
                ch = _at(line, cs - 1)
                if ch == " " or ch == "\t":
                    dir_end = cs - 1
                    break
                cs = line.find("#", cs + 1)
            while True:
                ch = _at(line, dir_end - 1)
                if ch == " " or ch == "\t":
                    dir_end -= 1
                else:
                    break
            n = self.push_count(dir_end) + self.push_spaces(True)
            self.push_count(len(line) - n)  # possible comment
            # The twin calls pushNewline() here without `yield*`: a generator never run pushes
            # nothing, and the newline is the next line's business.
            return "stream"
        if self.at_line_end():
            sp = self.push_spaces(True)
            self.push_count(len(line) - sp)
            self.push_newline()
            return "stream"
        self.out.append(DOCUMENT)
        return self.parse_line_start()

    def parse_line_start(self):
        ch = self.char_at(0)
        if ch == "-" or ch == ".":
            s = self.peek(3)
            if (s == "---" or s == "...") and _is_empty(self.char_at(3)):
                self.push_count(3)
                self.indent_value = 0
                self.indent_next = 0
                return "doc" if s == "---" else "stream"
        self.indent_value = self.push_spaces(False)
        if self.indent_next > self.indent_value and not _is_empty(self.char_at(1)):
            self.indent_next = self.indent_value
        return self.parse_block_start()

    def parse_block_start(self):
        ch0 = self.char_at(0)
        ch1 = self.char_at(1)
        if (ch0 == "-" or ch0 == "?" or ch0 == ":") and _is_empty(ch1):
            n = self.push_count(1) + self.push_spaces(True)
            self.indent_next = self.indent_value + 1
            self.indent_value += n
            return "block-start"
        return "doc"

    def parse_document(self):
        self.push_spaces(True)
        line = self.get_line()
        n = self.push_indicators()
        c = _at(line, n)
        if c == "#" or c is None:
            if c == "#":
                self.push_count(len(line) - n)
            self.push_newline()
            return self.parse_line_start()
        if c == "{" or c == "[":
            self.push_count(1)
            self.flow_key = False
            self.flow_level = 1
            return "flow"
        if c == "}" or c == "]":
            self.push_count(1)  # this is an error
            return "doc"
        if c == "*":
            self.push_until(_is_not_anchor_char)
            return "doc"
        if c == '"' or c == "'":
            return self.parse_quoted_scalar()
        if c == "|" or c == ">":
            n += self.parse_block_scalar_header()
            n += self.push_spaces(True)
            self.push_count(len(line) - n)
            self.push_newline()
            return self.parse_block_scalar()
        return self.parse_plain_scalar()

    def parse_flow_collection(self):
        indent = -1
        while True:
            nl = self.push_newline()
            if nl > 0:
                sp = self.push_spaces(False)
                self.indent_value = indent = sp
            else:
                sp = 0
            sp += self.push_spaces(True)
            if nl + sp <= 0:
                break
        line = self.get_line()
        if ((indent != -1 and indent < self.indent_next and _at(line, 0) != "#") or
                (indent == 0 and (line.startswith("---") or line.startswith("...")) and _is_empty(_at(line, 3)))):
            # Allowing for the terminal ] or } at the same (rather than greater) indent level as
            # the initial [ or { is technically invalid, but failing here would be surprising.
            at_flow_end_marker = (indent == self.indent_next - 1 and self.flow_level == 1 and
                                  (_at(line, 0) == "]" or _at(line, 0) == "}"))
            if not at_flow_end_marker:
                self.flow_level = 0  # this is an error
                self.out.append(FLOW_END)
                return self.parse_line_start()
        n = 0
        while _at(line, n) == ",":
            n += self.push_count(1)
            n += self.push_spaces(True)
            self.flow_key = False
        n += self.push_indicators()
        c = _at(line, n)
        if c is None:
            return "flow"
        if c == "#":
            self.push_count(len(line) - n)
            return "flow"
        if c == "{" or c == "[":
            self.push_count(1)
            self.flow_key = False
            self.flow_level += 1
            return "flow"
        if c == "}" or c == "]":
            self.push_count(1)
            self.flow_key = True
            self.flow_level -= 1
            return "flow" if self.flow_level else "doc"
        if c == "*":
            self.push_until(_is_not_anchor_char)
            return "flow"
        if c == '"' or c == "'":
            self.flow_key = True
            return self.parse_quoted_scalar()
        if c == ":":
            nxt = self.char_at(1)
            if self.flow_key or _is_empty(nxt) or nxt == ",":
                self.flow_key = False
                self.push_count(1)
                self.push_spaces(True)
                return "flow"
        self.flow_key = False
        return self.parse_plain_scalar()

    def parse_quoted_scalar(self):
        b = self.buffer
        quote = self.char_at(0)
        end = b.find(quote, self.pos + 1)
        if quote == "'":
            while end != -1 and _at(b, end + 1) == "'":
                end = b.find("'", end + 2)
        else:
            while end != -1:  # double-quote
                n = 0
                while _at(b, end - 1 - n) == "\\":
                    n += 1
                if n % 2 == 0:
                    break
                end = b.find('"', end + 1)
        # Only looking for newlines within the quotes; `substring(0, -1)` is empty.
        qb = b[:end] if end >= 0 else ""
        nl = qb.find("\n", self.pos)
        if nl != -1:
            while nl != -1:
                cs = self.continue_scalar(nl + 1)
                if cs == -1:
                    break
                nl = qb.find("\n", cs)
            if nl != -1:
                # this is an error caused by an unexpected unindent
                end = nl - (2 if _at(qb, nl - 1) == "\r" else 1)
        if end == -1:
            end = len(b)
        self.push_to_index(end + 1, False)
        return "flow" if self.flow_level else "doc"

    def parse_block_scalar_header(self):
        self.block_scalar_indent = -1
        self.block_scalar_keep = False
        i = self.pos
        while True:
            i += 1
            ch = _at(self.buffer, i)
            if ch == "+":
                self.block_scalar_keep = True
            elif ch is not None and "0" < ch <= "9":
                self.block_scalar_indent = int(ch) - 1
            elif ch != "-":
                break
        return self.push_until(lambda ch: _is_empty(ch) or ch == "#")

    def parse_block_scalar(self):
        b = self.buffer
        nl = self.pos - 1  # may be -1 if self.pos == 0
        indent = 0
        i = self.pos
        ch = _at(b, i)
        while ch:
            if ch == " ":
                indent += 1
            elif ch == "\n":
                nl = i
                indent = 0
            elif ch == "\r" and _at(b, i + 1) == "\n":
                pass
            else:
                break
            i += 1
            ch = _at(b, i)
        if indent >= self.indent_next:
            if self.block_scalar_indent == -1:
                self.indent_next = indent
            else:
                self.indent_next = self.block_scalar_indent + (1 if self.indent_next == 0 else self.indent_next)
            while True:
                cs = self.continue_scalar(nl + 1)
                if cs == -1:
                    break
                nl = b.find("\n", cs)
                if nl == -1:
                    break
            if nl == -1:
                nl = len(b)
        # Trailing insufficiently indented tabs are invalid. To catch that during parsing, they
        # are included in the block scalar value.
        i = nl + 1
        ch = _at(b, i)
        while ch == " ":
            i += 1
            ch = _at(b, i)
        if ch == "\t":
            while ch == "\t" or ch == " " or ch == "\r" or ch == "\n":
                i += 1
                ch = _at(b, i)
            nl = i - 1
        elif not self.block_scalar_keep:
            while True:
                j = nl - 1
                c = _at(b, j)
                if c == "\r":
                    j -= 1
                    c = _at(b, j)
                last_char = j  # Drop the line if last char not more indented
                while c == " ":
                    j -= 1
                    c = _at(b, j)
                if c == "\n" and j >= self.pos and j + 1 + indent > last_char:
                    nl = j
                else:
                    break
        self.out.append(SCALAR)
        self.push_to_index(nl + 1, True)
        return self.parse_line_start()

    def parse_plain_scalar(self):
        b = self.buffer
        in_flow = self.flow_level > 0
        end = self.pos - 1
        i = self.pos - 1
        while True:
            i += 1
            ch = _at(b, i)
            if not ch:
                break
            if ch == ":":
                nxt = _at(b, i + 1)
                if _is_empty(nxt) or (in_flow and nxt in _FLOW_INDICATORS):
                    break
                end = i
            elif _is_empty(ch):
                nxt = _at(b, i + 1)
                if ch == "\r":
                    if nxt == "\n":
                        i += 1
                        ch = "\n"
                        nxt = _at(b, i + 1)
                    else:
                        end = i
                if nxt == "#" or (in_flow and nxt in _FLOW_INDICATORS):
                    break
                if ch == "\n":
                    cs = self.continue_scalar(i + 1)
                    if cs == -1:
                        break
                    i = max(i, cs - 2)  # to advance, but still account for ' #'
            else:
                if in_flow and ch in _FLOW_INDICATORS:
                    break
                end = i
        self.out.append(SCALAR)
        self.push_to_index(end + 1, True)
        return "flow" if in_flow else "doc"

    def push_count(self, n):
        if n > 0:
            self.out.append(self.buffer[self.pos:self.pos + n])
            self.pos += n
            return n
        return 0

    def push_to_index(self, i, allow_empty):
        s = self.buffer[self.pos:i]
        if s:
            self.out.append(s)
            self.pos += len(s)
            return len(s)
        if allow_empty:
            self.out.append("")
        return 0

    def push_indicators(self):
        n = 0
        while True:
            c = self.char_at(0)
            if c == "!":
                n += self.push_tag()
                n += self.push_spaces(True)
                continue
            if c == "&":
                n += self.push_until(_is_not_anchor_char)
                n += self.push_spaces(True)
                continue
            if c == "-" or c == "?" or c == ":":  # `-` is an error, `?` one outside flow collections
                in_flow = self.flow_level > 0
                ch1 = self.char_at(1)
                if _is_empty(ch1) or (in_flow and ch1 in _FLOW_INDICATORS):
                    if not in_flow:
                        self.indent_next = self.indent_value + 1
                    elif self.flow_key:
                        self.flow_key = False
                    n += self.push_count(1)
                    n += self.push_spaces(True)
                    continue
            return n

    def push_tag(self):
        b = self.buffer
        if self.char_at(1) == "<":
            i = self.pos + 2
            ch = _at(b, i)
            while not _is_empty(ch) and ch != ">":
                i += 1
                ch = _at(b, i)
            return self.push_to_index(i + 1 if ch == ">" else i, False)
        i = self.pos + 1
        ch = _at(b, i)
        while ch:
            if ch in _TAG_CHARS:
                i += 1
                ch = _at(b, i)
            elif ch == "%" and _at(b, i + 1) in _HEX and _at(b, i + 2) in _HEX:
                i += 3
                ch = _at(b, i)
            else:
                break
        return self.push_to_index(i, False)

    def push_newline(self):
        ch = _at(self.buffer, self.pos)
        if ch == "\n":
            return self.push_count(1)
        if ch == "\r" and self.char_at(1) == "\n":
            return self.push_count(2)
        return 0

    def push_spaces(self, allow_tabs):
        b = self.buffer
        i = self.pos
        ch = _at(b, i)
        while ch == " " or (allow_tabs and ch == "\t"):
            i += 1
            ch = _at(b, i)
        n = i - self.pos
        if n > 0:
            self.out.append(b[self.pos:i])
            self.pos = i
        return n

    def push_until(self, test):
        b = self.buffer
        i = self.pos
        ch = _at(b, i)
        while not test(ch):
            i += 1
            ch = _at(b, i)
        return self.push_to_index(i, False)


# ── Parser (parse/parser.js, parse/cst.js) ────────────────────────────────────────────────────
#
# Tokens are dicts with the twin's property names; a property the twin deletes is deleted here,
# and one it tests for truth — an array is true even when empty — is tested for presence. Where
# the twin ends a handler with `pop(); step()` it re-enters `step()` from the top; here the
# handler returns True and `step()` loops, so that closing a deep nesting at once costs no stack.


def _token_type(source):
    if source == BOM:
        return "byte-order-mark"
    if source == DOCUMENT:
        return "doc-mode"
    if source == FLOW_END:
        return "flow-error-end"
    if source == SCALAR:
        return "scalar"
    simple = _SIMPLE_TOKENS.get(source)
    if simple:
        return simple
    return _FIRST_CHAR_TOKENS.get(source[:1])


_SIMPLE_TOKENS = {"---": "doc-start", "...": "doc-end", "": "newline", "\n": "newline", "\r\n": "newline",
                  "-": "seq-item-ind", "?": "explicit-key-ind", ":": "map-value-ind", "{": "flow-map-start",
                  "}": "flow-map-end", "[": "flow-seq-start", "]": "flow-seq-end", ",": "comma"}
_FIRST_CHAR_TOKENS = {" ": "space", "\t": "space", "#": "comment", "%": "directive-line", "*": "alias",
                      "&": "anchor", "!": "tag", "'": "single-quoted-scalar", '"': "double-quoted-scalar",
                      "|": "block-scalar-header", ">": "block-scalar-header"}
_FLOW_SCALARS = ("alias", "scalar", "single-quoted-scalar", "double-quoted-scalar")


def _includes_token(tokens, type_):
    return any(t["type"] == type_ for t in tokens)


def _find_non_empty_index(tokens):
    for i, t in enumerate(tokens):
        if t["type"] not in ("space", "comment", "newline"):
            return i
    return -1


def _is_flow_token(token):
    return token is not None and token["type"] in ("alias", "scalar", "single-quoted-scalar",
                                                   "double-quoted-scalar", "flow-collection")


def _get_prev_props(parent):
    t = parent["type"]
    if t == "document":
        return parent["start"]
    if t == "block-map":
        it = parent["items"][-1]
        return it["sep"] if it.get("sep") is not None else it["start"]
    if t == "block-seq":
        return parent["items"][-1]["start"]
    return []


def _get_first_key_start_props(prev):
    """Note: may modify the input list."""
    if not prev:
        return []
    i = len(prev) - 1
    while i >= 0:
        if prev[i]["type"] in ("doc-start", "explicit-key-ind", "map-value-ind", "seq-item-ind", "newline"):
            break
        i -= 1
    i += 1
    while i < len(prev) and prev[i]["type"] == "space":
        i += 1
    res = prev[i:]
    del prev[i:]
    return res


def _fix_flow_seq_items(fc):
    if fc["start"]["type"] == "flow-seq-start":
        for it in fc["items"]:
            if (it.get("sep") is not None and it.get("value") is None and
                    not _includes_token(it["start"], "explicit-key-ind") and
                    not _includes_token(it["sep"], "map-value-ind")):
                if it.get("key") is not None:
                    it["value"] = it["key"]
                it.pop("key", None)
                if _is_flow_token(it.get("value")):
                    value = it["value"]
                    if value.get("end") is not None:
                        value["end"].extend(it["sep"])
                    else:
                        value["end"] = it["sep"]
                else:
                    it["start"].extend(it["sep"])
                del it["sep"]


class _Parser:
    def __init__(self, on_new_line):
        self.at_new_line = True
        self.at_scalar = False
        self.indent = 0
        self.offset = 0
        self.on_key_line = False
        self.stack = []
        self.source = ""
        self.type = ""
        self.on_new_line = on_new_line
        self.out = []

    def parse(self, source):
        self.on_new_line(0)
        for lexeme in _Lexer().lex(source):
            self.next(lexeme)
        while self.stack:
            self.pop()
        return self.out

    def next(self, source):
        self.source = source
        if self.at_scalar:
            self.at_scalar = False
            self.step()
            self.offset += len(source)
            return
        type_ = _token_type(source)
        if not type_:
            message = f"Not a YAML token: {source}"
            self.pop({"type": "error", "offset": self.offset, "message": message, "source": source})
            self.offset += len(source)
        elif type_ == "scalar":
            self.at_new_line = False
            self.at_scalar = True
            self.type = "scalar"
        else:
            self.type = type_
            self.step()
            if type_ == "newline":
                self.at_new_line = True
                self.indent = 0
                self.on_new_line(self.offset + len(source))
            elif type_ == "space":
                if self.at_new_line and source[0] == " ":
                    self.indent += len(source)
            elif type_ in ("explicit-key-ind", "map-value-ind", "seq-item-ind"):
                if self.at_new_line:
                    self.indent += len(source)
            elif type_ in ("doc-mode", "flow-error-end"):
                return
            else:
                self.at_new_line = False
            self.offset += len(source)

    def source_token(self):
        return {"type": self.type, "offset": self.offset, "indent": self.indent, "source": self.source}

    def peek(self, n):
        return self.stack[-n] if len(self.stack) >= n else None

    def step(self):
        while self._step():
            pass

    def _step(self):
        top = self.peek(1)
        if self.type == "doc-end" and (top is None or top["type"] != "doc-end"):
            while self.stack:
                self.pop()
            self.stack.append({"type": "doc-end", "offset": self.offset, "source": self.source})
            return False
        if top is None:
            self.stream()
            return False
        t = top["type"]
        if t == "document":
            return self.document(top)
        if t in _FLOW_SCALARS:
            return self.scalar(top)
        if t == "block-scalar":
            return self.block_scalar(top)
        if t == "block-map":
            return self.block_map(top)
        if t == "block-seq":
            return self.block_sequence(top)
        if t == "flow-collection":
            return self.flow_collection(top)
        if t == "doc-end":
            self.document_end(top)
            return False
        self.pop()  # should not happen
        return False

    def pop(self, error=None):
        token = error if error is not None else (self.stack.pop() if self.stack else None)
        if token is None:
            self.out.append({"type": "error", "offset": self.offset, "source": "",
                             "message": "Tried to pop an empty stack"})
            return
        if not self.stack:
            self.out.append(token)
            return
        top = self.peek(1)
        if token["type"] == "block-scalar":
            # Block scalars use their parent rather than header indent
            token["indent"] = top["indent"] if "indent" in top else 0
        elif token["type"] == "flow-collection" and top["type"] == "document":
            # Ignore all indent for top-level flow collections
            token["indent"] = 0
        if token["type"] == "flow-collection":
            _fix_flow_seq_items(token)
        tt = top["type"]
        if tt == "document":
            top["value"] = token
        elif tt == "block-scalar":
            top["props"].append(token)  # error
        elif tt == "block-map":
            it = top["items"][-1]
            if it.get("value") is not None:
                top["items"].append({"start": [], "key": token, "sep": []})
                self.on_key_line = True
                return
            if it.get("sep") is not None:
                it["value"] = token
            else:
                it["key"] = token
                it["sep"] = []
                self.on_key_line = not it.get("explicitKey")
                return
        elif tt == "block-seq":
            it = top["items"][-1]
            if it.get("value") is not None:
                top["items"].append({"start": [], "value": token})
            else:
                it["value"] = token
        elif tt == "flow-collection":
            it = top["items"][-1] if top["items"] else None
            if it is None or it.get("value") is not None:
                top["items"].append({"start": [], "key": token, "sep": []})
            elif it.get("sep") is not None:
                it["value"] = token
            else:
                it["key"] = token
                it["sep"] = []
            return
        else:  # should not happen
            self.pop()
            self.pop(token)
        if tt in ("document", "block-map", "block-seq") and token["type"] in ("block-map", "block-seq"):
            last = token["items"][-1] if token["items"] else None
            if (last is not None and last.get("sep") is None and last.get("value") is None and
                    len(last["start"]) > 0 and _find_non_empty_index(last["start"]) == -1 and
                    (token["indent"] == 0 or
                     all(st["type"] != "comment" or (st.get("indent") is not None and st["indent"] < token["indent"])
                         for st in last["start"]))):
                if tt == "document":
                    top["end"] = last["start"]
                else:
                    top["items"].append({"start": last["start"]})
                token["items"].pop()

    def stream(self):
        t = self.type
        if t == "directive-line":
            self.out.append({"type": "directive", "offset": self.offset, "source": self.source})
            return
        if t in ("byte-order-mark", "space", "comment", "newline"):
            self.out.append(self.source_token())
            return
        if t in ("doc-mode", "doc-start"):
            doc = {"type": "document", "offset": self.offset, "start": []}
            if t == "doc-start":
                doc["start"].append(self.source_token())
            self.stack.append(doc)
            return
        self.out.append({"type": "error", "offset": self.offset,
                         "message": f"Unexpected {t} token in YAML stream", "source": self.source})

    def document(self, doc):
        if doc.get("value") is not None:
            return self.line_end(doc)
        t = self.type
        if t == "doc-start":
            if _find_non_empty_index(doc["start"]) != -1:
                self.pop()
                return True
            doc["start"].append(self.source_token())
            return False
        if t in ("anchor", "tag", "space", "comment", "newline"):
            doc["start"].append(self.source_token())
            return False
        bv = self.start_block_value(doc)
        if bv is not None:
            self.stack.append(bv)
        else:
            self.out.append({"type": "error", "offset": self.offset,
                             "message": f"Unexpected {t} token in YAML document", "source": self.source})
        return False

    def scalar(self, scalar):
        if self.type == "map-value-ind":
            prev = _get_prev_props(self.peek(2))
            start = _get_first_key_start_props(prev)
            if scalar.get("end") is not None:
                sep = scalar["end"]
                sep.append(self.source_token())
                del scalar["end"]
            else:
                sep = [self.source_token()]
            self.on_key_line = True
            self.stack[-1] = {"type": "block-map", "offset": scalar["offset"], "indent": scalar["indent"],
                              "items": [{"start": start, "key": scalar, "sep": sep}]}
            return False
        return self.line_end(scalar)

    def block_scalar(self, scalar):
        t = self.type
        if t in ("space", "comment", "newline"):
            scalar["props"].append(self.source_token())
            return False
        if t == "scalar":
            scalar["source"] = self.source
            # block-scalar source includes trailing newline
            self.at_new_line = True
            self.indent = 0
            nl = self.source.find("\n") + 1
            while nl != 0:
                self.on_new_line(self.offset + nl)
                nl = self.source.find("\n", nl) + 1
            self.pop()
            return False
        self.pop()  # should not happen
        return True

    def block_map(self, m):
        it = m["items"][-1]
        t = self.type
        # it["sep"] is present if the pair already has a key or a : separator
        if t == "newline":
            self.on_key_line = False
            if it.get("value") is not None:
                end = it["value"]["end"] if "end" in it["value"] else None
                last = end[-1] if isinstance(end, list) and end else None
                if last is not None and last["type"] == "comment":
                    end.append(self.source_token())
                else:
                    m["items"].append({"start": [self.source_token()]})
            elif it.get("sep") is not None:
                it["sep"].append(self.source_token())
            else:
                it["start"].append(self.source_token())
            return False
        if t in ("space", "comment"):
            if it.get("value") is not None:
                m["items"].append({"start": [self.source_token()]})
            elif it.get("sep") is not None:
                it["sep"].append(self.source_token())
            else:
                if self.at_indented_comment(it["start"], m["indent"]):
                    prev = m["items"][-2] if len(m["items"]) >= 2 else None
                    pv = prev.get("value") if prev is not None else None
                    end = pv.get("end") if pv is not None else None
                    if isinstance(end, list):
                        end.extend(it["start"])
                        end.append(self.source_token())
                        m["items"].pop()
                        return False
                it["start"].append(self.source_token())
            return False
        if self.indent >= m["indent"]:
            at_map_indent = not self.on_key_line and self.indent == m["indent"]
            at_next_item = (at_map_indent and (it.get("sep") is not None or bool(it.get("explicitKey"))) and
                            t != "seq-item-ind")
            # For empty nodes, assign newline-separated not indented empty tokens to following node
            start = []
            if at_next_item and it.get("sep") is not None and it.get("value") is None:
                nl = []
                for i, st in enumerate(it["sep"]):
                    if st["type"] == "newline":
                        nl.append(i)
                    elif st["type"] == "space":
                        pass
                    elif st["type"] == "comment":
                        if st["indent"] > m["indent"]:
                            nl.clear()
                    else:
                        nl.clear()
                if len(nl) >= 2:
                    start = it["sep"][nl[1]:]
                    del it["sep"][nl[1]:]
            if t in ("anchor", "tag"):
                if at_next_item or it.get("value") is not None:
                    start.append(self.source_token())
                    m["items"].append({"start": start})
                    self.on_key_line = True
                elif it.get("sep") is not None:
                    it["sep"].append(self.source_token())
                else:
                    it["start"].append(self.source_token())
                return False
            if t == "explicit-key-ind":
                if it.get("sep") is None and not it.get("explicitKey"):
                    it["start"].append(self.source_token())
                    it["explicitKey"] = True
                elif at_next_item or it.get("value") is not None:
                    start.append(self.source_token())
                    m["items"].append({"start": start, "explicitKey": True})
                else:
                    self.stack.append({"type": "block-map", "offset": self.offset, "indent": self.indent,
                                       "items": [{"start": [self.source_token()], "explicitKey": True}]})
                self.on_key_line = True
                return False
            if t == "map-value-ind":
                if it.get("explicitKey"):
                    if it.get("sep") is None:
                        if _includes_token(it["start"], "newline"):
                            it["key"] = None
                            it["sep"] = [self.source_token()]
                        else:
                            start2 = _get_first_key_start_props(it["start"])
                            self.stack.append({"type": "block-map", "offset": self.offset, "indent": self.indent,
                                               "items": [{"start": start2, "key": None, "sep": [self.source_token()]}]})
                    elif it.get("value") is not None:
                        m["items"].append({"start": [], "key": None, "sep": [self.source_token()]})
                    elif _includes_token(it["sep"], "map-value-ind"):
                        self.stack.append({"type": "block-map", "offset": self.offset, "indent": self.indent,
                                           "items": [{"start": start, "key": None, "sep": [self.source_token()]}]})
                    elif _is_flow_token(it.get("key")) and not _includes_token(it["sep"], "newline"):
                        start2 = _get_first_key_start_props(it["start"])
                        key = it["key"]
                        sep = it["sep"]
                        sep.append(self.source_token())
                        del it["key"]
                        del it["sep"]
                        self.stack.append({"type": "block-map", "offset": self.offset, "indent": self.indent,
                                           "items": [{"start": start2, "key": key, "sep": sep}]})
                    elif len(start) > 0:
                        # Not actually at next item
                        it["sep"] = it["sep"] + start + [self.source_token()]
                    else:
                        it["sep"].append(self.source_token())
                else:
                    if it.get("sep") is None:
                        it["key"] = None
                        it["sep"] = [self.source_token()]
                    elif it.get("value") is not None or at_next_item:
                        m["items"].append({"start": start, "key": None, "sep": [self.source_token()]})
                    elif _includes_token(it["sep"], "map-value-ind"):
                        self.stack.append({"type": "block-map", "offset": self.offset, "indent": self.indent,
                                           "items": [{"start": [], "key": None, "sep": [self.source_token()]}]})
                    else:
                        it["sep"].append(self.source_token())
                self.on_key_line = True
                return False
            if t in _FLOW_SCALARS:
                fs = self.flow_scalar(t)
                if at_next_item or it.get("value") is not None:
                    m["items"].append({"start": start, "key": fs, "sep": []})
                    self.on_key_line = True
                elif it.get("sep") is not None:
                    self.stack.append(fs)
                else:
                    it["key"] = fs
                    it["sep"] = []
                    self.on_key_line = True
                return False
            bv = self.start_block_value(m)
            if bv is not None:
                if bv["type"] == "block-seq":
                    if (not it.get("explicitKey") and it.get("sep") is not None and
                            not _includes_token(it["sep"], "newline")):
                        self.pop({"type": "error", "offset": self.offset,
                                  "message": "Unexpected block-seq-ind on same line with key", "source": self.source})
                        return False
                elif at_map_indent:
                    m["items"].append({"start": start})
                self.stack.append(bv)
                return False
        self.pop()
        return True

    def block_sequence(self, seq):
        it = seq["items"][-1]
        t = self.type
        if t == "newline":
            if it.get("value") is not None:
                end = it["value"]["end"] if "end" in it["value"] else None
                last = end[-1] if isinstance(end, list) and end else None
                if last is not None and last["type"] == "comment":
                    end.append(self.source_token())
                else:
                    seq["items"].append({"start": [self.source_token()]})
            else:
                it["start"].append(self.source_token())
            return False
        if t in ("space", "comment"):
            if it.get("value") is not None:
                seq["items"].append({"start": [self.source_token()]})
            else:
                if self.at_indented_comment(it["start"], seq["indent"]):
                    prev = seq["items"][-2] if len(seq["items"]) >= 2 else None
                    pv = prev.get("value") if prev is not None else None
                    end = pv.get("end") if pv is not None else None
                    if isinstance(end, list):
                        end.extend(it["start"])
                        end.append(self.source_token())
                        seq["items"].pop()
                        return False
                it["start"].append(self.source_token())
            return False
        if t in ("anchor", "tag"):
            if not (it.get("value") is not None or self.indent <= seq["indent"]):
                it["start"].append(self.source_token())
                return False
        elif t == "seq-item-ind":
            if self.indent == seq["indent"]:
                if it.get("value") is not None or _includes_token(it["start"], "seq-item-ind"):
                    seq["items"].append({"start": [self.source_token()]})
                else:
                    it["start"].append(self.source_token())
                return False
        if self.indent > seq["indent"]:
            bv = self.start_block_value(seq)
            if bv is not None:
                self.stack.append(bv)
                return False
        self.pop()
        return True

    def flow_collection(self, fc):
        it = fc["items"][-1] if fc["items"] else None
        t = self.type
        if t == "flow-error-end":
            while True:
                self.pop()
                top = self.peek(1)
                if top is None or top["type"] != "flow-collection":
                    break
            return False
        if len(fc["end"]) == 0:
            if t in ("comma", "explicit-key-ind"):
                if it is None or it.get("sep") is not None:
                    fc["items"].append({"start": [self.source_token()]})
                else:
                    it["start"].append(self.source_token())
                return False
            if t == "map-value-ind":
                if it is None or it.get("value") is not None:
                    fc["items"].append({"start": [], "key": None, "sep": [self.source_token()]})
                elif it.get("sep") is not None:
                    it["sep"].append(self.source_token())
                else:
                    it["key"] = None
                    it["sep"] = [self.source_token()]
                return False
            if t in ("space", "comment", "newline", "anchor", "tag"):
                if it is None or it.get("value") is not None:
                    fc["items"].append({"start": [self.source_token()]})
                elif it.get("sep") is not None:
                    it["sep"].append(self.source_token())
                else:
                    it["start"].append(self.source_token())
                return False
            if t in _FLOW_SCALARS:
                fs = self.flow_scalar(t)
                if it is None or it.get("value") is not None:
                    fc["items"].append({"start": [], "key": fs, "sep": []})
                elif it.get("sep") is not None:
                    self.stack.append(fs)
                else:
                    it["key"] = fs
                    it["sep"] = []
                return False
            if t in ("flow-map-end", "flow-seq-end"):
                fc["end"].append(self.source_token())
                return False
            bv = self.start_block_value(fc)
            if bv is not None:
                self.stack.append(bv)
                return False
            self.pop()
            return True
        parent = self.peek(2)
        if parent["type"] == "block-map" and ((t == "map-value-ind" and parent["indent"] == fc["indent"]) or
                                             (t == "newline" and parent["items"][-1].get("sep") is None)):
            self.pop()
            return True
        if t == "map-value-ind" and parent["type"] != "flow-collection":
            prev = _get_prev_props(parent)
            start = _get_first_key_start_props(prev)
            _fix_flow_seq_items(fc)
            sep = fc["end"][1:]
            del fc["end"][1:]
            sep.append(self.source_token())
            self.on_key_line = True
            self.stack[-1] = {"type": "block-map", "offset": fc["offset"], "indent": fc["indent"],
                              "items": [{"start": start, "key": fc, "sep": sep}]}
            return False
        return self.line_end(fc)

    def flow_scalar(self, type_):
        nl = self.source.find("\n") + 1
        while nl != 0:
            self.on_new_line(self.offset + nl)
            nl = self.source.find("\n", nl) + 1
        return {"type": type_, "offset": self.offset, "indent": self.indent, "source": self.source}

    def start_block_value(self, parent):
        t = self.type
        if t in _FLOW_SCALARS:
            return self.flow_scalar(t)
        if t == "block-scalar-header":
            return {"type": "block-scalar", "offset": self.offset, "indent": self.indent,
                    "props": [self.source_token()], "source": ""}
        if t in ("flow-map-start", "flow-seq-start"):
            return {"type": "flow-collection", "offset": self.offset, "indent": self.indent,
                    "start": self.source_token(), "items": [], "end": []}
        if t == "seq-item-ind":
            return {"type": "block-seq", "offset": self.offset, "indent": self.indent,
                    "items": [{"start": [self.source_token()]}]}
        if t == "explicit-key-ind":
            self.on_key_line = True
            start = _get_first_key_start_props(_get_prev_props(parent))
            start.append(self.source_token())
            return {"type": "block-map", "offset": self.offset, "indent": self.indent,
                    "items": [{"start": start, "explicitKey": True}]}
        if t == "map-value-ind":
            self.on_key_line = True
            start = _get_first_key_start_props(_get_prev_props(parent))
            return {"type": "block-map", "offset": self.offset, "indent": self.indent,
                    "items": [{"start": start, "key": None, "sep": [self.source_token()]}]}
        return None

    def at_indented_comment(self, start, indent):
        if self.type != "comment":
            return False
        if self.indent <= indent:
            return False
        return all(st["type"] in ("newline", "space") for st in start)

    def document_end(self, doc_end):
        if self.type != "doc-mode":
            if doc_end.get("end") is not None:
                doc_end["end"].append(self.source_token())
            else:
                doc_end["end"] = [self.source_token()]
            if self.type == "newline":
                self.pop()

    def line_end(self, token):
        t = self.type
        if t in ("comma", "doc-start", "doc-end", "flow-seq-end", "flow-map-end", "map-value-ind"):
            self.pop()
            return True
        if t == "newline":
            self.on_key_line = False
        # all other values are errors
        if token.get("end") is not None:
            token["end"].append(self.source_token())
        else:
            token["end"] = [self.source_token()]
        if t == "newline":
            self.pop()
        return False


class _LineCounter:
    def __init__(self):
        self.line_starts = []

    def add_new_line(self, offset):
        self.line_starts.append(offset)

    def line_pos(self, offset):
        starts = self.line_starts
        low, high = 0, len(starts)
        while low < high:
            mid = (low + high) >> 1
            if starts[mid] < offset:
                low = mid + 1
            else:
                high = mid
        if low < len(starts) and starts[low] == offset:
            return low + 1, 1
        if low == 0:
            return 0, offset
        return low, offset - starts[low - 1] + 1

    def start(self, line):
        """`lineStarts[line]`, None (`undefined`) outside the list."""
        return self.line_starts[line] if 0 <= line < len(self.line_starts) else None


def _too_deep(tokens) -> bool:
    """Collections nested deeper than MAX_DEPTH in a document of the syntax tree."""
    for token in tokens:
        if token["type"] != "document" or token.get("value") is None:
            continue
        stack = [(token["value"], 0)]
        while stack:
            node, depth = stack.pop()
            if "items" not in node:
                continue
            if depth + 1 > MAX_DEPTH:
                return True
            for item in node["items"]:
                if item.get("key") is not None:
                    stack.append((item["key"], depth + 1))
                if item.get("value") is not None:
                    stack.append((item["value"], depth + 1))
    return False


# ── Nodes (nodes/*.js) ────────────────────────────────────────────────────────────────────────

_UNDEFINED = object()


class _Scalar:
    __slots__ = ("value", "out", "range", "anchor")

    def __init__(self, value, out):
        self.value = value  # the JavaScript value, which keys are compared by
        self.out = out      # the value in Python's types, which `load` returns
        self.range = None
        self.anchor = None


class _Map:
    __slots__ = ("items", "range", "anchor", "flow")

    def __init__(self, flow=False):
        self.items = []
        self.range = None
        self.anchor = None
        self.flow = flow


class _Seq:
    __slots__ = ("items", "range", "anchor", "flow")

    def __init__(self, flow=False):
        self.items = []
        self.range = None
        self.anchor = None
        self.flow = flow


class _Pair:
    __slots__ = ("key", "value")

    def __init__(self, key, value=None):
        self.key = key
        self.value = value


class _Alias:
    __slots__ = ("source", "range")

    def __init__(self, source):
        self.source = source
        self.range = None


def _has_anchor(node):
    return isinstance(node, (_Scalar, _Map, _Seq)) and bool(node.anchor)


# ── Schema (schema/core, schema/common) ───────────────────────────────────────────────────────
#
# The core schema of YAML 1.2, as `{ schema: "core", resolveKnownTags: false }` sets it: no
# `!!timestamp`, no `!!binary`, no `!!set`. A tag outside it leaves the text, with a warning
# neither implementation prints.

_TWO53 = 2 ** 53


def _int_out(n: int):
    if abs(n) <= _TWO53:
        return n
    try:
        return float(n)
    except OverflowError:
        return -math.inf if n < 0 else math.inf


def _resolve_int(text: str):
    # parseInt(text, 10): a double. Past Python's 4 300 digits for int() the text is far past a
    # double, and float() reads it as Infinity, as the twin holds it.
    try:
        exact = int(text)
    except ValueError:
        value = float(text)
        return _Scalar(value, value)
    return _Scalar(_double(exact), _int_out(exact))


def _resolve_radix(text: str, base: int):
    exact = int(text[2:], base)
    return _Scalar(_double(exact), _int_out(exact))


def _double(n: int) -> float:
    try:
        return float(n)
    except OverflowError:
        return -math.inf if n < 0 else math.inf


def _resolve_float(text: str):
    value = float(text)
    return _Scalar(value, value)


def _resolve_float_nan(text: str):
    value = math.nan if text[-3:].lower() == "nan" else (-math.inf if text[0] == "-" else math.inf)
    return _Scalar(value, value)


def _resolve_str(text: str):
    return _Scalar(text, _from16(text))


class _Tag:
    __slots__ = ("name", "collection", "test", "resolve")

    def __init__(self, name, collection=None, test=None, resolve=None):
        self.name = name
        self.collection = collection
        self.test = re.compile(test) if test is not None else None
        self.resolve = resolve


_MAP_TAG = "tag:yaml.org,2002:map"
_SEQ_TAG = "tag:yaml.org,2002:seq"
_STR_TAG = "tag:yaml.org,2002:str"
_STR = _Tag(_STR_TAG, resolve=_resolve_str)
_CORE = [
    _Tag(_MAP_TAG, collection="map"),
    _Tag(_SEQ_TAG, collection="seq"),
    _STR,
    _Tag("tag:yaml.org,2002:null", test=r"(?:~|[Nn]ull|NULL)?", resolve=lambda s: _Scalar(None, None)),
    _Tag("tag:yaml.org,2002:bool", test=r"(?:[Tt]rue|TRUE|[Ff]alse|FALSE)",
         resolve=lambda s: _Scalar(s[0] in "tT", s[0] in "tT")),
    _Tag("tag:yaml.org,2002:int", test=r"0o[0-7]+", resolve=lambda s: _resolve_radix(s, 8)),
    _Tag("tag:yaml.org,2002:int", test=r"[-+]?[0-9]+", resolve=_resolve_int),
    _Tag("tag:yaml.org,2002:int", test=r"0x[0-9a-fA-F]+", resolve=lambda s: _resolve_radix(s, 16)),
    _Tag("tag:yaml.org,2002:float", test=r"(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)", resolve=_resolve_float_nan),
    _Tag("tag:yaml.org,2002:float", test=r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+",
         resolve=_resolve_float),
    _Tag("tag:yaml.org,2002:float", test=r"[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)", resolve=_resolve_float),
]


# ── Directives (doc/directives.js) ────────────────────────────────────────────────────────────

class _Directives:
    def __init__(self, yaml=None, tags=None):
        self.doc_start = None
        self.doc_end = False
        self.yaml = {"explicit": False, "version": "1.2", **(yaml or {})}
        self.tags = {"!!": "tag:yaml.org,2002:", **(tags or {})}
        self.at_next_document = False

    def at_document(self):
        res = _Directives(self.yaml, self.tags)
        if self.yaml["version"] == "1.1":
            self.at_next_document = True
        elif self.yaml["version"] == "1.2":
            self.at_next_document = False
            self.yaml = {"explicit": False, "version": "1.2"}
            self.tags = {"!!": "tag:yaml.org,2002:"}
        return res

    def add(self, line, on_error):
        if self.at_next_document:
            self.yaml = {"explicit": False, "version": "1.1"}
            self.tags = {"!!": "tag:yaml.org,2002:"}
            self.at_next_document = False
        parts = re.split(r"[ \t]+", js_trim(line))
        name = parts.pop(0)
        if name == "%TAG":
            if len(parts) != 2:
                on_error(0, "%TAG directive should contain exactly two parts")
                if len(parts) < 2:
                    return False
            self.tags[parts[0]] = parts[1]
            return True
        if name == "%YAML":
            self.yaml["explicit"] = True
            if len(parts) != 1:
                on_error(0, "%YAML directive should contain exactly one part")
                return False
            version = parts[0]
            if version in ("1.1", "1.2"):
                self.yaml["version"] = version
                return True
            on_error(6, f"Unsupported YAML version {version}", bool(re.fullmatch(r"[0-9]+\.[0-9]+", version)))
            return False
        on_error(0, f"Unknown directive {name}", True)
        return False

    def tag_name(self, source, on_error):
        if source == "!":
            return "!"  # non-specific tag
        if _at(source, 0) != "!":
            on_error(f"Not a valid tag: {source}")
            return None
        if _at(source, 1) == "<":
            verbatim = source[2:-1]
            if verbatim in ("!", "!!"):
                on_error(f"Verbatim tags aren't resolved, so {source} is invalid.")
                return None
            if source[-1] != ">":
                on_error("Verbatim tags must end with a >")
            return verbatim
        match = re.match(r"(.*!)([^!]*)\Z", source, re.S)
        handle, suffix = match.group(1), match.group(2)
        if not suffix:
            on_error(f"The {source} tag has no suffix")
        prefix = self.tags.get(handle)
        if prefix:
            try:
                return prefix + _decode_uri_component(suffix)
            except _URIError:
                on_error("URIError: URI malformed")
                return None
        if handle == "!":
            return source  # local tag
        on_error(f"Could not resolve tag: {source}")
        return None


class _Document:
    def __init__(self, directives):
        self.errors = []
        self.warnings = []
        # The document's version picks no schema here: `schema: "core"` overrides it.
        self.directives = directives.at_document()
        self.contents = None
        self.range = None


class _Ctx:
    def __init__(self, doc):
        self.at_key = False
        self.at_root = True
        self.directives = doc.directives


# ── Composer (compose/*.js) ───────────────────────────────────────────────────────────────────

def _error_pos(src):
    if isinstance(src, int):
        return [src, src + 1]
    if isinstance(src, list):
        return src if len(src) == 2 else [src[0], src[1]]
    source = src.get("source")
    return [src["offset"], src["offset"] + (len(source) if isinstance(source, str) else 1)]


class _Composer:
    def __init__(self):
        self.doc = None
        self.at_directives = False
        self.errors = []
        self.warnings = []
        self.directives = _Directives({"version": "1.2"})

    def on_error(self, source, code, message, warning=False):
        error = YAMLError(_error_pos(source), code, message)
        (self.warnings if warning else self.errors).append(error)

    def decorate(self, doc, after_doc):
        if after_doc:
            doc.errors.extend(self.errors)
            doc.warnings.extend(self.warnings)
        else:
            doc.errors = self.errors
            doc.warnings = self.warnings
        self.errors = []
        self.warnings = []

    def compose(self, tokens, end_offset):
        for token in tokens:
            yield from self.next(token)
        if self.doc is not None:
            self.decorate(self.doc, True)
            yield self.doc
            self.doc = None
        else:
            doc = _Document(self.directives)
            if self.at_directives:
                self.on_error(end_offset, "MISSING_CHAR", "Missing directives-end indicator line")
            doc.range = [0, end_offset, end_offset]
            self.decorate(doc, False)
            yield doc

    def next(self, token):
        t = token["type"]
        if t == "directive":
            def on_directive_error(offset, message, warning=False):
                pos = _error_pos(token)
                pos[0] += offset
                self.on_error(pos, "BAD_DIRECTIVE", message, warning)
            self.directives.add(token["source"], on_directive_error)
            self.at_directives = True
        elif t == "document":
            doc = _compose_doc(self.directives, token, self.on_error)
            if self.at_directives and not doc.directives.doc_start:
                self.on_error(token, "MISSING_CHAR", "Missing directives-end/doc-start indicator line")
            self.decorate(doc, False)
            if self.doc is not None:
                yield self.doc
            self.doc = doc
            self.at_directives = False
        elif t in ("byte-order-mark", "space", "comment", "newline"):
            pass
        elif t == "error":
            msg = f"{token['message']}: {_json_string(token['source'])}" if token.get("source") else token["message"]
            error = YAMLError(_error_pos(token), "UNEXPECTED_TOKEN", msg)
            if self.at_directives or self.doc is None:
                self.errors.append(error)
            else:
                self.doc.errors.append(error)
        elif t == "doc-end":
            if self.doc is None:
                self.errors.append(YAMLError(_error_pos(token), "UNEXPECTED_TOKEN",
                                             "Unexpected doc-end without preceding document"))
                return
            self.doc.directives.doc_end = True
            end = _resolve_end(token.get("end"), token["offset"] + len(token["source"]), True, self.on_error)
            self.decorate(self.doc, True)
            self.doc.range[2] = end[1]
        else:
            self.errors.append(YAMLError(_error_pos(token), "UNEXPECTED_TOKEN", f"Unsupported token {t}"))


class _Props:
    __slots__ = ("comma", "found", "comment", "has_newline", "anchor", "tag", "newline_after_prop", "end", "start")


def _resolve_props(tokens, flow, indicator, next_, offset, on_error, parent_indent, start_on_newline):
    at_newline = start_on_newline
    has_space = start_on_newline
    comment = ""
    comment_sep = ""
    has_newline = False
    req_space = False
    tab = None
    anchor = None
    tag = None
    newline_after_prop = None
    comma = None
    found = None
    start = None
    for token in tokens:
        t = token["type"]
        if req_space:
            if t not in ("space", "newline", "comma"):
                on_error(token["offset"], "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space")
            req_space = False
        if tab is not None:
            if at_newline and t != "comment" and t != "newline":
                on_error(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation")
            tab = None
        if t == "space":
            # At the doc level, tabs at line start may be parsed as leading white space rather
            # than indentation. In a flow collection, only the parser handles indent.
            if (not flow and (indicator != "doc-start" or next_ is None or next_["type"] != "flow-collection") and
                    "\t" in token["source"]):
                tab = token
            has_space = True
        elif t == "comment":
            if not has_space:
                on_error(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters")
            cb = token["source"][1:] or " "
            comment = cb if not comment else comment + comment_sep + cb
            comment_sep = ""
            at_newline = False
        elif t == "newline":
            if at_newline:
                if comment:
                    comment += token["source"]
            else:
                comment_sep += token["source"]
            at_newline = True
            has_newline = True
            if anchor is not None or tag is not None:
                newline_after_prop = token
            has_space = True
        elif t == "anchor":
            if anchor is not None:
                on_error(token, "MULTIPLE_ANCHORS", "A node can have at most one anchor")
            if token["source"].endswith(":"):
                on_error(token["offset"] + len(token["source"]) - 1, "BAD_ALIAS", "Anchor ending in : is ambiguous", True)
            anchor = token
            if start is None:
                start = token["offset"]
            at_newline = False
            has_space = False
            req_space = True
        elif t == "tag":
            if tag is not None:
                on_error(token, "MULTIPLE_TAGS", "A node can have at most one tag")
            tag = token
            if start is None:
                start = token["offset"]
            at_newline = False
            has_space = False
            req_space = True
        elif t == indicator:
            # Could here handle preceding comments differently
            if anchor is not None or tag is not None:
                on_error(token, "BAD_PROP_ORDER", f"Anchors and tags must be after the {token['source']} indicator")
            if found is not None:
                on_error(token, "UNEXPECTED_TOKEN", f"Unexpected {token['source']} in {flow or 'collection'}")
            found = token
            at_newline = indicator in ("seq-item-ind", "explicit-key-ind")
            has_space = False
        elif t == "comma" and flow:
            if comma is not None:
                on_error(token, "UNEXPECTED_TOKEN", f"Unexpected , in {flow}")
            comma = token
            at_newline = False
            has_space = False
        else:
            on_error(token, "UNEXPECTED_TOKEN", f"Unexpected {t} token")
            at_newline = False
            has_space = False
    last = tokens[-1] if tokens else None
    end = last["offset"] + len(last["source"]) if last is not None else offset
    if (req_space and next_ is not None and next_["type"] not in ("space", "newline", "comma") and
            (next_["type"] != "scalar" or next_["source"] != "")):
        on_error(next_["offset"], "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space")
    if tab is not None and ((at_newline and tab["indent"] <= parent_indent) or
                            (next_ is not None and next_["type"] in ("block-map", "block-seq"))):
        on_error(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation")
    props = _Props()
    props.comma = comma
    props.found = found
    props.comment = comment
    props.has_newline = has_newline
    props.anchor = anchor
    props.tag = tag
    props.newline_after_prop = newline_after_prop
    props.end = end
    props.start = start if start is not None else end
    return props


def _resolve_end(end, offset, req_space, on_error):
    """(comment, offset) after the tokens that end a node."""
    comment = ""
    if end is not None:
        has_space = False
        sep = ""
        for token in end:
            source = token["source"]
            t = token["type"]
            if t == "space":
                has_space = True
            elif t == "comment":
                if req_space and not has_space:
                    on_error(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters")
                cb = source[1:] or " "
                comment = cb if not comment else comment + sep + cb
                sep = ""
            elif t == "newline":
                if comment:
                    sep += source
                has_space = True
            else:
                on_error(token, "UNEXPECTED_TOKEN", f"Unexpected {t} at node end")
            offset += len(source)
    return comment, offset


def _contains_newline(key):
    if key is None:
        return False
    t = key["type"]
    if t in ("alias", "scalar", "double-quoted-scalar", "single-quoted-scalar"):
        if "\n" in key["source"]:
            return True
        if key.get("end") is not None:
            for st in key["end"]:
                if st["type"] == "newline":
                    return True
        return False
    if t == "flow-collection":
        for it in key["items"]:
            for st in it["start"]:
                if st["type"] == "newline":
                    return True
            if it.get("sep") is not None:
                for st in it["sep"]:
                    if st["type"] == "newline":
                        return True
            if _contains_newline(it.get("key")) or _contains_newline(it.get("value")):
                return True
        return False
    return True


def _empty_scalar_position(offset, before, pos):
    if before is not None:
        if pos is None:
            pos = len(before)
        i = pos - 1
        while i >= 0:
            st = before[i]
            if st["type"] in ("space", "comment", "newline"):
                offset -= len(st["source"])
                i -= 1
                continue
            # Technically, an empty scalar is immediately after the last non-empty node, but it's
            # more useful to place it after any whitespace.
            i += 1
            st = before[i] if i < len(before) else None
            while st is not None and st["type"] == "space":
                offset += len(st["source"])
                i += 1
                st = before[i] if i < len(before) else None
            break
    return offset


def _js_equal(a, b):
    """`===` between two scalar values: no number is a boolean here, as in Python."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, float) and isinstance(b, float) and a == b
    return a == b


def _map_includes(items, search):
    for pair in items:
        key = pair.key
        if key is search or (isinstance(key, _Scalar) and isinstance(search, _Scalar) and
                             _js_equal(key.value, search.value)):
            return True
    return False


def _compose_doc(directives, token, on_error):
    doc = _Document(directives)
    ctx = _Ctx(doc)
    start = token["start"]
    value = token.get("value")
    end = token.get("end")
    props = _resolve_props(start, None, "doc-start", value if value is not None else (end[0] if end else None),
                           token["offset"], on_error, 0, True)
    if props.found is not None:
        doc.directives.doc_start = True
        if value is not None and value["type"] in ("block-map", "block-seq") and not props.has_newline:
            on_error(props.end, "MISSING_CHAR", "Block collection cannot start on same line with directives-end marker")
    doc.contents = (_compose_node(ctx, value, props, on_error) if value is not None
                    else _compose_empty_node(ctx, props.end, start, None, props, on_error))
    content_end = doc.contents.range[2]
    _, re_offset = _resolve_end(end, content_end, False, on_error)
    doc.range = [token["offset"], content_end, re_offset]
    return doc


def _compose_node(ctx, token, props, on_error):
    anchor = props.anchor
    tag = props.tag
    node = None
    t = token["type"]
    if t == "alias":
        node = _compose_alias(token, on_error)
        if anchor is not None or tag is not None:
            on_error(token, "ALIAS_PROPS", "An alias node must not specify any properties")
    elif t in ("scalar", "single-quoted-scalar", "double-quoted-scalar", "block-scalar"):
        node = _compose_scalar(ctx, token, tag, on_error)
        if anchor is not None:
            node.anchor = anchor["source"][1:]
    elif t in ("block-map", "block-seq", "flow-collection"):
        node = _compose_collection(ctx, token, props, on_error)
        if anchor is not None:
            node.anchor = anchor["source"][1:]
    else:
        message = token["message"] if t == "error" else f"Unsupported token (type: {t})"
        on_error(token, "UNEXPECTED_TOKEN", message)
    if node is None:
        node = _compose_empty_node(ctx, token["offset"], None, None, props, on_error)
    if anchor is not None and getattr(node, "anchor", None) == "":
        on_error(anchor, "BAD_ALIAS", "Anchor cannot be an empty string")
    return node


def _compose_empty_node(ctx, offset, before, pos, props, on_error):
    token = {"type": "scalar", "offset": _empty_scalar_position(offset, before, pos), "indent": -1, "source": ""}
    node = _compose_scalar(ctx, token, props.tag, on_error)
    if props.anchor is not None:
        node.anchor = props.anchor["source"][1:]
        if node.anchor == "":
            on_error(props.anchor, "BAD_ALIAS", "Anchor cannot be an empty string")
    if props.comment:
        node.range[2] = props.end
    return node


def _compose_alias(token, on_error):
    offset = token["offset"]
    source = token["source"]
    alias = _Alias(source[1:])
    if alias.source == "":
        on_error(offset, "BAD_ALIAS", "Alias cannot be an empty string")
    if alias.source.endswith(":"):
        on_error(offset + len(source) - 1, "BAD_ALIAS", "Alias ending in : is ambiguous", True)
    value_end = offset + len(source)
    _, re_offset = _resolve_end(token.get("end"), value_end, True, on_error)
    alias.range = [offset, value_end, re_offset]
    return alias


def _compose_scalar(ctx, token, tag_token, on_error):
    if token["type"] == "block-scalar":
        value, _, rng = _resolve_block_scalar(ctx, token, on_error)
    else:
        value, _, rng = _resolve_flow_scalar(token, True, on_error)
    tag_name = (ctx.directives.tag_name(tag_token["source"], lambda msg: on_error(tag_token, "TAG_RESOLVE_FAILED", msg))
                if tag_token is not None else None)
    if tag_name:
        tag = _find_scalar_tag_by_name(value, tag_name, tag_token, on_error)
    elif token["type"] == "scalar":
        tag = next((t for t in _CORE if t.test is not None and t.test.fullmatch(value)), _STR)
    else:
        tag = _STR
    scalar = tag.resolve(value)
    scalar.range = rng
    return scalar


def _find_scalar_tag_by_name(value, tag_name, tag_token, on_error):
    if tag_name == "!":
        return _STR  # non-specific tag
    match_with_test = []
    for tag in _CORE:
        if tag.collection is None and tag.name == tag_name:
            if tag.test is not None:
                match_with_test.append(tag)
            else:
                return tag
    for tag in match_with_test:
        if tag.test.fullmatch(value):
            return tag
    on_error(tag_token, "TAG_RESOLVE_FAILED", f"Unresolved tag: {tag_name}", tag_name != _STR_TAG)
    return _STR


def _compose_collection(ctx, token, props, on_error):
    tag_token = props.tag
    tag_name = (ctx.directives.tag_name(tag_token["source"], lambda msg: on_error(tag_token, "TAG_RESOLVE_FAILED", msg))
                if tag_token is not None else None)
    if token["type"] == "block-seq":
        anchor = props.anchor
        nl = props.newline_after_prop
        if anchor is not None and tag_token is not None:
            last_prop = anchor if anchor["offset"] > tag_token["offset"] else tag_token
        else:
            last_prop = anchor if anchor is not None else tag_token
        if last_prop is not None and (nl is None or nl["offset"] < last_prop["offset"]):
            on_error(last_prop, "MISSING_CHAR", "Missing newline after block sequence props")
    if token["type"] == "block-map":
        exp_type = "map"
    elif token["type"] == "block-seq":
        exp_type = "seq"
    else:
        exp_type = "map" if token["start"]["source"] == "{" else "seq"
    if not (tag_token is None or not tag_name or tag_name == "!" or
            (tag_name == _MAP_TAG and exp_type == "map") or (tag_name == _SEQ_TAG and exp_type == "seq")):
        # The core schema has no other collection tag, and no known tags are resolved.
        on_error(tag_token, "TAG_RESOLVE_FAILED", f"Unresolved tag: {tag_name}", True)
    if token["type"] == "block-map":
        return _resolve_block_map(ctx, token, on_error)
    if token["type"] == "block-seq":
        return _resolve_block_seq(ctx, token, on_error)
    return _resolve_flow_collection(ctx, token, on_error)


_START_COL = "All mapping items must start at the same column"


def _resolve_block_map(ctx, bm, on_error):
    m = _Map()
    if ctx.at_root:
        ctx.at_root = False
    offset = bm["offset"]
    comment_end = None
    for coll_item in bm["items"]:
        start = coll_item["start"]
        key = coll_item.get("key")
        sep = coll_item.get("sep")
        value = coll_item.get("value")
        # key properties
        key_props = _resolve_props(start, None, "explicit-key-ind", key if key is not None else (sep[0] if sep else None),
                                   offset, on_error, bm["indent"], True)
        implicit_key = key_props.found is None
        if implicit_key:
            if key is not None:
                if key["type"] == "block-seq":
                    on_error(offset, "BLOCK_AS_IMPLICIT_KEY", "A block sequence may not be used as an implicit map key")
                elif "indent" in key and key["indent"] != bm["indent"]:
                    on_error(offset, "BAD_INDENT", _START_COL)
            if key_props.anchor is None and key_props.tag is None and sep is None:
                comment_end = key_props.end
                continue
            if key_props.newline_after_prop is not None or _contains_newline(key):
                on_error(key if key is not None else start[-1], "MULTILINE_IMPLICIT_KEY", "Implicit keys need to be on a single line")
        elif key_props.found.get("indent") != bm["indent"]:
            on_error(offset, "BAD_INDENT", _START_COL)
        # key value
        ctx.at_key = True
        key_start = key_props.end
        key_node = (_compose_node(ctx, key, key_props, on_error) if key is not None
                    else _compose_empty_node(ctx, key_start, start, None, key_props, on_error))
        ctx.at_key = False
        if _map_includes(m.items, key_node):
            on_error(key_start, "DUPLICATE_KEY", "Map keys must be unique")
        # value properties
        value_props = _resolve_props(sep if sep is not None else [], None, "map-value-ind", value, key_node.range[2],
                                     on_error, bm["indent"], key is None or key["type"] == "block-scalar")
        offset = value_props.end
        if value_props.found is not None:
            if implicit_key:
                if value is not None and value["type"] == "block-map" and not value_props.has_newline:
                    on_error(offset, "BLOCK_AS_IMPLICIT_KEY", "Nested mappings are not allowed in compact mappings")
                if key_props.start < value_props.found["offset"] - 1024:
                    on_error(key_node.range, "KEY_OVER_1024_CHARS",
                             "The : indicator must be at most 1024 chars after the start of an implicit block mapping key")
            # value value
            value_node = (_compose_node(ctx, value, value_props, on_error) if value is not None
                          else _compose_empty_node(ctx, offset, sep, None, value_props, on_error))
            offset = value_node.range[2]
            m.items.append(_Pair(key_node, value_node))
        else:
            # key with no value
            if implicit_key:
                on_error(key_node.range, "MISSING_CHAR", "Implicit map keys need to be followed by map values")
            m.items.append(_Pair(key_node))
    if comment_end and comment_end < offset:
        on_error(comment_end, "IMPOSSIBLE", "Map comment with trailing content")
    m.range = [bm["offset"], offset, comment_end if comment_end is not None else offset]
    return m


def _resolve_block_seq(ctx, bs, on_error):
    seq = _Seq()
    if ctx.at_root:
        ctx.at_root = False
    if ctx.at_key:
        ctx.at_key = False
    offset = bs["offset"]
    comment_end = None
    for item in bs["items"]:
        start = item["start"]
        value = item.get("value")
        props = _resolve_props(start, None, "seq-item-ind", value, offset, on_error, bs["indent"], True)
        if props.found is None:
            if props.anchor is not None or props.tag is not None or value is not None:
                if value is not None and value["type"] == "block-seq":
                    on_error(props.end, "BAD_INDENT", "All sequence items must start at the same column")
                else:
                    on_error(offset, "MISSING_CHAR", "Sequence item without - indicator")
            else:
                comment_end = props.end
                continue
        node = (_compose_node(ctx, value, props, on_error) if value is not None
                else _compose_empty_node(ctx, props.end, start, None, props, on_error))
        offset = node.range[2]
        seq.items.append(node)
    seq.range = [bs["offset"], offset, comment_end if comment_end is not None else offset]
    return seq


_BLOCK_IN_FLOW = "Block collections are not allowed within flow collections"


def _is_block(token):
    return token is not None and token["type"] in ("block-map", "block-seq")


def _resolve_flow_collection(ctx, fc, on_error):
    is_map = fc["start"]["source"] == "{"
    fc_name = "flow map" if is_map else "flow sequence"
    coll = _Map(flow=True) if is_map else _Seq(flow=True)
    at_root = ctx.at_root
    if at_root:
        ctx.at_root = False
    if ctx.at_key:
        ctx.at_key = False
    offset = fc["offset"] + len(fc["start"]["source"])
    items = fc["items"]
    for i, coll_item in enumerate(items):
        start = coll_item["start"]
        key = coll_item.get("key")
        sep = coll_item.get("sep")
        value = coll_item.get("value")
        props = _resolve_props(start, fc_name, "explicit-key-ind", key if key is not None else (sep[0] if sep else None),
                               offset, on_error, fc["indent"], False)
        if props.found is None:
            if props.anchor is None and props.tag is None and sep is None and value is None:
                if i == 0 and props.comma is not None:
                    on_error(props.comma, "UNEXPECTED_TOKEN", f"Unexpected , in {fc_name}")
                elif i < len(items) - 1:
                    on_error(props.start, "UNEXPECTED_TOKEN", f"Unexpected empty item in {fc_name}")
                offset = props.end
                continue
            if not is_map and _contains_newline(key):
                on_error(key, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line")
        if i == 0:
            if props.comma is not None:
                on_error(props.comma, "UNEXPECTED_TOKEN", f"Unexpected , in {fc_name}")
        else:
            if props.comma is None:
                on_error(props.start, "MISSING_CHAR", f"Missing , between {fc_name} items")
            if props.comment:
                prev_item_comment = ""
                for st in start:
                    if st["type"] in ("comma", "space"):
                        continue
                    if st["type"] == "comment":
                        prev_item_comment = st["source"][1:]
                    break
                if prev_item_comment:
                    # The twin hands this comment to the previous item; what stays here is what
                    # decides an empty node's end below.
                    props.comment = props.comment[len(prev_item_comment) + 1:]
        if not is_map and sep is None and props.found is None:
            # item is a value in a seq → key & sep are empty, start does not include ? or :
            value_node = (_compose_node(ctx, value, props, on_error) if value is not None
                          else _compose_empty_node(ctx, props.end, sep, None, props, on_error))
            coll.items.append(value_node)
            offset = value_node.range[2]
            if _is_block(value):
                on_error(value_node.range, "BLOCK_IN_FLOW", _BLOCK_IN_FLOW)
        else:
            # item is a key+value pair
            ctx.at_key = True
            key_start = props.end
            key_node = (_compose_node(ctx, key, props, on_error) if key is not None
                        else _compose_empty_node(ctx, key_start, start, None, props, on_error))
            if _is_block(key):
                on_error(key_node.range, "BLOCK_IN_FLOW", _BLOCK_IN_FLOW)
            ctx.at_key = False
            # value properties
            value_props = _resolve_props(sep if sep is not None else [], fc_name, "map-value-ind", value,
                                         key_node.range[2], on_error, fc["indent"], False)
            if value_props.found is not None:
                if not is_map and props.found is None:
                    if sep is not None:
                        for st in sep:
                            if st is value_props.found:
                                break
                            if st["type"] == "newline":
                                on_error(st, "MULTILINE_IMPLICIT_KEY",
                                         "Implicit keys of flow sequence pairs need to be on a single line")
                                break
                    if props.start < value_props.found["offset"] - 1024:
                        on_error(value_props.found, "KEY_OVER_1024_CHARS",
                                 "The : indicator must be at most 1024 chars after the start of an implicit flow sequence key")
            elif value is not None:
                if "source" in value and _at(value["source"], 0) == ":":
                    on_error(value, "MISSING_CHAR", f"Missing space after : in {fc_name}")
                else:
                    on_error(value_props.start, "MISSING_CHAR", f"Missing , or : between {fc_name} items")
            # value value
            if value is not None:
                value_node = _compose_node(ctx, value, value_props, on_error)
            elif value_props.found is not None:
                value_node = _compose_empty_node(ctx, value_props.end, sep, None, value_props, on_error)
            else:
                value_node = None
            if value_node is not None and _is_block(value):
                on_error(value_node.range, "BLOCK_IN_FLOW", _BLOCK_IN_FLOW)
            pair = _Pair(key_node, value_node)
            if is_map:
                if _map_includes(coll.items, key_node):
                    on_error(key_start, "DUPLICATE_KEY", "Map keys must be unique")
                coll.items.append(pair)
            else:
                m = _Map(flow=True)
                m.items.append(pair)
                end_range = (value_node if value_node is not None else key_node).range
                m.range = [key_node.range[0], end_range[1], end_range[2]]
                coll.items.append(m)
            offset = value_node.range[2] if value_node is not None else value_props.end
    expected_end = "}" if is_map else "]"
    ends = fc["end"]
    ce = ends[0] if ends else None
    ee = ends[1:]
    ce_pos = offset
    if ce is not None and ce["source"] == expected_end:
        ce_pos = ce["offset"] + len(ce["source"])
    else:
        name = fc_name[0].upper() + fc_name[1:]
        if at_root:
            on_error(offset, "MISSING_CHAR", f"{name} must end with a {expected_end}")
        else:
            on_error(offset, "BAD_INDENT", f"{name} in block collection must be sufficiently indented and end with a {expected_end}")
        if ce is not None and len(ce["source"]) != 1:
            ee.insert(0, ce)
    if ee:
        _, end_offset = _resolve_end(ee, ce_pos, True, on_error)
        coll.range = [fc["offset"], ce_pos, end_offset]
    else:
        coll.range = [fc["offset"], ce_pos, ce_pos]
    return coll


# ── Scalars (compose/resolve-flow-scalar.js, compose/resolve-block-scalar.js) ────────────────

def _resolve_flow_scalar(scalar, strict, on_error):
    """(value, comment, range) of a plain or quoted scalar."""
    offset = scalar["offset"]
    t = scalar["type"]
    source = scalar["source"]

    def rel_error(rel, code, msg):
        on_error(offset + rel, code, msg)

    if t == "scalar":
        value = _plain_value(source, rel_error)
    elif t == "single-quoted-scalar":
        value = _single_quoted_value(source, rel_error)
    elif t == "double-quoted-scalar":
        value = _double_quoted_value(source, rel_error)
    else:
        on_error(scalar, "UNEXPECTED_TOKEN", f"Expected a flow scalar value, but found: {t}")
        return "", "", [offset, offset + len(source), offset + len(source)]
    value_end = offset + len(source)
    comment, re_offset = _resolve_end(scalar.get("end"), value_end, strict, on_error)
    return value, comment, [offset, value_end, re_offset]


def _plain_value(source, on_error):
    bad_char = ""
    c = _at(source, 0)
    if c == "\t":
        bad_char = "a tab character"
    elif c == ",":
        bad_char = "flow indicator character ,"
    elif c == "%":
        bad_char = "directive indicator character %"
    elif c == "|" or c == ">":
        bad_char = f"block scalar indicator {c}"
    elif c == "@" or c == "`":
        bad_char = f"reserved character {c}"
    if bad_char:
        on_error(0, "BAD_SCALAR_START", f"Plain value cannot start with {bad_char}")
    return _fold_lines(source)


def _single_quoted_value(source, on_error):
    if _at(source, len(source) - 1) != "'" or len(source) == 1:
        on_error(len(source), "MISSING_CHAR", "Missing closing 'quote")
    return _fold_lines(source[1:-1]).replace("''", "'")


_FOLD_FIRST = re.compile(r"(.*?)(?<![ \t])[ \t]*\r?\n", re.S)
_FOLD_LINE = re.compile(r"[ \t]*(.*?)(?:(?<![ \t])[ \t]*)?\r?\n", re.S)
_FOLD_LAST = re.compile(r"[ \t]*(.*)", re.S)


def _fold_lines(source):
    match = _FOLD_FIRST.match(source)
    if not match:
        return source
    res = match.group(1)
    sep = " "
    pos = match.end()
    while True:
        match = _FOLD_LINE.match(source, pos)
        if not match:
            break
        if match.group(1) == "":
            if sep == "\n":
                res += sep
            else:
                sep = "\n"
        else:
            res += sep + match.group(1)
            sep = " "
        pos = match.end()
    match = _FOLD_LAST.match(source, pos)
    return res + sep + (match.group(1) if match else "")


_ESCAPE_CODES = {"0": "\0", "a": "\x07", "b": "\b", "e": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
                 "v": "\v", "N": "\u0085", "_": "\u00a0", "L": "\u2028", "P": "\u2029", " ": " ", '"': '"',
                 "/": "/", "\\": "\\", "\t": "\t"}
_HEX_RUN = re.compile(r"[0-9a-fA-F]+")


def _double_quoted_value(source, on_error):
    res = []
    n = len(source)
    i = 1
    while i < n - 1:
        ch = source[i]
        if ch == "\r" and _at(source, i + 1) == "\n":
            i += 1
            continue
        if ch == "\n":
            fold, i = _fold_newline(source, i)
            res.append(fold)
        elif ch == "\\":
            i += 1
            nxt = _at(source, i)
            cc = _ESCAPE_CODES.get(nxt) if nxt is not None else None
            if cc:
                res.append(cc)
            elif nxt == "\n":
                # skip escaped newlines, but still trim the following line
                nxt = _at(source, i + 1)
                while nxt == " " or nxt == "\t":
                    i += 1
                    nxt = _at(source, i + 1)
            elif nxt == "\r" and _at(source, i + 1) == "\n":
                # skip escaped CRLF newlines, but still trim the following line
                i += 1
                nxt = _at(source, i + 1)
                while nxt == " " or nxt == "\t":
                    i += 1
                    nxt = _at(source, i + 1)
            elif nxt in ("x", "u", "U"):
                length = 2 if nxt == "x" else 4 if nxt == "u" else 8
                res.append(_parse_char_code(source, i + 1, length, on_error))
                i += length
            else:
                raw = source[i - 1:i + 1]
                on_error(i - 1, "BAD_DQ_ESCAPE", f"Invalid escape sequence {raw}")
                res.append(raw)
        elif ch == " " or ch == "\t":
            # trim trailing whitespace
            ws_start = i
            nxt = _at(source, i + 1)
            while nxt == " " or nxt == "\t":
                i += 1
                nxt = _at(source, i + 1)
            if nxt != "\n" and not (nxt == "\r" and _at(source, i + 2) == "\n"):
                res.append(source[ws_start:i + 1] if i > ws_start else ch)
        else:
            res.append(ch)
        i += 1
    if _at(source, n - 1) != '"' or n == 1:
        on_error(n, "MISSING_CHAR", 'Missing closing "quote')
    return "".join(res)


def _fold_newline(source, offset):
    """Fold a single newline into a space, multiple newlines to N - 1 newlines."""
    fold = ""
    ch = _at(source, offset + 1)
    while ch in (" ", "\t", "\n", "\r"):
        if ch == "\r" and _at(source, offset + 2) != "\n":
            break
        if ch == "\n":
            fold += "\n"
        offset += 1
        ch = _at(source, offset + 1)
    return fold or " ", offset


def _parse_char_code(source, offset, length, on_error):
    cc = source[offset:offset + length]
    if len(cc) == length and _HEX_RUN.fullmatch(cc):
        code = int(cc, 16)
        if code <= 0x10FFFF:  # String.fromCodePoint
            return _from_code_point(code)
    raw = source[offset - 2:offset + length]
    on_error(offset - 2, "BAD_DQ_ESCAPE", f"Invalid escape sequence {raw}")
    return raw


def _resolve_block_scalar(ctx, scalar, on_error):
    """(value, comment, range) of a literal or folded block scalar."""
    start = scalar["offset"]
    header = _parse_block_scalar_header(scalar, True, on_error)
    if header is None:
        return "", "", [start, start, start]
    mode, header_indent, chomp, comment, header_length = header
    literal = mode != ">"
    source = scalar["source"]
    lines = _split_lines(source) if source else []
    # determine the end of content & start of chomping
    chomp_start = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        content = lines[i][1]
        if content == "" or content == "\r":
            chomp_start = i
        else:
            break
    # shortcut for empty contents
    if chomp_start == 0:
        value = "\n" * max(1, len(lines) - 1) if chomp == "+" and lines else ""
        end = start + header_length
        if source:
            end += len(source)
        return value, comment, [start, end, end]
    # find the indentation level to trim from start
    trim_indent = scalar["indent"] + header_indent
    offset = scalar["offset"] + header_length
    content_start = 0
    for i in range(chomp_start):
        indent, content = lines[i]
        if content == "" or content == "\r":
            if header_indent == 0 and len(indent) > trim_indent:
                trim_indent = len(indent)
        else:
            if len(indent) < trim_indent:
                on_error(offset + len(indent), "MISSING_CHAR",
                         "Block scalars with more-indented leading empty lines must use an explicit indentation indicator")
            if header_indent == 0:
                trim_indent = len(indent)
            content_start = i
            if trim_indent == 0 and not ctx.at_root:
                on_error(offset, "BAD_INDENT", "Block scalar values in collections must be indented")
            break
        offset += len(indent) + len(content) + 1
    # include trailing more-indented empty lines in content
    i = len(lines) - 1
    while i >= chomp_start:
        if len(lines[i][0]) > trim_indent:
            chomp_start = i + 1
        i -= 1
    value = ""
    sep = ""
    prev_more_indented = False
    # leading whitespace is kept intact
    for i in range(content_start):
        value += lines[i][0][trim_indent:] + "\n"
    for i in range(content_start, chomp_start):
        indent, content = lines[i]
        offset += len(indent) + len(content) + 1
        crlf = _at(content, len(content) - 1) == "\r"
        if crlf:
            content = content[:-1]
        if content and len(indent) < trim_indent:
            src = "explicit indentation indicator" if header_indent else "first line"
            on_error(offset - len(content) - (2 if crlf else 1), "BAD_INDENT",
                     f"Block scalar lines must not be less indented than their {src}")
            indent = ""
        if literal:
            value += sep + indent[trim_indent:] + content
            sep = "\n"
        elif len(indent) > trim_indent or _at(content, 0) == "\t":
            # more-indented content within a folded block
            if sep == " ":
                sep = "\n"
            elif not prev_more_indented and sep == "\n":
                sep = "\n\n"
            value += sep + indent[trim_indent:] + content
            sep = "\n"
            prev_more_indented = True
        elif content == "":
            # empty line
            if sep == "\n":
                value += "\n"
            else:
                sep = "\n"
        else:
            value += sep + content
            sep = " "
            prev_more_indented = False
    if chomp == "-":
        pass
    elif chomp == "+":
        for i in range(chomp_start, len(lines)):
            value += "\n" + lines[i][0][trim_indent:]
        if _at(value, len(value) - 1) != "\n":
            value += "\n"
    else:
        value += "\n"
    end = start + header_length + len(source)
    return value, comment, [start, end, end]


def _parse_block_scalar_header(scalar, strict, on_error):
    props = scalar["props"]
    if props[0]["type"] != "block-scalar-header":
        on_error(props[0], "IMPOSSIBLE", "Block scalar header not found")
        return None
    source = props[0]["source"]
    mode = source[0]
    indent = 0
    chomp = ""
    error = -1
    for i in range(1, len(source)):
        ch = source[i]
        if not chomp and (ch == "-" or ch == "+"):
            chomp = ch
        else:
            n = ord(ch) - 48 if "1" <= ch <= "9" else 0  # Number(ch): only 1-9 are true
            if not indent and n:
                indent = n
            elif error == -1:
                error = scalar["offset"] + i
    if error != -1:
        on_error(error, "UNEXPECTED_TOKEN", f"Block scalar header includes extra characters: {source}")
    has_space = False
    comment = ""
    length = len(source)
    for token in props[1:]:
        t = token["type"]
        if t == "space":
            has_space = True
            length += len(token["source"])
        elif t == "newline":
            length += len(token["source"])
        elif t == "comment":
            if strict and not has_space:
                on_error(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters")
            length += len(token["source"])
            comment = token["source"][1:]
        elif t == "error":
            on_error(token, "UNEXPECTED_TOKEN", token["message"])
            length += len(token["source"])
        else:
            on_error(token, "UNEXPECTED_TOKEN", f"Unexpected token in block scalar header: {t}")
            ts = token.get("source")
            if ts and isinstance(ts, str):
                length += len(ts)
    return mode, indent, chomp, comment, length


_SPLIT_LINES = re.compile(r"\n( *)")
_LEADING_SPACES = re.compile(r" *")


def _split_lines(source):
    """Lines as [indent, content]."""
    split = _SPLIT_LINES.split(source)
    first = split[0]
    spaces = _LEADING_SPACES.match(first).group()
    lines = [[spaces, first[len(spaces):]] if spaces else ["", first]]
    for i in range(1, len(split), 2):
        lines.append([split[i], split[i + 1]])
    return lines


# ── Errors (errors.js) ────────────────────────────────────────────────────────────────────────

def _prettify(src, lc, error):
    """The line and column after the message, and the line itself, as the twin writes them."""
    if error.pos is None or error.pos[0] == -1:
        return
    line, col = lc.line_pos(error.pos[0])
    end_line, end_col = lc.line_pos(error.pos[1])
    error.message += f" at line {line}, column {col}"
    ci = col - 1
    line_str = re.sub(r"[\n\r]+\Z", "", _substring(src, lc.start(line - 1), lc.start(line)))
    # Trim to max 80 chars, keeping col position near the middle
    if ci >= 60 and len(line_str) > 80:
        trim_start = min(ci - 39, len(line_str) - 79)
        line_str = "…" + line_str[trim_start:]
        ci -= trim_start - 1
    if len(line_str) > 80:
        line_str = line_str[:79] + "…"
    # Include previous line in context if pointing at line start
    if line > 1 and re.fullmatch(r" *", line_str[:max(ci, 0)]):
        prev = _substring(src, lc.start(line - 2), lc.start(line - 1))
        if len(prev) > 80:
            prev = prev[:79] + "…\n"
        line_str = prev + line_str
    if re.search(r"[^ ]", line_str):
        count = 1
        if end_line == line and end_col > col:
            count = max(1, min(end_col - col, 80 - ci))
        error.message += f":\n\n{line_str}\n{' ' * ci}{'^' * count}\n"


# ── To plain values (nodes/toJS.js, nodes/Alias.js, nodes/addPairToJSMap.js) ─────────────────

class _ToJS:
    def __init__(self, doc):
        self.anchors = {}  # id(node) → [node, data]
        self.doc = doc
        self.on_create = None
        self.nodes = None  # Alias.resolve's list, kept: the document does not change


class _AnchorData:
    __slots__ = ("alias_count", "count", "res")

    def __init__(self):
        self.alias_count = 0
        self.count = 1
        self.res = _UNDEFINED


def _visit_nodes(doc):
    """Every node of the document in the twin's `visit` order, depth first, a node before its items."""
    out = []
    stack = [doc.contents]
    while stack:
        node = stack.pop()
        if node is None:
            continue
        if isinstance(node, _Pair):
            stack.append(node.value)
            stack.append(node.key)
            continue
        out.append(node)
        if isinstance(node, (_Map, _Seq)):
            stack.extend(reversed(node.items))
    return out


def _resolve_alias(alias, ctx):
    """The last node before the alias with its anchor."""
    if ctx.nodes is None:
        ctx.nodes = [node for node in _visit_nodes(ctx.doc) if isinstance(node, _Alias) or _has_anchor(node)]
    found = None
    for node in ctx.nodes:
        if node is alias:
            break
        if getattr(node, "anchor", None) == alias.source:
            found = node
    return found


def _alias_count(node, ctx):
    if isinstance(node, _Alias):
        source = _resolve_alias(node, ctx)
        entry = ctx.anchors.get(id(source)) if source is not None else None
        return entry[1].count * entry[1].alias_count if entry is not None else 0
    if isinstance(node, (_Map, _Seq)):
        count = 0
        for item in node.items:
            c = _alias_count(item, ctx)
            if c > count:
                count = c
        return count
    if isinstance(node, _Pair):
        return max(_alias_count(node.key, ctx), _alias_count(node.value, ctx))
    return 1


def _to_js(node, ctx):
    if node is None:
        return None
    if not _has_anchor(node):
        return _to_json(node, ctx)
    data = _AnchorData()
    ctx.anchors[id(node)] = [node, data]

    def on_create(res):
        data.res = res
        ctx.on_create = None
    ctx.on_create = on_create
    res = _to_json(node, ctx)
    if ctx.on_create is not None:
        ctx.on_create(res)
    return res


def _to_json(node, ctx):
    if isinstance(node, _Scalar):
        return node.out
    if isinstance(node, _Map):
        res = {}
        if ctx.on_create is not None:
            ctx.on_create(res)
        for pair in node.items:
            js_key = _to_js(pair.key, ctx)
            key = _stringify_key(js_key)
            res[key] = _to_js(pair.value, ctx)
        _js_key_order(res)
        return res
    if isinstance(node, _Seq):
        res = []
        if ctx.on_create is not None:
            ctx.on_create(res)
        for item in node.items:
            res.append(_to_js(item, ctx))
        return res
    if isinstance(node, _Alias):
        source = _resolve_alias(node, ctx)
        if source is None:
            raise YAMLError(None, "REFERENCE",
                            f"Unresolved alias (the anchor must be set before the alias): {_from16(node.source)}")
        entry = ctx.anchors.get(id(source))
        if entry is None:
            # Resolve anchors for Node.prototype.toJS()
            _to_js(source, ctx)
            entry = ctx.anchors.get(id(source))
        data = entry[1] if entry is not None else None
        if data is None or data.res is _UNDEFINED:
            raise YAMLError(None, "REFERENCE", "This should not happen: Alias anchor was not resolved?")
        data.count += 1
        if data.alias_count == 0:
            data.alias_count = _alias_count(source, ctx)
        if data.count * data.alias_count > 100:  # maxAliasCount
            raise YAMLError(None, "REFERENCE", "Excessive alias count indicates a resource exhaustion attack")
        return data.res
    return node


def _stringify_key(js_key):
    if js_key is None:
        return ""
    if isinstance(js_key, (dict, list)):  # refused before conversion: see _rules
        raise AssertionError("a collection key reached the conversion")
    return js_string(js_key)


_ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")


def _js_key_order(res):
    """A JavaScript object's own keys: those that are array indices first, ascending, then the
    rest in the order they were added."""
    indices = [key for key in res if _ARRAY_INDEX.fullmatch(key) and int(key) < 2 ** 32 - 1]
    if not indices:
        return
    index_set = set(indices)
    order = sorted(indices, key=int) + [key for key in res if key not in index_set]
    if order == list(res):
        return
    items = [(key, res[key]) for key in order]
    res.clear()
    res.update(items)


# ── What both implementations add ─────────────────────────────────────────────────────────────

def _located(src, lc, message, offset):
    error = YAMLError([offset, offset + 1], "USEDESIGN", message)
    _prettify(src, lc, error)
    error.message = _from16(error.message)
    return error


_LONE_SURROGATE = re.compile("[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]")


def _rules(doc, src, lc):
    """A collection as a map key, an alias inside the node it names, and a string with half of a
    character in it — which only an escape writes, `"\\ud800"` — are refused, in the order the
    twin's `visit` meets them. The last is a string JavaScript keeps and this module cannot print:
    two such keys were two there and one here."""
    anchors = {}
    path = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, _Alias):
            target = anchors.get(node.source)
            if target is not None and any(p is target for p in path):
                raise _located(src, lc, f"Alias *{node.source} is inside the node it refers to", node.range[0])
            return
        if node.anchor:
            anchors[node.anchor] = node
        if isinstance(node, _Scalar) and isinstance(node.value, str) and _LONE_SURROGATE.search(node.value):
            raise _located(src, lc, "A string holds half of a surrogate pair, which is not a character", node.range[0])
        if isinstance(node, (_Map, _Seq)):
            path.append(node)
            for item in node.items:
                if isinstance(item, _Pair):
                    key = anchors.get(item.key.source) if isinstance(item.key, _Alias) else item.key
                    if isinstance(key, (_Map, _Seq)):
                        raise _located(src, lc, "Map keys must be scalars", item.key.range[0])
                    path.append(item)
                    walk(item.key)
                    walk(item.value)
                    path.pop()
                else:
                    walk(item)
            path.pop()

    walk(doc.contents)


def _document(text: str):
    """(document, text, line counter): the document as the twin's `parseDocument` returns it, its
    errors and warnings with their lines and columns written out — every one of them, for the
    differential test of this port; `load` throws the first."""
    src = _to16(text)
    lc = _LineCounter()
    tokens = _Parser(lc.add_new_line).parse(src)
    if _too_deep(tokens):
        raise YAMLError(None, "USEDESIGN", DEEP)
    composer = _Composer()
    doc = None
    for composed in composer.compose(tokens, len(src)):
        if doc is None:
            doc = composed
        else:
            doc.errors.append(YAMLError(composed.range[0:2], "MULTIPLE_DOCS",
                                        "Source contains multiple documents; please use YAML.parseAllDocuments()"))
            break
    for error in doc.errors + doc.warnings:
        _prettify(src, lc, error)
        error.message = _from16(error.message)
    return doc, src, lc
