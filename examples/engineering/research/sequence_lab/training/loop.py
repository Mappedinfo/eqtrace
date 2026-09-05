from .optimizer import gradient_step
from .gradients import head_gradients
from sequence_lab.model.head import predict
from shared_math.metrics import mean_squared_error

def fit(features, target, weight, bias, steps, learning_rate):
    history = []
    for _ in range(steps):
        prediction = predict(features, weight, bias)
        history.append(mean_squared_error(prediction, target))
        dw, db = head_gradients(features, prediction - target)
        weight, bias = gradient_step(weight, bias, dw, db, learning_rate)
    history.append(mean_squared_error(predict(features, weight, bias), target))
    return weight, bias, history
