import csv
from pathlib import Path
from .scalar import squared_error

def write_predictions(path, predicted, target):
    with Path(path).open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["index", "prediction", "target", "squared_error"])
        writer.writerows((i, float(p), float(y), squared_error(float(p),float(y))) for i,(p,y) in enumerate(zip(predicted,target)))
