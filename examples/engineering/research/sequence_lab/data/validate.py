import math

def validate_records(rows):
    expected = {"sample_id", "split", "target"} | {f"x{i}" for i in range(6)}
    if not rows:
        raise ValueError("empty dataset")
    for row in rows:
        if set(row) != expected or any(not math.isfinite(float(row[f"x{i}"])) for i in range(6)):
            raise ValueError("invalid sequence record")
        if not math.isfinite(float(row["target"])) or row["split"] not in ("train", "validation", "adapt"):
            raise ValueError("invalid target or split")
    if len({r["sample_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate sample ID")
