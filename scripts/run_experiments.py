#!/usr/bin/env python3
"""Run the authored fault corpus; every table entry comes from a current run."""
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import time

from eqtrace.project import check_project,write_report,checker_hashes

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence'


def main():
    corpus_path=ROOT/'experiments/corpus.json'
    cases=json.loads(corpus_path.read_text())
    OUT.mkdir(exist_ok=True)
    rows=[]
    start=time.perf_counter()
    for case in cases:
        contract={'id':case['id'],'label':('alg:' if case.get('source_kind')=='pseudocode' else 'eq:')+case['id'],'function':'f','inputs':case['inputs'],'domains':case['domains'],'nonzero':case.get('nonzero',[]),'policy':'algebraic'}
        # Rebuild retained sources so the generated receipt is locally verifiable.
        folder=OUT/'cases'/case['id'];folder.mkdir(parents=True,exist_ok=True)
        label=contract['label']
        if case.get('source_kind')=='pseudocode':
            paper='\\begin{algorithm}\n\\label{'+label+'}\n\\begin{algorithmic}\n'+case['formula']+'\n\\end{algorithmic}\n\\end{algorithm}\n'
        else: paper='\\begin{equation}\n\\label{'+label+'}\n'+case['formula']+'\n\\end{equation}\n'
        (folder/'paper.tex').write_text(paper);(folder/'implementation.py').write_text(case['code'])
        lines=['schema_version = 1','title = '+json.dumps(case['id']),'paper_sources = ["paper.tex"]','[[contracts]]','implementation = "implementation.py"']
        for key,value in contract.items():
            if key=='domains': value='{ '+', '.join(json.dumps(n)+' = '+json.dumps(v) for n,v in value.items())+' }'
            else:value=json.dumps(value)
            lines.append(key+' = '+value)
        manifest=folder/'eqtrace.toml';manifest.write_text('\n'.join(lines)+'\n')
        report=check_project(manifest)
        write_report(report,folder/'run')
        item=report['contracts'][0]
        records=item['execution'].get('records',[])
        # Ablations share the strict parser. A unavailable result is not credited
        # as bug detection. Smoke uses only the midpoint record, when one exists.
        row={'case':case['id'],'category':case['kind'],'expected':case['expected'],'observed':report['status'],
             'expectation_met':report['status']==case['expected'],
             'midpoint_only':records[0]['status'] if records else 'NOT_RUN',
             'structure_only':item.get('structural',{}).get('status','NOT_TRANSLATED'),
             'proof':item['proof']['status'],'execution':item['execution']['status'],
             'samples_executed':item['execution']['executed'],'duration_ms':report['duration_ms'],
             'receipt':str((folder/'run/report.json').relative_to(ROOT))}
        rows.append(row)
        print(f"{case['id']}: expected={row['expected']} observed={row['observed']} proof={row['proof']}")
    with (OUT/'results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    import z3
    summary={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'Authored synthetic fixtures; not an independently sampled real-world bug benchmark',
             'cases':len(rows),'expectations_met':sum(r['expectation_met'] for r in rows),
             'valid_cases':sum(r['expected']=='PASS' for r in rows),'invalid_or_unsupported':sum(r['expected']!='PASS' for r in rows),
             'false_strict_passes':sum(r['observed']=='PASS' and r['expected']!='PASS' for r in rows),
             'midpoint_false_passes':sum(r['midpoint_only']=='PASS' and r['expected']!='PASS' for r in rows),
             'structure_false_rejections_of_valid':sum(r['structure_only']=='DIFFERENT' and r['expected']=='PASS' for r in rows),
             'total_samples_executed':sum(r['samples_executed'] for r in rows),'total_ms':round((time.perf_counter()-start)*1000,3),
             'environment':{'python':platform.python_version(),'os':platform.system(),'machine':platform.machine(),'z3':z3.get_version_string()},
             'corpus_sha256':hashlib.sha256(corpus_path.read_bytes()).hexdigest(),'checker':checker_hashes(),'rows':rows}
    (OUT/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
    (OUT/'README.md').write_text('# Executed evidence\n\nReproduce with `make demo`. `results.json` records the authored corpus, checker hashes, environment, and per-case receipts.\n\nEach case keeps its synthetic source and a generated `run/index.html` workbench. Failed checks are intentional observations. The benchmark script exits nonzero if any observation disagrees with the authored expectation.\n')
    generated=ROOT/'paper/generated';generated.mkdir(exist_ok=True)
    macros={'CorpusCases':summary['cases'],'ExpectedMatches':summary['expectations_met'],'ValidCases':summary['valid_cases'],'InvalidCases':summary['invalid_or_unsupported'],'FalsePasses':summary['false_strict_passes'],'MidpointFalsePasses':summary['midpoint_false_passes'],'StructureFalseRejects':summary['structure_false_rejections_of_valid'],'ExecutedSamples':summary['total_samples_executed']}
    (generated/'results.tex').write_text('% Generated by scripts/run_experiments.py; do not hand-edit.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in macros.items())+'\n')
    table=['\\begin{tabular}{p{.39\\linewidth}lll}','\\toprule','Authored case & Target & Observed & Real check \\\\','\\midrule']
    short={'PROVED_REAL':'Proved','COUNTEREXAMPLE':'Counterexample','DOMAIN_ERROR':'Domain error','INVALID_DOMAIN':'Empty domain','NOT_RUN':'Not run'}
    for r in rows: table.append(r['case'].replace('-',' ')+' & '+r['expected'].title()+' & '+r['observed'].title()+' & '+short.get(r['proof'],r['proof'])+' \\\\')
    table+=['\\bottomrule','\\end{tabular}']
    (generated/'corpus-table.tex').write_text('\n'.join(table)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('checker','rows')},indent=2))
    return 0 if summary['expectations_met']==summary['cases'] else 1


if __name__=='__main__': raise SystemExit(main())
