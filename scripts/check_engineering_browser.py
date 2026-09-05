"""Inspect the offline multi-codebase engineering workbench."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
out=root/'artifacts/engineering-browser';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={'width':1536,'height':1120})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((root/'artifacts/engineering/index.html').as_uri(),wait_until='networkidle')
    assert page.locator('#status').inner_text()=='CHECKED_WITH_RUNS'
    assert '36' in page.locator('#summary').inner_text()
    page.screenshot(path=str(out/'engineering-flow.png'),full_page=True)
    page.locator('#flow-select').select_option('encoder-flow')
    page.locator('[data-id="attention"]').click()
    assert 'shared_math/softmax.py' in page.locator('#inspector').inner_text()
    page.locator('#drill-code').click()
    assert page.locator('#code-canvas .eng-node').count()==2
    page.locator('#code-canvas .eng-node').first.click()
    assert 'Observed runtime' in page.locator('#source-inspector').inner_text()
    page.screenshot(path=str(out/'block-source.png'),full_page=True)
    page.locator('[data-view="datasets"]').click()
    assert page.locator('#datasets-list tbody tr').count()==9
    page.locator('#datasets-list summary').click()
    assert '\\begin{tabular}' in page.locator('#datasets-list pre').inner_text()
    page.screenshot(path=str(out/'dataset-latex.png'),full_page=True)
    page.locator('[data-view="flow"]').click()
    page.locator('#flow-select').select_option('encoder-flow')
    page.locator('[data-id="attended"]').click()
    assert 'OBSERVED_MATCH' in page.locator('#inspector').inner_text()
    page.locator('[data-view="runs"]').click()
    assert 'artifact' in page.locator('#runs-list').inner_text().lower()
    assert page.locator('#runs-list details').count()>20
    page.locator('[data-view="equations"]').click()
    assert 'PROVED_REAL' in page.locator('#equations-list').inner_text()
    assert not errors,errors
    (out/'result.json').write_text(json.dumps({'status':'PASS','checks':['36-file inventory','multiple named flows','cross-codebase block drilldown','dataset schema and LaTeX','runtime shape contract','observed calls','attached scalar proof'],'console_errors':errors},indent=2))
    print('Engineering browser checks passed')
    browser.close()
