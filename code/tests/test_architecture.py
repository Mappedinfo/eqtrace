import json
from pathlib import Path
import pytest
from eqtrace.datasets import scan_dataset,dataset_latex
from eqtrace.codegraph import scan_codebases
from eqtrace.architecture import scan_architecture,trace_run
from eqtrace.ir import Unsupported


def test_csv_schema_and_latex_without_raw_rows(tmp_path):
    p=tmp_path/'data.csv';p.write_text('a,b,secret&name\n1,2.5,privatevalue\n2,,another\n')
    d=scan_dataset(p,'test')
    assert (d['rows_total'],len(d['columns']))==(2,3)
    assert d['columns'][1]['nulls']==1
    assert d['columns'][0]['min']==1
    assert 'privatevalue' not in json.dumps(d)
    assert r'secret\&name' in dataset_latex(d)


def test_partial_jsonl_and_missing_columns(tmp_path):
    p=tmp_path/'data.jsonl';p.write_text('{"x":1}\n{"y":2}\n{"x":3}\n')
    d=scan_dataset(p,'test',max_rows=2)
    assert d['status']=='PARTIAL' and d['rows_total'] is None
    assert {c['name']:c['nulls'] for c in d['columns']}=={'x':1,'y':1}


@pytest.mark.parametrize('text',['a,a\n1,2\n','a,b\n1,2,3\n'])
def test_malformed_csv_is_not_a_dataset_pass(tmp_path,text):
    p=tmp_path/'data.csv';p.write_text(text)
    with pytest.raises(Unsupported):scan_dataset(p,'test')


def test_codebase_imports_and_uncertain_paths(tmp_path):
    first=tmp_path/'first';second=tmp_path/'second';first.mkdir();second.mkdir()
    (first/'main.py').write_text('from shared import compute\ndef run(x):\n    try:\n        return compute(x)\n    except Exception:\n        return x\n')
    (second/'shared.py').write_text('def compute(x):\n    return x*x\n')
    scan=scan_codebases({'a':first,'b':second})
    assert scan['imports'][0]['targets']==['b:shared.py']
    assert scan['calls'][0]['targets']==['b:shared.py::compute']
    assert scan['findings'][0]['kind']=='exception_handler'
    assert 'Possible alternate path' in scan['findings'][0]['scope']


@pytest.fixture
def engineering(tmp_path):
    (tmp_path/'code').mkdir();(tmp_path/'data.csv').write_text('x\n1\n2\n')
    (tmp_path/'code/job.py').write_text('from pathlib import Path\n\ndef calculate():\n    value=Path("data.csv").read_text()\n    Path("result.txt").write_text(value)\n\nif __name__=="__main__":\n    calculate()\n')
    manifest=tmp_path/'architecture.toml'
    manifest.write_text('''schema_version=1
[[repositories]]
id="repo"
path="code"
[[datasets]]
id="data"
path="data.csv"
[[entities]]
id="result"
type="text"
meaning="observed output"
path="result.txt"
[[blocks]]
id="calculate"
meaning="copy input to result"
members=[{repository="repo",pattern="*.py"}]
inputs=["data"]
outputs=["result"]
[[runs]]
id="run"
repository="repo"
entrypoint="job.py"
blocks=["calculate"]
inputs=["data"]
outputs=["result"]
receipt="receipt.json"
''')
    return tmp_path,manifest


def test_engineering_scan_is_not_execution(engineering):
    root,manifest=engineering
    assert scan_architecture(manifest)['status']=='SCANNED'
    assert scan_architecture(manifest,require_runs=True)['status']=='BLOCKED'
    receipt=trace_run(manifest,'run')
    assert receipt['exit_code']==0
    report=scan_architecture(manifest,require_runs=True)
    assert report['status']=='CHECKED_WITH_RUNS'
    assert report['blocks'][0]['execution']=='CALLS_OBSERVED'
    assert any(o['entity']=='result' and o['write'] for o in receipt['trace']['artifact_opens'])
    (root/'data.csv').write_text('x\n3\n')
    report=scan_architecture(manifest,require_runs=True)
    assert report['status']=='BLOCKED' and 'Dataset changed' in str(report['errors'])


def test_old_output_cannot_stand_in_for_execution(engineering):
    root,manifest=engineering
    (root/'result.txt').write_text('an old output')
    (root/'code/job.py').write_text('def calculate():\n    return 1\n\nif __name__=="__main__":\n    calculate()\n')
    receipt=trace_run(manifest,'run')
    assert receipt['exit_code']!=0
    assert 'Output existed but was not written: result' in receipt['errors']
    assert scan_architecture(manifest,True)['status']=='BLOCKED'


def test_importing_a_module_does_not_execute_its_block(engineering):
    root,manifest=engineering
    (root/'code/job.py').write_text('from pathlib import Path\ndef calculate():\n    return 1\n\nPath("result.txt").write_text("output")\n')
    receipt=trace_run(manifest,'run')
    assert receipt['exit_code']==0
    report=scan_architecture(manifest,True)
    assert report['status']=='BLOCKED'
    assert 'No function execution observed' in str(report['errors'])


def test_dangling_membership_and_interfaces(engineering):
    root,manifest=engineering
    manifest.write_text(manifest.read_text().replace('pattern="*.py"','pattern="missing.py"').replace('inputs=["data"]','inputs=["unknown"]'))
    report=scan_architecture(manifest)
    assert report['status']=='BLOCKED'
    assert 'Empty membership' in str(report['errors']) and 'Dangling' in str(report['errors'])


def test_changed_output_invalidates_run(engineering):
    root,manifest=engineering
    trace_run(manifest,'run')
    (root/'result.txt').write_text('tampered')
    assert 'Artifact changed' in str(scan_architecture(manifest,True)['errors'])


def test_source_change_invalidates_run(engineering):
    root,manifest=engineering
    trace_run(manifest,'run')
    with (root/'code/job.py').open('a') as f:f.write('\n# different source revision\n')
    assert 'Source files changed' in str(scan_architecture(manifest,True)['errors'])


def test_observed_array_shape_mismatch_blocks_check(engineering):
    pytest.importorskip('numpy')
    root,manifest=engineering
    with manifest.open('a') as f:f.write('''
[[entities]]
id="array"
type="virtual_tensor"
meaning="array returned by calculation"
shape_axes=[2,4]
observed_at={file="repo:job.py",function="calculate",argument="$return"}
''')
    (root/'code/job.py').write_text('import numpy as np\nfrom pathlib import Path\ndef calculate():\n    Path("result.txt").write_text("ok")\n    return np.ones((2,3))\nif __name__=="__main__":\n    calculate()\n')
    assert trace_run(manifest,'run')['exit_code']==0
    report=scan_architecture(manifest,True)
    assert report['status']=='BLOCKED'
    assert report['shape_checks'][0]['status']=='MISMATCH'
