"""Local dataset observations. Rows are never embedded in exported summaries."""
from __future__ import annotations
import csv
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from .ir import Unsupported


def tex_escape(value):
    chars={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(chars.get(c,c) for c in str(value))


def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def classify(value):
    if value is None or value=='':return 'null',None
    if isinstance(value,bool):return 'boolean',None
    if isinstance(value,(list,dict)):return 'array' if isinstance(value,list) else 'object',None
    text=str(value)
    try:
        if text.strip() and all(c in '+-0123456789' for c in text.strip()):return 'integer',int(text)
        n=float(text)
        if math.isfinite(n):return 'number',n
        return 'nonfinite',None
    except (ValueError,OverflowError):return 'string',None


def scan_dataset(path: Path, dataset_id: str, max_rows=100000) -> dict:
    if not path.is_file():raise Unsupported(f'Dataset file not found: {path.name}')
    if path.stat().st_size>256*1024*1024:raise Unsupported('MVP dataset scan is limited to 256 MiB per file')
    if type(max_rows) is not int or not 1<=max_rows<=1000000:raise Unsupported('max_rows must be 1..1000000')
    before=file_hash(path)
    columns={};count=0;complete=True;row_errors=[]
    def add(row):
        nonlocal count
        if not isinstance(row,dict):raise Unsupported(f'Row {count+1} must be an object')
        if len(row)>256:raise Unsupported('Dataset has more than 256 columns')
        for name in row:
            if name not in columns:columns[name]={'name':name,'types':set(),'nulls':count,'present':0,'min':None,'max':None}
        for name,info in columns.items():
            value=row.get(name);kind,n=classify(value)
            info['types'].add(kind)
            if kind=='null':info['nulls']+=1
            else:info['present']+=1
            if n is not None:
                info['min']=n if info['min'] is None else min(info['min'],n)
                info['max']=n if info['max'] is None else max(info['max'],n)
        count+=1
    suffix=path.suffix.lower()
    with path.open(encoding='utf-8-sig',newline='') as f:
        if suffix=='.csv':
            reader=csv.DictReader(f)
            if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames) or any(not n for n in reader.fieldnames):raise Unsupported('CSV requires nonempty, unique headers')
            columns={n:{'name':n,'types':set(),'nulls':0,'present':0,'min':None,'max':None} for n in reader.fieldnames}
            def rows():
                for i,row in enumerate(reader,2):
                    if None in row:raise Unsupported(f'CSV row {i} has extra fields')
                    yield row
        elif suffix=='.jsonl':
            def rows():
                for i,line in enumerate(f,1):
                    if not line.strip():raise Unsupported(f'Empty JSONL record at line {i}')
                    try:yield json.loads(line)
                    except ValueError as exc:raise Unsupported(f'Malformed JSONL at line {i}') from exc
        else:raise Unsupported('Dataset frontend currently supports CSV and JSONL')
        for row in rows():
            if count>=max_rows:complete=False;break
            add(row)
    after=file_hash(path)
    if before!=after:raise Unsupported('Dataset changed while scanning; no stable observation')
    for info in columns.values():info['types']=sorted(info['types'])
    status='SCANNED' if complete and count else ('PARTIAL' if count else 'EMPTY')
    return {'id':dataset_id,'kind':'dataset','status':status,'evidence':'observed','format':suffix[1:],'sha256':after,'bytes':path.stat().st_size,
            'rows_scanned':count,'rows_total':count if complete else None,'complete':complete,'columns':list(columns.values()),
            'scope':'Full file hash; type/null/range statistics for scanned records only. No raw rows exported.'}


def dataset_latex(data: dict) -> str:
    lines=[r'\begin{tabular}{llll}',r'\toprule',r'Field & Observed type & Missing & Numeric range \\',r'\midrule']
    for c in data['columns']:
        bounds='--' if c['min'] is None else f"{c['min']:g} to {c['max']:g}"
        lines.append(' & '.join(tex_escape(x) for x in [c['name'],', '.join(c['types']),f"{c['nulls']}/{data['rows_scanned']}",bounds])+r' \\')
    lines += [r'\bottomrule',r'\end{tabular}',f"% Dataset {tex_escape(data['id'])}; scanned={data['rows_scanned']}; total={data['rows_total']}; SHA256={data['sha256']}"]
    return '\n'.join(lines)+'\n'
