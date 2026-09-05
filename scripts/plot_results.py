#!/usr/bin/env python3
"""results.csv -> paper/figures/main-result.pdf (code-drawn from real data)."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
plt.style.use(Path(__file__).resolve().parent / "matplotlib-style.mplstyle")


def main() -> None:
    data = ROOT / "experiments" / "results" / "results.csv"
    rows = list(csv.DictReader(data.open(encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar([r["method"] for r in rows], [float(r["metric"]) for r in rows])
    ax.set_ylabel("metric")
    out = ROOT / "paper" / "figures" / "main-result.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
