from sequence_lab.training.checkpoint import load_checkpoint
from sequence_lab.model.encoder import encode
from sequence_lab.model.head import predict
from shared_math.serialization import load_arrays
from shared_math.metrics import mean_squared_error
from shared_math.predictions import write_predictions

def evaluate(prepared, checkpoint, predictions_path):
    arrays = load_arrays(prepared)
    encoder, weight, bias = load_checkpoint(checkpoint)
    predicted = predict(encode(arrays["validation_x"], encoder), weight, bias)
    write_predictions(predictions_path, predicted, arrays["validation_y"])
    return {"validation_mse": mean_squared_error(predicted, arrays["validation_y"]), "validation_samples":len(predicted)}
