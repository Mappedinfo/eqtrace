"""Manifest binding, fail-closed merge policy, and source-bound receipts."""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import time
import tomllib

from . import __version__
from .ir import Unsupported, diff, graph, latex, latex_name, python_function
from .latex_parser import equations, parse_equation
from .python_parser import parse_function
from .pseudocode import algorithms, parse_pseudocode, pseudocode
from .verify import prove, execute


def digest(data: bytes) -> str: return hashlib.sha256(data).hexdigest()


def canonical(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def checker_hashes() -> dict:
    root = Path(__file__).parent
    return {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in (".py", ".html", ".css", ".js")}


def local_path(root: Path, path: str) -> Path:
    if not isinstance(path, str) or not path or Path(path).is_absolute(): raise Unsupported("Paths must be nonempty project-relative strings")
    p = (root / path).resolve()
    if not p.is_relative_to(root.resolve()): raise Unsupported(f"Path leaves project: {path}")
    return p


def validate(config: dict):
    if config.get("schema_version") != 1: raise Unsupported("schema_version must be 1")
    extra = set(config) - {"schema_version", "title", "paper_sources", "contracts", "exclude", "samples", "seed", "tolerance", "timeout_ms"}
    if extra: raise Unsupported(f"Unknown configuration keys: {sorted(extra)}")
    if not isinstance(config.get("paper_sources"), list) or not config["paper_sources"]: raise Unsupported("paper_sources must list the checked LaTeX files")
    if not all(isinstance(x, str) and x for x in config["paper_sources"]) or len(set(config["paper_sources"])) != len(config["paper_sources"]):
        raise Unsupported("paper_sources must be unique nonempty paths")
    if not isinstance(config.get("contracts"), list) or not config["contracts"]: raise Unsupported("At least one equation contract is required")
    for name, default, lo, hi in [("samples", 64, 1, 1000), ("seed", 1729, 0, 2**32 - 1), ("timeout_ms", 3000, 1, 10000)]:
        value = config.get(name, default)
        if type(value) is not int or not lo <= value <= hi: raise Unsupported(f"{name} must be an integer in [{lo}, {hi}]")
    tolerance = config.get("tolerance", 1e-10)
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 < tolerance <= 1e-2:
        raise Unsupported("tolerance must be finite and in (0, 0.01]")
    ids, labels = set(), set()
    for c in config["contracts"]:
        required = {"id", "label", "implementation", "function", "inputs", "domains"}
        if not isinstance(c, dict) or not required <= c.keys(): raise Unsupported("A contract is missing required fields")
        if set(c) - required - {"nonzero", "policy", "description"}: raise Unsupported("Unknown contract fields")
        if not isinstance(c["id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", c["id"]): raise Unsupported("Invalid contract id")
        if not isinstance(c["label"], str) or not c["label"]: raise Unsupported("Invalid equation label")
        if c["id"] in ids or c["label"] in labels: raise Unsupported("Duplicate contract id or equation binding")
        ids.add(c["id"]); labels.add(c["label"])
        inputs = c["inputs"]
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= 16 or not all(isinstance(n, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", n) and n != "math" for n in inputs) or len(set(inputs)) != len(inputs):
            raise Unsupported("inputs must contain 1..16 unique scalar identifiers")
        if not isinstance(c["domains"], dict) or set(c["domains"]) != set(inputs): raise Unsupported("Every input requires exactly one closed interval")
        for name, interval in c["domains"].items():
            if not isinstance(interval, list) or len(interval) != 2: raise Unsupported(f"Invalid domain for {name}")
            for value in interval:
                if type(value) not in (str, int, float) or len(str(value)) > 128: raise Unsupported("Invalid domain bound")
            try: lo, hi = (Fraction(str(x)) for x in interval)
            except (ValueError, ZeroDivisionError) as exc: raise Unsupported("Invalid rational domain bound") from exc
            if not -10**100 <= lo <= hi <= 10**100: raise Unsupported(f"Unordered or excessive domain for {name}")
        nonzero = c.get("nonzero", [])
        if not isinstance(nonzero, list) or not all(n in inputs for n in nonzero) or len(set(nonzero)) != len(nonzero): raise Unsupported("nonzero must name unique inputs")
        if c.get("policy", "algebraic") not in ("algebraic", "ordered"): raise Unsupported("policy must be algebraic or ordered")
        if not isinstance(c["function"], str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", c["function"]): raise Unsupported("Invalid function name")
    exclusions = config.get("exclude", [])
    if not isinstance(exclusions, list): raise Unsupported("exclude must be a list")
    for e in exclusions:
        if not isinstance(e, dict) or set(e) != {"label", "reason"} or not isinstance(e["reason"], str) or not e["reason"].strip():
            raise Unsupported("Exclusions require label and a nonempty reason")
        if e["label"] in labels: raise Unsupported("Duplicate or conflicting exclusion")
        labels.add(e["label"])


def check_project(manifest: Path, proof=True) -> dict:
    manifest = manifest.resolve(); root = manifest.parent
    started = time.perf_counter()
    report = {"schema_version": 1, "tool": "eqtrace", "version": __version__, "title": "EqTrace check",
              "created_at": datetime.now(timezone.utc).isoformat(), "status": "BLOCKED", "proof_required": proof,
              "manifest": manifest.name, "sources": {}, "checker": checker_hashes(),
              "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(), "platform": platform.system()},
              "scope": "Only manifest-selected equation files and validated target functions; no transitive imports or external callers",
              "errors": [], "contracts": []}
    def read(path):
        p = local_path(root, path); data = p.read_bytes()
        report["sources"][path] = digest(data)
        return data.decode("utf-8")
    try:
        config = tomllib.loads(read(manifest.name)); validate(config)
        report["title"] = str(config.get("title", "EqTrace check"))
        inventory = {}
        for path in config["paper_sources"]:
            source_text = read(path)
            displays = equations(source_text)
            algs = algorithms(source_text)
            if displays.keys() & algs.keys(): raise Unsupported("Equation and algorithm share a label")
            for label, eq in (displays | algs).items():
                if label in inventory: raise Unsupported(f"Duplicate equation label across files: {label}")
                inventory[label] = dict(eq, source=path)
        bound = {c["label"] for c in config["contracts"]}
        excluded = {e["label"] for e in config.get("exclude", [])}
        missing = inventory.keys() - bound - excluded
        unknown = (bound | excluded) - inventory.keys()
        if missing: report["errors"].append(f"Unbound equations: {sorted(missing)}")
        if unknown: report["errors"].append(f"Labels not found: {sorted(unknown)}")
        report["coverage"] = {"selected_files": config["paper_sources"], "labeled_equations": len(inventory), "bound": len(bound & inventory.keys()), "excluded": config.get("exclude", [])}
        for c in config["contracts"]:
            item = {"id": c["id"], "label": c["label"], "description": c.get("description", ""), "status": "BLOCKED",
                    "policy": c.get("policy", "algebraic"), "inputs": c["inputs"], "domains": c["domains"], "nonzero": c.get("nonzero", []),
                    "implementation": c["implementation"], "function": c["function"],
                    "proof": {"status": "NOT_RUN"}, "execution": {"status": "NOT_RUN", "executed": 0}, "errors": []}
            report["contracts"].append(item)
            try:
                if c["label"] not in inventory: raise Unsupported(f"Equation label missing: {c['label']}")
                eq = inventory[c["label"]]
                parser = parse_pseudocode if eq.get("kind") == "pseudocode" else parse_equation
                output, reference = parser(eq["text"], c["inputs"], eq["line"])
                item["source_kind"] = eq.get("kind", "equation")
                item.update({"equation_source": eq["source"], "equation_line": eq["line"], "equation_text": eq["text"].strip(),
                             "equation_latex": f"{latex_name(output)} = {latex(reference)}", "equation_graph": graph(reference, eq["source"]),
                             "generated_python": python_function(reference, c["inputs"], c["id"].replace("-", "_") + "_reference")})
                source = read(c["implementation"])
                function = parse_function(source, c["function"], c["inputs"])
                actual = function.expression
                item.update({"code_source": function.source, "code_line": function.line, "code_latex": f"{latex_name(output)} = {latex(actual)}",
                             "code_graph": graph(actual, c["implementation"]), "minimal_code": python_function(actual, c["inputs"], c["id"].replace("-", "_") + "_lowered"),
                             "code_pseudocode": pseudocode(actual, c["inputs"]), "code_algorithmic": pseudocode(actual, c["inputs"], tex=True),
                             "equation_pseudocode": pseudocode(reference, c["inputs"]),
                             "structural": {"status": "IDENTICAL" if reference.semantic() == actual.semantic() else "DIFFERENT", "differences": diff(reference, actual)}})
                item["proof"] = prove(reference, actual, c["domains"], c.get("nonzero", []), config.get("timeout_ms", 3000)) if proof else {"status": "NOT_REQUESTED"}
                item["execution"] = execute(reference, function, c["domains"], c.get("nonzero", []), config.get("samples", 64), config.get("seed", 1729), config.get("tolerance", 1e-10))
                structural_ok = item["policy"] == "algebraic" or item["structural"]["status"] == "IDENTICAL"
                proof_ok = item["proof"]["status"] == "PROVED_REAL" if proof else True
                if structural_ok and proof_ok and item["execution"]["status"] == "PASS":
                    item["status"] = "PASS" if proof else "SAMPLED_ONLY"
                else: item["status"] = "FAIL"
            except (Unsupported, OSError, UnicodeError, ValueError, RecursionError) as exc:
                item["errors"].append(f"{type(exc).__name__}: {exc}")
        if not report["errors"] and report["contracts"] and all(c["status"] == "PASS" for c in report["contracts"]): report["status"] = "PASS"
        elif not report["errors"] and report["contracts"] and all(c["status"] == "SAMPLED_ONLY" for c in report["contracts"]): report["status"] = "SAMPLED_ONLY"
        elif any(c["status"] == "FAIL" for c in report["contracts"]): report["status"] = "FAIL"
    except (Unsupported, OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
    report["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return report


def write_report(report: dict, out: Path) -> Path:
    from .render import render_html, mermaid, svg
    out.mkdir(parents=True, exist_ok=True)
    artifacts = {}
    def write(name, text):
        p = out / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
        artifacts[name] = digest(p.read_bytes())
    for c in report["contracts"]:
        cid = c["id"]
        for field, name in [("generated_python", "reference.py"), ("minimal_code", "lowered.py"), ("code_latex", "from-code.tex"), ("code_pseudocode", "from-code.txt"), ("code_algorithmic", "from-code.algorithmic.tex"), ("equation_pseudocode", "from-paper.txt")]:
            if field in c: write(f"{cid}/{name}", c[field] + "\n")
        for field, side in [("equation_graph", "equation"), ("code_graph", "code")]:
            if field in c:
                g = c[field]
                write(f"{cid}/{side}.graph.json", json.dumps(g, indent=2))
                write(f"{cid}/{side}.mmd", mermaid(g))
                write(f"{cid}/{side}.svg", svg(g))
        for q in c["proof"].get("queries", []): write(f"{cid}/{q['name']}.smt2", q["smt2"])
    report["artifacts"] = artifacts
    report.pop("integrity", None)
    report["integrity"] = {"algorithm": "sha256", "payload": digest(canonical(report)), "scope": "Integrity and freshness, not authenticity; an attacker can recompute this digest"}
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (out / "index.html").write_text(render_html(report), encoding="utf-8")
    return out / "report.json"


def verify_receipt(receipt: Path, root: Path) -> dict:
    errors = []
    try:
        report = json.loads(receipt.read_text())
        integrity = report.pop("integrity", {})
        if integrity.get("payload") != digest(canonical(report)): errors.append("Report payload digest mismatch")
        if not report.get("sources") or not report.get("checker"): errors.append("Missing provenance")
        for name, expected in report.get("sources", {}).items():
            try:
                if digest(local_path(root, name).read_bytes()) != expected: errors.append(f"Changed source: {name}")
            except (OSError, Unsupported): errors.append(f"Missing or invalid source: {name}")
        if report.get("checker") != checker_hashes(): errors.append("Checker implementation changed")
        for name, expected in report.get("artifacts", {}).items():
            try:
                if digest(local_path(receipt.parent, name).read_bytes()) != expected: errors.append(f"Changed artifact: {name}")
            except (OSError, Unsupported): errors.append(f"Missing or invalid artifact: {name}")
        if report.get("environment", {}).get("python") != platform.python_version(): errors.append("Python version changed")
        if report.get("environment", {}).get("platform") != platform.system(): errors.append("Operating system changed")
        if report.get("proof_required"):
            try:
                import z3
                versions = {c["proof"].get("version") for c in report["contracts"] if c["proof"].get("version")}
                if versions and versions != {z3.get_version_string()}: errors.append("Z3 version changed")
            except ImportError: errors.append("Z3 no longer available")
        if report.get("status") != "PASS": errors.append(f"Original receipt is not a strict pass: {report.get('status')}")
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors.append(f"Invalid receipt: {exc}")
    return {"status": "FRESH" if not errors else "STALE_OR_INVALID", "errors": errors}
