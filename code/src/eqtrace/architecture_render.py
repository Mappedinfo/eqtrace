"""Offline hierarchical workbench driven exclusively by architecture scan data."""
import json
from pathlib import Path


def render_architecture(report):
    root=Path(__file__).parent/'web'
    payload=json.dumps(report,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    return root.joinpath('architecture.html').read_text().replace('/* EQTRACE_CSS */',root.joinpath('style.css').read_text()+root.joinpath('architecture.css').read_text()).replace('/* EQTRACE_DATA */',payload).replace('/* EQTRACE_JS */',root.joinpath('architecture.js').read_text())
