"""Independent Python implementations; no EqTrace decorators or runtime imports."""


def weighted(x, z, alpha):
    return alpha * x + (1 - alpha) * z


def expanded(x):
    return x * x + 2 * x + 1


def normalize(x, mu, sigma, epsilon):
    d = x - mu
    scale = sigma + epsilon
    return d / scale
