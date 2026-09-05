'use strict';
let report=JSON.parse(document.getElementById('report-data').textContent);
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge=s=>`<span class="badge ${/CHECKED|OBSERVED|EXECUTED|SCANNED|PASS/.test(s)?'pass':/BLOCKED|FAIL|STALE/.test(s)?'fail':''}">${esc(s)}</span>`;
const pretty=x=>JSON.stringify(x,null,2);
const download=(name,text,type)=>{const a=document.createElement('a'),u=URL.createObjectURL(new Blob([text],{type}));a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
const panel=(label,body)=>`<h3>${esc(label)}</h3>${body}`;
let view='flow';
function setView(next){view=next;document.querySelectorAll('#views button').forEach(b=>b.classList.toggle('active',b.dataset.view===next));['flow','code','datasets','runs','equations'].forEach(v=>$(v+'-view').hidden=v!==next);if(next==='code')drawCode();}
const graphStates = {};
let codeFocus = null, packageFocus = null, currentCode = {nodes: [], edges: []};
function nodeLines(label) {
  const words = label.replaceAll('/', '/ ').split(/\s+/), lines = [''];
  for (const word of words) {
    const last = lines.length - 1;
    if (lines[last] && (lines[last] + word).length > 25) lines.push(word);
    else lines[last] += (lines[last] ? ' ' : '') + word;
  }
  return lines.slice(0, 2).map((line, i) => line.length > 26 ? line.slice(0, 25) + '…' :
    (i === 1 && lines.length > 2 ? line.slice(0, 24) + '…' : line));
}
function graphSvg(nodes, edges, mode) {
  const layout = EqTraceLayout.layout(nodes, edges, $(mode + '-direction').value);
  graphStates[mode] = {...layout, scale: 1};
  if (!nodes.length) return '<p class="empty-graph">No nodes match these filters.</p>';
  let html = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${layout.width} ${layout.height}" data-layout="dagre-layered" role="img" aria-label="${mode === 'code' ? 'Source dependency graph' : 'Semantic engineering flow'}"><style>.eng-node{cursor:pointer}.eng-edge{transition:opacity .12s}.eng-node.dimmed,.eng-edge.dimmed{opacity:.13}.eng-node.selected rect{stroke:#205e43;stroke-width:3}.eng-node.connected rect{stroke:#69875b;stroke-width:2}.eng-edge.connected path{stroke:#2c6a4b;stroke-width:2}.eng-node:hover rect,.eng-node:focus rect{stroke:#205e43;stroke-width:2.5}</style><defs><marker id="eng-arrow-${mode}" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="#81977a"/></marker></defs>`;
  for (const e of layout.edges) {
    const d = e.points.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ');
    html += `<g class="eng-edge" data-from="${esc(e.from)}" data-to="${esc(e.to)}"><title>${esc(e.from)} → ${esc(e.to)}${e.count > 1 ? ' · ' + e.count + ' imports' : ''}</title><path d="${d}" stroke="#9bad94" fill="none" stroke-width="1.35" stroke-linejoin="round" marker-end="url(#eng-arrow-${mode})" ${e.evidence === 'declared' ? 'stroke-dasharray="5 4"' : ''}/></g>`;
  }
  for (const n of layout.nodes) {
    const x = n.x - n.width / 2, y = n.y - n.height / 2;
    const palette = {dataset: ['#e3ecf5', '#8499ae'], block: ['#e4eedf', '#91a383'], entity: ['#fbf4e5', '#bbad8a'], package: ['#edf2e8', '#90a382'], file: ['#ffffff', '#a3af98']};
    const [fill, stroke] = palette[n.kind] || palette.file;
    const path = (n.path || '').split('/');
    const lines = n.kind === 'file' ? [path.pop(), path.join('/') || '(root)'].map(t => t.length > 26 ? t.slice(0, 25) + '…' : t) : nodeLines(n.label);
    const subtitle = n.kind === 'package' ? `${n.repository} · ${n.files.length} ${n.files.length === 1 ? 'file' : 'files'}` : n.kind === 'file' ? n.repository + (n.context ? ' · dependency' : ' · SCANNED') : `${n.kind} · ${n.status || n.evidence}`;
    html += `<g class="eng-node" data-id="${esc(n.id)}" data-kind="${esc(n.kind)}" role="button" tabindex="0" aria-label="${esc(n.label)}"><title>${esc(n.id)}</title><rect x="${x}" y="${y}" width="${n.width}" height="${n.height}" rx="8" fill="${fill}" stroke="${stroke}" ${n.context ? 'stroke-dasharray="4 3"' : ''}/>${lines.map((line, i) => `<text x="${x + 15}" y="${y + 27 + i * 17}" font-family="sans-serif" font-size="${n.kind === 'file' && i === 1 ? 11 : 14}" font-weight="500" fill="#29412b">${esc(line)}</text>`).join('')}<text x="${x + 15}" y="${y + n.height - 16}" font-family="monospace" font-size="10.5" fill="#65765f">${esc(subtitle)}</text></g>`;
  }
  return html + '</svg>';
}
function zoomGraph(mode, value, reset = false) {
  const state = graphStates[mode], canvas = $(mode + '-canvas'), svg = canvas.querySelector('svg');
  if (!state || !svg) return;
  const oldScale = state.scale, next = Math.max(.2, Math.min(2, value));
  const cx = (canvas.scrollLeft + canvas.clientWidth / 2) / oldScale, cy = (canvas.scrollTop + canvas.clientHeight / 2) / oldScale;
  state.scale = next; svg.style.width = state.width * next + 'px'; svg.style.height = state.height * next + 'px';
  canvas.scrollLeft = reset ? 0 : cx * next - canvas.clientWidth / 2;
  canvas.scrollTop = reset ? 0 : cy * next - canvas.clientHeight / 2;
  $(mode + '-zoom').textContent = Math.round(next * 100) + '%';
}
function prepareGraph(mode) {
  const canvas = $(mode + '-canvas'), state = graphStates[mode];
  // Preserve legible type by default; Fit is an explicit overview action.
  zoomGraph(mode, Math.min(1, Math.max(.8, Math.min((canvas.clientWidth - 24) / state.width, (canvas.clientHeight - 24) / state.height))), true);
  let drag;
  canvas.onpointerdown = event => {
    if (event.pointerType === 'touch' || event.button !== 0 || event.target.closest('.eng-node')) return;
    drag = {x: event.clientX, y: event.clientY, left: canvas.scrollLeft, top: canvas.scrollTop};
    canvas.setPointerCapture(event.pointerId); canvas.classList.add('panning');
  };
  canvas.onpointermove = event => {
    if (!drag) return;
    canvas.scrollLeft = drag.left - event.clientX + drag.x;
    canvas.scrollTop = drag.top - event.clientY + drag.y;
  };
  const stop = () => {drag = null; canvas.classList.remove('panning');};
  canvas.onpointerup = stop; canvas.onpointercancel = stop;
}
function highlightGraph(mode, id) {
  const state = graphStates[mode], neighbors = new Set([id]);
  for (const e of state.edges) {if (e.from === id) neighbors.add(e.to); if (e.to === id) neighbors.add(e.from);}
  $(mode + '-canvas').querySelectorAll('.eng-node').forEach(node => {
    node.classList.toggle('selected', node.dataset.id === id);
    node.classList.toggle('connected', node.dataset.id !== id && neighbors.has(node.dataset.id));
    node.classList.toggle('dimmed', !neighbors.has(node.dataset.id));
  });
  $(mode + '-canvas').querySelectorAll('.eng-edge').forEach(edge => {
    const connected = edge.dataset.from === id || edge.dataset.to === id;
    edge.classList.toggle('connected', connected); edge.classList.toggle('dimmed', !connected);
  });
}
function bindNodes(container,callback){container.querySelectorAll('.eng-node').forEach(el=>{el.onclick=()=>callback(el.dataset.id);el.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();callback(el.dataset.id);}};});}
function inspectNode(id){const n=report.nodes.find(n=>n.id===id);if(!n){$('inspector').textContent='No accepted nodes.';return;}const d=n.detail;let content=`<div class="eyebrow">${esc(n.kind)} / ${esc(n.evidence)}</div><h3>${esc(n.label)}</h3>${badge(n.status)}`;
  if(n.kind==='block'){content+=`<p>${esc(d.meaning)}</p><strong>Declared interfaces</strong><p>Inputs: ${esc((d.inputs||[]).join(', ')||'none')}<br>Outputs: ${esc((d.outputs||[]).join(', ')||'none')}</p><strong>${d.members.length} source files · ${d.executed_members.length} with observed function calls</strong><ul>${d.members.map(f=>`<li><span>${d.executed_members.includes(f)?'●':'○'}</span><code>${esc(f)}</code></li>`).join('')}</ul>`;if(d.equation_evidence?.length)content+=panel('Bound scalar contracts',d.equation_evidence.map(e=>`<p>${esc(e.binding)}<br>${badge(e.proof)} · ${e.executed_samples} samples</p>`).join(''));if(d.parent)content+=`<p>Parent block: ${esc(d.parent)}</p>`;if(d.findings.length)content+=panel('Review paths',d.findings.map(f=>`<p>${esc(f.kind)} at <code>${esc(f.file)}:${f.line}</code></p>`).join(''));content+='<button id="drill-code">Inspect block source graph →</button>';}
  else if(n.kind==='dataset'){content+=`<p>${esc(d.description)}</p><strong>${d.rows_scanned} rows scanned · ${d.columns.length} columns</strong><p>Full scan: ${d.complete}<br>Bytes: ${d.bytes}</p><code>SHA-256 ${esc(d.sha256)}</code><button id="drill-data">Inspect schema and LaTeX →</button>`;}
  else {
    content+=`<p>${esc(d.meaning)}</p><strong>Declared type</strong><p>${esc(d.type)}<br>${esc(d.shape||'')}</p>`;
    if(d.path)content+=`<code>${esc(d.path)}</code><p>Artifact: ${esc(d.artifact_status)}</p><code>${esc(d.sha256||'')}</code>`;
    else content+='<p>Virtual interface. Runtime observations are listed separately under Execution evidence.</p>';
    if(d.shape_check)content+=`<h3>Observed interface check</h3>${badge(d.shape_check.status)}<pre>${esc(pretty(d.shape_check.observations))}</pre>`;
  }
  $('inspector').innerHTML=content;if($('drill-code'))$('drill-code').onclick=()=>{$('block-filter').value=id;$('repo-filter').value='';$('code-detail').value='files';codeFocus=null;packageFocus=null;setView('code');};if($('drill-data'))$('drill-data').onclick=()=>setView('datasets');
}
function drawFlow() {
  const flow = report.flows.find(f => f.id === $('flow-select').value);
  const selected = new Set(flow?.nodes || report.nodes.map(n => n.id));
  const nodes = [...selected].map(id => report.nodes.find(n => n.id === id)).filter(Boolean);
  const edges = report.edges.concat(flow?.edges || []);
  $('flow-canvas').innerHTML = graphSvg(nodes, edges, 'flow'); prepareGraph('flow');
  bindNodes($('flow-canvas'), id => {highlightGraph('flow', id); inspectNode(id);});
  inspectNode(nodes.find(n => n.kind === 'block')?.id || nodes[0]?.id);
}
function clearCodeFocus() {codeFocus = null; packageFocus = null; drawCode();}
function inspectSource(id) {
  const node = currentCode.nodes.find(n => n.id === id);
  if (!node) return;
  highlightGraph('code', id);
  if (node.kind === 'package') {
    $('source-inspector').innerHTML = `<div class="eyebrow">${esc(node.repository)} / SOURCE PACKAGE</div><h3>${esc(node.label)}</h3><p>${node.files.length} files grouped by their source directory.</p><button id="open-package">Open ${node.files.length} files →</button><button id="focus-source">Focus direct connections</button><h3>Files</h3><ul>${node.files.map(f => `<li><span>·</span><code>${esc(f.split(':').slice(1).join(':'))}</code></li>`).join('')}</ul>`;
    $('open-package').onclick = () => {$('code-detail').value = 'files'; packageFocus = node.id; codeFocus = null; drawCode();};
  } else {
    const f = report.code.files.find(f => f.id === id), symbols = report.code.symbols.filter(s => s.file === id), calls = report.code.calls.filter(c => c.file === id);
    const observed = report.runs.filter(r => r.status === 'EXECUTED').flatMap(r => r.trace?.files || []).filter(o => o.file === id);
    $('source-inspector').innerHTML = `<div class="eyebrow">${esc(f.repository)} / STATIC SOURCE</div><h3>${esc(f.path)}</h3>${badge(f.status)}<p>${f.lines} lines · ${symbols.length} definitions<br>${calls.filter(c => c.resolution === 'unresolved').length} unresolved calls</p><button id="focus-source">Focus direct connections</button><p><code>${esc(f.sha256)}</code></p>` + panel('Definitions', symbols.map(s => `<p><code>${esc(s.qualified_name)}:${s.line}</code><br>${esc(s.kind)}</p>`).join('')) + panel('Observed runtime', observed.length ? observed.map(o => `<p>${o.lines.length} lines reached<br>${esc(Object.entries(o.calls).map(([n,k]) => n + ' × ' + k).join(', '))}</p>`).join('') : '<p>No fresh trace covers this file.</p>') + panel('Static call candidates', calls.slice(0,50).map(c => `<p><code>${esc(c.name)}:${c.line}</code><br>${esc(c.resolution)}</p>`).join(''));
  }
  $('focus-source').onclick = () => {codeFocus = id; packageFocus = null; drawCode();};
}
function drawCode() {
  let files = report.code?.files || [];
  const block = report.blocks.find(b => b.id === $('block-filter').value), repo = $('repo-filter').value;
  if (block) files = files.filter(f => block.members.includes(f.id));
  if (repo) files = files.filter(f => f.repository === repo);
  let edges = EqTraceLayout.uniqueEdges(files, (report.code?.imports || []).flatMap(e => e.targets.map(t => ({from: e.from, to: t, evidence: 'static'}))));
  let nodes = files.map(f => ({...f, kind: 'file', label: f.path}));
  if ($('code-detail').value === 'packages') ({nodes, edges} = EqTraceLayout.packages(files, edges));
  else if (packageFocus) {
    const members = new Set(files.filter(f => EqTraceLayout.packageId(f) === packageFocus).map(f => f.id));
    const ids = new Set(members);
    for (const e of edges) if (members.has(e.from)) ids.add(e.to);
    nodes = nodes.filter(n => ids.has(n.id)).map(n => ({...n, context: !members.has(n.id)}));
    edges = EqTraceLayout.uniqueEdges(nodes, edges);
  }
  if (codeFocus) ({nodes, edges} = EqTraceLayout.neighborhood(nodes, edges, codeFocus));
  currentCode = {nodes, edges};
  $('code-canvas').innerHTML = graphSvg(nodes, edges, 'code'); prepareGraph('code');
  $('code-count').textContent = `${nodes.length} ${$('code-detail').value === 'packages' ? 'packages · ' + files.length + ' files' : 'files'} · ${edges.length} connections`;
  $('code-context').hidden = !codeFocus && !packageFocus;
  $('code-context').innerHTML = `<button id="clear-code-focus">← ${packageFocus ? 'Package overview' : 'Show all ' + $('code-detail').value}</button><span>${esc(codeFocus ? 'Direct connections: ' + codeFocus : packageFocus ? packageFocus + ' + direct dependencies' : '')}</span>`;
  $('clear-code-focus').onclick = () => {if (packageFocus) $('code-detail').value = 'packages'; clearCodeFocus();};
  $('source-inspector').innerHTML = '<h3>Explore the dependencies</h3><p>Select a node to highlight its direct connections. Open a package to inspect its files.</p><small>Scroll to explore · drag the background to pan</small>';
  bindNodes($('code-canvas'), inspectSource);
  if (codeFocus && nodes.some(n => n.id === codeFocus)) inspectSource(codeFocus);
}
function renderTables(){
  $('datasets-list').innerHTML=report.datasets.map(d=>`<article class="data-section"><div class="dataset-header"><h3>${esc(d.id)}</h3>${badge(d.status)}</div><p>${esc(d.description)} · ${d.rows_scanned} rows scanned · ${d.complete?'complete file':'partial scan'} · ${d.bytes} bytes</p><table><thead><tr><th>Column</th><th>Observed types</th><th>Missing / scanned</th><th>Numeric range</th></tr></thead><tbody>${d.columns.map(c=>`<tr><td>${esc(c.name)}</td><td>${esc(c.types.join(', '))}</td><td>${c.nulls}/${d.rows_scanned}</td><td>${esc(c.min??'—')} … ${esc(c.max??'—')}</td></tr>`).join('')}</tbody></table><details><summary>Automatically generated LaTeX table</summary><pre>${esc(d.latex)}</pre></details><p><code>SHA-256 ${esc(d.sha256)}</code></p></article>`).join('')||'<p>No datasets selected.</p>';
  $('runs-list').innerHTML=report.runs.map(r=>`<article class="run-section"><div class="dataset-header"><h3>${esc(r.id)}</h3>${badge(r.status)}</div><p>${esc(r.trace?.scope||'No actual run recorded.')}</p>${r.errors.length?`<div class="notice bad">${esc(r.errors.join('; '))}</div>`:''}<p>${r.trace?.files?.length||0} source files observed · ${r.trace?.calls?.length||0} call relationships · ${r.trace?.duration_ms??'—'} ms</p><h3>Declared artifact I/O observed during this run</h3><pre>${esc(pretty(r.trace?.artifact_opens||[]))}</pre><h3>Functions and observed array interfaces</h3><div class="evidence-list">${(r.trace?.files||[]).filter(f=>f.arrays?.length||Object.keys(f.calls).some(n=>n!=='<module>')).map(f=>`<details><summary>${esc(f.file)} · ${f.lines.length} lines reached</summary><pre>${esc(pretty({calls:f.calls,array_arguments:f.arrays,exceptions:f.exceptions}))}</pre></details>`).join('')}</div></article>`).join('')||'<div class="notice">No runs declared. Static scans do not establish execution.</div>';
  $('equations-list').innerHTML=report.equations?.length?report.equations.map(e=>`<article class="data-section"><h3>${esc(e.manifest)}</h3>${badge(e.report.status)}${e.report.contracts.map(c=>`<p>${esc(c.id)} · ${esc(c.proof.status)} · ${c.execution.executed} executed samples</p>`).join('')}</article>`).join(''):'<div class="notice">No scalar equation contracts attached to this engineering manifest. Tensor block meanings and observed runtime shapes carry no real-equivalence proof. Use equation_manifests to attach checkable local kernels.</div>';
}
function render(){
  for(const key of ['nodes','edges','blocks','flows','datasets','runs','equations','errors'])report[key]??=[];
  $('title').textContent=report.title;$('scope').textContent=report.scope;$('status').innerHTML=esc(report.status);$('status').className='badge '+(report.errors.length?'fail':'pass');$('errors').innerHTML=report.errors.map(e=>`<div class="notice bad">${esc(e)}</div>`).join('');const s=report.summary||{};
  $('summary').innerHTML=[['CODEBASES',s.codebases],['SOURCE FILES',s.files],['SEMANTIC BLOCKS',s.blocks],['DATASETS',s.datasets],['EXECUTED RUNS',s.executed_runs]].map(([l,v])=>`<div class="stat"><strong>${v??'—'}</strong><small>${l}</small></div>`).join('');
  $('flow-select').innerHTML='<option value="">All declared entities</option>'+report.flows.map(f=>`<option value="${esc(f.id)}">${esc(f.label||f.id)}</option>`).join('');if(report.flows.length)$('flow-select').value=report.flows[0].id;
  $('block-filter').innerHTML='<option value="">All blocks</option>'+report.blocks.map(b=>`<option value="${esc(b.id)}">${esc(b.label||b.id)}</option>`).join('');$('repo-filter').innerHTML='<option value="">All codebases</option>'+[...new Set((report.code?.files||[]).map(f=>f.repository))].map(id=>`<option>${esc(id)}</option>`).join('');renderTables();drawFlow();setView(view);
}
document.querySelectorAll('#views button').forEach(b => b.onclick = () => setView(b.dataset.view));
$('flow-select').onchange = drawFlow; $('flow-direction').onchange = drawFlow;
for (const id of ['block-filter', 'repo-filter', 'code-detail']) $(id).onchange = clearCodeFocus;
$('code-direction').onchange = drawCode;
document.querySelectorAll('.graph-tools button[data-zoom]').forEach(button => button.onclick = () => {
  const mode = button.closest('[data-graph]').dataset.graph, state = graphStates[mode], canvas = $(mode + '-canvas');
  const action = button.dataset.zoom;
  const value = action === 'fit' ? Math.min((canvas.clientWidth - 24) / state.width, (canvas.clientHeight - 24) / state.height, 1) : action === 'reset' ? 1 : state.scale * (action === 'in' ? 1.2 : 1 / 1.2);
  zoomGraph(mode, value, action === 'fit' || action === 'reset');
});
$('svg-export').onclick = () => download('engineering-flow.svg', $('flow-canvas').innerHTML, 'image/svg+xml');
$('code-svg-export').onclick = () => download('source-dependencies.svg', $('code-canvas').innerHTML, 'image/svg+xml');
$('export').onclick = () => download('eqtrace-architecture.json', pretty(report), 'application/json');
$('import').onchange = async e => {
  try {
    const f = e.target.files[0];
    if (!f || f.size > 10e6) throw Error('Use an architecture JSON file below 10 MB');
    const next = JSON.parse(await f.text());
    if (next.report_kind !== 'architecture' || !Array.isArray(next.nodes)) throw Error('Expected an EqTrace architecture report');
    report = next; codeFocus = null; packageFocus = null; render();
  } catch (err) {$('errors').textContent = err.message;}
};
render();
