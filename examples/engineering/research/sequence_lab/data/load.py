import csv
from pathlib import Path

def load_records(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))
