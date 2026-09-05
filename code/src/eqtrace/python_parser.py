"""Validate a target function before lowering or compiling any of its AST."""
from __future__ import annotations

import ast
from dataclasses import dataclass
import math
import re
from itertools import islice

from .ir import Expr, Unsupported, number, walk, check_complexity


@dataclass
class Function:
    expression: Expr
    inputs: list[str]
    source: str
    tree: ast.FunctionDef
    line: int

    def compile(self):
        # No module execution, decorators, annotations, defaults, or arbitrary calls.
        module = ast.fix_missing_locations(ast.Module(body=[self.tree], type_ignores=[]))
        namespace = {"__builtins__": {}, "math": math}
        exec(compile(module, "<eqtrace-validated-target>", "exec"), namespace)
        return namespace[self.tree.name]


def parse_function(source: str, name: str, inputs: list[str] | None = None) -> Function:
    if len(source) > 250000: raise Unsupported("Python file exceeds 250000 characters")
    try: module = ast.parse(source)
    except (SyntaxError, RecursionError) as exc: raise Unsupported(f"Python syntax error: {exc}") from exc
    targets = [n for n in module.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(targets) != 1: raise Unsupported(f"Expected exactly one top-level function {name!r}, found {len(targets)}")
    fn = targets[0]
    if isinstance(fn, ast.AsyncFunctionDef): raise Unsupported("Async functions are unsupported")
    args = fn.args
    if fn.decorator_list or args.defaults or args.kw_defaults or args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs:
        raise Unsupported(f"Decorators/defaults/variadic or special arguments are unsupported at line {fn.lineno}")
    if fn.returns or any(a.annotation for a in args.args) or fn.type_comment or getattr(fn, "type_params", []):
        raise Unsupported("Annotations and type parameters are outside the executable subset; use plain scalar arguments")
    names = [a.arg for a in args.args]
    if inputs is not None and names != inputs:
        raise Unsupported(f"Function inputs {names} do not match ordered contract inputs {inputs}")
    if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n) or n == "math" for n in names + [name]):
        raise Unsupported("Invalid or reserved identifier")
    # Validate the containing module's inert shape, but compile only fn. A module
    # with side effects cannot masquerade as a checked production implementation.
    for n in module.body:
        if isinstance(n, ast.FunctionDef):
            if (n.name == "math" or n.decorator_list or n.args.defaults or n.args.kw_defaults or n.returns
                    or getattr(n, "type_params", []) or any(a.annotation for a in n.args.args + n.args.kwonlyargs + n.args.posonlyargs)):
                raise Unsupported(f"Module function header can evaluate unmodeled code at line {n.lineno}")
            continue
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str): continue
        if isinstance(n, ast.Import) and len(n.names) == 1 and n.names[0].name == "math" and n.names[0].asname is None: continue
        raise Unsupported(f"Module-level {type(n).__name__} is unsupported at line {n.lineno}")
    nodes = list(ast.walk(fn))
    if len(nodes) > 512: raise Unsupported("Function exceeds 512 AST nodes")
    if any(isinstance(n, ast.Name) and n.id == "math" for n in nodes) and not any(isinstance(n, ast.Import) and n.names[0].name == "math" for n in module.body):
        raise Unsupported("math calls require an explicit module-level import math")
    env = {n: Expr("var", value=n, line=a.lineno, column=a.col_offset + 1) for n, a in zip(names, args.args)}
    assigned, used = {}, set()
    def lower(n):
        line, col = n.lineno, n.col_offset + 1
        if isinstance(n, ast.Name):
            if n.id not in env: raise Unsupported(f"Unknown symbol {n.id!r} at {line}:{col}")
            used.add(n.id)
            return env[n.id]
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            raw = ast.get_source_segment(source, n)
            if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?", raw):
                raise Unsupported(f"Unsupported numeric spelling at {line}:{col}")
            if isinstance(n.value, float) and not math.isfinite(n.value): raise Unsupported("Nonfinite literal")
            return number(raw, line, col)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            a = lower(n.operand)
            return a if isinstance(n.op, ast.UAdd) else Expr("neg", (a,), line=line, column=col)
        if isinstance(n, ast.BinOp):
            if isinstance(n.op, ast.Pow):
                exp = n.right
                sign = 1
                if isinstance(exp, ast.UnaryOp) and isinstance(exp.op, (ast.USub, ast.UAdd)):
                    sign = -1 if isinstance(exp.op, ast.USub) else 1; exp = exp.operand
                if not isinstance(exp, ast.Constant) or type(exp.value) is not int or abs(exp.value) > 8:
                    raise Unsupported(f"Only literal integer powers -8..8 at {line}:{col}")
                return Expr("pow", (lower(n.left),), str(sign * exp.value), line, col)
            op = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div"}.get(type(n.op))
            if op: return Expr(op, (lower(n.left), lower(n.right)), line=line, column=col)
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "math" and n.func.attr in ("sqrt", "exp", "log") and len(n.args) == 1 and not n.keywords):
            return Expr(n.func.attr, (lower(n.args[0]),), line=line, column=col)
        raise Unsupported(f"Unsupported {type(n).__name__} at {line}:{col}; no replacement implementation is used")
    body = fn.body[:]
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str): body.pop(0)
    if not body or not isinstance(body[-1], ast.Return) or body[-1].value is None:
        raise Unsupported(f"Function {name} must end with a value return")
    for n in body[:-1]:
        if not isinstance(n, ast.Assign) or len(n.targets) != 1 or not isinstance(n.targets[0], ast.Name):
            raise Unsupported(f"Unsupported {type(n).__name__} at line {n.lineno}; branches, fallback and dead paths are rejected")
        target = n.targets[0].id
        if target in env or target == "math" or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", target):
            raise Unsupported(f"Reassignment or reserved identifier {target!r} at line {n.lineno}")
        env[target] = lower(n.value); assigned[target] = n.lineno
        if len(list(islice(walk(env[target]), 2049))) > 2048:
            raise Unsupported("Expanded expression exceeds 2048 nodes")
        check_complexity(env[target])
    result = lower(body[-1].value)
    dead = set(assigned) - used
    if dead: raise Unsupported(f"Unused assignments have no implemented output path: {sorted(dead)}")
    if len(list(islice(walk(result), 2049))) > 2048:
        raise Unsupported("Expanded expression exceeds 2048 nodes")
    check_complexity(result)
    return Function(result, names, ast.get_source_segment(source, fn), fn, fn.lineno)
