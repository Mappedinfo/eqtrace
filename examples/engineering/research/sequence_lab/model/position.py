import numpy as np

def positional_encoding(length, width):
    position = np.arange(length)[:, None]
    frequencies = 1 / (10000 ** (np.arange(width)[None, :] / width))
    return np.sin(position * frequencies)
