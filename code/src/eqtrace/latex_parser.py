"""Fully consuming LaTeX subset parser. No CAS parser or eval."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .ir import Expr, Unsupported, number, check_complexity

GREEK = {"alpha", "beta", "gamma", "delta", "epsilon", "theta", "lambda", "mu", "sigma", "tau"}


def strip_comments(text: str) -> str:
    # Preserve length and line positions. An even backslash count leaves % active.
    lines = []
    for line in text.splitlines(keepends=True):
        for i, ch in enumerate(line):
            if ch == "%":
                slashes, k = 0, i - 1
                while k >= 0 and line[k] == "\\":
                    slashes += 1; k -= 1
                if slashes % 2 == 0:
                    line = line[:i] + " " * (len(line.rstrip("\n")) - i) + ("\n" if line.endswith("\n") else "")
                    break
        lines.append(line)
    return "".join(lines)


def equations(text: str) -> dict[str, dict]:
    clean = strip_comments(text)
    found = {}
    for m in re.finditer(r"\\begin\{equation(\*?)\}(.*?)\\end\{equation\1\}", clean, re.S):
        body = m.group(2)
        labels = list(re.finditer(r"\\label\{([^{}]+)\}", body))
        if not labels: continue
        if len(labels) != 1: raise Unsupported("Each equation must have exactly one label")
        label = labels[0].group(1)
        if label in found: raise Unsupported(f"Duplicate equation label: {label}")
        body = re.sub(r"\\label\{[^{}]+\}", lambda x: " " * len(x.group()), body)
        found[label] = {"text": body, "line": clean.count("\n", 0, m.start(2)) + 1}
    # Labels inside unsupported display environments must not quietly disappear.
    all_labels = set(re.findall(r"\\label\{(eq:[^{}]+)\}", clean))
    missing = all_labels - found.keys()
    if missing: raise Unsupported(f"Equation labels outside supported equation environment: {sorted(missing)}")
    return found


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int


def tokenize(text: str, start_line=1) -> list[Token]:
    if len(text) > 10000: raise Unsupported("Equation exceeds 10000 characters")
    result, i = [], 0
    while i < len(text):
        if text[i].isspace(): i += 1; continue
        line = start_line + text.count("\n", 0, i)
        col = i - text.rfind("\n", 0, i)
        rest = text[i:]
        kind, val, size = "", "", 0
        if rest[0] == "\\":
            m = re.match(r"\\([A-Za-z]+|[,!;: ])", rest)
            if not m: raise Unsupported(f"Invalid command at {line}:{col}")
            cmd, size = m.group(1), len(m.group())
            if cmd in {"left", "right", ",", "!", ";", ":", " "}: i += size; continue
            if cmd in {"cdot", "times"}: kind, val = "*", "*"
            elif cmd in GREEK: kind, val = "var", cmd
            elif cmd == "mathrm":
                n = re.match(r"\\mathrm\{([A-Za-z][A-Za-z0-9_]*)\}", rest)
                if not n: raise Unsupported(f"Expected a single identifier in \\mathrm at {line}:{col}")
                kind, val, size = "var", n.group(1), len(n.group())
            elif cmd in {"frac", "sqrt", "exp", "log"}: kind, val = cmd, cmd
            else: raise Unsupported(f"Unsupported LaTeX command \\{cmd} at {line}:{col}")
        elif rest[0].isdigit() or (rest[0] == "." and len(rest) > 1 and rest[1].isdigit()):
            n = re.match(r"(?:\d+(?:\.\d*)?|\.\d+)", rest)
            kind, val, size = "num", n.group(), len(n.group())
        elif rest[0].isascii() and rest[0].isalpha():
            n = re.match(r"([A-Za-z])(?:_(?:\{(\d+)\}|(\d+)))?", rest)
            val = n.group(1) + ("_" + (n.group(2) or n.group(3)) if n.group(2) or n.group(3) else "")
            kind, size = "var", len(n.group())
        elif rest[0] in "+-*/^(){}=": kind = val = rest[0]; size = 1
        else: raise Unsupported(f"Unsupported token {rest[0]!r} at {line}:{col}")
        result.append(Token(kind, val, line, col)); i += size
    if len(result) > 512: raise Unsupported("Equation exceeds 512 tokens")
    result.append(Token("end", "", start_line + text.count("\n"), 0))
    return result


class Parser:
    def __init__(self, text, start_line=1): self.tokens = tokenize(text, start_line); self.i = 0
    @property
    def token(self): return self.tokens[self.i]
    def take(self, kind=None):
        t = self.token
        if kind and t.kind != kind: raise Unsupported(f"Expected {kind}, got {t.kind} at {t.line}:{t.col}")
        self.i += 1
        return t
    def group(self):
        t = self.take()
        if t.kind not in ("{", "("): raise Unsupported(f"Expected grouped argument at {t.line}:{t.col}")
        value = self.add()
        self.take("}" if t.kind == "{" else ")")
        return value
    def add(self):
        left = self.mul()
        while self.token.kind in ("+", "-"):
            t = self.take(); right = self.mul()
            left = Expr("add" if t.kind == "+" else "sub", (left, right), line=t.line, column=t.col)
        return left
    def mul(self):
        left = self.unary()
        starts = {"var", "num", "(", "{", "frac", "sqrt", "exp", "log"}
        while self.token.kind in {"*", "/"} | starts:
            t = self.token
            if t.kind in ("*", "/"): self.take(); op = "mul" if t.kind == "*" else "div"
            else:
                if t.kind == "num" and self.tokens[self.i - 1].kind == "num":
                    raise Unsupported("Adjacent numeric literals require an explicit operator")
                op = "mul"
            right = self.unary()
            left = Expr(op, (left, right), line=t.line, column=t.col)
        return left
    def unary(self):
        if self.token.kind in ("+", "-"):
            t = self.take(); a = self.unary()
            return a if t.kind == "+" else Expr("neg", (a,), line=t.line, column=t.col)
        left = self.atom()
        if self.token.kind == "^":
            t = self.take(); brace = self.token.kind == "{"
            if brace: self.take()
            sign = -1 if self.token.kind == "-" else 1
            if self.token.kind in ("+", "-"): self.take()
            n = self.take("num")
            if not n.value.isdigit() or abs(int(n.value)) > 8:
                raise Unsupported("Only literal integer powers from -8 to 8 are supported")
            if brace: self.take("}")
            left = Expr("pow", (left,), str(sign * int(n.value)), t.line, t.col)
        return left
    def atom(self):
        t = self.token
        if t.kind == "num": self.take(); return number(t.value, t.line, t.col)
        if t.kind == "var": self.take(); return Expr("var", value=t.value, line=t.line, column=t.col)
        if t.kind in ("(", "{"): return self.group()
        if t.kind == "frac":
            self.take(); a, b = self.group(), self.group()
            return Expr("div", (a, b), line=t.line, column=t.col)
        if t.kind in ("sqrt", "exp", "log"):
            self.take(); return Expr(t.kind, (self.group(),), line=t.line, column=t.col)
        raise Unsupported(f"Expected expression, got {t.kind} at {t.line}:{t.col}")


def parse_expression(text: str, start_line=1) -> Expr:
    p = Parser(text, start_line)
    try: out = p.add(); p.take("end")
    except RecursionError as exc: raise Unsupported("Expression nesting is too deep") from exc
    check_complexity(out)
    return out


def parse_equation(text: str, inputs: list[str], start_line=1) -> tuple[str, Expr]:
    p = Parser(text, start_line)
    name = p.take("var").value; p.take("=")
    try: out = p.add(); p.take("end")
    except RecursionError as exc: raise Unsupported("Expression nesting is too deep") from exc
    unknown = out.variables() - set(inputs)
    if unknown: raise Unsupported(f"Undeclared equation symbols: {sorted(unknown)}")
    if name in inputs: raise Unsupported("Output symbol must be distinct from inputs")
    check_complexity(out)
    return name, out
