from sequence_lab.model.encoder import encode
from .loop import fit
from .checkpoint import load_checkpoint, save_checkpoint
from shared_math.serialization import load_arrays

def finetune(prepared, source, destination, settings):
    arrays = load_arrays(prepared)
    encoder, weight, bias = load_checkpoint(source)
    features = encode(arrays["adapt_x"], encoder)
    weight, bias, history = fit(features, arrays["adapt_y"], weight, bias, settings.finetune_steps, settings.learning_rate)
    save_checkpoint(destination, encoder, weight, bias)
    return history
