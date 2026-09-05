"""A scalar leaf used by the larger prediction export pipeline."""

def squared_error(a, b):
    d = a - b
    return d * d
