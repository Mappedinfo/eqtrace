from shared_math.serialization import save_arrays, load_arrays

def save_checkpoint(path, encoder, weight, bias):
    save_arrays(path, dict(encoder, head_weight=weight, head_bias=bias))

def load_checkpoint(path):
    data = load_arrays(path)
    weight = data.pop("head_weight")
    bias = float(data.pop("head_bias"))
    return data, weight, bias
