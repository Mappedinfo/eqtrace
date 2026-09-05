"""Export manuscript tables and portable snapshots from current checked reports."""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def main():
    architecture = json.loads((ROOT/'artifacts/engineering/architecture.json').read_text())
    selfcheck = json.loads((ROOT/'artifacts/selfcheck/report.json').read_text())
    if architecture['status'] != 'CHECKED_WITH_RUNS' or selfcheck['status'] != 'PASS':
        raise SystemExit('Paper export requires current successful engineering and self-check runs')
    metrics = json.loads((ROOT/'examples/engineering/products/metrics.json').read_text())
    summary = architecture['summary']
    shapes = architecture['shape_checks']
    run = architecture['runs'][0]
    values = {'EngineeringFiles':summary['files'], 'EngineeringCodebases':summary['codebases'],
              'EngineeringBlocks':summary['blocks'], 'EngineeringFlows':len(architecture['flows']),
              'DatasetRows':architecture['datasets'][0]['rows_total'],
              'DatasetColumns':len(architecture['datasets'][0]['columns']),
              'ShapeContracts':sum(s['status']=='OBSERVED_MATCH' for s in shapes),
              'ObservedFiles':len(run['trace']['files']), 'SelfContracts':len(selfcheck['contracts']),
              'ValidationSamples':metrics['validation_samples'],
              'TrainingSteps':len(metrics['training_loss'])-1, 'AdaptationSteps':len(metrics['finetuning_loss'])-1,
              'TrainingInitial':format(metrics['training_loss'][0],'.6f'),
              'TrainingFinal':format(metrics['training_loss'][-1],'.6f'),
              'AdaptationInitial':format(metrics['finetuning_loss'][0],'.6f'),
              'AdaptationFinal':format(metrics['finetuning_loss'][-1],'.6f'),
              'ValidationMSE':format(metrics['validation_mse'],'.6f')}
    tests = ROOT/'artifacts/tests.xml'
    if tests.is_file():
        suites=ET.parse(tests).getroot().findall('testsuite')
        if any(int(s.get('failures','0'))+int(s.get('errors','0')) for s in suites):
            raise SystemExit('Unit test failures prevent paper evidence export')
        values['UnitTests']=sum(int(s.get('tests','0'))-int(s.get('skipped','0')) for s in suites)
    generated=ROOT/'paper/generated'
    generated.mkdir(exist_ok=True)
    (generated/'engineering.tex').write_text('% Generated from current artifacts by scripts/export_paper_evidence.py\n'+
        '\n'.join('\\newcommand{\\'+k+'}{'+str(v)+'}' for k,v in values.items())+'\n')
    (generated/'dataset-table.tex').write_text(architecture['datasets'][0]['latex'])
    (ROOT/'evidence/engineering-summary.json').write_text(json.dumps({'values':values,'summary':summary,
        'run_status':run['status'],'source_hashes':architecture['source_hashes'],
        'dataset_sha256':architecture['datasets'][0]['sha256'],'checker':architecture['checker']},indent=2)+'\n')
    # Release snapshots are observations of this host/run. Re-run make demo on a
    # different environment before describing them as fresh verification.
    for src,dst in [('artifacts/engineering','docs/demo/engineering'),
                    ('artifacts/equations','docs/demo/equations'),
                    ('artifacts/self-architecture','docs/demo/self-architecture')]:
        destination=ROOT/dst;destination.mkdir(parents=True,exist_ok=True)
        for path in (ROOT/src).iterdir():
            if path.is_file():shutil.copy2(path,destination/path.name)
    print(json.dumps(values,indent=2))

if __name__=='__main__':main()
