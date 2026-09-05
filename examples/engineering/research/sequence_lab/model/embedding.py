import numpy as np

def embed(values, width):
    scales = np.linspace(0.5, 1.5, width)
    return values[:, :, None] * scales[None, None, :]
