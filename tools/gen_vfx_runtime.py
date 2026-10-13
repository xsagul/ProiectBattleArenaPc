"""Normal VFX reconstruction: prove all four callbacks and three native helpers.

This generator does not import, edit, or publish experimental artifacts.
"""
import copy
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M

GEN=ROOT/'client-src/src/gen'
MANIFEST=ROOT/'tools/vfx_runtime_layouts.json'
HEADER=GEN/'VfxRuntimePointers.h'
SOURCE=GEN/'VfxRuntimeCallbacks.cpp'
NAMES=('VfxProbabilityTableData','VfxAnimatedVector3fVariableData','ValueVector3',
       'FlexValueVector3','VfxFlexShapeDefinitionData','VfxFieldAccelerationDefinitionData',
       'VfxFieldOrbitalDefinitionData','VfxParentInheritanceParams','VfxTrailDefinitionData')
ORDER=(('create','MetaCreate','PAXXZ'),('construct','MetaConstruct','XPAX@Z'),
       ('destroy','MetaDestroy','XPAX@Z'),('destruct','MetaDestruct','XPAX@Z'))
CALLBACKS={
 'VfxProbabilityTableData':(0xa57d10,0xa58af0,0xa58140,0xa58180),
 'VfxAnimatedVector3fVariableData':(0xa59340,0xa59470,0xa585f0,0xa58640),
 'ValueVector3':(0x1db9e0,0x1dba10,0xa58930,0xa57cc0),
 'FlexValueVector3':(0xa58330,0xa583e0,0xa57f40,0xa57fa0),
 'VfxFlexShapeDefinitionData':(0x24e360,0x24e3b0,0xa57e70,0xa57ea0),
 'VfxFieldAccelerationDefinitionData':(0xa58d20,0xa58d60,0xa57f40,0xa57fa0),
 'VfxFieldOrbitalDefinitionData':(0xa58dd0,0xa58e10,0xa57f40,0xa57fa0),
 'VfxParentInheritanceParams':(0xa58f20,0xa58f60,0xa57f40,0xa57fa0),
 'VfxTrailDefinitionData':(0xa59260,0xa592b0,0xa57c60,0xa57cc0)}
SIZES={name:dict(zip((x[0] for x in ORDER),sizes)) for name,sizes in {
 'VfxProbabilityTableData':(72,59,55,40),
 'VfxAnimatedVector3fVariableData':(7,84,74,58),
 'ValueVector3':(45,32,94,77),
 'FlexValueVector3':(53,39,94,77),
 'VfxFlexShapeDefinitionData':(80,67,40,28),
 'VfxFieldAccelerationDefinitionData':(49,36,94,77),
 'VfxFieldOrbitalDefinitionData':(49,36,94,77),
 'VfxParentInheritanceParams':(50,36,94,77),
 'VfxTrailDefinitionData':(65,52,94,77)}.items()}
EXPECTED={
 'VfxProbabilityTableData':(32,[(0,'BinList<float>'),(12,'BinList<float>'),(24,'float')]),
 'VfxAnimatedVector3fVariableData':(64,[(0,'BinList<MetaPointer<VfxProbabilityTableData>>'),(12,'BinList<float>'),(24,'BinList<Vector3>')]),
 'ValueVector3':(16,[(0,'Vector3'),(12,'MetaPointer<VfxAnimatedVector3fVariableData>')]),
 'FlexValueVector3':(20,[(0,'u32'),(4,'MetaEmbed<ValueVector3>')]),
 'VfxFlexShapeDefinitionData':(36,[(i*4,'float') for i in range(7)]+[(28,'MetaPointer<FlexTypeFloat>'),(32,'MetaPointer<FlexValueVector3>')]),
 'FlexTypeFloat':(8,[(0,'u32'),(4,'float')]),
 'VfxFieldAccelerationDefinitionData':(20,[(0,'bool'),(4,'MetaEmbed<ValueVector3>')]),
 'VfxFieldOrbitalDefinitionData':(20,[(0,'bool'),(4,'MetaEmbed<ValueVector3>')]),
 'VfxParentInheritanceParams':(20,[(0,'u8'),(4,'MetaEmbed<ValueVector3>')]),
 'VfxTrailDefinitionData':(28,[(0,'MetaEmbed<ValueVector3>'),(16,'float'),(20,'int'),(24,'u8'),(25,'u8')])}
HELPERS=(('VfxProbabilityOwners.cpp','??1VfxProbabilityOwners@@QAE@XZ',0xa64c90,79,
          'VfxProbabilityOwners::~VfxProbabilityOwners() = default;'),
         ('VfxFlexPointer.cpp','??1?$VfxOwnedPointer@UFlexValueVector3@@@@QAE@XZ',0xa64b00,92,
          'VfxOwnedPointer<FlexValueVector3>::~VfxOwnedPointer() { delete value; }'),
         ('VfxDynamicAllocate.cpp','VfxDynamicAllocate',0xa681b0,97,
          'VfxAnimatedVector3fVariableData* __fastcall VfxDynamicAllocate(void*) { return new VfxAnimatedVector3fVariableData; }'))
ALLOWED={'??2@YAPAXI@Z':0x9bb8d0,'??3@YAXPAX@Z':0x9bb930,
         '??3@YAXPAXI@Z':0x9bb940,'?g_JungleDefaultPosition@@3UVector3@@B':0x3195f70,
         '?g_VfxZeroUpper@@3MB':0xfb8cdc,'?g_VfxZeroLower@@3MB':0xfb8de0,
         '?g_VfxOneUpper@@3MB':0x1566378,'?g_VfxOneLower@@3MB':0x1566374}
TOLERANCES={0xfb8cdc:'bd378635',0xfb8de0:'bd3786b5',0x1566378:'0800803f',0x1566374:'efff7f3f'}
HEADER_SOURCE='''// Native VFX ownership, separately proved from serialized list tags.
#pragma once
#include "ReflectedBuffers.h"
#include "ReflectedElementDefaults.h"
struct FlexValueVector3;
struct VfxProbabilityTableData;
struct VfxAnimatedVector3fVariableData;
template<class T> struct VfxOwnedPointer {
    T* value = nullptr;
    ~VfxOwnedPointer() { delete value; }
};
template<> struct VfxOwnedPointer<FlexValueVector3> {
    FlexValueVector3* value = nullptr;
    ~VfxOwnedPointer();
};
struct VfxProbabilityOwners {
    VfxOwnedPointer<VfxProbabilityTableData> probabilityTables[3];
    ~VfxProbabilityOwners();
};
struct VfxRawAllocation {
    void* data = nullptr;
    ~VfxRawAllocation() { ::operator delete(data); }
};
struct VfxConstantVector3 : Vector3 {
    VfxConstantVector3() { x=0; y=0; z=0; }
    VfxConstantVector3(const Vector3& value) : Vector3(value) {}
};
static_assert(sizeof(VfxConstantVector3)==12,"native scalar vector");
VfxAnimatedVector3fVariableData* __fastcall VfxDynamicAllocate(void* context);
'''


def metadata(im,a,f,g):
    import gen_meta as A
    name=a.cls[g];size,expected=EXPECTED[name]
    if name not in a.unique or f['parent'] is not None or f['poly'] or f['size']!=size or f['align']!=4:
        raise ValueError('VFX metadata size/base/alignment changed: '+name)
    members=[]
    for event in a.followed.get(g,()):
        if event[0]!='call' or event[2]!=g or event[1]==A.META_CTOR:continue
        args=event[3];wrapper=A.member_wrapper(im,event[1]);descriptor=A.container_wrapper(im,event[1])
        if len(args)!=3 or any(x[0]!='imm' for x in args):raise ValueError('VFX member arguments')
        if wrapper:typ=a.member_type(*wrapper[:2])
        elif descriptor and descriptor['code']==0x80 and descriptor['slot']==5 and descriptor['size']==12:
            element=descriptor['stores'].get(4);stride=descriptor['stores'].get(8)
            if not element or element[0]!=1 or not stride or stride[0]!=4:raise ValueError('VFX list descriptor')
            typ='BinList<'+a.element(element[1],stride[1],descriptor['of'])+'>'
        else:raise ValueError('VFX member wrapper')
        members.append(dict(offset=args[1][1],name=A.cpp_member_name(a.names.get(args[0][1]) or f'm_{args[0][1]:08x}'),
            type=typ,wrapper=event[1],args=args,wrapper_body=im.text(event[1]),descriptor=descriptor))
    members.sort(key=lambda m:m['offset'])
    if [(m['offset'],m['type']) for m in members]!=expected:raise ValueError('VFX reflected members changed: '+name)
    return json.loads(json.dumps(dict(name=name,facts=f,members=members,
        callbacks={k:im.text(f[k]) if f[k] else None for k in ('create','construct','destroy','destruct','v2')},
        helpers={hex(rva):im.text(rva) for _,_,rva,_,_ in HELPERS},
        tolerances={hex(rva):bytes(im.img[rva:rva+4]).hex() for rva in TOLERANCES},
        default_vector=bytes(im.img[0x3195f70:0x3195f7c]).hex())))


def fields(row):
    names={m['offset']:m['name'] for m in row['members']}
    def field(typ,off,init=''):
        return f'    {typ} {names[off]}'+(' = '+init if init else '')+f'; // +{off:#x}'
    name=row['name']
    if name=='VfxProbabilityTableData':return [field('ReflectedBuffer<float>',0),field('ReflectedBuffer<float>',12),field('float',24,'1.0f'),
        '    bool unknown1c = true;','    bool unknown1d = false;','    u8 unknown1e[2];']
    if name=='VfxAnimatedVector3fVariableData':return [field('VfxProbabilityOwners',0),field('ReflectedBuffer<float>',12),field('ReflectedBuffer<Vector3>',24),
        '    u8 unknown24 = 0;','    u8 unknown25;','    u16 unknown26 = 0;','    u32 unknown28 = 0;','    u32 unknown2c = 0xffffffff;',
        '    u8 unknown30[12];','    VfxRawAllocation unknown3c;']
    if name=='ValueVector3':return [field('VfxConstantVector3',0),field('VfxOwnedPointer<VfxAnimatedVector3fVariableData>',12),
        '    ValueVector3() = default;',f'    ValueVector3(const Vector3& value) : {names[0]}(value) {{}}']
    if name=='FlexValueVector3':return [field('u32',0,'0'),f'    ::ValueVector3 {names[4]}{{g_JungleDefaultPosition}}; // +4']
    if name=='VfxFlexShapeDefinitionData':return [field('float',i*4,'0.0f') for i in range(7)]+[
        field('VfxOwnedPointer<FlexTypeFloat>',28),field('VfxOwnedPointer<FlexValueVector3>',32)]
    if name=='VfxFieldAccelerationDefinitionData':return [field('bool',0,'true'),field('::ValueVector3',4)]
    if name=='VfxFieldOrbitalDefinitionData':return [field('bool',0,'true'),f'    ::ValueVector3 {names[4]}{{{{0.0f,1.0f,0.0f}}}};']
    if name=='VfxParentInheritanceParams':return [field('u8',0,'0'),f'    ::ValueVector3 {names[4]}{{g_JungleDefaultPosition}};']
    if name=='VfxTrailDefinitionData':return [field('::ValueVector3',0),field('float',16,'0'),field('int',20,'0'),field('u8',24,'0'),field('u8',25,'0')]
    raise ValueError('Unsupported VFX runtime layout')


def layout_of(im,a,f,g):
    if a.cls[g] not in NAMES or not MANIFEST.exists():return None
    saved=json.loads(MANIFEST.read_text());row=next(r for r in saved if r['name']==a.cls[g])
    if metadata(im,a,f,g)!=row:raise ValueError('VFX runtime evidence changed: '+a.cls[g])
    import gen_meta as A
    dep=next((dg,df) for dg,df in A.class_facts(im,a).items() if a.cls[dg]=='FlexTypeFloat')
    if metadata(im,a,dep[1],dep[0])!=next(r for r in saved if r['name']=='FlexTypeFloat'):
        raise ValueError('VFX scalar pointee evidence changed')
    return fields(row)


def definitions():
    out=['extern const float g_VfxZeroUpper,g_VfxZeroLower,g_VfxOneUpper,g_VfxOneLower;']
    for name in NAMES:
        out.extend([f'template<> void* MetaCreate<{name}>() {{ return '+('VfxDynamicAllocate(nullptr)' if name=='VfxAnimatedVector3fVariableData' else 'new '+name)+'; }',
            f'template<> void MetaConstruct<{name}>(void* p) {{ new(p) {name}; }}',
            f'template<> void MetaDestroy<{name}>(void* p) {{ delete static_cast<{name}*>(p); }}',
            f'template<> void MetaDestruct<{name}>(void* p) {{ static_cast<{name}*>(p)->~{name}(); }}'])
    out.append('''template<> void MetaVirtual2<VfxProbabilityTableData>(void* p) {
    auto v=static_cast<VfxProbabilityTableData*>(p);
    v->unknown1d=false;
    v->unknown1c=(v->keyTimes.count==0);
    if(v->keyTimes.count==2) {
        auto key=v->keyTimes.data;
        Vector2 keys{key[0],key[1]};
        if(keys.x<=g_VfxZeroUpper && keys.x>=g_VfxZeroLower &&
           keys.y<=g_VfxOneUpper && keys.y>=g_VfxOneLower) v->unknown1d=true;
    }
}''')
    return out


def verify(header,paths,callback):
    allowed=dict(ALLOWED);saved=copy.deepcopy(M.rebuilt_symbols());out=[]
    def check(path,symbol,rva,size,obj):
        x=M.compare(str(path),symbol,rva,M.FLAGS,obj);full,code,_=M.function_of(obj,symbol);targets=M.symbol_addresses(rva,code)
        if x[3] is not None or x[1]!=size or any(allowed.get(sym)!=target for sym,target in targets):
            raise ValueError(f'VFX complete body/target differs: {full}: {x}: {targets}')
        return dict(symbol=full,rva=rva,bytes=x[1],targets=targets)
    try:
        for path,(_,symbol,rva,size,_) in zip(paths,HELPERS):
            row=check(path,symbol,rva,size,M.compile_obj(str(path),M.FLAGS));out.append(row)
            M.rebuilt_symbols().setdefault(rva,[]).append(row['symbol']);allowed[row['symbol']]=rva
        obj=M.compile_obj(str(callback),M.FLAGS)
        for name in NAMES:
            for (key,fn,suffix),rva in zip(ORDER,CALLBACKS[name]):
                out.append(check(callback,f'??${fn}@U{name}@@@@YA{suffix}',rva,SIZES[name][key],obj))
        out.append(check(callback,'??$MetaVirtual2@UVfxProbabilityTableData@@@@YAXPAX@Z',0xa581b0,93,obj))
    finally:M.rebuilt_symbols.v=saved
    return out


def main():
    import gen_sources as G,gen_meta as A
    im=G.Image();a=A.analysis(im);facts=A.class_facts(im,a)
    rows=[metadata(im,a,f,g) for g,f in facts.items() if a.cls[g] in EXPECTED]
    if len(rows)!=len(EXPECTED) or any(row['default_vector']!='00'*12 for row in rows):raise ValueError('VFX metadata/global missing')
    if any(row['tolerances']!={hex(rva):data for rva,data in TOLERANCES.items()} for row in rows):raise ValueError('VFX endpoint tolerance globals changed')
    if next(row for row in rows if row['name']=='VfxProbabilityTableData')['facts']['v2']!=0xa581b0:raise ValueError('VFX probability post-load entry changed')
    for row in rows:
        if row['name'] in NAMES and tuple(row['facts'][key] for key,_,_ in ORDER)!=CALLBACKS[row['name']]:raise ValueError('VFX callback pointer changed')
    support=ROOT/'client-src/obj/root_vfx_runtime_support.h'
    support.write_text(re.sub(r'#include "([^"]+)"',lambda m:'#include "'+(GEN/m[1]).as_posix()+'"',HEADER_SOURCE))
    header=ROOT/'client-src/obj/root_vfx_runtime_classes.h'
    lines=['#include "'+support.name+'"']
    production_header=(GEN/'BinClasses.h').read_text()
    scalar=re.search(r'struct FlexTypeFloat\n\{\n.*?\n\};',production_header,re.S)
    if not scalar:raise ValueError('VFX scalar definition absent')
    lines.append(scalar[0])
    for name in NAMES:
        row=next(r for r in rows if r['name']==name)
        lines.extend(['struct '+name+' {',*fields(row),'};'])
    header.write_text('\n'.join(lines)+'\n')
    paths=[]
    for filename,_,_,_,definition in HELPERS:
        p=ROOT/'client-src/obj'/('root_runtime_'+filename);p.write_text('#include "'+header.name+'"\n'+definition+'\n');paths.append(p)
    callback=ROOT/'client-src/obj/root_vfx_runtime_callbacks.cpp'
    callback.write_text('#include "'+header.name+'"\n'+'\n'.join(definitions())+'\n')
    audit=verify(header,paths,callback)
    HEADER.write_text(HEADER_SOURCE,encoding='utf-8',newline='\n');MANIFEST.write_text(json.dumps(rows,indent=2)+'\n')
    lines,_=A.bin_classes(im,a);(GEN/'BinClasses.h').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    claimed=set()
    for p in M.sources():
        if pathlib.Path(p).name==SOURCE.name:continue
        claimed.update(int(x,16) for x in re.findall(r'^// match: ([0-9a-f]+)',pathlib.Path(p).read_text(),re.M))
    production_paths=[]
    for row,(filename,_,_,_,definition) in zip(audit,HELPERS):
        p=GEN/filename;p.write_text(f'// match: {row["rva"]:x} {row["symbol"]}\n#include "BinClasses.h"\n'+definition+'\n');production_paths.append(p)
    claims=[]
    for row in audit[3:]:
        kind='same' if row['rva'] in claimed else 'match';claimed.add(row['rva']);claims.append(f'// {kind}: {row["rva"]:x} {row["symbol"]}')
    SOURCE.write_text('\n'.join([*claims,'#include "BinClasses.h"',*definitions(),'']))
    M.rebuilt_symbols.__dict__.pop('v',None)
    final=verify(GEN/'BinClasses.h',production_paths,SOURCE)
    (ROOT/'client-src/obj/root_vfx_runtime_audit.json').write_text(json.dumps(final,indent=2)+'\n')
    print('VFX runtime:',len(final),'complete bodies,',sum(row['bytes'] for row in final),'bytes verified')


if __name__=='__main__':main()
