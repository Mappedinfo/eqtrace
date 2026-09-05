from pathlib import Path
import numpy as np

def save_arrays(path, arrays):
    with Path(path).open("wb") as stream:
        np.savez(stream, **arrays)

def load_arrays(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {name: arrays[name] for name in arrays.files}
