def mean_squared_error(predicted, target):
    return float(((predicted - target) ** 2).mean())
