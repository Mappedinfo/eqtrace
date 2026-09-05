"""Ordered scalar expressions: one representation for exporters and checks."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from typing import Mapping


class Unsupported(ValueError):
    """Input has no declared semantics in EqTrace's accepted subset."""


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple[Expr, ...] = ()
    value: str = ""
    line: int = 0
    column: int = 0

    def semantic(self):
        return [self.op, self.value, [a.semantic() for a in self.args]]

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.semantic(), separators=(",", ":")).encode()).hexdigest()

    def variables(self) -> set[str]:
        return {self.value} if self.op == "var" else set().union(*(a.variables() for a in self.args))


def number(value: str, line=0, column=0) -> Expr:
    if len(value) > 128:
        raise Unsupported("Numeric literal exceeds 128 characters")
    try:
        n = Fraction(value)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise Unsupported(f"Invalid finite rational: {value}") from exc
    if max(n.numerator.bit_length(), n.denominator.bit_length()) > 4096:
        raise Unsupported("Numeric literal exceeds 4096 bits")
    return Expr("const", value=str(n), line=line, column=column)


def walk(expr: Expr):
    yield expr
    for child in expr.args:
        yield from walk(child)


def check_complexity(expr: Expr, depth=0):
    if depth > 48: raise Unsupported("Expression depth exceeds 48")
    # Reject nested exponent towers even when the input is syntactically small.
    def power_weight(n):
        child = max((power_weight(c) for c in n.args), default=1)
        return child * max(1, abs(int(n.value))) if n.op == "pow" else child
    if depth == 0 and power_weight(expr) > 64: raise Unsupported("Cumulative power degree exceeds 64")
    for child in expr.args: check_complexity(child, depth + 1)


def evaluate(expr: Expr, values: Mapping[str, float | Fraction]):
    """Exact rationals until an elementary function explicitly requires libm."""
    if expr.op == "var":
        v = values[expr.value]
        return v if isinstance(v, Fraction) else Fraction(v)
    if expr.op == "const":
        return Fraction(expr.value)
    a = [evaluate(child, values) for child in expr.args]
    if expr.op == "add": return a[0] + a[1]
    if expr.op == "sub": return a[0] - a[1]
    if expr.op == "mul": return a[0] * a[1]
    if expr.op == "div": return a[0] / a[1]
    if expr.op == "pow": return a[0] ** int(expr.value)
    if expr.op == "neg": return -a[0]
    if expr.op in ("sqrt", "exp", "log"):
        return getattr(math, expr.op)(float(a[0]))
    raise Unsupported(f"Unknown operation: {expr.op}")


def python_expr(expr: Expr) -> str:
    if expr.op == "var": return expr.value
    if expr.op == "const":
        n = Fraction(expr.value)
        return str(n.numerator) if n.denominator == 1 else f"({n.numerator} / {n.denominator})"
    a = [python_expr(c) for c in expr.args]
    if expr.op in ("add", "sub", "mul", "div"):
        return f"({a[0]} {dict(add='+', sub='-', mul='*', div='/')[expr.op]} {a[1]})"
    if expr.op == "neg": return f"(-{a[0]})"
    if expr.op == "pow": return f"({a[0]} ** {expr.value})"
    return f"math.{expr.op}({a[0]})"


def python_function(expr: Expr, inputs: list[str], name="reference") -> str:
    prefix = "import math\n\n" if any(n.op in ("sqrt", "exp", "log") for n in walk(expr)) else ""
    return f"{prefix}def {name}({', '.join(inputs)}):\n    return {python_expr(expr)}\n"


def latex_name(name: str) -> str:
    if len(name) == 1: return name
    if name in {"alpha", "beta", "gamma", "delta", "epsilon", "theta", "lambda", "mu", "sigma", "tau"}:
        return "\\" + name
    if "_" in name:
        base, sub = name.split("_", 1)
        if len(base) == 1 and sub.isdigit(): return f"{base}_{{{sub}}}"
    return f"\\mathrm{{{name}}}"


def latex(expr: Expr) -> str:
    if expr.op == "var": return latex_name(expr.value)
    if expr.op == "const":
        n = Fraction(expr.value)
        return str(n.numerator) if n.denominator == 1 else f"\\frac{{{n.numerator}}}{{{n.denominator}}}"
    a = [latex(c) for c in expr.args]
    if expr.op in ("add", "sub", "mul"):
        sign = dict(add="+", sub="-", mul="\\cdot")[expr.op]
        return f"\\left({a[0]} {sign} {a[1]}\\right)"
    if expr.op == "div": return f"\\frac{{{a[0]}}}{{{a[1]}}}"
    if expr.op == "neg": return f"-\\left({a[0]}\\right)"
    if expr.op == "pow": return f"\\left({a[0]}\\right)^{{{expr.value}}}"
    if expr.op == "sqrt": return f"\\sqrt{{{a[0]}}}"
    return f"\\{expr.op}\\left({a[0]}\\right)"


def graph(expr: Expr, source: str) -> dict:
    """Merge equal subexpressions, retaining all source occurrences."""
    nodes, by_key, edges = [], {}, []
    def visit(n):
        children = [visit(a) for a in n.args]
        key = n.fingerprint()
        origin = {"source": source, "line": n.line, "column": n.column}
        if key in by_key:
            item = nodes[by_key[key]]
            if origin not in item["origins"]: item["origins"].append(origin)
            return item["id"]
        idx = len(nodes)
        nid = f"n{idx}"
        by_key[key] = idx
        nodes.append({"id": nid, "op": n.op, "value": n.value, "inputs": children,
                      "fingerprint": key, "expression": python_expr(n), "latex": latex(n),
                      "origins": [origin]})
        edges.extend({"from": c, "to": nid, "slot": i} for i, c in enumerate(children))
        return nid
    root = visit(expr)
    return {"schema_version": 1, "root": root, "nodes": nodes, "edges": edges}


def diff(left: Expr, right: Expr, path="return") -> list[dict]:
    if left.semantic() == right.semantic(): return []
    if left.op != right.op or left.value != right.value or len(left.args) != len(right.args):
        return [{"path": path, "equation": python_expr(left), "code": python_expr(right),
                 "equation_line": left.line, "code_line": right.line}]
    result = []
    for i, (a, b) in enumerate(zip(left.args, right.args)):
        result.extend(diff(a, b, f"{path}.{left.op}[{i}]"))
    return result
