import numpy as np

def softmax(values, axis=-1):
    shifted = values - values.max(axis=axis, keepdims=True)
    weights = np.exp(shifted)
    return weights / weights.sum(axis=axis, keepdims=True)
