"""Explicit straight-line algorithmic subset and minimal SSA exporters."""
from __future__ import annotations
import re
from itertools import islice
from .ir import Expr, Unsupported, latex, latex_name, python_expr, walk, check_complexity
from .latex_parser import strip_comments, parse_equation


def algorithms(text: str) -> dict:
    clean, found = strip_comments(text), {}
    for m in re.finditer(r"\\begin\{algorithm\}(?:\[[^\]]*\])?(.*?)\\end\{algorithm\}", clean, re.S):
        labels = re.findall(r"\\label\{([^{}]+)\}", m.group(1))
        if not labels: continue
        if len(labels) != 1 or labels[0] in found: raise Unsupported("Algorithms require one unique label")
        inner = re.search(r"\\begin\{algorithmic\}(?:\[\d+\])?(.*?)\\end\{algorithmic\}", m.group(1), re.S)
        if not inner: raise Unsupported("Labeled algorithm requires an algorithmic environment")
        found[labels[0]] = {"text": inner.group(1), "line": clean.count("\n", 0, m.start(1) + inner.start(1)) + 1, "kind": "pseudocode"}
    missing = set(re.findall(r"\\label\{(alg:[^{}]+)\}", clean)) - found.keys()
    if missing: raise Unsupported(f"Unsupported algorithm environment: {sorted(missing)}")
    return found


def parse_pseudocode(text: str, inputs: list[str], start_line=1) -> tuple[str, Expr]:
    env = {n: Expr("var", value=n, line=start_line) for n in inputs}
    assigned, used = set(), set()
    required, result, output = False, None, "result"
    def expression(rhs, line):
        _, parsed = parse_equation("\\mathrm{EqTraceOutput} = " + rhs, list(env), line)
        def expand(n):
            if n.op == "var": used.add(n.value); return env[n.value]
            return Expr(n.op, tuple(expand(a) for a in n.args), n.value, n.line, n.column)
        expanded = expand(parsed)
        if len(list(islice(walk(expanded), 2049))) > 2048: raise Unsupported("Expanded pseudocode exceeds 2048 nodes")
        check_complexity(expanded)
        return expanded
    for offset, raw in enumerate(strip_comments(text).splitlines()):
        line, raw = start_line + offset, raw.strip()
        if not raw: continue
        if result is not None: raise Unsupported(f"Statements after Return at line {line}")
        req = re.fullmatch(r"\\Require\s*\$(.+)\$", raw)
        ensure = re.fullmatch(r"\\Ensure\s*\$(.+)\$", raw)
        ret = re.fullmatch(r"(?:\\State\s*)?\\Return\s*\$(.+)\$", raw)
        state = re.fullmatch(r"\\State\s*\$(.+?)\s*\\gets\s*(.+)\$", raw)
        if req:
            if required or assigned: raise Unsupported("Require must occur once before assignments")
            names = [parse_equation(part.strip() + " = 0", [], line)[0] for part in req.group(1).split(",")]
            if names != inputs: raise Unsupported(f"Pseudocode Require {names} disagrees with ordered inputs {inputs}")
            required = True
        elif ensure:
            output, _ = parse_equation(ensure.group(1) + " = 0", [], line)
            if output in inputs: raise Unsupported("Ensure output must be distinct from inputs")
        elif ret:
            if not required: raise Unsupported("Pseudocode requires an explicit Require declaration")
            result = expression(ret.group(1), line)
        elif state:
            if not required: raise Unsupported("Pseudocode requires an explicit Require declaration")
            name, _ = parse_equation(state.group(1) + " = 0", [], line)
            if name in env or name == "EqTraceOutput": raise Unsupported(f"Reassignment at line {line}")
            env[name] = expression(state.group(2), line); assigned.add(name)
        else: raise Unsupported(f"Unsupported pseudocode at line {line}: {raw[:100]}")
    if result is None: raise Unsupported("Pseudocode must contain one final Return")
    if assigned - used: raise Unsupported(f"Unused pseudocode assignments: {sorted(assigned - used)}")
    return output, result


def pseudocode(expr: Expr, inputs: list[str], tex=False) -> str:
    lines, seen = [], {}
    def visit(n):
        if n.op in ("var", "const"): return n
        key = n.fingerprint()
        if key in seen: return seen[key]
        args = tuple(visit(a) for a in n.args)
        i = len(seen); name = f"t_{i}"
        while name in inputs or name in {v.value for v in seen.values()}: i += 1; name = f"t_{i}"
        simplified = Expr(n.op, args, n.value)
        if tex: lines.append(f"\\State ${latex_name(name)} \\gets {latex(simplified)}$")
        else: lines.append(f"{name} <- {python_expr(simplified)}")
        seen[key] = Expr("var", value=name)
        return seen[key]
    root = visit(expr)
    if tex:
        return "\\begin{algorithmic}\n\\Require $" + ", ".join(latex_name(n) for n in inputs) + "$\n" + "\n".join(lines) + f"\n\\State \\Return ${latex(root)}$\n\\end{{algorithmic}}\n"
    return "inputs " + ", ".join(inputs) + "\n" + "\n".join(lines) + f"\nreturn {python_expr(root)}\n"
