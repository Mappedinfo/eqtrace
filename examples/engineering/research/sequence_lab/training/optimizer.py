def gradient_step(weight, bias, dw, db, learning_rate):
    return weight - learning_rate * dw, bias - learning_rate * db
