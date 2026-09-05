"""Loopback preview with bounded, temporary, strictly parsed comparisons."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import tempfile

from .project import check_project, validate
from .render import render_html


def toml_string(value): return json.dumps(value)


def temporary_check(payload):
    if not isinstance(payload, dict) or set(payload) != {"latex", "code", "contract", "kind"}: raise ValueError("Invalid request fields")
    if not all(isinstance(payload[k], str) and len(payload[k]) <= 20000 for k in ("latex", "code")): raise ValueError("Sources must be strings up to 20000 characters")
    if payload["kind"] not in ("equation", "pseudocode"): raise ValueError("Unknown source kind")
    contract = dict(payload["contract"], implementation="implementation.py")
    config = {"schema_version": 1, "paper_sources": ["paper.tex"], "contracts": [contract]}
    validate(config)
    # TOML strings/arrays/inline dictionaries are encoded without eval or templates.
    lines = ['schema_version = 1', 'title = "Live comparison"', 'paper_sources = ["paper.tex"]', '[[contracts]]']
    for key, value in contract.items():
        if key == "domains":
            value = "{ " + ", ".join(f"{toml_string(n)} = {json.dumps(bounds)}" for n, bounds in value.items()) + " }"
        else: value = json.dumps(value)
        lines.append(f"{key} = {value}")
    with tempfile.TemporaryDirectory(prefix="eqtrace-live-") as tmp:
        root = Path(tmp)
        if payload["kind"] == "equation": paper = "\\begin{equation}\n\\label{" + contract["label"] + "}\n" + payload["latex"] + "\n\\end{equation}\n"
        else: paper = "\\begin{algorithm}\n\\label{" + contract["label"] + "}\n\\begin{algorithmic}\n" + payload["latex"] + "\n\\end{algorithmic}\n\\end{algorithm}\n"
        (root / "paper.tex").write_text(paper)
        (root / "implementation.py").write_text(payload["code"])
        manifest = root / "eqtrace.toml"; manifest.write_text("\n".join(lines))
        report = check_project(manifest)
        report["scope"] = "Temporary live edit; original project files unchanged. Exported live results are previews, not durable receipts."
        return report


def serve(manifest: Path, port: int):
    if not 1024 <= port <= 65535: raise ValueError("Use an unprivileged port 1024..65535")
    class Handler(BaseHTTPRequestHandler):
        def send(self, code, data, content_type):
            self.send_response(code); self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src blob: data:; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(data)
        def valid_host(self): return self.headers.get("Host") == f"127.0.0.1:{port}"
        def do_GET(self):
            if not self.valid_host(): self.send(403, b"Forbidden Host", "text/plain"); return
            if self.path not in ("/", "/index.html"): self.send(404, b"Not found", "text/plain"); return
            self.send(200, render_html(check_project(manifest)).encode(), "text/html; charset=utf-8")
        def do_POST(self):
            if not self.valid_host() or self.headers.get("Origin") != f"http://127.0.0.1:{port}": self.send(403, b'{"error":"Same-origin loopback requests only"}', "application/json"); return
            if self.path != "/api/check": self.send(404, b'{"error":"Not found"}', "application/json"); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536 or self.headers.get("Content-Type") != "application/json": raise ValueError("Expected bounded JSON request")
                report = temporary_check(json.loads(self.rfile.read(size)))
                self.send(200, json.dumps(report, allow_nan=False).encode(), "application/json")
            except (ValueError, TypeError, KeyError) as exc: self.send(400, json.dumps({"error": str(exc)}).encode(), "application/json")
        def log_message(self, format, *args): pass
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"EqTrace workbench: http://127.0.0.1:{port}", flush=True)
        try: server.serve_forever()
        except KeyboardInterrupt: pass
