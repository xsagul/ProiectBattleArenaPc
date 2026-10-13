"""Prove string-bearing element layouts from metadata and complete destructors.

Constructor parity is independent: publishing a layout does not claim that its
default initialization reproduces the client constructor.
"""
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M

GEN=ROOT/'client-src/src/gen'
MANIFEST=ROOT/'tools/reflected_lifetime_layouts.json'
SOURCE=GEN/'ReflectedElementLifetimes.cpp'
HEADER=GEN/'ReflectedElementDefaults.h'
HEADER_SOURCE='''// Shared reflected defaults measured in the client image.
#pragma once
#include "../Meta.h"
extern const Vector3 g_JungleDefaultPosition; // VA 0x3715f70, twelve zero bytes
'''
NAMES=('FontLocaleType','JungleLocationMapInformation','TftMapItemData','CursorData',
       'StealthVfx','MasteryData','NeutralMinionSpawnConfig','AudioStatusEvents','ESportTeamEntry')


def candidate(im,a,f,g):
    import gen_meta as A
    if f['parent'] is not None or f['poly'] or f['align']!=4:return None
    members=[]
    for event in a.followed.get(g,()):
        if event[0]!='call' or event[2]!=g or event[1]==A.META_CTOR:continue
        args=event[3];wrapper=A.member_wrapper(im,event[1])
        if not wrapper or wrapper[1] or wrapper[0] not in A.PRIM_SIZE or len(args)!=3 or any(x[0]!='imm' for x in args):return None
        code=wrapper[0]
        members.append(dict(offset=args[1][1],code=code,type=A.PRIMITIVE[code],
            name=A.cpp_member_name(a.names.get(args[0][1]) or f'm_{args[0][1]:08x}'),hash=args[0][1],wrapper=event[1]))
    members.sort(key=lambda member:member['offset'])
    pos=0
    for member in members:
        off=member['offset'];width=A.PRIM_SIZE[member['code']]
        alignment=1 if member['code'] in (1,2,3) else 2 if member['code'] in (4,5) else 8 if member['code'] in (8,9) else 4
        if alignment>f['align'] or off!=(pos+alignment-1)//alignment*alignment or off+width>f['size']:return None
        pos=off+width
    if f['size']!=(pos+3)//4*4 or not any(member['type']=='MetaString' for member in members):return None
    if not f['destroy'] or not f['destruct']:return None
    keys=['destroy','destruct'];initializers={};native_ctor=None;globals=[]
    if a.cls[g]=='FontLocaleType':
        if bytes(im.img[0x1565498:0x156549e])!=b'en_us\0':return None
        initializers={'localeName':'{"en_us"}'}
        globals=[dict(va=0x1ae5498,bytes=b'en_us\0'.hex())]
        keys=['create','construct',*keys]
    if a.cls[g]=='JungleLocationMapInformation':
        if bytes(im.img[0x3195f70:0x3195f7c])!=bytes(12):return None
        initializers={'Position':'g_JungleDefaultPosition','Index':'0','Location':'0'}
        globals=[dict(va=0x3715f70,bytes='00'*12)]
        keys=['create','construct',*keys]
    if a.cls[g]=='CursorData':
        native_ctor=0x61b990
        targets={item[2] for item in (A.out_of_line(im,f['create']),A.out_of_line(im,f['construct'])) if item}
        if targets!={native_ctor} or not im.text(native_ctor).startswith('mov dword ptr [ecx], 0\nmov dword ptr [ecx + 4], 0\n'):return None
        initializers={'mHotSpot':'{0,0}'}
    return dict(name=a.cls[g],size=f['size'],align=f['align'],members=members,
        initializers=initializers,globals=globals,native_ctor=native_ctor,
        native_ctor_body=im.text(native_ctor) if native_ctor is not None else None,
        callbacks={key:f[key] for key in keys},bodies={key:im.text(f[key]) for key in keys})


def fields(row):
    return [f'    {member["type"]} {member["name"]}'+(' = '+row['initializers'][member['name']] if member['name'] in row['initializers'] else '')+
            f';     // +{member["offset"]:#x}, reflected lifetime'
            for member in row['members']]


def layout_of(im,a,f,g):
    rows=json.loads(MANIFEST.read_text(encoding='utf-8')) if MANIFEST.exists() else []
    row=next((row for row in rows if row['name']==a.cls[g]),None)
    if row is None:return None
    if candidate(im,a,f,g)!=row:raise ValueError('Reflected element lifetime evidence changed: '+a.cls[g])
    return fields(row)


def definitions(rows):
    import gen_reflected_buffers as B
    return [line for row in rows for (key,_,_),line in zip(B.CALLBACK_ORDER,B.definitions([row]))
            if key in row['callbacks']]


def verify(path,rows):
    obj=M.compile_obj(str(path),M.FLAGS);out=[]
    expected={'??1RString@@QAE@XZ':0x9bab90,'??3@YAXPAX@Z':0x9bb930,'??3@YAXPAXI@Z':0x9bb940,
        '??2@YAPAXI@Z':0x9bb8d0,'?g_empty_string_data@@3PBDB':0x15c67f0,
        '?g_JungleDefaultPosition@@3UVector3@@B':0x3195f70,
        '??0MetaString@@QAE@PBD@Z':0x9b78e0,'??_C@_05PFEAJGOD@en_us@':0x1565498}
    import gen_reflected_buffers as B
    for row in rows:
        checks=[(key,row['callbacks'][key],f'??${fn}@U{row["name"]}@@@@YA{suffix}')
                for key,fn,suffix in B.CALLBACK_ORDER if key in row['callbacks']]
        for key,rva,symbol in checks:
            result=M.compare(str(path),symbol,rva,M.FLAGS,obj)
            _,code,_=M.function_of(obj,symbol);targets=M.symbol_addresses(rva,code)
            if result[3] is not None or any(expected.get(sym)!=target for sym,target in targets):
                raise ValueError(f'Element lifetime differs: {row["name"]} {key}: {result}: {targets}')
            out.append(dict(name=row['name'],key=key,rva=rva,bytes=result[1],targets=targets))
    return out


def main():
    import gen_meta as A,gen_sources as G
    im=G.Image();a=A.analysis(im);facts=A.class_facts(im,a)
    rows=[candidate(im,a,f,g) for g,f in facts.items() if a.cls[g] in NAMES]
    if len(rows)!=len(NAMES) or any(row is None for row in rows):raise ValueError('Element metadata missing or incompatible')
    rows.sort(key=lambda row:row['name'])
    header=(GEN/'BinClasses.h').read_text(encoding='utf-8')
    for row in rows:
        pattern=r'(struct '+re.escape(row['name'])+r'\n\{\n).*?(\n\};)'
        declarations=[f'    {row["name"]}();'] if row['native_ctor'] is not None else []
        header,count=re.subn(pattern,lambda m:m[1]+'\n'.join([*declarations,*fields(row)])+m[2],header,flags=re.S)
        if count!=1:raise ValueError('Element class definition not unique: '+row['name'])
    header=header.replace('#include "MetaClasses.h"','#include "MetaClasses.h"\nextern const Vector3 g_JungleDefaultPosition;')
    header=re.sub(r'^#include "([^"]+)"',lambda m:'#include "'+(GEN/m[1]).resolve().as_posix()+'"',header,flags=re.M)
    (ROOT/'client-src/obj/root_reflected_element_classes.h').write_text(header,encoding='utf-8')
    probe=ROOT/'client-src/obj/root_reflected_element_lifetimes.cpp'
    probe.write_text('\n'.join(['#include "root_reflected_element_classes.h"',*definitions(rows),'']),encoding='utf-8')
    verify(probe,rows)
    HEADER.write_text(HEADER_SOURCE,encoding='utf-8',newline='\n')
    MANIFEST.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    lines,_=A.bin_classes(im,a)
    (GEN/'BinClasses.h').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    claimed=set()
    for source in M.sources():
        if pathlib.Path(source).resolve()==SOURCE.resolve():continue
        claimed.update(int(rva,16) for rva in re.findall(r'^// match: ([0-9a-f]+)',pathlib.Path(source).read_text(encoding='utf-8'),re.M))
    claims=[]
    for row in rows:
        for key,rva in row['callbacks'].items():
            kind='same' if rva in claimed else 'match';claimed.add(rva)
            import gen_reflected_buffers as B
            _,fn,suffix=next(item for item in B.CALLBACK_ORDER if item[0]==key)
            claims.append(f'// {kind}: {rva:x} ??${fn}@U{row["name"]}@@@@YA{suffix}')
    SOURCE.write_text('\n'.join(['// Real string subobject destruction; no class destructor aliases.',
        '// Generated by tools/gen_reflected_lifetimes.py.',*claims,'#include "BinClasses.h"',*definitions(rows),'']),encoding='utf-8',newline='\n')
    M.rebuilt_symbols.__dict__.pop('v',None)
    audit=verify(SOURCE,rows)
    (ROOT/'client-src/obj/root_reflected_element_lifetimes_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('Reflected string element layouts:',len(rows),'complete lifecycle callbacks:',len(audit))


if __name__=='__main__':main()
