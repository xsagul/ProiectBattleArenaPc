"""Fixed cursor arrays, proved through native construction and destruction.

The reflected list wrapper alone is insufficient evidence for twelve-byte
dynamic storage: these two owners contain seven and three CursorData values.
"""
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M
import gen_reflected_buffers as B

GEN=ROOT/'client-src/src/gen'
MANIFEST=ROOT/'tools/cursor_array_layouts.json'
NATIVE=GEN/'CursorArrayNative.cpp'
CALLBACKS=GEN/'CursorArrayCallbacks.cpp'
COUNTS={'CursorDataCaptureCooldownContext':7,'CursorDataTeamContext':3}


def candidate(im,a,f,g):
    count=COUNTS.get(a.cls[g])
    if count is None:return None
    evidence=B.candidate(im,a,f,g)
    if evidence is None or f['size']!=56*count or evidence['member']['element']!='CursorData' or evidence['member']['stride']!=56:
        return None
    if evidence['native_ctor'] is None or evidence['native_dtor'] is None:return None
    return dict(evidence=evidence,count=count,native_ctor_body=im.text(evidence['native_ctor']))


def fields(row):
    member=row['evidence']['member']
    return [f'    CursorData {member["name"]}[{row["count"]}];     // +0x0, fixed array; no buffer pointer']


def layout_of(im,a,f,g):
    rows=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else []
    row=next((row for row in rows if row['evidence']['name']==a.cls[g]),None)
    if row is None:return None
    if json.loads(json.dumps(candidate(im,a,f,g)))!=row:raise ValueError('Fixed cursor array evidence changed: '+a.cls[g])
    return fields(row)


def native_definitions(rows):
    lines=['CursorData::CursorData() = default;']
    for row in rows:
        name=row['evidence']['name']
        lines += [f'{name}::{name}() = default;',f'{name}::~{name}() = default;']
    return lines


def verify_native(path,rows):
    obj=M.compile_obj(str(path),M.FLAGS);audit=[]
    checks=[('CursorData','ctor',0x61b990)]
    checks += [(row['evidence']['name'],kind,row['evidence']['native_'+kind]) for row in rows for kind in ('ctor','dtor')]
    allowed={'?g_empty_string_data@@3PBDB':0x15c67f0,'??1RString@@QAE@XZ':0x9bab90}
    for name,kind,rva in checks:
        symbol=f'??{0 if kind=="ctor" else 1}{name}@@QAE@XZ'
        result=M.compare(str(path),symbol,rva,M.FLAGS,obj)
        _,code,_=M.function_of(obj,symbol);targets=M.symbol_addresses(rva,code)
        if result[3] is not None or any(allowed.get(sym)!=target for sym,target in targets):
            raise ValueError(f'Fixed cursor native method differs: {name} {kind}: {result}: {targets}')
        audit.append(dict(name=name,kind=kind,rva=rva,bytes=result[1],targets=targets))
    return audit


def verify_callbacks(path,rows):
    # Binding is allowed only after these actual native bodies have passed.
    native=[dict(name=row['evidence']['name'],rva=row['evidence']['native_dtor']) for row in rows]
    good,bad=B.verify(path,[row['evidence'] for row in rows],native)
    if bad:raise ValueError('Fixed cursor callbacks differ: '+str(bad))
    return good


def main():
    import gen_sources as G,gen_meta as A
    im=G.Image();a=A.analysis(im);facts=A.class_facts(im,a)
    rows=[candidate(im,a,f,g) for g,f in facts.items() if a.cls[g] in COUNTS]
    if len(rows)!=2 or any(row is None for row in rows):raise ValueError('Fixed cursor array metadata incompatible')
    rows.sort(key=lambda row:row['evidence']['name'])
    header=(GEN/'BinClasses.h').read_text(encoding='utf-8')
    for row in rows:
        name=row['evidence']['name'];pattern=r'(struct '+name+r'\n\{\n)(.*?)(\n\};)'
        def replace(match):
            declarations=[line for line in match[2].splitlines() if re.match(r'\s*(?:~)?'+name+r'\(\);',line)]
            return match[1]+'\n'.join([*declarations,*fields(row)])+match[3]
        header,count=re.subn(pattern,replace,header,flags=re.S)
        if count!=1:raise ValueError('Fixed cursor definition not unique')
    header=re.sub(r'^#include "([^"]+)"',lambda m:'#include "'+(GEN/m[1]).resolve().as_posix()+'"',header,flags=re.M)
    (ROOT/'client-src/obj/root_cursor_array_classes.h').write_text(header,encoding='utf-8')
    native_probe=ROOT/'client-src/obj/root_cursor_array_native.cpp'
    native_probe.write_text('\n'.join(['#include "root_cursor_array_classes.h"',*native_definitions(rows),'']),encoding='utf-8')
    native_audit=verify_native(native_probe,rows)
    callback_probe=ROOT/'client-src/obj/root_cursor_array_callbacks.cpp'
    callback_probe.write_text('\n'.join(['#include "root_cursor_array_classes.h"',*B.definitions([row['evidence'] for row in rows]),'']),encoding='utf-8')
    verify_callbacks(callback_probe,rows)
    MANIFEST.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    lines,_=A.bin_classes(im,a)
    (GEN/'BinClasses.h').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    claimed=set()
    for source in M.sources():
        if pathlib.Path(source).resolve() in (NATIVE.resolve(),CALLBACKS.resolve()):continue
        claimed.update(int(rva,16) for rva in re.findall(r'^// match: ([0-9a-f]+)',pathlib.Path(source).read_text(encoding='utf-8'),re.M))
    native_claims=[]
    for item in native_audit:
        rva=item['rva'];kind='same' if rva in claimed else 'match';claimed.add(rva)
        native_claims.append(f'// {kind}: {rva:x} ??{0 if item["kind"]=="ctor" else 1}{item["name"]}@@QAE@XZ')
    NATIVE.write_text('\n'.join(['// Native cursor fixed arrays; all five defaulted C++ methods are verified.',
        '// Generated by tools/gen_cursor_arrays.py.',*native_claims,'#include "BinClasses.h"',*native_definitions(rows),'']),encoding='utf-8',newline='\n')
    claims=[]
    for row in rows:
        for key,fn,suffix in B.CALLBACK_ORDER:
            rva=row['evidence']['callbacks'][key];kind='same' if rva in claimed else 'match';claimed.add(rva)
            claims.append(f'// {kind}: {rva:x} ??${fn}@U{row["evidence"]["name"]}@@@@YA{suffix}')
    CALLBACKS.write_text('\n'.join(['// Complete lifecycle of the two fixed cursor arrays.',
        '// Generated by tools/gen_cursor_arrays.py.',*claims,'#include "BinClasses.h"',*B.definitions([row['evidence'] for row in rows]),'']),encoding='utf-8',newline='\n')
    M.rebuilt_symbols.__dict__.pop('v',None)
    native_final=verify_native(NATIVE,rows);verify_callbacks(CALLBACKS,rows)
    (ROOT/'client-src/obj/root_cursor_arrays_audit.json').write_text(json.dumps(dict(native=native_final,callbacks=rows),indent=2),encoding='utf-8')
    print('Fixed cursor arrays:',len(rows),'native methods:',len(native_final),'callbacks:',8)


if __name__=='__main__':main()
