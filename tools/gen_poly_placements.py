"""Placement callbacks (MetaConstruct<K>) of described classes that only store constants: the class layout is
derived from what the callback writes plus the reflected members, compiled as `new (p) K` and compared with the
client. Reflected plain members keep their name and type; everything else the callback writes is a placeholder
of the width of the store (unknownXX), so a layout says only what the client's code shows.

  gen_poly_placements.py probe [class ...]   -> client-src/obj/poly_placements_probe.cpp + .json (nothing published)
  gen_poly_placements.py write               -> tools/poly_placement_layouts.json: the layouts the probe proved
  gen_poly_placements.py publish             -> client-src/src/gen/PolyPlacementCallbacks.cpp, after BinClasses.h
                                                was written again with those layouts (gen_sources.py BinClasses.h)

The probe compiles stand-in classes P_<K> next to the generated BinClasses.h; it does not claim anything. A layout
enters the manifest only for a polymorphic class without described children and without a constructor of its own
in the client, whose stand-in gave the client's bytes. gen_meta.bin_classes takes the member lines from the manifest
(layout_of) and gen_small leaves the callbacks to the typed functions (owners).
"""
import bisect
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import packet_emu as P  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

GEN = os.path.join(ROOT, 'client-src', 'src', 'gen')
MANIFEST = os.path.join(HERE, 'poly_placement_layouts.json')
CALLBACKS = os.path.join(GEN, 'PolyPlacementCallbacks.cpp')
HEADER = os.path.join(GEN, 'PolyPlacementGlobals.h')
NL = chr(10)
META_CTOR = 0x9b9a60
EMPTY_STRING = 0x1b467f0            # VA of the pointer every empty RString starts with
RDATA = (0xfab000, 0x1752000)       # rva range of .rdata
# reflected plain types: size, alignment
PLAIN = {'bool': (1, 1), 'u8': (1, 1), 'i8': (1, 1), 'u16': (2, 2), 'short': (2, 2), 'int': (4, 4), 'u32': (4, 4),
         'float': (4, 4), 'u64': (8, 8), 'Vector2': (8, 4), 'Vector3': (12, 4), 'Vector4': (16, 4), 'Color': (4, 1),
         'HashValue': (4, 4), 'FileLink': (8, 8), 'MetaString': (12, 4)}
FLOATS = {'float': 1, 'Vector2': 2, 'Vector3': 3, 'Vector4': 4}


def classes():
    """name -> dict(size, parent, members [(offset, type, name)], init rva) from the generated MetaClasses.cpp."""
    text = open(os.path.join(GEN, 'MetaClasses.cpp'), encoding='utf-8').read()
    init = {m[2]: int(m[1], 16) for m in re.finditer(r'^// match: ([0-9a-f]+) \?\?__E(\w+)_Meta@@YAXXZ', text, re.M)}
    out = {}
    for m in re.finditer(r'^inline (\w+)_MetaClass::\1_MetaClass\(\)\n(.*?)^\}', text, re.M | re.S):
        name, body = m[1], m[2]
        head = re.search(r'(0x[0-9a-f]+), (0x[0-9a-f]+), (?:true|false), (?:true|false)\)', body)
        parent = re.search(r'parent = (?:&(\w+)_Meta|MetaStaticClass<(\w+)>\(\));', body)
        members = []
        for x in re.finditer(r'AddMember<(.+)>\((?:HASH\("(\w+)"\)|0x([0-9a-f]+)u?), (0x[0-9a-f]+), ', body):
            members.append((int(x[4], 16), x[1], x[2] or 'm_' + x[3]))
        if head:
            out[name] = dict(size=int(head[1], 16), align=int(head[2], 16), init=init.get(name),
                             parent=parent and (parent[1] or parent[2]), members=sorted(members))
    return out


def construct_of(init, starts, md):
    """rva of the placement callback a description's initializer passes to the description constructor."""
    if init is None:
        return None
    pushes = []
    for i in md.disasm(bytes(P.IMG[init:init + 96]), P.BASE + init):
        if i.mnemonic == 'push':
            pushes.append(int(i.op_str, 16) if i.op_str.startswith('0x') or i.op_str.isdigit() else None)
        elif i.mnemonic == 'call':
            if int(i.op_str, 16) - P.BASE != META_CTOR or len(pushes) != 10 or not pushes[6]:
                return None
            return pushes[6] - P.BASE
        elif i.mnemonic != 'mov':
            return None
    return None


def stores_of(rva, starts, md):
    """What a call-free placement callback writes: [(offset, size, ('imm', bytes) | ('global', va))] in the
    client's order, or a string saying why the function is not of that form."""
    end = starts[bisect.bisect_right(starts, rva)]
    this, held, out = None, {}, []
    for i in md.disasm(bytes(P.IMG[rva:end]), P.BASE + rva):
        t = f'{i.mnemonic} {i.op_str}'
        if i.mnemonic in ('int3', 'nop'):
            continue
        if t == 'ret ':
            return out
        m = re.fullmatch(r'mov (e\w\w), dword ptr \[esp \+ 4\]', t)
        if m and this is None:
            this = m[1]
            continue
        if this is None:
            return 'no this'
        at = rf'\[{this}(?: \+ (0x[0-9a-f]+|\d+))?\]'
        m = re.fullmatch(rf'mov (byte|word|dword) ptr {at}, (0x[0-9a-f]+|\d+)', t)
        if m:
            n = {'byte': 1, 'word': 2, 'dword': 4}[m[1]]
            out.append((int(m[2] or '0', 0), n, ('imm', int(m[3], 0).to_bytes(n, 'little'))))
            continue
        m = re.fullmatch(r'mov (e\w\w), dword ptr \[(0x[0-9a-f]+)\]', t)
        if m and m[1] != this:
            held[m[1]] = ('global', int(m[2], 16))
            continue
        m = re.fullmatch(rf'mov dword ptr {at}, (e\w\w)', t)
        if m and m[2] in held:
            out.append((int(m[1] or '0', 0), 4, held[m[2]]))
            continue
        if t == 'xorps xmm0, xmm0':
            held['xmm0'] = ('imm', bytes(16))
            continue
        m = re.fullmatch(r'mov(ss|ups|aps|q|sd) xmm(\d), (?:dword|xmmword|qword) ptr \[(0x[0-9a-f]+)\]', t)
        if m:
            n = {'ss': 4, 'ups': 16, 'aps': 16, 'q': 8, 'sd': 8}[m[1]]
            a = int(m[3], 16) - P.BASE
            if not RDATA[0] <= a < RDATA[1]:
                return 'vector from a variable'
            held['xmm' + m[2]] = ('imm', bytes(P.IMG[a:a + n]))
            continue
        m = re.fullmatch(rf'mov(ss|ups|q|lpd|sd) (?:dword|xmmword|qword) ptr {at}, xmm(\d)', t)
        if m and 'xmm' + m[3] in held:
            n = {'ss': 4, 'ups': 16, 'q': 8, 'lpd': 8, 'sd': 8}[m[1]]
            out.append((int(m[2] or '0', 0), n, ('imm', held['xmm' + m[3]][1][:n])))
            continue
        return 'unsupported: ' + t
    return 'no end'


def is_table(off, n, what):
    """A store of a pointer into .rdata at offset 0: the vtable pointer (a float such as 1.0f is far above the image)."""
    if off or n != 4 or what[0] != 'imm':
        return False
    return RDATA[0] <= int.from_bytes(what[1], 'little') - P.BASE < RDATA[1]


def fl(b):
    x = struct.unpack('<f', b)[0]
    if x != x or x in (float('inf'), float('-inf')):
        return None
    for p in range(1, 10):
        s = f'{x:.{p}g}'
        if struct.pack('<f', float(s)) == b:
            break
    return (s if ('.' in s or 'e' in s) else s + '.0') + 'f'


def literal(typ, raw):
    v = int.from_bytes(raw, 'little')
    if typ == 'bool':
        return ('true' if v == 1 else 'false') if v < 2 else None
    if typ in ('int', 'short', 'i8'):
        return str(int.from_bytes(raw, 'little', signed=True))
    if typ in ('u8', 'u16', 'u32', 'u64'):
        return str(v) if v < 10 else f'{v:#x}'
    if typ == 'HashValue':
        return f'{{{v:#x}}}'
    if typ in FLOATS:
        parts = [fl(raw[i:i + 4]) for i in range(0, len(raw), 4)]
        if None in parts:
            return None
        return parts[0] if typ == 'float' else '{' + ', '.join(parts) + '}'
    if typ == 'Color':
        return '{' + ', '.join(str(b) for b in raw) + '}'
    return None


def layout(cls, name, stores):
    """Member lines of class `name` from its stores, or a string saying what stops it. The vtable store is left to
    the compiler; stores below the class's own start belong to its base and are not described here."""
    c = cls[name]
    base = cls[c['parent']]['size'] if c['parent'] else 4
    if c['parent'] and c['parent'] not in cls:
        return 'base without a description'
    written = {}                    # offset -> (size, what) of each store
    for off, n, what in stores:
        if is_table(off, n, what):
            continue
        for j in range(off, off + n):
            if any(o <= j < o + s for o, (s, _) in written.items()):
                return 'a byte written twice'
        written[off] = (n, what)
    if any(off < base for off in written):
        return 'stores into the base'
    lines, externs, pos = [], set(), base
    todo = sorted(written)

    def take(off, n):
        """bytes [off, off+n) as immediate bytes when stores cover them exactly, else None; consumes the stores."""
        raw, j = b'', off
        while j < off + n:
            if j not in written or written[j][1][0] != 'imm' or j + written[j][0] > off + n:
                return None
            raw += written[j][1][1]
            j += written[j][0]
        j = off
        while j < off + n:
            todo.remove(j)
            j += written[j][0]
        return raw

    def gap(to):
        nonlocal pos
        while todo and todo[0] < to:
            off = todo.pop(0)
            n, what = written[off]
            if off + n > to:
                return False
            if off < pos:
                return False
            align = min(n, 4)
            if off != (pos + align - 1) // align * align:
                lines.append(f'    u8 unused{pos:02x}[{off - pos:#x}];')
            t = {1: 'u8', 2: 'u16', 4: 'u32', 8: 'u64'}.get(n)
            if what[0] == 'global':
                if what[1] == EMPTY_STRING:
                    return False            # a string nothing reflects: its type is not known
                externs.add(what[1])
                lines.append(f'    u32 unknown{off:02x} = g_{what[1]:x};')
            elif t and n < 8:
                v = int.from_bytes(what[1], 'little')
                lines.append(f'    {t} unknown{off:02x} = {v if v < 10 else hex(v)};')
            elif not any(what[1]):
                lines.append(f'    u32 unknown{off:02x}[{n // 4}] = {{}};')
            else:
                parts = [fl(what[1][i:i + 4]) for i in range(0, n, 4)]
                if None in parts:
                    return False
                lines.append(f'    float unknown{off:02x}[{n // 4}] = {{{", ".join(parts)}}};')
            pos = off + n
        return True

    for off, typ, member in c['members']:
        if off < base:
            continue                # reflected by this class, stored in its base (seen in UI classes)
        if typ not in PLAIN:
            continue                # containers, pointers, links: only what the callback writes there is described
        size, align = PLAIN[typ]
        if not gap(off):
            return 'unreflected stores do not tile'
        if off < pos:
            return 'members overlap'
        if off != (pos + align - 1) // align * align:
            lines.append(f'    u8 unused{pos:02x}[{off - pos:#x}];')
        if typ == 'MetaString':
            w = [written.get(off + j) for j in (0, 4, 8)]
            if w[0] != (4, ('global', EMPTY_STRING)) or w[1] != (4, ('imm', bytes(4))) or w[2] != (4, ('imm', bytes(4))):
                return 'string member not initialised as an empty string'
            for j in (0, 4, 8):
                todo.remove(off + j)
            lines.append(f'    MetaString {member};')
        elif off in written and written[off][1][0] == 'global' and typ in ('HashValue', 'u32', 'int'):
            todo.remove(off)
            externs.add(written[off][1][1])
            init = f'{{(u32)g_{written[off][1][1]:x}}}' if typ == 'HashValue' else f' = g_{written[off][1][1]:x}'
            lines.append(f'    {typ} {member}{init};')
        else:
            raw = take(off, size) if off in written else None
            if raw is None and any(off <= j < off + size for j in written if j in todo):
                return 'member partly written'
            init = literal(typ, raw) if raw is not None else None
            if raw is not None and init is None:
                return 'no literal for ' + typ
            lines.append(f'    {typ} {member}' + ('' if init is None else (init if init[0] == '{' else ' = ' + init)) + ';')
        pos = off + size
    if not gap(c['size']):
        return 'unreflected stores do not tile'
    return lines, sorted(externs)


def blocked(cls, starts, md):
    """(class, construct rva, why it is open) for descriptions whose placement callback is not rebuilt under its
    own name: lifted generically by gen_small, or not rebuilt at all."""
    rebuilt = M.rebuilt_symbols()
    for name, c in sorted(cls.items()):
        rva = construct_of(c['init'], starts, md)
        if rva is None:
            continue
        own = f'??$MetaConstruct@U{name}@@@@'
        symbols = rebuilt.get(rva, [])
        if any(s.startswith('??$MetaConstruct@') or s.startswith('??0') for s in symbols):
            continue                # typed already (possibly folded with another class's callback)
        yield name, rva, 'generic' if symbols else 'not rebuilt', own


def probe(only):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    starts = sorted(M.starts())
    cls = classes()
    src = ['// Stand-in classes for the placement callbacks of described classes (tools/gen_poly_placements.py probe).',
           '#include "../src/gen/BinClasses.h"', '#include <new>']
    rows, externs, units = [], set(), []
    for name, rva, state, own in blocked(cls, starts, md):
        if only and name not in only:
            continue
        row = dict(name=name, rva=hex(rva), state=state)
        rows.append(row)
        stores = stores_of(rva, starts, md)
        if isinstance(stores, str):
            row['result'] = stores
            continue
        if not any(is_table(off, n, w) for off, n, w in stores):
            row['result'] = 'no vtable store'
            continue
        made = layout(cls, name, stores)
        if isinstance(made, str):
            row['result'] = made
            continue
        lines, ext = made
        externs |= set(ext)
        c = cls[name]
        base = c['parent'] or 'BinObject'
        units.append((row, [f'struct P_{name} : {base}', '{', '    const MetaClass* GetClass() const override;'] +
                      lines + ['};', f'static_assert(sizeof(P_{name}) == {c["size"]:#x});',
                               f'void Construct_{name}(void* p) {{ new (p) P_{name}; }}', '']))
        row['layout'] = lines
    src += [f'extern int g_{va:x};' for va in sorted(externs)] + ['']
    for row, text in units:
        src += text
    path = os.path.join(M.OUT, 'poly_placements_probe.cpp')
    with open(path, 'w', encoding='utf-8', newline=NL) as f:
        f.write(NL.join(src) + NL)
    if units:
        obj = M.compile_obj(path, M.FLAGS)
        for row, _ in units:
            _, n, same, first, detail = M.compare(path, f'?Construct_{row["name"]}@@', int(row['rva'], 16), M.FLAGS, obj)
            row.update(bytes=n, identical=same, result='identical' if first is None else 'different')
            if first is not None:
                row['detail'] = detail
    with open(os.path.join(M.OUT, 'poly_placements_probe.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=1)
    count = {}
    for row in rows:
        key = row['result'] if not row['result'].startswith('unsupported') else 'unsupported instruction'
        count[key] = count.get(key, 0) + 1
    for key, n in sorted(count.items(), key=lambda x: -x[1]):
        print(f'{n:5}  {key}')
    print('identical bytes:', sum(r['bytes'] for r in rows if r['result'] == 'identical'))
    return rows, cls


def manifest():
    if not hasattr(manifest, 'v'):
        manifest.v = {}
        if os.path.exists(MANIFEST):
            manifest.v = {r['name']: r for r in json.load(open(MANIFEST, encoding='utf-8'))}
    return manifest.v


def owners():
    """rva -> symbol prefix of the typed callback that owns the client function (for gen_small.NATIVE_OWNERS)."""
    out = {}
    for r in manifest().values():
        out[int(r['construct'], 16)] = f'??$MetaConstruct@U{r["name"]}@@@@'
        if r.get('create'):
            out[int(r['create'], 16)] = f'??$MetaCreate@U{r["name"]}@@@@'
    return out


def layout_of(im, a, f, g):
    """Member lines for gen_meta.bin_classes, when the description still is the one the manifest was proved on."""
    row = manifest().get(a.cls[g])
    if not row:
        return None
    parent = a.cls[f['parent']] if f['parent'] is not None else None
    if f['construct'] != int(row['construct'], 16) or f['size'] != row['size'] or parent != row['parent']:
        raise ValueError('placement evidence changed: ' + a.cls[g])
    return row['lines']


def header_lines():
    externs = sorted({va for r in manifest().values() for va in r['externs']})
    return ['// Globals read by default member initialisers of BinClasses.h (tools/gen_poly_placements.py).',
            '#pragma once'] + [f'extern int g_{va:x};' for va in externs]


def callbacks():
    """rvas of every function a class description's initializer hands to the description constructor (create,
    destroy, construct, destruct, post-load): the typed generators own these."""
    if not hasattr(callbacks, 'v'):
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        callbacks.v = set()
        for c in classes().values():
            pushes = []
            for i in md.disasm(bytes(P.IMG[c['init']:c['init'] + 96]), P.BASE + c['init']) if c['init'] else ():
                if i.mnemonic == 'push':
                    pushes.append(int(i.op_str, 16) if i.op_str.startswith('0x') or i.op_str.isdigit() else None)
                elif i.mnemonic == 'call':
                    if len(pushes) == 10:
                        callbacks.v |= {x - P.BASE for x in pushes[4:9] if x}
                    break
        # and the constructor / destructor such a callback only calls or jumps to
        starts = sorted(M.starts())
        for rva in list(callbacks.v):
            end = starts[bisect.bisect_right(starts, rva)]
            if end - rva > 64:
                continue
            for i in md.disasm(bytes(P.IMG[rva:end]), P.BASE + rva):
                if i.mnemonic in ('call', 'jmp') and i.op_str.startswith('0x'):
                    t = int(i.op_str, 16) - P.BASE
                    if 0x60000 <= t < 0x9bb8d0 or 0x9bb960 <= t < 0xbc0000:
                        if not rva <= t < end:
                            callbacks.v.add(t)
    return callbacks.v


def create_of(init, md):
    """rva of the creation callback a description's initializer passes (None when it passes none)."""
    if init is None:
        return None
    pushes = []
    for i in md.disasm(bytes(P.IMG[init:init + 96]), P.BASE + init):
        if i.mnemonic == 'push':
            pushes.append(int(i.op_str, 16) if i.op_str.startswith('0x') or i.op_str.isdigit() else None)
        elif i.mnemonic == 'call':
            return pushes[8] - P.BASE if len(pushes) == 10 and pushes[8] else None
    return None


OPAQUE = re.compile(r'    const MetaClass\* GetClass\(\) const override;\n(?:    u8 unknown\w+\[0x[0-9a-f]+\];\n)?')


def write():
    """The manifest: the probe's identical classes that are leaves and have no constructor of their own."""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    rows, cls = probe(set())
    parents = {c['parent'] for c in cls.values()}
    declared = open(os.path.join(GEN, 'BinClasses.h'), encoding='utf-8').read()
    out, why = list(manifest().values()), {}
    for r in rows:
        if r['result'] != 'identical':
            continue
        name = r['name']
        block = re.search(rf'^struct {name}(?: : \w+)?\n\{{\n(.*?)^\}};', declared, re.M | re.S)
        if name in parents:
            reason = 'has described children'
        elif not block:
            reason = 'not defined in BinClasses.h'
        elif re.search(rf'^\s*~?{name}\(', block[1], re.M):
            reason = 'constructor or destructor of its own'
        elif not OPAQUE.fullmatch(block[1]):
            reason = 'laid out by another generator'
        else:
            create = create_of(cls[name]['init'], md)
            ext = sorted({int(x, 16) for x in re.findall(r'g_([0-9a-f]+)', ' '.join(r['layout']))})
            out.append(dict(name=name, construct=r['rva'], create=create and hex(create), size=cls[name]['size'],
                            parent=cls[name]['parent'], bytes=r['bytes'], lines=r['layout'], externs=ext))
            continue
        why[reason] = why.get(reason, 0) + 1
    out.sort(key=lambda r: r['name'])
    with open(MANIFEST, 'w', encoding='utf-8', newline=NL) as f:
        json.dump(out, f, indent=1)
        f.write(NL)
    manifest.__dict__.pop('v', None)
    with open(HEADER, 'w', encoding='utf-8', newline=NL) as f:
        f.write(NL.join(header_lines()) + NL)
    print(f'manifest: {len(out)} classes; left out: {why}')


def publish():
    """The typed callbacks of the manifest's classes, each compiled from the real BinClasses.h definition and kept
    only when it is the client's function (bytes and targets)."""
    rebuilt = M.rebuilt_symbols()
    items = []
    for r in sorted(manifest().values(), key=lambda r: r['name']):
        k = r['name']
        items.append((int(r['construct'], 16), f'??$MetaConstruct@U{k}@@@@YAXPAX@Z',
                      f'template<> void MetaConstruct<{k}>(void* p) {{ new (p) {k}; }}'))
        taken = [x for x in rebuilt.get(int(r['create'], 16), []) if x.startswith('??$MetaCreate@')] \
            if r.get('create') else ['none']
        if not taken or all(f'@U{k}@@' in x for x in taken):
            items.append((int(r['create'], 16), f'??$MetaCreate@U{k}@@@@YAPAXXZ',
                          f'template<> void* MetaCreate<{k}>() {{ return new {k}; }}'))

    def text(kept):
        return NL.join(['// Placement and creation callbacks of the classes whose layout tools/gen_poly_placements.py',
                        '// derived from the client (tools/poly_placement_layouts.json). Every claim was compiled and',
                        '// compared before it was written here.'] +
                       [f'// match: {rva:x} {sym}' for rva, sym, _ in kept] +
                       ['#include "BinClasses.h"', '#include <new>'] + [line for _, _, line in kept]) + NL
    with open(CALLBACKS, 'w', encoding='utf-8', newline=NL) as f:
        f.write(text(items))
    M.rebuilt_symbols.__dict__.pop('v', None)
    obj = M.compile_obj(CALLBACKS, M.FLAGS)
    kept, dropped = [], []
    for item in items:
        (kept if M.compare(CALLBACKS, item[1], item[0], M.FLAGS, obj)[3] is None else dropped).append(item)
    with open(CALLBACKS, 'w', encoding='utf-8', newline=NL) as f:
        f.write(text(kept))
    M.rebuilt_symbols.__dict__.pop('v', None)
    print(f'{os.path.basename(CALLBACKS)}: {len(kept)} of {len(items)} callbacks identical')
    for rva, sym, _ in dropped:
        print(f'  not identical, left out: {rva:x} {sym}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'probe':
        probe(set(sys.argv[2:]))
    elif len(sys.argv) > 1 and sys.argv[1] == 'write':
        write()
    elif len(sys.argv) > 1 and sys.argv[1] == 'publish':
        publish()
    else:
        print(__doc__)
