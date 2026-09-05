def algorithm_normalization_reference(x, mu, sigma, epsilon):
    return ((x - mu) / (sigma + epsilon))
