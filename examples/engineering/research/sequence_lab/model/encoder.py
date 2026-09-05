from .embedding import embed
from .position import positional_encoding
from .block import transformer_block

def encode(values, weights):
    width = weights["q"].shape[0]
    tokens = embed(values, width) + positional_encoding(values.shape[1], width)
    return transformer_block(tokens, weights).mean(axis=1)
