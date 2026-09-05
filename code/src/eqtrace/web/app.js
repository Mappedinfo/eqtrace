'use strict';
let report = JSON.parse(document.getElementById('report-data').textContent);
let selected = 0;
const $ = id => document.getElementById(id);
const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const badge = s => `<span class="badge ${esc(String(s).toLowerCase())}">${esc(s)}</span>`;
const json = x => JSON.stringify(x,null,2);
const current = () => report.contracts[selected];
const notice = (s,cls='') => `<div class="notice ${cls}">${s}</div>`;
function setText(id,s){$(id).textContent=s??'';}
function download(name,text,type){const a=document.createElement('a');const url=URL.createObjectURL(new Blob([text],{type}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function mathml(g){
  if(!g)return '<span>Not translated</span>';
  const nodes=Object.fromEntries(g.nodes.map(n=>[n.id,n]));
  function build(id,depth=0){
    if(depth>80)return '<mtext>…</mtext>';
    const n=nodes[id];if(!n)return '<mtext>?</mtext>';
    const a=n.inputs.map(i=>build(i,depth+1));
    if(n.op==='var')return `<mi>${esc(n.value)}</mi>`;
    if(n.op==='const'){const parts=n.value.split('/');return parts.length===2?`<mfrac><mn>${esc(parts[0])}</mn><mn>${esc(parts[1])}</mn></mfrac>`:`<mn>${esc(n.value)}</mn>`;}
    if(n.op==='div')return `<mfrac>${a[0]}${a[1]}</mfrac>`;
    if(n.op==='pow')return `<msup><mrow><mo>(</mo>${a[0]}<mo>)</mo></mrow><mn>${esc(n.value)}</mn></msup>`;
    if(n.op==='sqrt')return `<msqrt>${a[0]}</msqrt>`;
    if(n.op==='neg')return `<mrow><mo>−</mo><mo>(</mo>${a[0]}<mo>)</mo></mrow>`;
    if(['exp','log'].includes(n.op))return `<mrow><mi mathvariant="normal">${n.op}</mi><mo>(</mo>${a[0]}<mo>)</mo></mrow>`;
    return `<mrow><mo>(</mo>${a[0]}<mo>${{add:'+',sub:'−',mul:'·'}[n.op]||'?'}</mo>${a[1]}<mo>)</mo></mrow>`;
  }
  return `<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">${build(g.root)}</math>`;
}
function mergeGraphs(c){
  const nodes=[],edges=[],lookup=new Map(),edgeSet=new Set(),roots=[];
  for(const [side,g] of [['paper',c.equation_graph],['code',c.code_graph]]){
    if(!g)continue;
    const ids={};
    for(const n of g.nodes){
      let merged=lookup.get(n.fingerprint);
      if(!merged){merged={...n,id:'m'+nodes.length,inputs:n.inputs.map(i=>ids[i]),sides:[],origins:[]};nodes.push(merged);lookup.set(n.fingerprint,merged);}
      merged.sides.push(side);merged.origins.push(...n.origins);ids[n.id]=merged.id;
    }
    for(const e of g.edges){const edge={from:ids[e.from],to:ids[e.to],slot:e.slot};const key=json(edge);if(!edgeSet.has(key)){edges.push(edge);edgeSet.add(key);}}
    roots.push(ids[g.root]);
  }
  return {nodes,edges,roots};
}
let merged=null;
function drawGraph(c){
  merged=mergeGraphs(c);
  const depths={},rows={},pos={};
  for(const n of merged.nodes){const d=Math.max(-1,...n.inputs.map(i=>depths[i]??0))+1;depths[n.id]=d;const row=rows[d]||0;rows[d]=row+1;pos[n.id]=[30+d*156,30+row*82];}
  const width=175+Math.max(0,...Object.values(depths))*156,height=80+Math.max(1,...Object.values(rows))*82;
  const parts=[`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Merged paper and code computation graph"><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#93a092"/></marker></defs>`];
  for(const e of merged.edges){const [x,y]=pos[e.from],[xx,yy]=pos[e.to];parts.push(`<path d="M${x+112},${y+24} C${x+138},${y+24} ${xx-24},${yy+24} ${xx},${yy+24}" fill="none" stroke="#afbbad" stroke-width="1.4" marker-end="url(#a)"/><text x="${xx-13}" y="${yy+18+e.slot*12}" fill="#70816f" font-size="9">${e.slot}</text>`);}
  for(const n of merged.nodes){const [x,y]=pos[n.id],shared=n.sides.length===2;const fill=shared?'#e6efe2':n.sides[0]==='paper'?'#fff1d7':'#f8e4dc';const label=['var','const'].includes(n.op)?n.value:n.op+(n.value?' '+n.value:'');parts.push(`<g class="graph-node" tabindex="0" role="button" data-node="${n.id}" aria-label="${esc(label)}"><title>${esc(n.expression)}</title><rect x="${x}" y="${y}" width="112" height="49" rx="5" fill="${fill}" stroke="#9cab94"/><text x="${x+56}" y="${y+21}" text-anchor="middle" font-family="monospace" font-size="13" fill="#28482f">${esc(label.slice(0,19))}</text><text x="${x+56}" y="${y+37}" text-anchor="middle" font-family="monospace" font-size="8" fill="#6b7b65">${shared?'shared':n.sides[0]} ${merged.roots.includes(n.id)?'· output':''}</text></g>`);}
  parts.push('</svg>');$('graph-canvas').innerHTML=parts.join('');
  function inspect(el){const n=merged.nodes.find(n=>n.id===el.dataset.node);$('node-detail').innerHTML=`<strong>${esc(n.op)} · ${esc(n.sides.join(' + '))}</strong><br><code>${esc(n.expression)}</code><br>Ordered inputs: ${esc(n.inputs.join(', ')||'leaf')}<br>${n.origins.map(o=>`${esc(o.source)}:${o.line}:${o.column}`).join(' · ')}<br><small>Semantic SHA-256 ${esc(n.fingerprint)}</small>`;}
  document.querySelectorAll('.graph-node').forEach(el=>{el.onclick=()=>inspect(el);el.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();inspect(el);}};});
  setText('node-detail','Select a computation node. Green = shared; amber = paper only; terracotta = code only.');
}
function renderSamples(){const rows=current()?.execution?.records||[];const only=$('fail-only').checked;$('samples').innerHTML=rows.map((r,i)=>({...r,i})).filter(r=>!only||r.status!=='PASS').map(r=>`<tr class="${r.status==='PASS'?'':'failure'}"><td>${r.i+1}</td><td>${esc(JSON.stringify(r.inputs))}</td><td>${esc(r.expected??r.reason??'—')}</td><td>${esc(r.actual??'—')}</td><td>${esc(r.normalized_squared_error??'—')}</td><td>${badge(r.status)}</td></tr>`).join('')||'<tr><td colspan="6">No samples in this view.</td></tr>';}
function renderNav(){const query=$('search').value.toLowerCase();$('contracts').innerHTML=report.contracts.map((c,i)=>({...c,i})).filter(c=>(c.id+' '+c.label).toLowerCase().includes(query)).map(c=>`<button data-index="${c.i}" class="${c.i===selected?'active':''}"><strong>${esc(c.id)}</strong><small>${esc(c.label)} · ${esc(c.status)}</small></button>`).join('');document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{selected=Number(b.dataset.index);render();});}
function render(){
  renderNav();setText('project-title',report.title);setText('scope',report.scope);$('overall').outerHTML=`<span id="overall" class="badge ${esc(report.status.toLowerCase())}">${esc(report.status)}</span>`;setText('version',report.version);
  $('global-errors').innerHTML=(report.errors||[]).map(e=>notice(esc(e),'bad')).join('');
  setText('selection',`${report.contracts.length} selected contracts · ${report.coverage?.labeled_equations??'—'} labeled displays · ${report.duration_ms} ms · ${report.created_at}`);
  const c=current();if(!c){setText('contract-title','No valid contracts');return;}
  setText('contract-title',c.id);setText('description',c.description||c.label);$('contract-status').outerHTML=`<span id="contract-status" class="badge ${esc(c.status.toLowerCase())}">${esc(c.status)}</span>`;
  const checks=[['ORDERED STRUCTURE',c.structural?.status||'NOT_TRANSLATED',`${c.structural?.differences?.length??0} local differences · ${c.policy} merge policy`],['REAL EQUIVALENCE',c.proof.status,c.proof.backend?`${c.proof.backend} ${c.proof.version} · explicit domain`:(c.proof.reason||'No proof executed')],['CURRENT SOURCE EXECUTION',c.execution.status,`${c.execution.passed??0} / ${c.execution.requested??0} samples passed · ${c.execution.executed??0} executed`]];
  $('checks').innerHTML=checks.map(([label,value,detail])=>`<div class="check"><div class="check-label">${label}</div><strong>${esc(value)}</strong><small>${esc(detail)}</small></div>`).join('');
  setText('paper-location',`${c.equation_source||'—'}:${c.equation_line||'—'}`);setText('code-location',`${c.implementation}:${c.code_line||'—'}`);
  $('paper-math').innerHTML=mathml(c.equation_graph);$('code-math').innerHTML=mathml(c.code_graph);setText('paper-source',c.equation_text);setText('code-source',c.code_source||c.errors?.join('\n'));setText('generated-code',c.generated_python);setText('pseudocode',c.code_pseudocode);
  let messages=(c.errors||[]).map(e=>notice(esc(e),'bad'));
  const ds=c.structural?.differences||[];
  if(ds.length)messages.push(notice(`<strong>${ds.length} structure difference${ds.length===1?'':'s'}</strong> · ${c.proof.status==='PROVED_REAL'?'The real expressions are equivalent within the contract. Review operation order separately.':'Inspect the changed expressions and solver evidence.'}<br>`+ds.map(d=>`<code>${esc(d.path)}</code>: <code>${esc(d.equation)}</code> → <code>${esc(d.code)}</code> (code line ${d.code_line})`).join('<br>')));
  else if(c.structural)messages.push(notice('The ordered expressions match. Source execution and real-domain proof are checked separately.','good'));
  if(c.proof.status==='COUNTEREXAMPLE'||c.proof.status==='DOMAIN_ERROR')messages.push(notice(`${esc(c.proof.reason)}. Witness: <code>${esc(JSON.stringify(c.proof.witness))}</code>`,'bad'));
  $('differences').innerHTML=messages.join('');
  $('edit-paper').value=c.equation_text||'';$('edit-code').value=c.code_source||'';
  $('proof-summary').innerHTML=notice(`${badge(c.proof.status)} &nbsp; ${esc(c.proof.reason||'Proof was not requested')}<br><small>${esc(c.proof.scope||'')}. ${esc(c.execution.reference_semantics||'')}.</small>`);
  $('witness').innerHTML=c.proof.witness?notice(`<strong>Solver witness</strong><pre>${esc(json(c.proof.witness))}</pre>`,'bad'):'';
  setText('smt',(c.proof.queries||[]).map(q=>`; ${q.name}: ${q.result}\n${q.smt2}`).join('\n'));
  renderSamples();drawGraph(c);
  setText('trust','A receipt binds source content, checker code, settings, and execution records. Freshness is checked with eqtrace verify. Hashes detect accidental changes; they are not signatures or a proof of the checker.');
  setText('provenance-data',json({manifest:report.manifest,sources:report.sources,checker:report.checker,environment:report.environment,domain:c.domains,nonzero:c.nonzero,execution_scope:c.execution.execution_scope,integrity:report.integrity}));
}
$('search').oninput=renderNav;$('fail-only').onchange=renderSamples;
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('.tab-panel').forEach(x=>x.hidden=x.id!==b.dataset.tab);});
$('download').onclick=()=>download('eqtrace-report.json',json(report),'application/json');
$('export-svg').onclick=()=>download(current().id+'-merged.svg',$('graph-canvas').innerHTML,'image/svg+xml');
$('import').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>5e6)throw Error('Receipt exceeds 5 MB');const next=JSON.parse(await f.text());if(next.schema_version!==1||!Array.isArray(next.contracts)||next.contracts.length>100)throw Error('Unsupported receipt');report=next;selected=0;render();}catch(err){$('global-errors').innerHTML=notice(esc(err.message),'bad');}};
$('run').onclick=async()=>{setText('run-message','Checking current edits…');$('run').disabled=true;try{if(location.protocol==='file:')throw Error('Start eqtrace serve to run live edits.');const c=current();const response=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latex:$('edit-paper').value,code:$('edit-code').value,contract:{id:c.id,label:c.label,function:c.function,inputs:c.inputs,domains:c.domains,nonzero:c.nonzero,policy:c.policy},kind:c.source_kind})});const data=await response.json();if(!response.ok)throw Error(data.error||'Check failed');report=data;selected=0;render();setText('run-message','Checked. Temporary edits; project files unchanged.');}catch(err){setText('run-message',err.message);}finally{$('run').disabled=false;}};
render();
