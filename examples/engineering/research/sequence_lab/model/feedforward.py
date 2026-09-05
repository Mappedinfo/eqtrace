import numpy as np

def feedforward(values, weights):
    hidden = np.maximum(0, values @ weights["ff1"])
    return hidden @ weights["ff2"]
