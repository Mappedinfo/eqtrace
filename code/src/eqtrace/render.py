"""Dependency-free graph rendering and an offline evidence workbench."""
from html import escape
import json
from pathlib import Path


def mermaid(g: dict) -> str:
    lines = ["flowchart LR"]
    for n in g["nodes"]:
        label = n["value"] if n["op"] in ("var", "const") else n["op"] + (" " + n["value"] if n["value"] else "")
        lines.append(f'  {n["id"]}["{escape(label, quote=True)}"]')
    for e in g["edges"]: lines.append(f'  {e["from"]} -->|{e["slot"]}| {e["to"]}')
    return "\n".join(lines) + "\n"


def svg(g: dict, highlights=None) -> str:
    highlights = set(highlights or [])
    depths, rows, positions = {}, {}, {}
    for n in g["nodes"]:
        depth = max((depths[i] + 1 for i in n["inputs"]), default=0)
        depths[n["id"]] = depth
        row = rows.get(depth, 0); rows[depth] = row + 1
        positions[n["id"]] = (28 + depth * 154, 28 + row * 78)
    width, height = 160 + max(depths.values(), default=0) * 154, 50 + max(rows.values(), default=1) * 78
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Ordered scalar computation graph">',
             '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#88968e"/></marker></defs>']
    for e in g["edges"]:
        x, y = positions[e["from"]]; xx, yy = positions[e["to"]]
        parts.append(f'<path d="M{x+108},{y+24} C{x+133},{y+24} {xx-25},{yy+24} {xx},{yy+24}" fill="none" stroke="#aab7ae" stroke-width="1.5" marker-end="url(#arrow)"/>')
        parts.append(f'<text x="{xx-13}" y="{yy+17+e["slot"]*13}" font-size="9" fill="#65736a">{e["slot"]}</text>')
    for n in g["nodes"]:
        x, y = positions[n["id"]]
        label = n["value"] if n["op"] in ("var", "const") else n["op"] + (" " + n["value"] if n["value"] else "")
        fill = "#fff1df" if n["fingerprint"] in highlights else ("#e4eee7" if n["id"] == g["root"] else "#ffffff")
        parts.append(f'<g class="graph-node" data-node="{n["id"]}" tabindex="0" role="button" aria-label="{escape(label)}">')
        parts.append(f'<title>{escape(n["expression"])}</title><rect x="{x}" y="{y}" width="108" height="48" rx="5" fill="{fill}" stroke="#9dad9f"/>')
        parts.append(f'<text x="{x+54}" y="{y+21}" text-anchor="middle" font-size="13" font-family="monospace" fill="#203e30">{escape(label[:18])}</text>')
        parts.append(f'<text x="{x+54}" y="{y+37}" text-anchor="middle" font-size="9" font-family="monospace" fill="#6a7c6e">{n["id"]} · {n["op"]}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def render_html(report: dict) -> str:
    root = Path(__file__).parent / "web"
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return (root.joinpath("index.html").read_text().replace("/* EQTRACE_CSS */", root.joinpath("style.css").read_text())
            .replace("/* EQTRACE_DATA */", payload).replace("/* EQTRACE_JS */", root.joinpath("app.js").read_text()))
