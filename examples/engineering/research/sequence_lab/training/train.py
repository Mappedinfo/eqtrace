from sequence_lab.model.parameters import initial_parameters
from sequence_lab.model.encoder import encode
from sequence_lab.model.head import initialize_head
from .loop import fit
from .checkpoint import save_checkpoint
from shared_math.serialization import load_arrays

def train(prepared, destination, settings):
    arrays = load_arrays(prepared)
    encoder = initial_parameters(settings.width, settings.seed)
    features = encode(arrays["train_x"], encoder)
    weight, bias = initialize_head(settings.width)
    weight, bias, history = fit(features, arrays["train_y"], weight, bias, settings.train_steps, settings.learning_rate)
    save_checkpoint(destination, encoder, weight, bias)
    return history
