"""Child-process main-thread tracing for explicit user-requested pipeline runs."""
import json
from pathlib import Path
import runpy
import sys
import time
import importlib.metadata


def main():
    config=json.loads(Path(sys.argv[1]).read_text())
    roots={k:Path(v).resolve() for k,v in config['roots'].items()}
    files={str((roots[f['repository']]/f['path']).resolve()):f['id'] for f in config['files']}
    records={};edges={};opens=[]
    artifacts={str(Path(v).resolve()):k for k,v in config.get('artifacts',{}).items()}
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(Path(args[0]).resolve());entity=artifacts.get(path)
            if entity:
                mode=args[1] or '';flags=args[2] or 0
                writing=any(c in mode for c in 'wax+') or bool(flags & 3)
                opens.append({'entity':entity,'write':writing})
    sys.addaudithook(audit)
    def trace(frame,event,arg):
        fid=files.get(frame.f_code.co_filename)
        if not fid:return None
        name=frame.f_code.co_qualname
        if event=='call':
            item=records.setdefault(fid,{'file':fid,'calls':{},'lines':set(),'exceptions':[],'arrays':[]})
            item['calls'][name]=item['calls'].get(name,0)+1
            for key,value in frame.f_locals.items():
                if type(value).__name__=='ndarray' and type(value).__module__=='numpy':
                    fact={'function':name,'argument':key,'shape':list(value.shape),'dtype':str(value.dtype)}
                    if fact not in item['arrays'] and len(item['arrays'])<100:item['arrays'].append(fact)
            caller=frame.f_back
            if caller:
                source=files.get(caller.f_code.co_filename)
                if source:
                    key=(source+'::'+caller.f_code.co_qualname,fid+'::'+name)
                    edges[key]=edges.get(key,0)+1
        elif event=='line':records.setdefault(fid,{'file':fid,'calls':{},'lines':set(),'exceptions':[]})['lines'].add(frame.f_lineno)
        elif event=='exception':
            records[fid]['exceptions'].append({'line':frame.f_lineno,'type':arg[0].__name__})
        elif event=='return' and type(arg).__name__=='ndarray' and type(arg).__module__=='numpy':
            fact={'function':name,'argument':'$return','shape':list(arg.shape),'dtype':str(arg.dtype)}
            if fact not in records[fid]['arrays'] and len(records[fid]['arrays'])<100:records[fid]['arrays'].append(fact)
        return trace
    exit_code=0
    for root in reversed(list(roots.values())):sys.path.insert(0,str(root))
    sys.argv=[config['entrypoint']]+config.get('args',[])
    sys.settrace(trace)
    started=time.perf_counter()
    try:runpy.run_path(config['entrypoint'],run_name='__main__')
    except SystemExit as exc:
        exit_code=exc.code if isinstance(exc.code,int) else (0 if exc.code is None else 1)
        if exit_code:raise
    except BaseException:
        exit_code=1
        raise
    finally:
        sys.settrace(None)
        for item in records.values():item['lines']=sorted(item['lines'])
        versions={}
        for package in ('numpy','torch','scipy'):
            if package in sys.modules:
                try:versions[package]=importlib.metadata.version(package)
                except importlib.metadata.PackageNotFoundError:versions[package]='unknown'
        result={'exit_code':exit_code,'duration_ms':round((time.perf_counter()-started)*1000,3),'files':list(records.values()),'artifact_opens':opens,'external_versions':versions,
                'calls':[{'from':a,'to':b,'count':n,'evidence':'observed'} for (a,b),n in edges.items()],
                'scope':'Observed Python calls and lines in the child main thread only; no GPU, native kernel, child-thread, or subprocess trace'}
        Path(config['trace_out']).write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
