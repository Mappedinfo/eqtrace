#!/usr/bin/env python3
"""Run experiments -> experiments/results/results.csv.

The paper's figures and tables must trace back to this CSV (or to scripts that
consume it). Never type result numbers into the paper by hand."""
from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "experiments" / "results"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [
        {"method": "baseline", "metric": 0.0},
        {"method": "ours", "metric": 0.0},
    ]
    with (OUT / "results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["method", "metric"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUT / 'results.csv'} — replace placeholder rows with real runs")


if __name__ == "__main__":
    main()
