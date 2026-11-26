"""Static parser for JavaScript object literals (no code is ever executed).

Reads a module of the form `export default { ... };` and returns the literal
as Python data. It accepts only literal syntax: objects, arrays, strings
('...', "...", `...` without ${}), numbers, true/false/null/undefined,
identifier or quoted keys, comments and trailing commas. Anything else
(function calls, spreads, expressions, variables) raises JSLiteralError, so a
file that isn't plain data is rejected rather than interpreted.
"""

import re


class JSLiteralError(ValueError):
    pass


_NUM = re.compile(r"-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")
_IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}


class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0

    def error(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise JSLiteralError(f"{msg} at line {line}")

    def skip(self):
        s = self.s
        while self.i < len(s):
            c = s[self.i]
            if c in " \t\r\n﻿":
                self.i += 1
            elif s.startswith("//", self.i):
                j = s.find("\n", self.i)
                self.i = len(s) if j < 0 else j + 1
            elif s.startswith("/*", self.i):
                j = s.find("*/", self.i + 2)
                if j < 0:
                    self.error("unterminated comment")
                self.i = j + 2
            else:
                break

    def peek(self):
        self.skip()
        return self.s[self.i] if self.i < len(self.s) else ""

    def expect(self, ch):
        if self.peek() != ch:
            self.error(f"expected {ch!r}, got {self.peek()!r}")
        self.i += 1

    def value(self):
        c = self.peek()
        if c == "{":
            return self.obj()
        if c == "[":
            return self.arr()
        if c in "\"'`":
            return self.string()
        m = _NUM.match(self.s, self.i)
        if m and (c.isdigit() or c in "-."):
            self.i = m.end()
            t = m.group(0)
            return int(t, 16) if t.lower().startswith(("0x", "-0x")) else (
                float(t) if any(x in t for x in ".eE") else int(t))
        m = _IDENT.match(self.s, self.i)
        if m:
            word = m.group(0)
            lits = {"true": True, "false": False, "null": None, "undefined": None}
            if word in lits:
                self.i = m.end()
                return lits[word]
            self.error(f"non-literal identifier {word!r}")
        self.error(f"unexpected {c!r}")

    def string(self):
        q = self.s[self.i]
        self.i += 1
        out = []
        s = self.s
        while True:
            if self.i >= len(s):
                self.error("unterminated string")
            c = s[self.i]
            if c == q:
                self.i += 1
                return "".join(out)
            if q == "`" and s.startswith("${", self.i):
                self.error("template expression")
            if c == "\\":
                n = s[self.i + 1]
                if n == "u":
                    if s[self.i + 2] == "{":
                        j = s.index("}", self.i)
                        out.append(chr(int(s[self.i + 3:j], 16)))
                        self.i = j + 1
                    else:
                        out.append(chr(int(s[self.i + 2:self.i + 6], 16)))
                        self.i += 6
                    continue
                if n == "x":
                    out.append(chr(int(s[self.i + 2:self.i + 4], 16)))
                    self.i += 4
                    continue
                if n == "\n":
                    self.i += 2
                    continue
                out.append(_ESC.get(n, n))
                self.i += 2
                continue
            if c == "\n" and q != "`":
                self.error("newline in string")
            out.append(c)
            self.i += 1

    def key(self):
        c = self.peek()
        if c in "\"'":
            return self.string()
        m = _IDENT.match(self.s, self.i) or _NUM.match(self.s, self.i)
        if not m:
            self.error("bad key")
        self.i = m.end()
        return m.group(0)

    def obj(self):
        self.expect("{")
        out = {}
        while True:
            if self.peek() == "}":
                self.i += 1
                return out
            if self.s.startswith("...", self.i):
                self.error("spread")
            k = self.key()
            self.expect(":")
            out[k] = self.value()
            c = self.peek()
            if c == ",":
                self.i += 1
            elif c != "}":
                self.error(f"expected , or }} got {c!r}")

    def arr(self):
        self.expect("[")
        out = []
        while True:
            if self.peek() == "]":
                self.i += 1
                return out
            out.append(self.value())
            c = self.peek()
            if c == ",":
                self.i += 1
            elif c != "]":
                self.error(f"expected , or ] got {c!r}")


def parse_module(text):
    """Parse `export default <literal>;` (the only statement allowed)."""
    p = _Parser(text)
    p.skip()
    if not p.s.startswith("export default", p.i):
        p.error("expected 'export default'")
    p.i += len("export default")
    result = p.value()
    if p.peek() == ";":
        p.i += 1
    p.skip()
    if p.i != len(p.s):
        p.error("extra content after the literal")
    return result
