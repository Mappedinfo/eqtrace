"""Deterministic synthetic data; no personal or external records."""
import csv
from pathlib import Path
import random

rng=random.Random(2026)
out=Path(__file__).parent/'data/sequences.csv'
with out.open('w',newline='') as stream:
    writer=csv.writer(stream)
    writer.writerow(['sample_id','split',*[f'x{i}' for i in range(6)],'target'])
    for i in range(384):
        split='train' if i<256 else ('validation' if i<320 else 'adapt')
        values=[rng.uniform(-1,1)+(0.25 if split=='adapt' else 0) for _ in range(6)]
        target=0.7*sum(values)/len(values)+0.2*max(values)+rng.gauss(0,0.01)
        writer.writerow([i,split,*[round(x,8) for x in values],round(target,8)])
print(out.name,'384 rows, 9 columns')
