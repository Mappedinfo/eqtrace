"""Browser integration checks against an already running loopback workbench."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright, expect

url = sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8765'
out = Path(__file__).resolve().parents[1] / 'artifacts/browser'
out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
    errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.goto(url,wait_until='networkidle')
    assert page.locator('#overall').inner_text()=='PASS'
    assert page.locator('nav button').count()==4
    assert page.locator('math').count()==2
    page.screenshot(path=str(out/'compare.png'),full_page=True)
    page.get_by_role('tab',name='02').click()
    assert page.locator('.graph-node').count()>0
    page.locator('.graph-node').first.click()
    assert 'Semantic SHA-256' in page.locator('#node-detail').inner_text()
    page.screenshot(path=str(out/'graph.png'),full_page=True)
    with page.expect_download() as dl:
        page.locator('#export-svg').click()
    assert dl.value.suggested_filename.endswith('-merged.svg')
    page.locator('#search').fill('expanded')
    assert page.locator('nav button').count()==1
    page.locator('nav button').click()
    page.get_by_role('tab',name='01').click()
    assert 'DIFFERENT' in page.locator('#checks').inner_text()
    assert 'PROVED_REAL' in page.locator('#checks').inner_text()
    page.locator('#edit summary').click()
    page.locator('#edit-code').fill('def expanded(x):\n    return x*x + 1\n')
    page.locator('#run').click()
    expect(page.locator('#overall')).to_have_text('FAIL')
    assert 'COUNTEREXAMPLE' in page.locator('#checks').inner_text()
    page.get_by_role('tab',name='03').click()
    page.locator('#fail-only').check()
    assert page.locator('#samples tr').count()>0
    page.screenshot(path=str(out/'counterexample.png'),full_page=True)
    assert not errors,errors
    assert all(r.startswith(url) or r.startswith('blob:') for r in requests),requests
    assert page.request.post(url+'/api/check',data='{}',headers={'Origin':'https://example.com','Content-Type':'application/json'}).status==403
    page.goto(url,wait_until='networkidle')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    (out/'result.json').write_text(json.dumps({'status':'PASS','checks':['initial receipt','rendered math','graph selection','SVG export','filter','algebraic difference','live edit counterexample','execution filter','no external assets','cross-origin rejection','mobile width'],'console_errors':errors},indent=2))
    print('Browser checks passed; artifacts/browser contains screenshots and result.json')
    browser.close()
