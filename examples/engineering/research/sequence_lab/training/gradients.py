def head_gradients(features, residual):
    n = len(residual)
    return (2 / n) * (features.T @ residual), 2 * residual.mean()
