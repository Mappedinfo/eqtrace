from fractions import Fraction
import json
from pathlib import Path
import sys
import pytest

from eqtrace.ir import Unsupported, evaluate, latex
from eqtrace.latex_parser import equations, parse_equation, parse_expression
from eqtrace.python_parser import parse_function
from eqtrace.pseudocode import parse_pseudocode, pseudocode
from eqtrace.project import check_project, write_report, verify_receipt
from eqtrace.verify import prove, execute
from eqtrace.cli import main
from eqtrace.server import temporary_check


def pair(formula, code, inputs=('x',)):
    return parse_equation(formula, list(inputs))[1], parse_function(code, 'f', list(inputs))


@pytest.mark.parametrize('formula,code,values,expected', [
    (r'y = 2x + 1', 'def f(x):\n    return 2*x+1', {'x':3}, 7),
    (r'y = -x^2', 'def f(x):\n    return -x**2', {'x':3}, -9),
    (r'y = \frac{x+1}{2}', 'def f(x):\n    return (x+1)/2', {'x':3}, 2),
    (r'y = x^{-2}', 'def f(x):\n    return x**-2', {'x':2}, Fraction(1,4)),
    (r'y = \sqrt{x}', 'import math\ndef f(x):\n    return math.sqrt(x)', {'x':4}, 2),
    (r'y = \log{\exp{x}}', 'import math\ndef f(x):\n    return math.log(math.exp(x))', {'x':1}, 1),
])
def test_parser_semantics(formula, code, values, expected):
    ref, fn = pair(formula, code)
    assert ref.semantic() == fn.expression.semantic()
    assert evaluate(ref, values) == expected
    assert fn.compile()(**values) == expected
    assert parse_expression(latex(ref)).semantic() == ref.semantic()


@pytest.mark.parametrize('formula', [r'y = x +', r'y = \unknown{x}', r'y = x^9', r'y = x^x', r'y = x^2^3', r'y = \frac{x}{2} junk', r'y = 1 2', r'y = x; 0', r'y = \sum_i x_i', r'y = x % ignored', r'y = x + z'])
def test_latex_rejects_partial_or_unknown(formula):
    with pytest.raises(Unsupported): parse_equation(formula, ['x'])


@pytest.mark.parametrize('code', [
    'def f(x):\n    pass',
    'def f(x):\n    # intended square\n    return',
    'def f(x):\n    try:\n        return x*x\n    except Exception:\n        return x',
    'def f(x):\n    if x>0:\n        return x*x\n    return x',
    'def f(x):\n    return x if x>0 else 0',
    'def f(x):\n    return eval("x*x")',
    'def f(x):\n    return __import__("os").system("touch impossible")',
    'def f(x):\n    return x//2',
    'def f(x):\n    y=x*x\n    return x',
    'def f(x):\n    x=x*x\n    return x',
    'def f(x):\n    return x\n    return x*x',
    'def f(x=1):\n    return x',
    '@unknown\ndef f(x):\n    return x',
    'def f(x: unknown()):\n    return x',
    'def f(x):\n    return math.exp(x)',
    'def f(x):\n    return [x]',
    'def f(x):\n    return float("nan")',
    'def f(x):\n    return 1e999',
    'def f(x):\n    return x**9',
    'def f(x):\n    return x**x',
    'print("side effect")\ndef f(x):\n    return x',
    'def f(x):\n    return x\ndef f(x):\n    return 0',
])
def test_python_fail_closed(code):
    with pytest.raises(Unsupported): parse_function(code, 'f', ['x'])


def test_zero_power_preserves_domain():
    left, fn = pair(r'y = (1/x)^0', 'def f(x):\n    return (1/x)**0')
    assert prove(left, fn.expression, {'x':[-1,1]}, [])['status'] == 'DOMAIN_ERROR'


def test_algebraic_equality_differs_from_structure():
    left, fn = pair(r'y = (x+1)^2', 'def f(x):\n    return x*x+2*x+1')
    assert left.semantic() != fn.expression.semantic()
    result = prove(left, fn.expression, {'x':[-5,5]}, [])
    assert result['status'] == 'PROVED_REAL'
    assert [q['result'] for q in result['queries']] == ['sat','unsat','unsat']
    import z3
    for query in result['queries']:
        solver = z3.Solver(); solver.from_string(query['smt2'])
        assert str(solver.check()) == query['result']


@pytest.mark.parametrize('formula,code,domain,nonzero,status', [
    (r'y = x^2', 'def f(x):\n    return x', [-2,2], [], 'COUNTEREXAMPLE'),
    (r'y = x/x', 'def f(x):\n    return 1', [-1,1], [], 'DOMAIN_ERROR'),
    (r'y = x/x', 'def f(x):\n    return 1', [-1,1], ['x'], 'PROVED_REAL'),
    (r'y = x', 'def f(x):\n    return x', [0,0], ['x'], 'INVALID_DOMAIN'),
    (r'y = \exp{x}', 'import math\ndef f(x):\n    return math.exp(x)', [-1,1], [], 'UNSUPPORTED'),
])
def test_proof_outcomes(formula,code,domain,nonzero,status):
    left, fn = pair(formula,code)
    assert prove(left,fn.expression,{'x':domain},nonzero)['status'] == status


def test_float_cancellation_is_not_real_proof():
    left, fn = pair(r'y = x', 'def f(x):\n    return (x+10000000000000000)-10000000000000000')
    assert prove(left, fn.expression, {'x':[-1,1]}, [])['status'] == 'PROVED_REAL'
    result = execute(left, fn, {'x':[-1,1]}, [], 16)
    assert result['status'] == 'FAIL'
    assert any(r['status'] == 'MISMATCH' for r in result['records'])


def test_pseudocode_roundtrip_and_sources():
    source = r'''\Require $x, \mu$
\Ensure $y$
\State $d \gets x - \mu$
\State \Return $d^2$'''
    _, expr = parse_pseudocode(source,['x','mu'],20)
    assert expr.line == 23
    assert evaluate(expr,{'x':3,'mu':1}) == 4
    text = pseudocode(expr,['x','mu'],tex=True)
    body = text.split('\\begin{algorithmic}\n')[1].split('\\end{algorithmic}')[0]
    assert parse_pseudocode(body,['x','mu'])[1].semantic() == expr.semantic()


@pytest.mark.parametrize('source', [
    r'\State \Return $x$',
    '\\Require $x$\n\\If{$x>0$}\n\\State \\Return $x$\n\\EndIf',
    '\\Require $x$\n\\State $d \\gets x^2$\n\\State \\Return $x$',
    '\\Require $x$\n\\State $x \\gets x^2$\n\\State \\Return $x$',
    '\\Require $z$\n\\State \\Return $x$',
    '\\Require $x$\n\\State \\Return $x$\n\\State $d \\gets 0$',
])
def test_pseudocode_unsupported(source):
    with pytest.raises(Unsupported): parse_pseudocode(source,['x'])


@pytest.fixture
def project(tmp_path):
    (tmp_path/'paper.tex').write_text('\\begin{equation}\n\\label{eq:test}\ny = x^2\n\\end{equation}\n')
    (tmp_path/'impl.py').write_text('def f(x):\n    return x**2\n')
    (tmp_path/'eqtrace.toml').write_text('''schema_version = 1
paper_sources = ["paper.tex"]
samples = 16
[[contracts]]
id = "test"
label = "eq:test"
implementation = "impl.py"
function = "f"
inputs = ["x"]
domains = {x = [-2,2]}
''')
    return tmp_path


def test_receipt_current_source_and_artifact_tampering(project):
    report = check_project(project/'eqtrace.toml')
    assert report['status'] == 'PASS'
    path = write_report(report,project/'out')
    assert verify_receipt(path,project)['status'] == 'FRESH'
    (project/'out/test/reference.py').write_text('wrong')
    assert 'Changed artifact: test/reference.py' in verify_receipt(path,project)['errors']
    path = write_report(check_project(project/'eqtrace.toml'),project/'out')
    (project/'impl.py').write_text('def f(x):\n    return x\n')
    assert 'Changed source: impl.py' in verify_receipt(path,project)['errors']
    tampered = json.loads(path.read_text());tampered['status']='FAIL';path.write_text(json.dumps(tampered))
    assert 'Report payload digest mismatch' in verify_receipt(path,project)['errors']


def test_sample_only_is_not_merge_pass(project):
    assert main(['check',str(project/'eqtrace.toml'),'--sample-only','--out',str(project/'out')]) == 3
    report=json.loads((project/'out/report.json').read_text())
    assert report['status']=='SAMPLED_ONLY'
    assert verify_receipt(project/'out/report.json',project)['status']=='STALE_OR_INVALID'


@pytest.mark.parametrize('mutation', ['missing','unbound','duplicate','empty','unknown_setting','no_samples','external_path','domain_missing'])
def test_manifest_failures(project,mutation):
    manifest=project/'eqtrace.toml'
    if mutation=='missing': (project/'impl.py').unlink()
    elif mutation=='unbound': (project/'paper.tex').write_text((project/'paper.tex').read_text()+'\\begin{equation}\\label{eq:other}y=x\\end{equation}')
    elif mutation=='duplicate': (project/'paper.tex').write_text((project/'paper.tex').read_text()*2)
    elif mutation=='empty': manifest.write_text('schema_version=1\npaper_sources=["paper.tex"]\ncontracts=[]')
    elif mutation=='unknown_setting': manifest.write_text('skip_errors=true\n'+manifest.read_text())
    elif mutation=='no_samples': manifest.write_text(manifest.read_text().replace('samples = 16','samples = 0'))
    elif mutation=='external_path': manifest.write_text(manifest.read_text().replace('"impl.py"','"../impl.py"'))
    elif mutation=='domain_missing': manifest.write_text(manifest.read_text().replace('domains = {x = [-2,2]}','domains = {}'))
    assert check_project(manifest)['status'] != 'PASS'


def test_live_check_runs_and_detects_mutation():
    payload={'latex':'y = x^2','code':'def f(x):\n    return x\n','kind':'equation','contract':{'id':'live','label':'eq:live','function':'f','inputs':['x'],'domains':{'x':[-2,2]},'nonzero':[],'policy':'algebraic'}}
    report=temporary_check(payload)
    assert report['status']=='FAIL'
    assert report['contracts'][0]['proof']['status']=='COUNTEREXAMPLE'


def test_unknown_solver_result_never_passes(monkeypatch):
    import z3
    monkeypatch.setattr(z3.Solver,'check',lambda self,*args:z3.unknown)
    left,fn=pair('y=x','def f(x):\n    return x')
    assert prove(left,fn.expression,{'x':[-1,1]},[])['status']=='UNKNOWN'


def test_z3_missing_explicitly_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules,'z3',None)
    left,fn=pair('y=x','def f(x):\n    return x')
    assert prove(left,fn.expression,{'x':[-1,1]},[])['status']=='UNAVAILABLE'
