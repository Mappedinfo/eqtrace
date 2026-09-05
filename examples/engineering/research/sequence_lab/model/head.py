import numpy as np

def initialize_head(width):
    return np.zeros(width), 0.0

def predict(features, weight, bias):
    return features @ weight + bias
