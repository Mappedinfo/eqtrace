"""Hierarchical engineering contracts: codebases, datasets, blocks, and run traces."""
from __future__ import annotations
from datetime import datetime,timezone
import fnmatch
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import importlib.metadata

from .codegraph import scan_codebases
from .datasets import scan_dataset,dataset_latex,file_hash
from .ir import Unsupported
from .project import canonical,digest,checker_hashes,check_project,local_path


def load_architecture(manifest):
    manifest=Path(manifest).resolve();root=manifest.parent
    config=tomllib.loads(manifest.read_text())
    if config.get('schema_version')!=1:raise Unsupported('architecture schema_version must be 1')
    extra=set(config)-{'schema_version','title','repositories','datasets','entities','blocks','flows','runs','equation_manifests'}
    if extra:raise Unsupported(f'Unknown architecture fields: {sorted(extra)}')
    ids=set()
    for collection in ('repositories','datasets','entities','blocks','flows','runs'):
        rows=config.get(collection,[])
        if not isinstance(rows,list) or len(rows)>200:raise Unsupported(f'{collection} must be a list of at most 200 entries')
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',row['id']):raise Unsupported('All semantic entities need stable simple IDs')
            if row['id'] in ids:raise Unsupported('Semantic IDs must be unique across entity kinds')
            ids.add(row['id'])
    if not config.get('repositories') or not config.get('blocks'):raise Unsupported('At least one source root and semantic block are required')
    roots={}
    for repo in config['repositories']:
        if set(repo)-{'id','path','description'}:raise Unsupported('Unknown repository fields')
        if not isinstance(repo.get('path'),str) or not repo['path']:raise Unsupported('Repository path must be explicit')
        path=(root/repo['path']).resolve()
        if not path.is_dir():raise Unsupported(f"Missing codebase: {repo['id']}")
        roots[repo['id']]=path
    for block in config['blocks']:
        if set(block)-{'id','label','meaning','members','inputs','outputs','parent','equations'}:raise Unsupported('Unknown block fields')
        if not isinstance(block.get('meaning'),str) or not block['meaning'].strip():raise Unsupported('Blocks require an explicit declared meaning')
        if not isinstance(block.get('members'),list) or not block['members']:raise Unsupported('Blocks require file membership selectors')
        for member in block['members']:
            if set(member)!={'repository','pattern'} or member['repository'] not in roots or not isinstance(member['pattern'],str):raise Unsupported('Invalid block member selector')
        for side in ('inputs','outputs'):
            if not isinstance(block.get(side,[]),list) or not all(isinstance(x,str) for x in block.get(side,[])):raise Unsupported('Block ports must name semantic entities')
    for d in config.get('datasets',[]):
        if set(d)-{'id','path','description','max_rows','required_columns','allow_nulls'}:raise Unsupported('Unknown dataset fields')
        local_path(root,d.get('path'))
    for e in config.get('entities',[]):
        if set(e)-{'id','label','meaning','type','shape','path','shape_axes','observed_at','dtype'}:raise Unsupported('Unknown entity fields')
        if not e.get('type') or not e.get('meaning'):raise Unsupported('Virtual entities require declared type and meaning')
        if 'path' in e:local_path(root,e['path'])
        if 'shape_axes' in e:
            if not isinstance(e['shape_axes'],list) or not all((type(v) is int and v>=0) or (isinstance(v,str) and v.isidentifier()) for v in e['shape_axes']):raise Unsupported('shape_axes must contain dimensions or symbolic axes')
            if not isinstance(e.get('observed_at'),dict) or set(e['observed_at'])!={'file','function','argument'}:raise Unsupported('Shape contracts need an explicit observation binding')
    for run in config.get('runs',[]):
        if set(run)-{'id','repository','entrypoint','args','blocks','inputs','outputs','receipt','timeout_seconds'}:raise Unsupported('Unknown run fields')
        if run.get('repository') not in roots:raise Unsupported('Run repository not found')
        local_path(roots[run['repository']],run.get('entrypoint'))
        local_path(root,run.get('receipt'))
        if not all(isinstance(x,str) for x in run.get('args',[])):raise Unsupported('Run arguments must be strings')
        timeout=run.get('timeout_seconds',120)
        if type(timeout) is not int or not 1<=timeout<=600:raise Unsupported('Run timeout must be 1..600 seconds')
    return root,config,roots


def scan_architecture(manifest,require_runs=False):
    manifest=Path(manifest).resolve()
    report={'schema_version':1,'report_kind':'architecture','title':'Engineering contract graph','created_at':datetime.now(timezone.utc).isoformat(),
            'status':'BLOCKED','errors':[],'warnings':[],'nodes':[],'edges':[],'datasets':[],'blocks':[],'runs':[],
            'manifest':manifest.name,'manifest_sha256':file_hash(manifest),'checker':checker_hashes(),
            'scope':'Block meaning and interfaces are declarations. Source and dataset scans are observations. Only bound scalar equation contracts carry real-equivalence evidence.'}
    try:
        root,config,roots=load_architecture(manifest);report['title']=config.get('title',report['title'])
        code=scan_codebases(roots);report['code']=code
        for f in code['files']:
            if f['status']!='SCANNED':report['errors'].append(f"Unparsed file {f['id']}: {f['reason']}")
        report['source_hashes']={f['id']:f['sha256'] for f in code['files']}
        for d in config.get('datasets',[]):
            data=scan_dataset(local_path(root,d['path']),d['id'],d.get('max_rows',100000))
            data.update({'path':d['path'],'description':d.get('description',''),'latex':dataset_latex(data)})
            columns={c['name']:c for c in data['columns']}
            for name in d.get('required_columns',[]):
                if name not in columns:report['errors'].append(f"Dataset {d['id']} lacks column {name}")
            if d.get('allow_nulls',True) is False and any(c['nulls'] for c in data['columns']):report['errors'].append(f"Dataset {d['id']} has null values")
            if data['status']!='SCANNED':report['errors'].append(f"Dataset {d['id']} is {data['status']}; complete nonempty scan required")
            report['datasets'].append(data)
            report['nodes'].append({'id':d['id'],'kind':'dataset','label':d['id'],'evidence':'observed','status':data['status'],'detail':data})
        for e in config.get('entities',[]):
            detail=dict(e)
            if e.get('path'):
                p=local_path(root,e['path']);detail['artifact_status']='PRESENT' if p.is_file() else 'MISSING'
                if p.is_file():detail['sha256']=file_hash(p);detail['bytes']=p.stat().st_size
            report['nodes'].append({'id':e['id'],'kind':'entity','label':e.get('label',e['id']),'evidence':'declared','status':'DECLARED','detail':detail})
        entities={n['id'] for n in report['nodes']}
        block_ids={b['id'] for b in config['blocks']}
        for block in config['blocks']:
            members=[]
            for selector in block['members']:
                matched=[f['id'] for f in code['files'] if f['repository']==selector['repository'] and fnmatch.fnmatchcase(f['path'],selector['pattern'])]
                if not matched:report['errors'].append(f"Empty membership selector in {block['id']}: {selector}")
                members.extend(matched)
            members=sorted(set(members))
            parent=block.get('parent')
            if parent and (parent not in block_ids or parent==block['id']):report['errors'].append(f"Invalid block parent: {block['id']}")
            for side in ('inputs','outputs'):
                for entity in block.get(side,[]):
                    if entity not in entities:report['errors'].append(f"Dangling {side} entity {entity} in {block['id']}")
                    report['edges'].append({'from':entity if side=='inputs' else block['id'],'to':block['id'] if side=='inputs' else entity,'kind':'consumes' if side=='inputs' else 'produces','evidence':'declared'})
            item=dict(block,members=members,evidence='declared',execution='NOT_EXECUTED',findings=[f for f in code['findings'] if f['file'] in members])
            report['blocks'].append(item)
            report['nodes'].append({'id':block['id'],'kind':'block','label':block.get('label',block['id']),'evidence':'declared','status':'NOT_EXECUTED','detail':item})
        parents={b['id']:b.get('parent') for b in config['blocks']}
        for bid in parents:
            path=set();node=bid
            while node:
                if node in path:report['errors'].append(f'Block hierarchy cycle at {bid}');break
                path.add(node);node=parents.get(node)
        known={n['id'] for n in report['nodes']}
        flows=[]
        for flow in config.get('flows',[]):
            if set(flow)-{'id','label','nodes','edges'}:raise Unsupported('Unknown flow fields')
            selected=flow.get('nodes',list(known))
            if not all(n in known for n in selected):report['errors'].append(f"Unknown flow node in {flow['id']}")
            edges=[]
            for edge in flow.get('edges',[]):
                if not isinstance(edge,list) or len(edge)!=2 or not all(n in selected for n in edge):raise Unsupported('Flow edges need two selected entity IDs')
                edges.append({'from':edge[0],'to':edge[1],'kind':'sequence','evidence':'declared'})
            flows.append(dict(flow,edges=edges))
        report['flows']=flows
        report['equations']=[]
        equation_map={}
        for path in config.get('equation_manifests',[]):
            eq=check_project(local_path(root,path));report['equations'].append({'manifest':path,'report':eq})
            if eq['status']!='PASS':report['errors'].append(f'Scalar equation checks did not pass: {path}')
            for contract in eq['contracts']:equation_map[path+'#'+contract['id']]=(contract,path)
        for block in report['blocks']:
            block['equation_evidence']=[]
            for key in block.get('equations',[]):
                if key not in equation_map:report['errors'].append(f'Unknown equation binding in block: {key}');continue
                c,eq_path=equation_map[key]
                implementation=local_path(local_path(root,eq_path).parent,c['implementation'])
                candidates=[f"{repo}:{implementation.relative_to(repo_root).as_posix()}" for repo,repo_root in roots.items() if implementation.is_relative_to(repo_root)]
                if not set(candidates)&set(block['members']):report['errors'].append(f'Equation implementation is outside bound block: {key}')
                block['equation_evidence'].append({'binding':key,'status':c['status'],'proof':c['proof']['status'],'executed_samples':c['execution']['executed']})
        dataset_map={d['id']:d for d in report['datasets']}
        node_map={n['id']:n for n in report['nodes']}
        for run in config.get('runs',[]):
            receipt_path=local_path(root,run['receipt'])
            state={'id':run['id'],'status':'NOT_EXECUTED','blocks':run.get('blocks',[]),'receipt':run['receipt'],'errors':[]}
            for b in run.get('blocks',[]):
                if b not in block_ids:state['errors'].append(f'Unknown run block {b}')
            if receipt_path.is_file():
                receipt=json.loads(receipt_path.read_text());integrity=receipt.pop('integrity',None)
                if integrity!=digest(canonical(receipt)):state['errors'].append('Run receipt digest mismatch')
                if receipt.get('manifest_sha256')!=report['manifest_sha256']:state['errors'].append('Architecture manifest changed')
                if receipt.get('source_hashes')!=report['source_hashes']:state['errors'].append('Source files changed')
                if receipt.get('checker')!=report['checker']:state['errors'].append('Checker changed')
                if receipt.get('exit_code')!=0:state['errors'].append('Run failed')
                if receipt.get('run_id')!=run['id'] or receipt.get('entrypoint')!=run['repository']+':'+run['entrypoint'] or receipt.get('args')!=run.get('args',[]):state['errors'].append('Receipt is for a different command')
                if receipt.get('python')!=sys.version.split()[0]:state['errors'].append('Python runtime changed')
                for package,version in receipt.get('trace',{}).get('external_versions',{}).items():
                    try:actual=importlib.metadata.version(package)
                    except importlib.metadata.PackageNotFoundError:actual=None
                    if actual!=version:state['errors'].append(f'Observed dependency version changed: {package}')
                written={o['entity'] for o in receipt.get('trace',{}).get('artifact_opens',[]) if o['write']}
                if not set(run.get('outputs',[]))<=written:state['errors'].append('Declared outputs were not written during this run')
                for entity,expected in receipt.get('artifact_hashes',{}).items():
                    detail=node_map.get(entity,{}).get('detail',{});path=detail.get('path')
                    if not path or not local_path(root,path).is_file() or file_hash(local_path(root,path))!=expected:state['errors'].append(f'Artifact changed or missing: {entity}')
                for entity,expected in receipt.get('dataset_hashes',{}).items():
                    if dataset_map.get(entity,{}).get('sha256')!=expected:state['errors'].append(f'Dataset changed or missing: {entity}')
                state['trace']=receipt.get('trace',{});state['status']='STALE_OR_FAILED' if state['errors'] else 'EXECUTED'
            if require_runs and state['status']!='EXECUTED':report['errors'].append(f"Run {run['id']} is {state['status']}: {state['errors']}")
            report['runs'].append(state)
        for block in report['blocks']:
            observed=set()
            function_names={f['id']:{s['qualified_name'] for s in code['symbols'] if s['file']==f['id'] and s['kind'] in ('function','async_function')} for f in code['files']}
            for run in report['runs']:
                if run['status']=='EXECUTED':observed.update(f['file'] for f in run.get('trace',{}).get('files',[]) if set(f['calls'])&function_names.get(f['file'],set()))
            block['executed_members']=sorted(set(block['members'])&observed)
            block['execution']='CALLS_OBSERVED' if block['executed_members'] else 'NOT_EXECUTED'
            node_map[block['id']]['status']=block['execution']
        if require_runs:
            expected_blocks={b for run in config.get('runs',[]) for b in run.get('blocks',[])}
            for block in report['blocks']:
                if block['id'] in expected_blocks and block['execution']=='NOT_EXECUTED':report['errors'].append(f"No function execution observed for block {block['id']}")
        if require_runs and not config.get('runs'):report['errors'].append('No declared runs to verify')
        report['shape_checks']=[]
        for entity in config.get('entities',[]):
            if 'shape_axes' not in entity:continue
            binding=entity['observed_at'];observations=[]
            for run in report['runs']:
                if run['status']!='EXECUTED':continue
                for file in run.get('trace',{}).get('files',[]):
                    if file['file']==binding['file']:observations.extend(a for a in file.get('arrays',[]) if a['function']==binding['function'] and a['argument']==binding['argument'])
            errors=[]
            for observed in observations:
                wanted=entity['shape_axes'];got=observed['shape'];symbols={}
                if len(wanted)!=len(got):errors.append(f'Rank mismatch: expected {wanted}, observed {got}');continue
                for expected,actual in zip(wanted,got):
                    if isinstance(expected,int) and expected!=actual:errors.append(f'Shape mismatch: expected {wanted}, observed {got}')
                    if isinstance(expected,str):
                        if expected in symbols and symbols[expected]!=actual:errors.append(f'Repeated symbolic axis mismatch: {expected}')
                        symbols[expected]=actual
                if entity.get('dtype') and observed['dtype']!=entity['dtype']:errors.append(f"dtype mismatch: {observed['dtype']}")
            state='MISMATCH' if errors else ('OBSERVED_MATCH' if observations else 'NOT_OBSERVED')
            result={'entity':entity['id'],'status':state,'expected':entity['shape_axes'],'binding':binding,'observations':observations,'errors':errors}
            report['shape_checks'].append(result);node_map[entity['id']]['detail']['shape_check']=result
            if errors or (require_runs and not observations):report['errors'].append(f"Shape contract {entity['id']}: {state}")
        report['status']='BLOCKED' if report['errors'] else ('CHECKED_WITH_RUNS' if require_runs else 'SCANNED')
        report['summary']={'codebases':len(roots),'files':len(code['files']),'symbols':len(code['symbols']),'static_calls':len(code['calls']),'unresolved_calls':sum(c['resolution']!='candidate' for c in code['calls']),
                           'datasets':len(report['datasets']),'blocks':len(report['blocks']),'executed_runs':sum(r['status']=='EXECUTED' for r in report['runs']),
                           'scalar_contracts':sum(len(e['report']['contracts']) for e in report['equations'])}
    except (Unsupported,OSError,ValueError,TypeError,KeyError,RecursionError) as exc:report['errors'].append(f'{type(exc).__name__}: {exc}')
    return report


def trace_run(manifest,run_id):
    root,config,roots=load_architecture(manifest)
    runs=[r for r in config.get('runs',[]) if r['id']==run_id]
    if len(runs)!=1:raise Unsupported(f'Unknown run ID {run_id}')
    run=runs[0];snapshot=scan_architecture(manifest)
    if snapshot['errors']:raise Unsupported('Resolve architecture scan errors before execution: '+'; '.join(snapshot['errors']))
    node_map={n['id']:n for n in snapshot['nodes']}
    paths={}
    for entity in run.get('inputs',[])+run.get('outputs',[]):
        if entity not in node_map or not node_map[entity]['detail'].get('path'):raise Unsupported('Runs require materialized input/output entities')
        paths[entity]=local_path(root,node_map[entity]['detail']['path'])
    for entity in run.get('inputs',[]):
        if not paths[entity].is_file():raise Unsupported(f'Missing run input: {entity}')
    entry=local_path(roots[run['repository']],run['entrypoint'])
    if not entry.is_file():raise Unsupported('Run entrypoint is missing')
    destination=local_path(root,run['receipt']);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eqtrace-trace-') as tmp:
        tmp=Path(tmp);tracefile=tmp/'trace.json'
        child={'roots':{k:str(v) for k,v in roots.items()},'files':snapshot['code']['files'],'entrypoint':str(entry),'args':run.get('args',[]),'trace_out':str(tracefile),'artifacts':{e:str(p) for e,p in paths.items()}}
        job=tmp/'job.json';job.write_text(json.dumps(child))
        try:
            process=subprocess.run([sys.executable,str(Path(__file__).with_name('instrument.py')),str(job)],cwd=root,capture_output=True,text=True,timeout=run.get('timeout_seconds',120))
            exit_code=process.returncode;stdout=process.stdout;stderr=process.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code=124;stdout=exc.stdout.decode() if isinstance(exc.stdout,bytes) else exc.stdout or '';stderr='Run timed out; no successful execution receipt'
        trace=json.loads(tracefile.read_text()) if tracefile.is_file() else {'files':[],'calls':[],'scope':'Worker produced no trace'}
    errors=[]
    for entity in run.get('outputs',[]):
        if not paths[entity].is_file():errors.append(f'Missing declared output: {entity}')
        elif entity not in {o['entity'] for o in trace.get('artifact_opens',[]) if o['write']}:errors.append(f'Output existed but was not written: {entity}')
    after=scan_codebases(roots)
    if {f['id']:f['sha256'] for f in after['files']}!=snapshot['source_hashes']:errors.append('Source files changed during execution')
    dataset_hashes={d['id']:d['sha256'] for d in snapshot['datasets']}
    for d in snapshot['datasets']:
        if file_hash(local_path(root,d['path']))!=d['sha256']:errors.append(f"Dataset changed during execution: {d['id']}")
    receipt={'schema_version':1,'run_id':run_id,'created_at':datetime.now(timezone.utc).isoformat(),'manifest_sha256':snapshot['manifest_sha256'],
             'source_hashes':snapshot['source_hashes'],'checker':snapshot['checker'],'dataset_hashes':dataset_hashes,
             'artifact_hashes':{e:file_hash(p) for e,p in paths.items() if p.is_file()},'exit_code':exit_code if not errors else 1,'errors':errors,'trace':trace,
             'entrypoint':run['repository']+':'+run['entrypoint'],'args':run.get('args',[]),'python':sys.version.split()[0],
             'scope':'Explicit pipeline command executed in a child process. No sandbox guarantee. Trace coverage is restricted to selected Python source roots and the main thread.'}
    receipt['integrity']=digest(canonical(receipt));destination.write_text(json.dumps(receipt,indent=2)+'\n')
    destination.with_suffix('.stdout.log').write_text(stdout);destination.with_suffix('.stderr.log').write_text(stderr)
    return receipt


def write_architecture(report,out):
    from .architecture_render import render_architecture
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for data in report['datasets']:(out/(data['id']+'.tex')).write_text(data['latex'])
    (out/'architecture.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    (out/'index.html').write_text(render_architecture(report))
    lines=['flowchart LR']
    for n in report['nodes']:lines.append('  '+n['id']+'["'+n['label'].replace('"','&quot;')+'"]')
    for e in report['edges']:lines.append(f"  {e['from']} -->|{e['kind']}| {e['to']}")
    (out/'architecture.mmd').write_text('\n'.join(lines)+'\n')
