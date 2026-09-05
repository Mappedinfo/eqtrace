import numpy as np

def layer_norm(values, epsilon=1e-6):
    center = values.mean(axis=-1, keepdims=True)
    variance = ((values - center) ** 2).mean(axis=-1, keepdims=True)
    return (values - center) / np.sqrt(variance + epsilon)
