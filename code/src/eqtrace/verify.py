"""Separate solver evidence from sampled CPython execution evidence."""
from __future__ import annotations

from fractions import Fraction
import math
import random
import time

from .ir import Expr, Unsupported, evaluate, walk
from .kernels import normalized_squared_error


def prove(left: Expr, right: Expr, domains: dict, nonzero: list[str], timeout_ms=3000) -> dict:
    scope = "Real denotations over declared intervals; not IEEE floating-point equivalence or a Lean certificate"
    start = time.perf_counter()
    try: import z3
    except ImportError:
        return {"status": "UNAVAILABLE", "reason": "Install eqtrace[proof] for the Z3 backend", "scope": scope}
    if any(n.op in ("exp", "log", "sqrt") for e in (left, right) for n in walk(e)):
        return {"status": "UNSUPPORTED", "reason": "Elementary functions are outside the rational SMT fragment", "scope": scope}
    variables = {name: z3.Real(name) for name in domains}
    assumptions = []
    for name, (lo, hi) in domains.items():
        assumptions += [variables[name] >= z3.RealVal(str(Fraction(str(lo)))), variables[name] <= z3.RealVal(str(Fraction(str(hi))))]
    assumptions += [variables[n] != 0 for n in nonzero]
    guards = []
    def lower(n):
        if n.op == "var": return variables[n.value]
        if n.op == "const": return z3.RealVal(n.value)
        a = [lower(c) for c in n.args]
        if n.op == "add": return a[0] + a[1]
        if n.op == "sub": return a[0] - a[1]
        if n.op == "mul": return a[0] * a[1]
        if n.op == "div": guards.append(a[1] != 0); return a[0] / a[1]
        if n.op == "neg": return -a[0]
        if n.op == "pow":
            exponent = int(n.value)
            if exponent < 0: guards.append(a[0] != 0)
            return a[0] ** exponent if exponent != 0 else z3.RealVal(1)
        raise Unsupported(f"No SMT semantics for {n.op}")
    l, r = lower(left), lower(right)
    queries = []
    def query(name, constraints):
        solver = z3.Solver(); solver.set(timeout=timeout_ms)
        solver.add(*constraints)
        smt = solver.to_smt2()
        answer = solver.check()
        record = {"name": name, "smt2": smt, "result": str(answer)}
        if answer == z3.sat:
            record["model"] = {n: str(solver.model().eval(v, model_completion=True)) for n, v in variables.items()}
        if answer == z3.unknown: record["reason"] = solver.reason_unknown()
        queries.append(record)
        return answer, record
    result, record = query("nonempty_domain", assumptions)
    status, reason = "UNKNOWN", "Solver could not establish a nonempty domain"
    witness = None
    if result == z3.unsat:
        status, reason = "INVALID_DOMAIN", "Assumptions have no model; vacuous equivalence is rejected"
    elif result == z3.sat:
        result, record = query("totality", assumptions + [z3.Not(z3.And(*guards))])
        if result == z3.sat:
            status, reason, witness = "DOMAIN_ERROR", "A division or negative power can be undefined in the declared domain", record["model"]
        elif result == z3.unknown:
            status, reason = "UNKNOWN", record["reason"]
        else:
            result, record = query("equivalence", assumptions + [l != r])
            if result == z3.unsat:
                status, reason = "PROVED_REAL", "No unequal result exists under the declared real semantics (Z3 UNSAT)"
            elif result == z3.sat:
                status, reason, witness = "COUNTEREXAMPLE", "Z3 found unequal real denotations", record["model"]
            else: status, reason = "UNKNOWN", record["reason"]
    return {"status": status, "reason": reason, "scope": scope, "backend": "z3", "version": z3.get_version_string(),
            "timeout_ms_per_query": timeout_ms, "queries": queries, "witness": witness,
            "duration_ms": round((time.perf_counter() - start) * 1000, 3)}


def sample_inputs(domains: dict, nonzero: list[str], count: int, seed: int) -> list[dict]:
    """Deterministic boundary/coordinate probes followed by seeded random probes."""
    rng = random.Random(seed)
    bounds = {n: (Fraction(str(lo)), Fraction(str(hi))) for n, (lo, hi) in domains.items()}
    mids = {n: (lo + hi) / 2 for n, (lo, hi) in bounds.items()}
    for n in nonzero:
        if mids[n] == 0: mids[n] = bounds[n][1] if bounds[n][1] else bounds[n][0]
    def admissible(row): return all(row[n] != 0 for n in nonzero)
    def floating(row):
        # Floating probes must still lie inside the exact declared interval.
        result = {}
        for n, value in row.items():
            lo, hi = bounds[n]; v = float(value)
            if Fraction(v) < lo: v = math.nextafter(v, math.inf)
            if Fraction(v) > hi: v = math.nextafter(v, -math.inf)
            if not math.isfinite(v) or not lo <= Fraction(v) <= hi: return None
            result[n] = v
        return result if admissible(result) else None
    rows, seen = [], set()
    def add(row):
        if admissible(row):
            value = floating(row)
            if value is not None:
                key = tuple(value.items())
                if key not in seen: rows.append(value); seen.add(key)
    add(mids)
    for name, (lo, hi) in bounds.items():
        for value in [lo, hi] + ([Fraction(0)] if lo <= 0 <= hi else []):
            add(dict(mids, **{name: value}))
    for _ in range(count * 20):
        if len(rows) >= count: break
        add({n: lo + Fraction(rng.getrandbits(53), 2**53) * (hi - lo) for n, (lo, hi) in bounds.items()})
    return rows[:count]


def execute(reference: Expr, function, domains: dict, nonzero: list[str], count=64, seed=1729, tolerance=1e-10) -> dict:
    """Compare the actual validated source function with the equation interpreter."""
    inputs = sample_inputs(domains, nonzero, count, seed)
    records, passed = [], 0
    callable_ = function.compile()
    rational = not any(n.op in ("exp", "sqrt", "log") for n in walk(reference))
    for row in inputs:
        rec = {"inputs": row}
        try:
            expected = evaluate(reference, row)
            actual = callable_(**row)
            if type(actual) not in (float, int) or not math.isfinite(actual) or not math.isfinite(float(expected)):
                raise ValueError("Nonfinite or nonscalar output")
            # Fraction prevents the checker error metric from overflowing or
            # rounding a counterexample away. The runtime remains ordinary Python.
            error = normalized_squared_error(Fraction(actual), Fraction(expected))
            ok = error <= Fraction(str(tolerance)) ** 2
            rec.update({"expected": float(expected), "actual": actual,
                        "normalized_squared_error": float(error), "status": "PASS" if ok else "MISMATCH"})
            if not ok: rec["expected_exact"] = str(expected)
            passed += ok
        except (ArithmeticError, ValueError, TypeError) as exc:
            rec.update({"status": "ERROR", "reason": f"{type(exc).__name__}: {exc}"})
        records.append(rec)
    status = "PASS" if len(records) == count and passed == count else "FAIL"
    return {"status": status, "requested": count, "executed": len(records), "passed": passed,
            "seed": seed, "tolerance": tolerance, "distinct_inputs": len({tuple(r["inputs"].items()) for r in records}),
            "reference_semantics": "exact rational arithmetic on binary input values" if rational else "rational arithmetic plus CPython libm elementary operations",
            "execution_scope": "validated target function extracted from source; module and external callers are not executed",
            "records": records}
