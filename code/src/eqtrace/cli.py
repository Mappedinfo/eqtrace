"""Scriptable checks, translation, receipt validation, and a loopback workbench."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from .ir import Unsupported, graph, latex, python_function
from .latex_parser import parse_equation
from .pseudocode import parse_pseudocode, pseudocode
from .python_parser import parse_function
from .project import check_project, verify_receipt, write_report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="eqtrace", description="Link paper equations, pseudocode, datasets, and multi-file engineering evidence.")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Run a source-bound merge check and export an offline workbench")
    check.add_argument("manifest", type=Path, nargs="?", default=Path("eqtrace.toml"))
    check.add_argument("--out", type=Path, default=Path("artifacts/check"))
    check.add_argument("--sample-only", action="store_true", help="Explicitly skip formal checks; result is SAMPLED_ONLY and not a strict merge pass")
    verify = sub.add_parser("verify", help="Reject stale/edited receipts against current project and checker sources")
    verify.add_argument("receipt", type=Path)
    verify.add_argument("--project", type=Path, default=Path.cwd())
    translate = sub.add_parser("translate", help="Export minimal Python, LaTeX, pseudocode, and graph from one source")
    translate.add_argument("source", type=Path)
    translate.add_argument("--from", dest="language", choices=["latex", "pseudocode", "python"], required=True)
    translate.add_argument("--inputs", help="Comma-separated input names (required for paper inputs)")
    translate.add_argument("--function", default="compute")
    translate.add_argument("--out", type=Path, default=Path("artifacts/translation"))
    serve = sub.add_parser("serve", help="Run a loopback-only live comparison workbench")
    serve.add_argument("manifest", type=Path, nargs="?", default=Path("eqtrace.toml"))
    serve.add_argument("--port", type=int, default=8765)
    architecture = sub.add_parser("architecture", help="Scan multi-file / multi-codebase blocks and datasets into an interactive engineering graph")
    architecture.add_argument("manifest", type=Path)
    architecture.add_argument("--out", type=Path, default=Path("artifacts/architecture"))
    architecture.add_argument("--require-runs", action="store_true", help="Require fresh execution and declared output evidence")
    trace = sub.add_parser("trace", help="Explicitly execute a declared Python pipeline and record main-thread source/artifact evidence")
    trace.add_argument("manifest", type=Path)
    trace.add_argument("run_id")
    args = parser.parse_args(argv)
    if args.command in ("architecture", "trace"):
        from .architecture import scan_architecture, write_architecture, trace_run
        try:
            if args.command == "trace":
                receipt = trace_run(args.manifest, args.run_id)
                print(json.dumps({"run_id": args.run_id, "exit_code": receipt["exit_code"], "errors": receipt["errors"], "files_observed": len(receipt["trace"]["files"])}, indent=2))
                return 0 if receipt["exit_code"] == 0 else 1
            report = scan_architecture(args.manifest, args.require_runs)
            write_architecture(report, args.out)
            print(json.dumps({"status": report["status"], "summary": report.get("summary"), "errors": report["errors"], "workbench": str(args.out / "index.html")}, indent=2))
            return 0 if not report["errors"] else 1
        except (Unsupported, OSError, ValueError, TypeError, KeyError) as exc:
            print(f"BLOCKED: {exc}"); return 1
    if args.command == "check":
        report = check_project(args.manifest, proof=not args.sample_only)
        receipt = write_report(report, args.out)
        print(f"{report['status']}: {len(report['contracts'])} contracts; {report['duration_ms']} ms")
        for c in report["contracts"]:
            print(f"  {c['id']}: {c['status']} | proof={c['proof']['status']} | executed={c['execution']['executed']}")
            for error in c["errors"]: print(f"    {error}")
        for error in report["errors"]: print(f"  {error}")
        print(f"Receipt: {receipt}\nWorkbench: {args.out / 'index.html'}")
        return 0 if report["status"] == "PASS" else (3 if report["status"] == "SAMPLED_ONLY" else 1)
    if args.command == "verify":
        result = verify_receipt(args.receipt, args.project)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "FRESH" else 1
    if args.command == "serve":
        from .server import serve
        serve(args.manifest, args.port)
        return 0
    try:
        source = args.source.read_text()
        inputs = args.inputs.split(",") if args.inputs else None
        if args.language == "python":
            fn = parse_function(source, args.function, inputs); expr, inputs = fn.expression, fn.inputs
        else:
            if not inputs: raise Unsupported("--inputs is required to disambiguate paper symbols")
            _, expr = (parse_pseudocode if args.language == "pseudocode" else parse_equation)(source, inputs)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "minimal.py").write_text(python_function(expr, inputs))
        (args.out / "equation.tex").write_text("\\mathrm{result} = " + latex(expr) + "\n")
        (args.out / "pseudocode.txt").write_text(pseudocode(expr, inputs))
        (args.out / "algorithmic.tex").write_text(pseudocode(expr, inputs, tex=True))
        g = graph(expr, args.source.name)
        (args.out / "graph.json").write_text(json.dumps(g, indent=2))
        from .render import mermaid, svg
        (args.out / "graph.mmd").write_text(mermaid(g)); (args.out / "graph.svg").write_text(svg(g))
        print(f"TRANSLATED (not executed or proved): {args.out}")
        return 0
    except (Unsupported, OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}"); return 1


if __name__ == "__main__": raise SystemExit(main())
