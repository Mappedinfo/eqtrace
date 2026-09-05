import numpy as np

def initial_parameters(width, seed):
    rng = np.random.default_rng(seed)
    return {name: rng.normal(0, 0.1, (width, width)) for name in ("q", "k", "v", "o", "ff1", "ff2")}
