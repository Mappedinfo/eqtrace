def algorithm_normalization_lowered(x, mu, sigma, epsilon):
    return ((x - mu) / (sigma + epsilon))
