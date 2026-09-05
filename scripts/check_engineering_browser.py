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
    requests=[];page.on('request',lambda r:requests.append(r.url))
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
    # The reported 637px window must start with readable packages, not 36 tiny cards.
    for width,height in [(1536,1120),(637,863)]:
        page.set_viewport_size({'width':width,'height':height})
        page.reload(wait_until='networkidle')
        page.locator('[data-view="code"]').click()
        assert page.locator('#code-canvas .eng-node').count()==7
        assert '36 files' in page.locator('#code-count').inner_text()
        assert page.locator('#code-canvas svg').get_attribute('data-layout')=='dagre-layered'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('#code-canvas .eng-node text').first.evaluate(
            'e => e.getBBox().height * e.getScreenCTM().a') >= 11
        page.locator('#code-view').scroll_into_view_if_needed()
        page.screenshot(path=str(out/f'source-packages-{width}.png'),full_page=width>1000)
        before=page.locator('#code-zoom').inner_text()
        page.locator('[data-graph="code"] [data-zoom="in"]').click()
        assert page.locator('#code-zoom').inner_text()!=before
        page.locator('[data-graph="code"] [data-zoom="fit"]').click()
        assert page.locator('#code-canvas').evaluate('e => e.scrollHeight <= e.clientHeight+1')
        model=page.locator('[data-id="package:research:sequence_lab/model"]')
        model.click()
        assert page.locator('#code-canvas .eng-node.dimmed').count()>0
        assert page.locator('#code-canvas .eng-edge.connected').count()>0
        page.locator('#focus-source').click()
        assert page.locator('#code-canvas .eng-node').count()<7
        page.locator('#clear-code-focus').click()
        assert page.locator('#code-canvas .eng-node').count()==7
        model.click()
        page.locator('#open-package').click()
        assert 10 < page.locator('#code-canvas .eng-node').count() < 36
        assert page.locator('#code-canvas rect[stroke-dasharray]').count()>0
        assert 'direct dependencies' in page.locator('#code-context').inner_text()
        page.locator('#clear-code-focus').click()
        assert page.locator('#code-detail').input_value()=='packages'
        page.locator('#code-detail').select_option('files')
        assert page.locator('#code-canvas .eng-node').count()==36
        # Isolated __init__ files can be focused without inventing connections.
        page.locator('[data-id="research:sequence_lab/model/__init__.py"]').click()
        page.locator('#focus-source').click()
        assert page.locator('#code-canvas .eng-node').count()==1
        page.locator('#clear-code-focus').click()
        page.locator('#code-detail').select_option('packages')
        page.locator('#code-direction').select_option('LR')
        entry=page.locator('[data-id="package:research:."] rect')
        main=page.locator('[data-id="package:research:sequence_lab"] rect')
        assert float(entry.get_attribute('x')) < float(main.get_attribute('x'))
        page.locator('[data-graph="code"] [data-zoom="reset"]').click()
        canvas=page.locator('#code-canvas')
        canvas.scroll_into_view_if_needed()
        box=canvas.bounding_box()
        page.mouse.move(box['x']+min(300,box['width']-20),box['y']+8)
        page.mouse.down();page.mouse.move(box['x']+30,box['y']+8,steps=6);page.mouse.up()
        assert canvas.evaluate('e => e.scrollLeft')>0
        with page.expect_download() as download:
            page.locator('#code-svg-export').click()
        svg_path=out/f'source-dependencies-{width}.svg'
        download.value.save_as(svg_path)
        from xml.etree import ElementTree
        svg=ElementTree.parse(svg_path).getroot()
        assert svg.tag.endswith('svg') and svg.get('viewBox')
    assert not [url for url in requests if url.startswith(('https://','http://'))],requests
    assert not errors,errors
    (out/'result.json').write_text(json.dumps({'status':'PASS','checks':['36-file inventory','multiple named flows','cross-codebase block drilldown','dataset schema and LaTeX','runtime shape contract','observed calls','attached scalar proof','offline layered layout','637px package overview','dependency highlight and focus','package expansion with external dependencies','36-file view','zoom, fit and drag pan','layout direction','SVG export'],'console_errors':errors},indent=2))
    print('Engineering browser checks passed')
    browser.close()
