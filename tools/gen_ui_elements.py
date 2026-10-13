"""Native UI data ownership and constructors, with complete body/target gates.

The current BinObject virtual interface is incomplete. These proofs cover the
listed function bodies, not every slot or byte of the client vtables.
"""
import copy
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import match_func as M

GEN = ROOT / 'client-src/src/gen'
MANIFEST = ROOT / 'tools/ui_element_layouts.json'
HEADER = GEN / 'UiElementOwners.h'
EXPECTED = {
    'AnchorBase': (4, None, []),
    'AnchorSingle': (12, 'AnchorBase', [(4, 'Vector2')]),
    'UiPositionBase': (4, None, []),
    'UiPositionRect': (32, 'UiPositionBase', [(4,'Vector4'),(20,'u16'),(22,'u16'),(24, 'MetaPointer<AnchorBase>'), (28, 'bool'), (29, 'bool'), (30, 'bool'), (31, 'bool')]),
    'UiElementIData': (20, None, [(4, 'MetaString'), (16, 'MetaLink<Class_aae83c5b>')]),
    'UiElementData': (36, 'UiElementIData', [(20, 'bool'), (21, 'bool'), (22,'bool'),(24,'u32'),(28, 'u32'), (32, 'MetaPointer<UiPositionBase>')]),
    'UIElementI': (44, None, []),
    'UIElement': (128, 'UIElementI', []),
    'UiElementAsset': (184, 'UIElement', []),
}
CONSTRUCTORS = {'UiPositionRect': 0xae0ac0, 'UiElementData': 0xadfd20, 'UIElement':0xadfb60, 'UiElementAsset':0xadfc40}
PLACEMENTS = {
    'Class_c27090c2':(0xadc380,0xadef80,72), 'Class_720bb1aa':(0xadc4d0,0xadefe0,76),
    'Class_9b78684f':(0xadc350,0xadf040,72), 'Class_f395015b':(0xadc8e0,0xadf0a0,72),
    'Class_be3f7ef7':(0xadc210,0xadf100,72), 'Class_81990a5e':(0xadc300,0xadf160,76),
    'Class_f6fd1c96':(0xadc940,0xadf1c0,76), 'Class_0d221f07':(0xadc500,0xadf280,72),
    'Class_ee4da73f':(0xadc490,0xadf2e0,72), 'Class_acf7065b':(0xadc860,0xadf340,84),
    'Class_5e46619e':(0xadc830,0xadf3b0,80), 'Class_a82317ef':(0xadc560,0xadf420,72),
    'UiElementEffect':(0xadc970,0xadfd90,216),
}
GLOBALS = {0x3195f68: 4, 0x3195f6c: 4, 0x3195f7c: 16}
ALLOWED = {
    '??2@YAPAXI@Z': 0x9bb8d0, '??3@YAXPAXI@Z': 0x9bb940,
    '??1RString@@QAE@XZ': 0x9bab90, '??_7BinObject@@6B@': 0xfb3474,
    '?g_empty_string_data@@3PBDB': 0x15c67f0,
    '??_7AnchorSingle@@6B@': 0x15d12e8, '??_7UiPositionRect@@6B@': 0x15d1320,
    '??_7UiElementIData@@6B@': 0x15d12dc, '??_7UiElementData@@6B@': 0x15d1340,
    '?g_UiAnchorX@@3MB': 0x3195f68, '?g_UiAnchorY@@3MB': 0x3195f6c,
    '?g_UiDefaultRect@@3UVector4@@B': 0x3195f7c,
    '?AnchorSingle_Meta@@3UAnchorSingle_MetaClass@@A': 0x31a4bf8,
    '?UiPositionRect_Meta@@3UUiPositionRect_MetaClass@@A': 0x31a4580,
    '?UiElementIData_Meta@@3UUiElementIData_MetaClass@@A': 0x31a4ab8,
    '?UiElementData_Meta@@3UUiElementData_MetaClass@@A': 0x31a4788,
    '??_7UIElementI@@6B@':0x15d1108, '??_7UIElement@@6B@':0x15d1418, '??_7UiElementAsset@@6B@':0x15d14b8,
    '?g_UiAssetDefaultVector@@3UVector4@@B':0x3195f7c,
    '?g_UiAssetDefaultLow@@3MB':0x3195f68, '?g_UiAssetDefaultHigh@@3MB':0x3195f6c,
    '?Release@UiAssetReference@@QAEIXZ':0xaaa4c0,
    '?UIElementI_Meta@@3UUIElementI_MetaClass@@A':0x31a38e8,
    '?UIElement_Meta@@3UUIElement_MetaClass@@A':0x31a43a0,
    '?UiElementAsset_Meta@@3UUiElementAsset_MetaClass@@A':0x31a39d8,
}
ALLOWED.update({'??0'+name+'@@QAE@XZ':rva for name,(_,rva,_) in PLACEMENTS.items()})
SUPPORT = '''// UI native owners; serialized pointer/link tags are described separately.
#pragma once
#include "MetaClasses.h"
#include <cfloat>
extern const Vector4 g_UiDefaultRect;
extern const float g_UiAnchorX, g_UiAnchorY;
template<class T> struct UiDataOwner {
    T* value;
    UiDataOwner(T* p = nullptr) : value(p) {}
    ~UiDataOwner() { delete value; }
};
struct UiSceneLink {
    u32 value = 0;
    ~UiSceneLink() { value = 0; }
};
struct UiAllocation12 { u32 words[3]; };
struct UiAllocationOwner12 {
    UiAllocation12* value = nullptr;
    ~UiAllocationOwner12() { ::operator delete(value, sizeof(UiAllocation12)); }
};
// External ABI, inspected at aaa4c0; its complete body remains unreconstructed.
struct UiAssetReference { u32 Release(); };
struct UiNullableAssetReference {
    UiAssetReference* value = nullptr;
    ~UiNullableAssetReference() { if(value) value->Release(); }
};
extern const Vector4 g_UiAssetDefaultVector;
extern const float g_UiAssetDefaultLow, g_UiAssetDefaultHigh;
static_assert(sizeof(UiAllocation12)==12);
static_assert(sizeof(UiAllocationOwner12)==4);
static_assert(sizeof(UiNullableAssetReference)==4);
'''
GROUPS = [
    ('UiPositionRectCtor.cpp', '''UiPositionRect::UiPositionRect() = default;
template<> void MetaConstruct<AnchorSingle>(void* p) { new(p) AnchorSingle; }
const MetaClass* AnchorSingle::GetClass() const { return &AnchorSingle_Meta; }
const MetaClass* UiPositionRect::GetClass() const { return &UiPositionRect_Meta; }
''', [
        ('??0UiPositionRect@@QAE@XZ', 0xae0ac0, 111),
        ('??$MetaConstruct@UAnchorSingle@@@@YAXPAX@Z', 0xadb850, 37),
        ('??_GAnchorSingle@@UAEPAXI@Z', 0x109480, 33),
        ('??_GUiPositionRect@@UAEPAXI@Z', 0xae38e0, 46),
        ('?GetClass@AnchorSingle@@UBEPBUMetaClass@@XZ', 0xaed8f0, 6),
        ('?GetClass@UiPositionRect@@UBEPBUMetaClass@@XZ', 0xaedbd0, 6)]),
    ('UiElementDataCtor.cpp', '''UiElementData::UiElementData() = default;
const MetaClass* UiElementIData::GetClass() const { return &UiElementIData_Meta; }
const MetaClass* UiElementData::GetClass() const { return &UiElementData_Meta; }
''', [
        ('??0UiElementData@@QAE@XZ', 0xadfd20, 107),
        ('??_GUiElementIData@@UAEPAXI@Z', 0xae3530, 48),
        ('??_GUiElementData@@UAEPAXI@Z', 0xae2b30, 61),
        ('?GetClass@UiElementIData@@UBEPBUMetaClass@@XZ', 0xaed850, 6),
        ('?GetClass@UiElementData@@UBEPBUMetaClass@@XZ', 0xaed7d0, 6)]),
    ('UiPositionCallbacks.cpp', '''template<> void* MetaCreate<UiPositionRect>() { return new UiPositionRect; }
template<> void MetaConstruct<UiPositionRect>(void* p) { new(p) UiPositionRect; }
template<> void* MetaCreate<AnchorSingle>() { return new AnchorSingle; }
template<> void MetaDestroy<UiPositionRect>(void* p) { delete static_cast<UiPositionRect*>(p); }
template<> void MetaDestruct<UiPositionRect>(void* p) { static_cast<UiPositionRect*>(p)->~UiPositionRect(); }
template<> void MetaDestroy<AnchorSingle>(void* p) { delete static_cast<AnchorSingle*>(p); }
template<> void MetaDestruct<AnchorSingle>(void* p) { static_cast<AnchorSingle*>(p)->~AnchorSingle(); }
''', [
        ('??$MetaCreate@UUiPositionRect@@@@YAPAXXZ', 0xadc0b0, 24),
        ('??$MetaConstruct@UUiPositionRect@@@@YAXPAX@Z', 0xadc120, 9),
        ('??$MetaCreate@UAnchorSingle@@@@YAPAXXZ', 0xadd220, 50),
        ('??$MetaDestroy@UUiPositionRect@@@@YAXPAX@Z', 0xf1270, 15),
        ('??$MetaDestruct@UUiPositionRect@@@@YAXPAX@Z', 0xf12a0, 11),
        ('??$MetaDestroy@UAnchorSingle@@@@YAXPAX@Z', 0xf1270, 15),
        ('??$MetaDestruct@UAnchorSingle@@@@YAXPAX@Z', 0xf12a0, 11)]),
    ('UIElementCtor.cpp', '''UIElement::UIElement() = default;
const MetaClass* UIElementI::GetClass() const { return &UIElementI_Meta; }
const MetaClass* UIElement::GetClass() const { return &UIElement_Meta; }
''', [('??0UIElement@@QAE@XZ',0xadfb60,220),
      ('??_GUIElementI@@UAEPAXI@Z',0xae34f0,49),
      ('?GetClass@UIElementI@@UBEPBUMetaClass@@XZ',0xaedb50,6),
      ('?GetClass@UIElement@@UBEPBUMetaClass@@XZ',0xaed7b0,6)]),
    ('UiElementAssetCtor.cpp', '''UiElementAsset::UiElementAsset() {
    unknown84=false;
    unknown98=g_UiAssetDefaultVector;
    unknowna8=g_UiAssetDefaultLow;
    unknownac=g_UiAssetDefaultHigh;
    unknownb0=g_UiAssetDefaultLow;
    unknownb4=g_UiAssetDefaultHigh;
}
const MetaClass* UiElementAsset::GetClass() const { return &UiElementAsset_Meta; }
''', [('??0UiElementAsset@@QAE@XZ',0xadfc40,153),
      ('?GetClass@UiElementAsset@@UBEPBUMetaClass@@XZ',0xaedac0,6)]),
    ('UiElementLifetimes.cpp', '''UIElement::~UIElement() = default;
UiElementAsset::~UiElementAsset() = default;
''', [('??_GUIElement@@UAEPAXI@Z',0xae2da0,71),('??_GUiElementAsset@@UAEPAXI@Z',0xae2df0,92)]),
]
GROUPS.append(('UiElementPlacements.cpp',
    '\n'.join(f'template<> void MetaConstruct<{name}>(void* p) {{ new(p) {name}; }}' for name in PLACEMENTS)+'\n',
    [(f'??$MetaConstruct@U{name}@@@@YAXPAX@Z',rva,9) for name,(rva,_,_) in PLACEMENTS.items()]))


def placement_metadata(im,a,f,g):
    import gen_meta as A
    name=a.cls[g]
    wrapper,ctor,size=PLACEMENTS[name]
    parent='UiElementAsset' if name=='UiElementEffect' else 'Class_a34b6ba4'
    if name not in a.unique or f['size']!=size or f['align']!=4 or not f['poly'] or a.cls[f['parent']]!=parent or f['construct']!=wrapper or A.out_of_line(im,wrapper)!=('jump',None,ctor):
        raise ValueError('UI placement metadata/constructor changed: '+name)
    events=a.followed.get(g,())
    return json.loads(json.dumps(dict(name=name,facts=f,events=events,
        event_bodies={str(event[1]):im.text(event[1]) for event in events if event[0]=='call'},
        constructor=im.text(ctor),placement=im.text(wrapper))))


def metadata(im, a, f, g):
    import gen_meta as A
    name = a.cls[g]
    size, parent, expected = EXPECTED[name]
    if name not in a.unique or not f['poly'] or f['align'] != 4 or f['size'] != size or (a.cls[f['parent']] if f['parent'] else None) != parent:
        raise ValueError('UI metadata size/base changed: ' + name)
    members = []
    for event in a.followed.get(g, ()):
        if event[0] != 'call' or event[2] != g or event[1] == A.META_CTOR:
            continue
        args = event[3]
        wrapper = A.member_wrapper(im, event[1])
        if not wrapper or len(args) != 3 or any(x[0] != 'imm' for x in args):
            raise ValueError('UI member wrapper changed: ' + name)
        members.append(dict(offset=args[1][1], name=A.cpp_member_name(a.names.get(args[0][1]) or f'm_{args[0][1]:08x}'),
                            type=a.member_type(*wrapper[:2]), wrapper=event[1], args=args, body=im.text(event[1])))
    members.sort(key=lambda x: x['offset'])
    if [(m['offset'], m['type']) for m in members] != expected:
        raise ValueError('UI reflected members changed: ' + name)
    ctor = CONSTRUCTORS.get(name)
    return json.loads(json.dumps(dict(name=name, facts=f, members=members,
        callbacks={key: im.text(f[key]) if f[key] else None for key in ('create', 'construct', 'destroy', 'destruct', 'v2')},
        constructor=im.text(ctor) if ctor else None,
        release=im.text(0xaaa4c0),
        globals={hex(rva): bytes(im.img[rva:rva+length]).hex() for rva, length in GLOBALS.items()})))


def fields(row):
    names = {m['offset']: m['name'] for m in row['members']}
    def field(typ, offset, init=''):
        return f'    {typ} {names[offset]}' + init + f'; // +{offset:#x}'
    name = row['name']
    if name in ('AnchorBase', 'UiPositionBase'):
        return []
    if name == 'AnchorSingle':
        return [field('::Vector2', 4, '{g_UiAnchorX, g_UiAnchorY}')]
    if name == 'UiPositionRect':
        return [field('::Vector4',4,' = g_UiDefaultRect'),field('u16',20,' = 0'),field('u16',22,' = 0'),
                field('UiDataOwner<AnchorBase>', 24, '{new AnchorSingle()}')] + [field('bool', off, ' = false') for off in range(28, 32)]
    if name == 'UiElementIData':
        return [field('::MetaString', 4), field('UiSceneLink', 16)]
    if name == 'UiElementData':
        return [field('bool', 20, ' = false'), field('bool', 21, ' = false'),field('bool',22,' = false'),
                field('u32',24,' = 0'), field('u32', 28, ' = 0'), field('UiDataOwner<UiPositionBase>', 32, '{new UiPositionRect}')]
    if name == 'UIElementI':
        return ['    ~UIElementI() override = default;',
                '    ::MetaString name; // +0x4', '    u32 unknown10=0, unknown14=0;',
                '    ::MetaString secondName; // +0x18', '    u32 unknown24=0, unknown28=0;']
    if name == 'UIElement':
        return ['    ~UIElement() override;', '    int unknown2c=-1;', '    UiAllocationOwner12 unknown30;',
                '    u32 unknown34=0, unknown38=0;', '    float unknown3c=FLT_MAX, unknown40, unknown44=FLT_MAX, unknown48;',
                '    u32 unknown4c=0, unknown50=0, unknown54=0, unknown58=0, unknown5c=0, unknown60=0;',
                '    float unknown64=1, unknown68=1, unknown6c=1, unknown70=1, unknown74=1;',
                '    u32 flags78=0x3000400;', '    int unknown7c=-1;']
    if name == 'UiElementAsset':
        return ['    ~UiElementAsset() override;', '    UiNullableAssetReference unknown80;',
                '    bool unknown84;', '    u8 pad85[3];', '    u32 unknown88=0, unknown8c=0;',
                '    float unknown90=1, unknown94=1;', '    ::Vector4 unknown98;', '    float unknowna8, unknownac, unknownb0, unknownb4;']
    raise ValueError('UI layout unsupported')


def layout_of(im, a, f, g):
    if a.cls[g] not in EXPECTED or not MANIFEST.exists():
        return None
    saved = json.loads(MANIFEST.read_text(encoding='utf-8'))
    row = next(r for r in saved if r['name'] == a.cls[g])
    if metadata(im, a, f, g) != row:
        raise ValueError('UI native evidence changed: ' + a.cls[g])
    return fields(row)


def verify(paths):
    allowed = dict(ALLOWED)
    saved = copy.deepcopy(M.rebuilt_symbols())
    rows = []
    try:
        for path, (_, _, checks) in zip(paths, GROUPS):
            obj = M.compile_obj(str(path), M.FLAGS)
            for symbol, rva, size in checks:
                result = M.compare(str(path), symbol, rva, M.FLAGS, obj)
                full, code, _ = M.function_of(obj, symbol)
                targets = M.symbol_addresses(rva, code)
                if result[3] is not None or result[1] != size or any(allowed.get(sym) != target for sym, target in targets):
                    raise ValueError(f'UI complete body/target mismatch: {full}: {result}: {targets}')
                rows.append(dict(source=path.name, symbol=full, rva=rva, bytes=size, targets=targets))
                M.rebuilt_symbols().setdefault(rva, []).append(full)
                allowed[full] = rva
    finally:
        M.rebuilt_symbols.v = saved
    return rows


def main():
    import gen_sources as G
    import gen_meta as A
    im = G.Image()
    a = A.analysis(im)
    rows = [metadata(im, a, f, g) for g, f in A.class_facts(im, a).items() if a.cls[g] in EXPECTED]
    if len(rows) != len(EXPECTED) or any(any(value != '00' * GLOBALS[int(key, 16)] for key, value in row['globals'].items()) for row in rows):
        raise ValueError('UI metadata/default globals missing or changed')
    placement_rows=[placement_metadata(im,a,f,g) for g,f in A.class_facts(im,a).items() if a.cls[g] in PLACEMENTS]
    if len(placement_rows)!=len(PLACEMENTS):raise ValueError('UI placements missing')
    probe_header = ROOT / 'client-src/obj/root_ui_elements.h'
    lines = [SUPPORT.replace('#include "MetaClasses.h"', '#include "' + (GEN / 'MetaClasses.h').as_posix() + '"')]
    for name, (_, parent, _) in EXPECTED.items():
        row = next(r for r in rows if r['name'] == name)
        lines += ['struct ' + name + ' : ' + (parent or 'BinObject') + ' {',
                  '    const MetaClass* GetClass() const override;']
        if name in CONSTRUCTORS:
            lines.append('    ' + name + '();')
        lines += fields(row) + ['};']
    production_header=(GEN/'BinClasses.h').read_text(encoding='utf-8')
    for name in ('UiElementAssetData','Class_a34b6ba4',*PLACEMENTS):
        definition=re.search(r'^struct '+name+r'(?: : \w+)?\n\{\n.*?^\};',production_header,re.M|re.S)
        if not definition:raise ValueError('UI derived definition missing: '+name)
        lines.append(definition[0])
    probe_header.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    paths = []
    for filename, body, _ in GROUPS:
        path = ROOT / 'client-src/obj' / ('root_probe_' + filename)
        path.write_text('#include "' + probe_header.name + '"\n' + body, encoding='utf-8')
        paths.append(path)
    verify(paths)
    HEADER.write_text(SUPPORT, encoding='utf-8', newline='\n')
    MANIFEST.write_text(json.dumps(rows+placement_rows, indent=2) + '\n', encoding='utf-8')
    lines, _ = A.bin_classes(im, a)
    (GEN / 'BinClasses.h').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    claimed = set()
    for source in M.sources():
        if pathlib.Path(source).name in {g[0] for g in GROUPS}:
            continue
        claimed.update(int(x, 16) for x in re.findall(r'^// match: ([0-9a-f]+)', pathlib.Path(source).read_text(encoding='utf-8'), re.M))
    paths = []
    for filename, body, checks in GROUPS:
        claims = []
        for symbol, rva, _ in checks:
            kind = 'same' if rva in claimed else 'match'
            claimed.add(rva)
            claims.append(f'// {kind}: {rva:x} {symbol}')
        path = GEN / filename
        path.write_text('\n'.join(claims) + '\n#include "BinClasses.h"\n' + body, encoding='utf-8', newline='\n')
        paths.append(path)
    M.rebuilt_symbols.__dict__.pop('v', None)
    audit = verify(paths)
    (ROOT / 'client-src/obj/root_ui_elements_audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    print('UI data:', len(audit), 'complete bodies,', sum(row['bytes'] for row in audit), 'bytes verified')


if __name__ == '__main__':
    main()
