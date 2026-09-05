"""Small arithmetic kernels exercised by EqTrace's self-application contracts."""


def squared_error(a, b):
    d = a - b
    return d * d


def normalized_squared_error(a, b):
    d = a - b
    return (d * d) / (1 + b * b)
