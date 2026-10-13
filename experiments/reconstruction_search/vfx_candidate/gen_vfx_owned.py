"""Isolated owned-pointer reconstruction candidate with complete native proof.

This module never edits the production pipeline, writes source under client-src,
or installs persistent symbol bindings. The metadata container tag describes
serialization; the separately compiled native destructor proves its storage.

    python experiments/reconstruction_search/vfx_candidate/gen_vfx_owned.py --probe-only

The bundle has a layout_of hook for later reviewed integration. A saved manifest
is accepted only when the current metadata, wrapper descriptors, and all native
bodies still equal the evidence from the successful candidate compilation.
"""
import argparse
import copy
import hashlib
import json
import pathlib
import sys

BUNDLE = pathlib.Path(__file__).resolve().parent
ROOT = BUNDLE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import match_func as M

MANIFEST = BUNDLE / 'vfx_owned_layouts.json'
AUDIT = BUNDLE / 'vfx_owned_audit.json'
NAMES = ('VfxProbabilityTableData', 'VfxAnimatedVector3fVariableData',
         'ValueVector3', 'FlexValueVector3', 'VfxFlexShapeDefinitionData')
DEPENDENCIES = {'FlexValueVector3': ('ValueVector3',)}
FLAGS = ['-O2', '-std:c++17']
HELPERS = (
    dict(name='VfxProbabilityOwners', rva=0xa64c90,
         symbol='??1VfxProbabilityOwners@@QAE@XZ', source='VfxProbabilityOwners.cpp',
         definition='VfxProbabilityOwners::~VfxProbabilityOwners() = default;'),
    dict(name='VfxOwnedPointer<FlexValueVector3>', rva=0xa64b00,
         symbol='??1?$VfxOwnedPointer@UFlexValueVector3@@@@QAE@XZ', source='VfxFlexPointer.cpp',
         definition='VfxOwnedPointer<FlexValueVector3>::~VfxOwnedPointer() { delete value; }'),
)
OPERATORS = {'??3@YAXPAX@Z': 0x9bb930, '??3@YAXPAXI@Z': 0x9bb940}
EXPECTED = {
    'VfxProbabilityTableData': (32, [(0, 'BinList<float>'), (12, 'BinList<float>'), (24, 'float')]),
    'VfxAnimatedVector3fVariableData': (64, [(0, 'BinList<MetaPointer<VfxProbabilityTableData>>'),
                                        (12, 'BinList<float>'), (24, 'BinList<Vector3>')]),
    'ValueVector3': (16, [(0, 'Vector3'), (12, 'MetaPointer<VfxAnimatedVector3fVariableData>')]),
    'FlexValueVector3': (20, [(0, 'u32'), (4, 'MetaEmbed<ValueVector3>')]),
    'VfxFlexShapeDefinitionData': (36, [(i * 4, 'float') for i in range(7)] +
                                 [(28, 'MetaPointer<FlexTypeFloat>'), (32, 'MetaPointer<FlexValueVector3>')]),
    'FlexTypeFloat': (8, [(0, 'u32'), (4, 'float')]),
}

HEADER_SOURCE = '''// Candidate runtime ownership; serialized tags stay in metadata.
#pragma once
#include "@META@"
#include "@BUFFERS@"
struct FlexValueVector3;
struct VfxProbabilityTableData;
template<class T> struct VfxOwnedPointer {
    T* value = nullptr;
    ~VfxOwnedPointer() { delete value; }
};
template<> struct VfxOwnedPointer<FlexValueVector3> {
    FlexValueVector3* value = nullptr;
    ~VfxOwnedPointer(); // body compiled separately, native helper 0xa64b00
};
struct VfxProbabilityOwners {
    VfxOwnedPointer<VfxProbabilityTableData> probabilityTables[3];
    ~VfxProbabilityOwners(); // defaulted separately, native helper 0xa64c90
};
struct VfxRawAllocation {
    void* data = nullptr;
    ~VfxRawAllocation() { ::operator delete(data); }
};
static_assert(sizeof(VfxOwnedPointer<FlexValueVector3>) == 4, "native pointer storage");
static_assert(sizeof(VfxProbabilityOwners) == 12, "three native owned pointers");
'''


def canonical(value):
    return json.loads(json.dumps(value))


def metadata(im, a, f, g):
    """Resolve every member; fail closed on missing, ambiguous, or extra data."""
    import gen_meta as A
    name = a.cls[g]
    if name not in EXPECTED or name not in a.unique:
        return None
    size, expected_members = EXPECTED[name]
    if f['parent'] is not None or f['poly'] or f['align'] != 4 or f['size'] != size:
        return None
    members = []
    for event in a.followed.get(g, ()):
        if event[0] != 'call' or event[2] != g or event[1] == A.META_CTOR:
            continue
        args = event[3]
        if len(args) != 3 or any(x[0] != 'imm' for x in args):
            return None
        wrapper = A.member_wrapper(im, event[1])
        descriptor = A.container_wrapper(im, event[1])
        if wrapper:
            typ = a.member_type(*wrapper[:2])
        elif descriptor:
            if descriptor['code'] != 0x80 or descriptor['slot'] != 5 or descriptor['size'] != 12:
                return None
            element, stride = descriptor['stores'].get(4), descriptor['stores'].get(8)
            if not element or not stride or element[0] != 1 or stride[0] != 4:
                return None
            element_type = a.element(element[1], stride[1], descriptor['of'])
            typ = f'BinList<{element_type}>' if element_type else None
        else:
            return None
        if typ is None:
            return None
        members.append(dict(offset=args[1][1], name=A.cpp_member_name(
            a.names.get(args[0][1]) or f'm_{args[0][1]:08x}'), hash=args[0][1],
            serialized_type=typ, wrapper=event[1], wrapper_body=im.text(event[1]),
            member_wrapper=wrapper, container_descriptor=descriptor, last=args[2][1]))
    members.sort(key=lambda x: x['offset'])
    if [(x['offset'], x['serialized_type']) for x in members] != expected_members:
        return None
    return dict(name=name, description=g, size=size, align=4, members=members)


def candidate(im, a, f, g):
    row = metadata(im, a, f, g)
    if row is None or a.cls[g] not in NAMES:
        return None
    if not f['destroy'] or not f['destruct']:
        return None
    # Creation bodies are fingerprints only, never parity claims in this module.
    row['callbacks'] = {key: f[key] for key in ('destroy', 'destruct')}
    row['callback_bodies'] = {key: im.text(rva) for key, rva in row['callbacks'].items()}
    row['creation_evidence'] = {key: dict(rva=f[key], body=im.text(f[key]) if f[key] else None)
                                for key in ('create', 'construct')}
    row['native_helpers'] = [dict(rva=item['rva'], body=im.text(item['rva']))
                             for item in HELPERS]
    row['embedded_dependencies'] = list(DEPENDENCIES.get(row['name'], ()))
    row['fields'] = fields(row)
    return canonical(row)


def fields(row):
    """Storage choice is backed by all the native destruction paths below."""
    name = row['name']
    member_names = {x['offset']: x['name'] for x in row['members']}
    def field(typ, off, init=''):
        return f'    {typ} {member_names[off]}' + (f' = {init}' if init else '') + f'; // +{off:#x}'
    if name == 'VfxProbabilityTableData':
        return [field('ReflectedBuffer<float>', 0), field('ReflectedBuffer<float>', 12),
                field('float', 24, '1.0f'), '    u16 unknown1c = 1;', '    u8 unknown1e[2];']
    if name == 'VfxAnimatedVector3fVariableData':
        return [field('VfxProbabilityOwners', 0), field('ReflectedBuffer<float>', 12),
                field('ReflectedBuffer<Vector3>', 24), '    u8 unknown24 = 0;', '    u8 unknown25;',
                '    u16 unknown26 = 0;', '    u32 unknown28 = 0;', '    u32 unknown2c = 0xffffffff;',
                '    u8 unknown30[12];', '    VfxRawAllocation unknown3c; // native cleanup frees this pointer']
    if name == 'ValueVector3':
        return [field('Vector3', 0, '{}'), field('VfxOwnedPointer<VfxAnimatedVector3fVariableData>', 12)]
    if name == 'FlexValueVector3':
        return [field('u32', 0, '0'), field('::ValueVector3', 4)]
    if name == 'VfxFlexShapeDefinitionData':
        return [field('float', i * 4, '0.0f') for i in range(7)] + [
            field('VfxOwnedPointer<FlexTypeFloat>', 28), field('VfxOwnedPointer<FlexValueVector3>', 32)]
    raise ValueError('Unsupported owned layout: ' + name)


def layout_of(im, a, f, g):
    if a.cls[g] not in NAMES or not MANIFEST.exists():
        return None
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    row = next((x for x in manifest['classes'] if x['name'] == a.cls[g]), None)
    if row is None:
        return None
    if manifest['schema'] != 1 or manifest['flags'] != FLAGS or candidate(im, a, f, g) != row:
        raise ValueError('VFX ownership evidence changed: ' + a.cls[g])
    helpers = canonical([dict(item, body=im.text(item['rva'])) for item in HELPERS])
    if manifest['helpers'] != helpers or manifest['allowed_operators'] != OPERATORS:
        raise ValueError('VFX native helper evidence changed')
    if not hasattr(im, '_vfx_candidate_dependency'):
        import gen_meta as A
        facts = A.class_facts(im, a)
        dependencies = [metadata(im, a, df, dg) for dg, df in facts.items() if a.cls[dg] == 'FlexTypeFloat']
        im._vfx_candidate_dependency = canonical(dependencies)
    if manifest['dependencies'] != im._vfx_candidate_dependency:
        raise ValueError('VFX scalar pointee evidence changed')
    return list(row['fields'])


def render_classes(rows, dependency):
    lines = ['// Isolated candidate definitions, not included by the production pipeline.',
             '#pragma once', '#include "VfxOwnedPointers.h"', '#include <cstddef>',
             'struct FlexTypeFloat { u32 mFlexID = 0; float mValue = 0; };',
             f'static_assert(sizeof(FlexTypeFloat) == {dependency["size"]}, "metadata");']
    # NAMES is also a valid order for embedded ValueVector3 in FlexValueVector3.
    for name in NAMES:
        row = next(x for x in rows if x['name'] == name)
        lines += [f'struct {name} {{', *fields(row), '};',
                  f'static_assert(sizeof({name}) == {row["size"]}, "native size");']
        lines += [f'static_assert(offsetof({name}, {m["name"]}) == {m["offset"]}, "metadata offset");'
                  for m in row['members']]
    lines.append('static_assert(offsetof(VfxAnimatedVector3fVariableData, unknown3c) == 60, "cleanup pointer");')
    return '\n'.join(lines) + '\n'


def callback_definitions(rows):
    lines = []
    for row in rows:
        name = row['name']
        lines += [f'template<> void MetaDestroy<{name}>(void* p) {{ delete static_cast<{name}*>(p); }}',
                  f'template<> void MetaDestruct<{name}>(void* p) {{ static_cast<{name}*>(p)->~{name}(); }}']
    return lines


def check(path, symbol, rva, obj, allowed):
    result = M.compare(str(path), symbol, rva, FLAGS, obj)
    full, code, _ = M.function_of(obj, symbol)
    targets = M.symbol_addresses(rva, code)
    bad = [(sym, target) for sym, target in targets if allowed.get(sym) != target]
    detail = dict(source=str(path), symbol=full, rva=rva, bytes=result[1], identical=result[2],
                  first_difference=result[3], diagnostic=result[4], targets=targets,
                  exact=result[3] is None and not bad, bad_targets=bad)
    if not detail['exact']:
        raise ValueError('Native owned lifetime mismatch: ' + json.dumps(detail))
    return detail


def verify(rows):
    """Bind helpers only after their own compiled body and every target pass."""
    saved = copy.deepcopy(M.rebuilt_symbols())
    allowed = dict(OPERATORS)
    audit = []
    try:
        for helper in HELPERS:
            path = BUNDLE / helper['source']
            obj = M.compile_obj(str(path), FLAGS)
            result = check(path, helper['symbol'], helper['rva'], obj, allowed)
            audit.append(result)
            M.rebuilt_symbols().setdefault(helper['rva'], []).append(result['symbol'])
            allowed[result['symbol']] = helper['rva']
        path = BUNDLE / 'VfxOwnedCallbacks.cpp'
        obj = M.compile_obj(str(path), FLAGS)
        for row in rows:
            for key, fn in [('destroy', 'MetaDestroy'), ('destruct', 'MetaDestruct')]:
                symbol = f'??${fn}@U{row["name"]}@@@@YAXPAX@Z'
                audit.append(check(path, symbol, row['callbacks'][key], obj, allowed))
        # Each folded callback has its own compiled body, checked independently.
        return audit
    finally:
        M.rebuilt_symbols.v = saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-only', action='store_true',
                        help='mandatory isolated mode; no production publication')
    args = parser.parse_args()
    if not args.probe_only:
        parser.error('This prototype requires --probe-only; production publication is handled separately.')
    production_sources = tuple(M.sources())
    watched = [ROOT/'tools/gen_meta.py', ROOT/'tools/gen_sources.py', ROOT/'tools/match_func.py',
               ROOT/'client-src/src/gen/BinClasses.h', ROOT/'client-src/src/gen/MetaFunctions.cpp']
    fingerprints = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}
    import gen_sources as G, gen_meta as A
    im = G.Image()
    a = A.analysis(im)
    facts = A.class_facts(im, a)
    rows = [candidate(im, a, f, g) for g, f in facts.items() if a.cls[g] in NAMES]
    if len(rows) != len(NAMES) or any(row is None for row in rows):
        raise ValueError('Owned VFX metadata missing or incompatible')
    dependency_rows = [metadata(im, a, f, g) for g, f in facts.items() if a.cls[g] == 'FlexTypeFloat']
    if len(dependency_rows) != 1 or dependency_rows[0] is None:
        raise ValueError('FlexTypeFloat must be a trivial eight-byte scalar dependency')
    dependency = canonical(dependency_rows[0])
    rows.sort(key=lambda x: NAMES.index(x['name']))
    header = HEADER_SOURCE.replace('@META@', (ROOT / 'client-src/src/Meta.h').as_posix())
    header = header.replace('@BUFFERS@', (ROOT / 'client-src/src/gen/ReflectedBuffers.h').as_posix())
    (BUNDLE / 'VfxOwnedPointers.h').write_text(header, encoding='utf-8', newline='\n')
    (BUNDLE / 'VfxOwnedClasses.h').write_text(render_classes(rows, dependency), encoding='utf-8', newline='\n')
    for helper in HELPERS:
        (BUNDLE / helper['source']).write_text('#include "VfxOwnedClasses.h"\n' + helper['definition'] + '\n',
                                               encoding='utf-8', newline='\n')
    (BUNDLE / 'VfxOwnedCallbacks.cpp').write_text('\n'.join([
        '#include "VfxOwnedClasses.h"', *callback_definitions(rows), '']), encoding='utf-8', newline='\n')
    bindings_before = copy.deepcopy(M.rebuilt_symbols())
    audit = verify(rows)
    if M.rebuilt_symbols() != bindings_before:
        raise ValueError('Prototype leaked a temporary native helper binding')
    evidence = dict(schema=1, flags=FLAGS, classes=rows, dependencies=[dependency],
                    helpers=[dict(item, body=im.text(item['rva'])) for item in HELPERS],
                    allowed_operators=OPERATORS)
    # Only successful complete candidates become available to layout_of.
    MANIFEST.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    for g, f in facts.items():
        if a.cls[g] in NAMES and layout_of(im, a, f, g) != next(x['fields'] for x in rows if x['name'] == a.cls[g]):
            raise ValueError('Round-trip layout evidence failed')
    if tuple(M.sources()) != production_sources:
        raise ValueError('Prototype changed production source discovery')
    if {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched} != fingerprints:
        raise ValueError('Production baseline changed during isolated proof; retry on a stable baseline')
    AUDIT.write_text(json.dumps(dict(schema=1, checks=audit, functions=len(audit),
                                   bytes=sum(x['bytes'] for x in audit),
                                   isolation=dict(sources_unchanged=True, watched_files=fingerprints,
                                                  persistent_bindings=False)), indent=2) + '\n', encoding='utf-8')
    print(f'Isolated VFX candidate: {len(rows)} types, {len(audit)}/{len(audit)} exact bodies, '
          f'{sum(x["bytes"] for x in audit)} bytes; no production edits or persistent aliases.')


if __name__ == '__main__':
    main()
