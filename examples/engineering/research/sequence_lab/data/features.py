import numpy as np

def encode_records(rows):
    x = np.array([[float(row[f"x{i}"]) for i in range(6)] for row in rows], dtype=np.float64)
    y = np.array([float(row["target"]) for row in rows], dtype=np.float64)
    return x, y
