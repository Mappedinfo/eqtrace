from .load import load_records
from .validate import validate_records
from .features import encode_records
from .split import split_records
from shared_math.serialization import save_arrays

def prepare(source, destination):
    rows = load_records(source)
    validate_records(rows)
    partitions = split_records(rows)
    arrays = {}
    for split, records in partitions.items():
        arrays[split + "_x"], arrays[split + "_y"] = encode_records(records)
    save_arrays(destination, arrays)
    return {name: len(rows) for name, rows in partitions.items()}
