import json
from pathlib import Path

def write_report(path, observations):
    Path(path).write_text(json.dumps(observations, indent=2, allow_nan=False) + "\n")
