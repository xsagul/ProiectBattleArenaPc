"""Bounded compiler-oracle experiment; never publishes reconstruction claims.

Known proposal rules are ranked from persisted failures/successes. This is not
an autonomous decompiler: semantic seeds and layout hypotheses are explicit.
"""
import argparse
import difflib
import hashlib
import json
import pathlib
import re
import sqlite3
import sys
import time

BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M


def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else value.encode()).hexdigest()


def production_state():
    sources=sorted(str(pathlib.Path(p).resolve()) for p in M.sources())
    paths={pathlib.Path(p) for p in sources}
    paths.update((ROOT/'client-src/src').rglob('*.h'))
    paths.update((ROOT/'tools').glob('*.py'))
    paths.update((ROOT/'tools').glob('*layouts.json'))
    paths.update((ROOT/'client-src').glob('*.tsv'))
    paths.update(ROOT/'client-src'/name for name in ('functions.txt','exe_image_unpacked.bin'))
    return dict(sources=sources,files={str(p.resolve()):digest(p.read_bytes()) for p in sorted(paths)})


def matching_brace(source,opening):
    """Skip comments and quoted literals while locating a C++ body boundary."""
    depth=0;mode=None;i=opening
    while i<len(source):
        char=source[i];pair=source[i:i+2]
        if mode=='line':
            if char=='\n':mode=None
        elif mode=='block':
            if pair=='*/':mode=None;i+=1
        elif mode in ('"',"'"):
            if char=='\\':i+=1
            elif char==mode:mode=None
        elif pair=='//':mode='line';i+=1
        elif pair=='/*':mode='block';i+=1
        elif char in ('"',"'"):mode=char
        elif char=='{':depth+=1
        elif char=='}':
            depth-=1
            if depth==0:return i
        i+=1
    raise ValueError('Unclosed C++ body')


def validate_case(path):
    case=json.loads(path.read_text(encoding='utf-8'))
    case['rva']=int(str(case['rva']),0)
    case['expected_targets']={name:int(str(rva),0) for name,rva in case['expected_targets'].items()}
    case['source_path']=(path.parent/case['source']).resolve()
    source=case['source_path'].read_text(encoding='utf-8')
    if case.get('source_sha256') and digest(case['source_path'].read_bytes())!=case['source_sha256']:
        raise ValueError('Independent seed fingerprint changed')
    if re.search(r'\b(?:__asm|_emit)\b|\basm\s*\(',source):raise ValueError('Assembly is outside this experiment')
    case['seed']=source
    claimed=case['rva'] in M.rebuilt_symbols()
    case['coverage_at_start']='claimed' if claimed else 'uncovered'
    if case.get('requires_uncovered') and claimed:raise ValueError('Case is already claimed by production')
    if case.get('kind','function')=='function':
        fn=case['function'];signature=fn['signature']
        if source.count(signature)!=1:raise ValueError('Function signature must identify exactly one definition')
        start=source.index(signature)+len(signature)
        opening=source.index('{',start);closing=matching_brace(source,opening)
        case['body_span']=(opening,closing)
        if any(parameter.get('capture') not in ('value','reference') for parameter in fn.get('parameters',[])):
            raise ValueError('Each parameter needs a capture constraint')
    elif case['kind']=='layout':
        if len(case['axes'])!=1:raise ValueError('Initial layout prototype supports one bounded integer axis')
        axis=case['axes'][0]
        if not source.count(axis['token']):raise ValueError('Layout token missing')
        if len(axis['values'])>8 or any(type(value) is not int or value<1 or value>16 for value in axis['values']):
            raise ValueError('Layout domain exceeds this prototype')
    else:raise ValueError('Unsupported case kind')
    return case


def proposals(case):
    source=case['seed']
    if case.get('kind')=='layout':
        axis=case['axes'][0]
        return [dict(name=f'{axis["name"]}={value}',family='layout_extent',
            source=source.replace(axis['token'],str(value)),assumptions=['Bounded layout hypothesis; full native body and targets must match.'])
            for value in axis['values']]
    opening,closing=case['body_span'];body=source[opening+1:closing];fn=case['function']
    params=fn.get('parameters',[])
    rows=[dict(name='baseline',family='baseline',source=source,assumptions=['Provided semantic seed.'])]
    if not fn.get('member'):return rows
    def wrap(name,capture,code):
        suffix='\n    experiment_init();\n' if fn.get('constructor') else '\n    return experiment_init();\n'
        return_type='' if fn.get('constructor') else ' -> '+fn['return_type']
        replacement='\n    auto experiment_init = ['+capture+']() mutable'+return_type+' {'+code+'\n    };'+suffix
        return dict(name=name,family='lambda_capture',source=source[:opening+1]+replacement+source[closing:],
            assumptions=['Captures copy only pointer/value parameters or preserve reference parameters.','Original operations remain in their original order.'])
    capture=['this']+[('&' if p['capture']=='reference' else '')+p['name'] for p in params]
    rows.append(wrap('lambda_value',', '.join(capture),body))
    rows.append(wrap('lambda_reference',', '.join(['this']+['&'+p['name'] for p in params]),body))
    fields=fn.get('member_fields',[])
    if fields:
        rewritten=body.replace('this->','experiment_self->')
        for field in fields:
            rewritten=re.sub(r'(?<![.\w:>])\b'+re.escape(field)+r'\b','experiment_self->'+field,rewritten)
        capture=['experiment_self=this']+[('&' if p['capture']=='reference' else '')+p['name'] for p in params]
        rows.append(wrap('lambda_self_value',', '.join(capture),rewritten))
    # One deliberately narrow AST rule; it applies to expressions, not RVAs/names.
    expression=re.fullmatch(r'\s*return double\((\w+\(\))\s*-\s*(\*\w+)\)\s*\*\s*(\w+)\s*;\s*',body)
    if expression:
        lhs,rhs,factor=expression.groups()
        replacements=[('hoist_counter',f'\n const auto experiment_counter={lhs};\n return double(experiment_counter - {rhs}) * {factor};\n'),
            ('hoist_operands',f'\n const auto experiment_counter={lhs};\n const auto experiment_origin={rhs};\n return double(experiment_counter-experiment_origin) * {factor};\n')]
        for name,replacement in replacements:
            rows.append(dict(name=name,family='expression_temporaries',source=source[:opening+1]+replacement+source[closing:],
                assumptions=['Counter evaluates before the origin load, as required by the case ABI constraints.']))
    # Do not spend trials on textual proposals that are literally identical.
    seen=set();unique=[]
    for row in rows:
        fingerprint=digest(row['source'])
        if fingerprint not in seen:seen.add(fingerprint);unique.append(row)
    return unique


def classify(ours,theirs,result,targets_ok):
    if not targets_ok and (result[3] is None or result[4].startswith('same bytes, different targets:')):return 'relocation_targets'
    if result[3] is None and len(ours)!=len(theirs):return 'extent_mismatch'
    if result[3] is None:return 'exact'
    from capstone import Cs,CS_ARCH_X86,CS_MODE_32
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    left=list(md.disasm(ours,0));right=list(md.disasm(theirs,0))
    a=[i.mnemonic for i in left];b=[i.mnemonic for i in right]
    similarity=difflib.SequenceMatcher(a=a,b=b,autojunk=False).ratio()
    if len(ours)==len(theirs) and similarity>=0.8:return 'register_or_operand_schedule'
    if abs(len(ours)-len(theirs))<=4 and similarity>=0.8:return 'return_or_small_shape'
    if abs(len(ours)-len(theirs))>16:return 'layout_or_large_shape'
    return 'control_flow_or_shape'


class History:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS trials (key TEXT PRIMARY KEY, case_id TEXT, learning_use TEXT, feature TEXT, family TEXT, variant TEXT, exact INTEGER, quality REAL, result TEXT)')
        self.db.commit()

    def cached(self,key):
        row=self.db.execute('SELECT result FROM trials WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def store(self,key,case,proposal,feature,result):
        self.db.execute('INSERT OR REPLACE INTO trials VALUES (?,?,?,?,?,?,?,?,?)',
            (key,case['id'],case.get('learning_use','training'),feature,proposal['family'],proposal['name'],int(result['exact']),result['quality'],json.dumps(result)))
        self.db.commit()

    def rank(self,feature,proposal):
        # Beta-smoothed success probability plus measured partial improvement.
        rows=self.db.execute("SELECT exact,quality FROM trials WHERE feature=? AND variant=? AND learning_use='training'",
            (feature,proposal['name'])).fetchall()
        if not rows:return 0.5
        return (1+sum(row[0] for row in rows))/(2+len(rows)) + 0.1*sum(row[1] for row in rows)/len(rows)


def evaluate(case,proposal,directory):
    source=directory/(digest(proposal['source'])[:20]+'.cpp')
    source.write_text(proposal['source'],encoding='utf-8',newline='\n')
    before=time.perf_counter();old_out=M.OUT
    try:
        M.OUT=str(directory/'objects');obj=M.compile_obj(str(source),case.get('flags',M.FLAGS))
        result=M.compare(str(source),case['symbol'],case['rva'],case.get('flags',M.FLAGS),obj)
        _,code,_=M.function_of(obj,case['symbol']);code=code[:result[1]]
        addresses=M.symbol_addresses(case['rva'],code)
        actual=dict(addresses)
        targets_ok=actual==case['expected_targets'] and all(case['expected_targets'].get(name)==rva for name,rva in addresses)
        import packet_emu as P
        reference=bytes(P.IMG[case['rva']:case['rva']+case['expected_size']])
        exact=result[3] is None and targets_ok and result[1]==case['expected_size']
        return dict(exact=exact,bytes=result[1],identical_bytes=result[2],first_difference=result[3],targets=addresses,
            targets_ok=targets_ok,failure_class=classify(code,reference,result,targets_ok),detail=result[4],
            quality=result[2]/max(case['expected_size'],result[1]),elapsed_ms=round((time.perf_counter()-before)*1000),
            source=str(source),code_fingerprint=digest(code+json.dumps(addresses).encode()))
    except SystemExit as error:
        return dict(exact=False,quality=0,failure_class='compile_error',detail=str(error),elapsed_ms=round((time.perf_counter()-before)*1000),source=str(source))
    finally:M.OUT=old_out


def run(case_path,run_dir,history,max_trials=8):
    if not run_dir.resolve().is_relative_to(BASE):raise ValueError('Experiment artifacts must stay in the experimental directory')
    case=validate_case(case_path);run_dir.mkdir(parents=True,exist_ok=True)
    protected=production_state();binding_state=json.dumps(M.rebuilt_symbols(),sort_keys=True)
    env=digest(json.dumps(protected,sort_keys=True)+digest(pathlib.Path(M.CL).read_bytes())+digest(pathlib.Path(__file__).read_bytes()))
    pool=proposals(case);records=[];compilations=0;feature='unobserved';output_seen=set()
    try:
        while pool and len(records)<max_trials:
            if feature=='unobserved':index=0
            else:index=max(range(len(pool)),key=lambda i:history.rank(feature,pool[i]))
            proposal=pool.pop(index)
            key=digest(json.dumps([env,case['rva'],case['symbol'],case['expected_targets'],case.get('flags',M.FLAGS),proposal['source']],sort_keys=True))
            result=history.cached(key);cached=result is not None
            if result is None:
                result=evaluate(case,proposal,run_dir)
                compilations+=1;history.store(key,case,proposal,feature,result)
            record=dict(proposal=proposal['name'],family=proposal['family'],assumptions=proposal['assumptions'],cached=cached,**result)
            record['repeated_output']=result.get('code_fingerprint') in output_seen
            if result.get('code_fingerprint'):output_seen.add(result['code_fingerprint'])
            records.append(record)
            print(case['id'],proposal['name'],result['failure_class'],f"{result.get('identical_bytes',0)}/{result.get('bytes',0)}",'cached' if cached else 'compiled',flush=True)
            if result['exact']:break
            if feature=='unobserved':feature=result['failure_class']
        after=production_state()
        if after!=protected or json.dumps(M.rebuilt_symbols(),sort_keys=True)!=binding_state:
            raise ValueError('Production inputs or reconstruction bindings changed during experiment')
        summary=dict(case_id=case['id'],rva=hex(case['rva']),origin=case['coverage_at_start'],role=case.get('role'),
            learning_use=case.get('learning_use','training'),semantic_seed=case.get('seed_interpretation','provided'),
            exact=any(row['exact'] for row in records),trials=len(records),compilations=compilations,
            best_quality=max((row['quality'] for row in records),default=0),production_unchanged=True,
            bindings_unchanged=True,published=False,records=records)
        (run_dir/'report.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        return summary
    finally:history.db.commit()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',type=pathlib.Path)
    parser.add_argument('--run-dir',type=pathlib.Path,required=True)
    parser.add_argument('--history',type=pathlib.Path,default=BASE/'runs/history.sqlite3')
    parser.add_argument('--max-trials',type=int,default=8)
    args=parser.parse_args()
    if not args.history.resolve().is_relative_to(BASE):raise ValueError('History must stay experimental')
    if args.max_trials<1 or args.max_trials>16:raise ValueError('Trial budget must be between 1 and 16')
    args.history.parent.mkdir(parents=True,exist_ok=True)
    report=run(args.case.resolve(),args.run_dir.resolve(),History(args.history),args.max_trials)
    print(json.dumps({key:value for key,value in report.items() if key!='records'}),flush=True)


if __name__=='__main__':main()
