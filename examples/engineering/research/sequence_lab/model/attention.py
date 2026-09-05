import numpy as np
from shared_math.softmax import softmax

def attention(values, weights):
    q = values @ weights["q"]
    k = values @ weights["k"]
    v = values @ weights["v"]
    scores = (q @ np.swapaxes(k, -1, -2)) / np.sqrt(q.shape[-1])
    probabilities = softmax(scores, axis=-1)
    return (probabilities @ v) @ weights["o"]
