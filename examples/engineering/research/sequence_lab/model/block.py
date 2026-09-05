from .attention import attention
from .feedforward import feedforward
from .normalization import layer_norm

def transformer_block(values, weights):
    attended = values + attention(layer_norm(values), weights)
    return attended + feedforward(layer_norm(attended), weights)
