"""Static source facts across Python roots, with unresolved calls retained."""
from __future__ import annotations
import ast
import os
from pathlib import Path
from .datasets import file_hash
from .ir import Unsupported

SKIP={'.git','.venv','venv','node_modules','__pycache__','dist','build','.pytest_cache'}


def source_files(root):
    result=[]
    for folder,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d not in SKIP and not (Path(folder)/d).is_symlink())
        for name in sorted(files):
            p=Path(folder)/name
            if p.suffix=='.py':
                if p.is_symlink():raise Unsupported('Source symlinks require an explicit root mapping')
                result.append(p)
                if len(result)>2000:raise Unsupported('MVP source scan is limited to 2000 Python files per root')
    return result


def scan_codebases(roots):
    files,symbols,imports,calls,findings=[],[],[],[],[]
    module_map={};symbol_map={}
    for repo_id,root in roots.items():
        for path in source_files(root):
            rel=path.relative_to(root).as_posix();module=rel[:-3].replace('/','.')
            if module.endswith('.__init__'):module=module[:-9]
            if module=='__init__':module=''
            fid=f'{repo_id}:{rel}'
            try:
                if path.stat().st_size>1000000:raise Unsupported('Python source file exceeds 1 MiB')
                text=path.read_text();tree=ast.parse(text)
            except (ValueError,SyntaxError,UnicodeError,OSError) as exc:
                files.append({'id':fid,'repository':repo_id,'path':rel,'module':module,'status':'UNPARSED','reason':str(exc),'sha256':file_hash(path)})
                continue
            files.append({'id':fid,'repository':repo_id,'path':rel,'module':module,'status':'SCANNED','sha256':file_hash(path),'lines':len(text.splitlines())})
            module_map.setdefault(module,[]).append(fid)
            aliases={}
            package=module if path.name=='__init__.py' else module.rpartition('.')[0]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    for alias in node.names:
                        aliases[alias.asname or alias.name.split('.')[0]]=alias.name if alias.asname else alias.name.split('.')[0]
                        imports.append({'from':fid,'module':alias.name,'line':node.lineno,'evidence':'static'})
                elif isinstance(node,ast.ImportFrom):
                    prefix=node.module or ''
                    if node.level:
                        parts=package.split('.') if package else []
                        prefix='.'.join(parts[:max(0,len(parts)-node.level+1)]+([prefix] if prefix else []))
                    for alias in node.names:aliases[alias.asname or alias.name]=prefix+'.'+alias.name
                    imports.append({'from':fid,'module':prefix,'line':node.lineno,'evidence':'static'})
            class Visitor(ast.NodeVisitor):
                def __init__(self):self.scope=[]
                def define(self,node,kind):
                    qual='.'.join(self.scope+[node.name]);sid=fid+'::'+qual
                    symbol={'id':sid,'file':fid,'name':node.name,'qualified_name':qual,'kind':kind,'line':node.lineno,'end_line':node.end_lineno}
                    symbols.append(symbol);symbol_map.setdefault(module+'.'+qual,[]).append(sid)
                    self.scope.append(node.name);self.generic_visit(node);self.scope.pop()
                def visit_FunctionDef(self,node):self.define(node,'function')
                def visit_AsyncFunctionDef(self,node):self.define(node,'async_function')
                def visit_ClassDef(self,node):self.define(node,'class')
                def visit_Call(self,node):
                    def dotted(n):
                        if isinstance(n,ast.Name):return n.id
                        if isinstance(n,ast.Attribute):
                            base=dotted(n.value);return base+'.'+n.attr if base else None
                        return None
                    name=dotted(node.func)
                    target=None
                    if name:
                        head,*tail=name.split('.')
                        if head in aliases:target='.'.join([aliases[head]]+tail)
                        elif head not in ('self','cls'):target=module+'.'+name
                    calls.append({'from':fid+('::'+'.'.join(self.scope) if self.scope else ''),'file':fid,'name':name or '<dynamic>','candidate':target,'line':node.lineno,'evidence':'static_candidate'})
                    if name in ('eval','exec','getattr','__import__','importlib.import_module'):
                        findings.append({'file':fid,'line':node.lineno,'end_line':node.end_lineno,'kind':'dynamic_dispatch','scope':'Static indication; behavior not established'})
                    self.generic_visit(node)
                def visit_ExceptHandler(self,node):
                    findings.append({'file':fid,'line':node.lineno,'end_line':node.end_lineno,'kind':'exception_handler','scope':'Possible alternate path; not evidence of a fallback'})
                    self.generic_visit(node)
                def visit_Pass(self,node):findings.append({'file':fid,'line':node.lineno,'end_line':node.lineno,'kind':'pass_statement','scope':'Review whether this is an intentional empty body'})
            Visitor().visit(tree)
    for edge in imports:
        edge['targets']=module_map.get(edge['module'],[])
        edge['resolution']='candidate' if edge['targets'] else 'external_or_unresolved'
    for edge in calls:
        edge['targets']=symbol_map.get(edge['candidate'],[])
        edge['resolution']='candidate' if len(edge['targets'])==1 else ('ambiguous' if edge['targets'] else 'unresolved')
    return {'files':files,'symbols':symbols,'imports':imports,'calls':calls,'findings':findings,
            'scope':'Static Python AST scan. Import and call targets are syntactic candidates; dynamic dispatch and alias shadowing are not resolved.'}
