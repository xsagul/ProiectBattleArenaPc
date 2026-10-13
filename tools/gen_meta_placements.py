"""Metadata-backed placement initialization and singleton registration.

This is normal reconstruction, independent of experiments/reconstruction_search.
Every emitted lifecycle specialization and native callee is compiled and checked.
"""
import json
import pathlib
import re
import sys

ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'tools'))
import match_func as M

GEN=ROOT/'client-src/src/gen'
MANIFEST=ROOT/'tools/meta_placement_layouts.json'
HEADER=GEN/'MetaPlacementSupport.h'
CALLBACKS=GEN/'MetaPlacementCallbacks.cpp'
PARENT=GEN/'LogicBoolDriverCtor.cpp'
REGISTRY=GEN/'SummonerRegistry.cpp'
TYPED_GLOBALS={'g_36ed6c0','g_2aa7460'}
FIELDS={
 'CollectiblesEsportsTeamData':['    u32 teamId = 0;','    MetaString shortName;','    MetaString fullName;','    MetaString leagueName;'],
 'SummonerIconData':['    u32 iconId = 0;','    u32 esportsTeam = 0; // serialized MetaLink, four-byte non-owning storage',
    '    MetaString gameTexture;','    bool GoldEsportsSupportIcon = false;','    MetaString eSportsEventMutator;'],
 'GDSMapObjectBannerInfo':['    u32 BannerData = 0; // serialized MetaLink, four-byte non-owning storage'],
 'Class_bafabcc8':['    Class_bafabcc8() : LevelSingleton<Class_bafabcc8>(this) {}',
    '    ReflectedBuffer<u32> m_ed45c0f6;','    std::list<u32> unknown10;'],
}
RVA={'Class_bafabcc8':0x26f0c0,'CollectiblesEsportsTeamData':0x2d0b90,'GDSMapObjectBannerInfo':0x2d09e0,
     'HasReceivedAnimEmoteEventBoolDriver':0x2d0a90,'IsLocalPlayerBoolDriver':0x2d0ae0,
     'IsMovingBoolDriver':0x2d0b30,'SummonerIconData':0x2d0c40}
EXPECTED_SIZES={0xa21cf0:9,0xf95b0:73,0x124b60:489,0x125680:10,0x63c7c0:133,
                0x26f0c0:72,0x2d0b90:77,0x2d09e0:18,0x2d0a90:20,0x2d0ae0:20,
                0x2d0b30:20,0x2d0c40:66,0x2d0d00:19}
NATIVE_HELPERS=(0xa21cf0,0xf95b0,0x124b60,0x125680,0x63c7c0)
HEADER_SOURCE='''// Native placement support, distinct from serialized container tags.
#pragma once
#include "ReflectedBuffers.h"
#include <list>
#include <map>
#include <cstddef>
struct Class_bafabcc8;
extern Class_bafabcc8* g_36ed6c0; // VA 0x36ed6c0
template<class T> struct LevelSingleton {
    LevelSingleton(T* owner) { g_36ed6c0 = owner; }
};
struct SummonerIconData;
struct SummonerRegistry {
    u8 unknown00[0x1c];
    std::map<u32,SummonerIconData*> icons;
    void Register(u32 id, SummonerIconData* icon);
    SummonerIconData* Find(u32 id);
};
static_assert(offsetof(SummonerRegistry,icons)==0x1c,"native registry map offset");
extern SummonerRegistry* g_2aa7460; // VA 0x2aa7460
'''
ALLOWED={'??2@YAPAXI@Z':0x9bb8d0,'??3@YAXPAX@Z':0x9bb930,'??3@YAXPAXI@Z':0x9bb940,
 '?g_empty_string_data@@3PBDB':0x15c67f0,'??1RString@@QAE@XZ':0x9bab90,
 '??_7ILogicBoolDriver@@6B@':0x15cb058,'??0ILogicBoolDriver@@QAE@XZ':0xa21cf0,
 '??_7GDSMapObjectBannerInfo@@6B@':0x15796e0,'??_7HasReceivedAnimEmoteEventBoolDriver@@6B@':0x1579bc0,
 '??_7IsLocalPlayerBoolDriver@@6B@':0x1579be0,'??_7IsMovingBoolDriver@@6B@':0x1579c00,
 '?g_36ed6c0@@3PAUClass_bafabcc8@@A':0x316d6c0,'??_7Class_bafabcc8@@6B@':0x156d774,
 '?g_2aa7460@@3PAUSummonerRegistry@@A':0x2527460,'?Register@SummonerRegistry@@QAEXIPAUSummonerIconData@@@Z':0x63c7c0,
 '??_C@_0BB@GCADKGJO@map?1set?5too?5long@':0xfb3488,'?_Xlength_error@std@@YAXPBD@Z':0xf4375f}


def evidence(im,a,f,g):
    import gen_meta as A
    members=[]
    for event in a.followed.get(g,()):
        if event[0]!='call' or event[2]!=g or event[1]==A.META_CTOR:continue
        members.append(dict(wrapper=event[1],args=event[3],body=im.text(event[1]),
            descriptor=A.container_wrapper(im,event[1]),type=A.member_wrapper(im,event[1])))
    return json.loads(json.dumps(dict(name=a.cls[g],facts=f,members=members,
        native_helpers={hex(rva):im.text(rva) for rva in NATIVE_HELPERS},
        bodies={key:im.text(f[key]) for key in ('create','construct','destroy','destruct','v2') if f[key]})))


def layout_of(im,a,f,g):
    name=a.cls[g]
    if name not in FIELDS:return None
    rows=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    saved=next((row for row in rows if row['name']==name),None)
    if saved is None:return None
    if evidence(im,a,f,g)!=saved:raise ValueError('Placement layout evidence changed: '+name)
    return FIELDS[name]


def check(path,symbol,rva,allowed,bind=False):
    obj=M.compile_obj(str(path),M.FLAGS)
    result=M.compare(str(path),symbol,rva,M.FLAGS,obj)
    fullname,code,_=M.function_of(obj,symbol);targets=M.symbol_addresses(rva,code)
    if result[1]!=EXPECTED_SIZES[rva] or result[3] is not None or any(allowed.get(sym)!=target for sym,target in targets):
        raise ValueError(f'Placement source differs: {fullname}: {result}: {targets}')
    if bind:
        M.rebuilt_symbols().setdefault(rva,[]).append(fullname);allowed[fullname]=rva
    return dict(symbol=fullname,rva=rva,bytes=result[1],targets=targets)


def callback_definitions():
    return [f'template<> void MetaConstruct<{name}>(void* p) {{ new (p) {name}; }}' for name in RVA]+[
        'template<> void MetaVirtual2<SummonerIconData>(void* p) { auto icon=static_cast<SummonerIconData*>(p); g_2aa7460->Register(icon->iconId,icon); }']


def main():
    import copy
    import gen_sources as G,gen_meta as A
    im=G.Image();a=A.analysis(im);facts=A.class_facts(im,a)
    rows=[evidence(im,a,f,g) for g,f in facts.items() if a.cls[g] in FIELDS]
    if len(rows)!=len(FIELDS):raise ValueError('Placement classes missing')
    for row in rows:
        if row['facts']['construct']!=RVA[row['name']]:raise ValueError('Placement callback changed')
    # Prove the modified complete header before publishing its layout evidence.
    header=(GEN/'BinClasses.h').read_text()
    header=header.replace('#include "MetaPlacementSupport.h"\n','')
    support=ROOT/'client-src/obj/root_meta_placement_support.h'
    support.write_text(HEADER_SOURCE.replace('#include "ReflectedBuffers.h"',f'#include "{(GEN/"ReflectedBuffers.h").as_posix()}"'))
    header=header.replace('#include "MetaClasses.h"','#include "MetaClasses.h"\n#include "root_meta_placement_support.h"')
    for name,fields in FIELDS.items():
        pattern=r'(struct '+name+r'(?: : [^\n]+)?\n\{\n)(.*?)(\n\};)'
        def replace(match):
            declarations=[line for line in match[2].splitlines() if 'GetClass() const override;' in line]
            head=match[1]
            if name=='Class_bafabcc8':head=head.replace(' : BinObject',' : LevelSingleton<Class_bafabcc8>, BinObject')
            return head+'\n'.join([*declarations,*fields])+match[3]
        header,count=re.subn(pattern,replace,header,flags=re.S)
        if count!=1:raise ValueError('No unique placement class definition')
    header=re.sub(r'(struct ILogicBoolDriver : \w+\n\{\n)',r'\1    ILogicBoolDriver(); // rva 0xa21cf0\n',header)
    # Avoid duplicated constructor declarations on subsequent regeneration.
    header=re.sub(r'(    ILogicBoolDriver\(\);[^\n]*\n)    ILogicBoolDriver\(\);[^\n]*\n',r'\1',header)
    header=re.sub(r'^#include "([^"]+)"',lambda m:m[0] if m[1]=='root_meta_placement_support.h' else '#include "'+(GEN/m[1]).resolve().as_posix()+'"',header,flags=re.M)
    hp=ROOT/'client-src/obj/root_meta_placement_classes.h';hp.write_text(header)
    parent_probe=ROOT/'client-src/obj/root_logic_bool_ctor.cpp';parent_probe.write_text('#include "root_meta_placement_classes.h"\nILogicBoolDriver::ILogicBoolDriver() {}\n')
    registry_probe=ROOT/'client-src/obj/root_summoner_registry.cpp';registry_probe.write_text('#include "root_meta_placement_classes.h"\nvoid SummonerRegistry::Register(u32 id,SummonerIconData* icon) { icons[id]=icon; }\nSummonerIconData* SummonerRegistry::Find(u32 id) { auto p=icons.find(id); return p==icons.end()?nullptr:p->second; }\n')
    callback_probe=ROOT/'client-src/obj/root_meta_placement_callbacks.cpp';callback_probe.write_text('\n'.join(['#include "root_meta_placement_classes.h"',*callback_definitions(),'']))
    saved=copy.deepcopy(M.rebuilt_symbols());allowed=dict(ALLOWED);audit=[]
    try:
        audit.append(check(parent_probe,'??0ILogicBoolDriver@@QAE@XZ',0xa21cf0,allowed,True))
        for symbol,rva in [('_Find_lower_bound',0xf95b0),('_Insert_node',0x124b60),('_Throw_tree_length_error',0x125680),('?Register@SummonerRegistry@@',0x63c7c0)]:
            audit.append(check(registry_probe,symbol,rva,allowed,True))
        for name,rva in RVA.items():audit.append(check(callback_probe,f'??$MetaConstruct@U{name}@@@@YAXPAX@Z',rva,allowed))
        audit.append(check(callback_probe,'??$MetaVirtual2@USummonerIconData@@@@YAXPAX@Z',0x2d0d00,allowed))
    finally:M.rebuilt_symbols.v=saved
    MANIFEST.write_text(json.dumps(rows,indent=2)+'\n')
    HEADER.write_text(HEADER_SOURCE,encoding='utf-8',newline='\n')
    lines,_=A.bin_classes(im,a);(GEN/'BinClasses.h').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    # Only these generators own the new TU files; every symbol has a proved body.
    PARENT.write_text('// match: a21cf0 ??0ILogicBoolDriver@@QAE@XZ\n#include "BinClasses.h"\nILogicBoolDriver::ILogicBoolDriver() {}\n')
    registry_claims=[f'// same: {row["rva"]:x} {row["symbol"]}' for row in audit[1:4]]+[f'// match: 63c7c0 {audit[4]["symbol"]}']
    REGISTRY.write_text('\n'.join([*registry_claims,registry_probe.read_text().replace('root_meta_placement_classes.h','BinClasses.h')]))
    claimed=set()
    for path in M.sources():
        if pathlib.Path(path).resolve()==CALLBACKS.resolve():continue
        claimed.update(int(rva,16) for rva in re.findall(r'^// match: ([0-9a-f]+)',pathlib.Path(path).read_text(),re.M))
    claims=[]
    for row in audit[5:]:
        kind='same' if row['rva'] in claimed else 'match';claimed.add(row['rva'])
        claims.append(f'// {kind}: {row["rva"]:x} {row["symbol"]}')
    CALLBACKS.write_text('\n'.join([*claims,'#include "BinClasses.h"',*callback_definitions(),'']))
    M.rebuilt_symbols.__dict__.pop('v',None);final_allowed=dict(ALLOWED);final=[]
    final.append(check(PARENT,'??0ILogicBoolDriver@@QAE@XZ',0xa21cf0,final_allowed))
    for row in audit[1:5]:
        final.append(check(REGISTRY,row['symbol'],row['rva'],final_allowed));final_allowed[row['symbol']]=row['rva']
    for row in audit[5:]:final.append(check(CALLBACKS,row['symbol'],row['rva'],final_allowed))
    (ROOT/'client-src/obj/root_meta_placements_audit.json').write_text(json.dumps(final,indent=2)+'\n')
    print('Placement/native closure:',len(final),'complete bodies verified')


if __name__=='__main__':main()
