"""Reconstruct field constructors as typed members, each with its own default and byte codec.

The schema is read from member addresses and bounds of the byte loops. All initialization stores outside the
loops must be accounted for; the usual compile-and-compare gate decides which source form is actually emitted.
"""
import re
import os

import gen_fields as F

# Value layout proved by the default branch of packet reader 0x85ff20: the value at +0x14 is assigned by
# 0x140460, a vector of trivially destructible 12-byte elements. Its constructor writes three zero words.
VECTOR_MEMBERS = {0x7b8280: {0x14: (0x140460, 12)}}


def constructor_schema(im, rva):
    text = im.text(rva) or ''
    if 'call ' in text or not text.endswith('ret'):
        return None
    root = re.search(r'^mov (edi|esi|ebx), ecx$', text, re.M)
    if not root:
        return None
    root = root[1]
    tables = re.findall(r'^mov dword ptr \[' + root + r'\], (0x[0-9a-f]+)$', text, re.M)
    packet = len(tables) == 2 and tables[0] == '0x153357c'
    if len(tables) != 1 and not packet:
        return None
    ins = list(im.md.disasm(im.img[rva:rva + im.size(rva)], rva))
    lines = text.split('\n')
    index = {i.address: k for k, i in enumerate(ins)}
    loops = {}
    for k, line in enumerate(lines):
        back = re.fullmatch(r'jne (0x[0-9a-f]+)', line)
        if not back or F.number(back[1]) >= ins[k].address:
            continue
        start = index.get(F.number(back[1]))
        compare = re.fullmatch(r'cmp (\w+), (\w+)', lines[k - 1]) if k >= 2 else None
        if start is None or not compare or lines[k - 2] != 'inc ' + compare[1]:
            return None
        ptr, end = compare[1], compare[2]
        stores = [j for j in range(start, k - 2) if re.fullmatch(r'mov byte ptr \[' + ptr + r'\], \wl', lines[j])]
        if len(stores) != 1:
            return None
        loops[start] = (k, ptr, end, stores[0])
    if not loops:
        return None
    addresses, values, writes, fields, globals_ = {'ecx': 0}, {}, {}, [], {}

    def memory(operand):
        m = re.fullmatch(r'\[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]', operand)
        if not m or m[1] not in addresses:
            return None
        return addresses[m[1]] + (F.number(m[3]) * (-1 if m[2] == '-' else 1) if m[3] else 0)

    def value(operand):
        register = F.R8.get(operand, {'ax': 'eax', 'bx': 'ebx', 'cx': 'ecx', 'dx': 'edx'}.get(operand, operand))
        if register in values:
            return values[register]
        if re.fullmatch(r'-?(?:0x[0-9a-f]+|\d+)', operand):
            return ('constant', F.number(operand), 0)
        return None

    k = 0
    while k < len(lines):
        if k in loops:
            stop, ptr, end, store = loops[k]
            if ptr not in addresses or end not in addresses:
                return None
            off, size = addresses[ptr], addresses[end] - addresses[ptr]
            if off < 4 or size not in F.UINT:
                return None
            steps = F.chain_of(lines[k:store + 1], im.img, {}, {ptr: F.CURSOR}, lenient=True)
            if steps is None:
                return None
            seed = writes.pop((off, size), None)
            if seed is None and size == 8:
                lo, hi = writes.pop((off, 4), None), writes.pop((off + 4, 4), None)
                if lo and hi and lo[0] == hi[0] == 'constant':
                    seed = ('constant', (lo[1] & 0xffffffff) | ((hi[1] & 0xffffffff) << 32), 0)
            if seed is None:
                return None
            fields.append((off, size, seed, steps))
            addresses = {r: v for r, v in addresses.items() if r in (root, ptr, end)}
            addresses[ptr] = addresses[end]
            values.clear()
            k = stop + 1
            continue
        line = lines[k]
        op, _, rest = line.partition(' ')
        args = [x.strip() for x in rest.split(',')]
        if op in ('mov', 'movzx'):
            dest, source = args
            if dest in F.R32:
                addr = addresses.get(source)
                val = value(source)
                glob = re.fullmatch(r'(byte|word|dword) ptr \[(0x[0-9a-f]+)\]', source)
                if glob:
                    va, size = F.number(glob[2]), {'byte': 1, 'word': 2, 'dword': 4}[glob[1]]
                    globals_[va] = max(globals_.get(va, 0), size)
                    val = ('global', va, size)
                addresses.pop(dest, None)
                values.pop(dest, None)
                if addr is not None:
                    addresses[dest] = addr
                if val is not None:
                    values[dest] = val
            else:
                dest = re.fullmatch(r'(byte|word|dword) ptr (\[.*\])', dest)
                if not dest:
                    return None
                off = memory(dest[2])
                val = value(source)
                if off is None or val is None:
                    return None
                if off == 0 and source in tables:
                    k += 1
                    continue
                if val[0] == 'constant' and F.BASE <= val[1] <= F.BASE + len(im.img) - 4:
                    import struct
                    target = struct.unpack_from('<I', im.img, val[1] - F.BASE)[0] - F.BASE
                    if target in im.starts:
                        return None  # a nested vtable needs its own class, never an absolute integer initializer
                size = {'byte': 1, 'word': 2, 'dword': 4}[dest[1]]
                if off < 4 or (off, size) in writes:
                    return None
                writes[off, size] = val
        elif op == 'lea':
            off = memory(args[1])
            addresses.pop(args[0], None)
            values.pop(args[0], None)
            if off is not None:
                addresses[args[0]] = off
        elif op == 'xor' and args[0] == args[1] and args[0] in F.R32:
            values[args[0]] = ('constant', 0, 0)
            addresses.pop(args[0], None)
        elif op in ('push', 'pop', 'nop', 'cmp', 'ret') or op.startswith('j'):
            pass
        else:
            return None
        k += 1
    fields += [(off, size, seed, None) for (off, size), seed in writes.items()]
    fields.sort(key=lambda f: f[0])
    # The measured empty RString initialization: shared data pointer, length zero, capacity zero.
    grouped, k = [], 0
    while k < len(fields):
        off, size, seed, steps = fields[k]
        if (size == 4 and seed == ('global', 0x1b467f0, 4) and steps is None and k + 2 < len(fields)
                and fields[k + 1] == (off + 4, 4, ('constant', 0, 0), None)
                and fields[k + 2] == (off + 8, 4, ('constant', 0, 0), None)):
            grouped.append((off, 12, ('string', 0, 0), None))
            k += 3
        else:
            grouped.append(fields[k])
            k += 1
    fields = grouped
    for off, (assign, stride) in VECTOR_MEMBERS.get(rva, {}).items():
        parts = [(off + 4 * i, 4, ('constant', 0, 0), None) for i in range(3)]
        if not all(part in fields for part in parts):
            return None
        fields = [f for f in fields if f not in parts] + [(off, 12, ('vector', assign, stride), None)]
    fields.sort(key=lambda f: f[0])
    end = 4
    for off, size, seed, steps in fields:
        if off < end:
            return None
        end = off + size
    if packet and (len(fields) < 2 or fields[0][0:2] != (4, 2) or fields[1][0:2] != (6, 4)
                   or fields[0][2][0] != 'constant' or fields[1][2][0] != 'global'):
        return None
    import struct
    table = F.number(tables[-1])
    getter = struct.unpack_from('<I', im.img, table - F.BASE + 8)[0] - F.BASE
    size_code = im.text(getter) or ''
    size_match = re.fullmatch(r'mov eax, (0x[0-9a-f]+|\d+)\nret', size_code)
    extent = F.number(size_match[1]) if size_match else end
    if not end <= extent <= 4096:
        return None
    return fields, globals_, packet, extent


def seed_expression(seed, size):
    kind, operand, width = seed
    if kind == 'global':
        return f'({F.UINT[size]})g_{operand:x}'
    return hex(operand & ((1 << (size * 8)) - 1)) + ('ULL' if size == 8 else '')


def constructor_source(fields, form, packet=False, class_name='NAME', extent=None):
    helpers, members, initializers, body, pos = [], [], [], [], 4
    if packet:
        initializers.append('C2S_Base(' + seed_expression(fields[0][2], 2) + ', ' +
                            f'g_{fields[1][2][1]:x})')
        fields, pos = fields[2:], 10
    for off, size, seed, steps in fields:
        typ = ('RString' if seed[0] == 'string' else f'AssignedVector_{seed[1]:x}' if seed[0] == 'vector'
               else F.UINT[size])
        initial = '' if seed[0] in ('string', 'vector') else seed_expression(seed, size)
        if off > pos:
            members.append(f'u8 gap{pos:x}[{off - pos}];')
        if steps is None:
            members.append(f'{typ} field{off:x};')
            if seed[0] not in ('string', 'vector'):
                initializers.append(f'field{off:x}({initial})')
        elif form == 'members':
            name = f'Encoded_NAME_{off:x}'
            helpers.append(f'struct {name} {{ {typ} value; __forceinline {name}() : value({initial}) {{ '
                           f'for (u8* b = (u8*)&value; b != (u8*)&value + sizeof(value); ++b) {{ '
                           f'u8 x = *b; {F.statements(steps)} *b = x; }} }} }};')
            members.append(f'{name} field{off:x};')
        else:
            members.append(f'{typ} field{off:x};')
            loop = (f'field{off:x} = {initial}; for (u8* b = (u8*)&field{off:x}; '
                    f'b != (u8*)&field{off:x} + sizeof(field{off:x}); ++b) {{ u8 x = *b; '
                    f'{F.statements(steps)} *b = x; }}')
            body.append(loop)
        pos = off + size
    if extent is not None and extent > pos:
        members.append(f'u8 tail[{extent - pos}];')
    init = ' : ' + ', '.join(initializers) if initializers else ''
    copies = ' '.join(f'field{off:x} = other.field{off:x};' for off, size, seed, steps in fields)
    source = ('#pragma pack(push, 1)\n' + '\n'.join(helpers) + '\n' +
            ('struct CLASS : C2S_Base { ' if packet else 'struct CLASS { ') +
            'virtual void Write(PacketTrivialVectorStorage& buffer); '
            'virtual char Read(const u8** cursor, const u8* end); '
            'virtual u32 GetSize() const { return sizeof(CLASS); } virtual ~CLASS() = default; '
            + ' '.join(members) + ' CLASS(); __forceinline CLASS& operator=(const CLASS& other) { ' + copies +
            ' return *this; } };\n#pragma pack(pop)\nCLASS::CLASS()' + init + ' { '
            + ' '.join(body) + ' }')
    return source.replace('CLASS', class_name)


def constructor_candidates(im):
    candidates, tables, globals_, names = {}, set(), {}, {}
    import match_func as M
    path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldConstructors.cpp')
    own = {int(s, 16) for s in re.findall(r'^// match: ([0-9a-f]+)', open(path, encoding='utf-8').read(), re.M)} \
        if os.path.exists(path) else set()
    for s in im.starts:
        if (s in im.done and s not in own) or not 0x1000 <= s < 0xbc0000 or not 35 <= im.size(s) <= 1800:
            continue
        schema = constructor_schema(im, s)
        if not schema:
            continue
        fields, declared, packet, extent = schema
        for va, size in declared.items():
            globals_[va] = max(globals_.get(va, 0), size)
        tables.update(v for off, size, seed, steps in fields for op, v in steps or () if op == 'table')
        if packet:
            text = im.text(s)
            root = re.search(r'^mov (edi|esi|ebx), ecx$', text, re.M)[1]
            va = F.number(re.findall(r'mov dword ptr \[' + root + r'\], (0x[0-9a-f]+)', text)[-1])
            labelled = [n.removesuffix('_vtable') for n in M.known_names().get(va - F.BASE, ())
                        if re.fullmatch(r'(?:C2S|S2C)_\d+_vtable', n)]
            if len(labelled) != 1 or labelled[0] in names.values():
                continue
            names[s] = labelled[0]
            candidates[s] = [constructor_source(fields, 'members', True, labelled[0], extent)]
        else:
            names[s] = 'NAME'
            candidates[s] = [constructor_source(fields, form, extent=extent) for form in ('members', 'body')]
    prelude = ['#include "../src/RString.h"', '#include "../src/PacketVector.h"']
    prelude.append('#pragma pack(push, 1)\nstruct C2S_Base { '
                   'virtual void Write(PacketTrivialVectorStorage& buffer); '
                   'virtual char Read(const u8** cursor, const u8* end); virtual u32 GetSize() const; '
                   'virtual ~C2S_Base() = default; u16 header4; u32 header6; '
                   '__forceinline C2S_Base(u16 id, const u32& netid) : header4(id), header6(netid) {} '
                   '};\n#pragma pack(pop)')
    for assign, stride in sorted({v for members in VECTOR_MEMBERS.values() for v in members.values()}):
        name = f'AssignedVector_{assign:x}'
        prelude.append(f'struct {name} : PacketTrivialVectorStorage {{ {name}& operator=(const {name}& other); }};')
    prelude += [f'extern {F.UINT[size]} g_{va:x};' for va, size in sorted(globals_.items())]
    found = F.pick(candidates, tables, prelude,
                   lambda rva, k: f'??0{names[rva] if names[rva] != "NAME" else f"Try_{rva:x}_{k}"}@@')
    return candidates, tables, prelude, found, names


def field_classes(im):
    candidates, tables, prelude, found, names = constructor_candidates(im)
    lines = ['// Encoded field types, shared by their constructors and packet readers (generated by',
             '// tools/gen_sources.py, tools/gen_field_classes.py). Names are ours. Only constructors verified',
             '// against the client are included; member assignments copy their stored representation.',
             '#pragma once', '#include "../FieldCodec.h"', '#include "../RString.h"', '#include "../PacketVector.h"']
    lines += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)]
    lines += [x for x in prelude if not x.startswith('#include')] + ['']
    for s, k in sorted(found.items()):
        src = candidates[s][k].replace('NAME', f'FieldCtor_{s:x}')
        name = names[s] if names[s] != 'NAME' else f'FieldCtor_{s:x}'
        decl = src.split(f'{name}::{name}()', 1)[0]
        lines += [f'// ctor: {s:x} {name}', decl]
    return lines, len(found)


def field_constructors(im):
    candidates, tables, prelude, found, names = constructor_candidates(im)
    lines = ['// Encoded field constructors (generated by tools/gen_sources.py, tools/gen_field_classes.py).',
             '// The layout, defaults and byte codecs come from the client; names are ours: FieldCtor_<rva>.',
             f'// {len(found)} of {len(candidates)} constructors are identical.']
    actual = {s: names[s] if names[s] != 'NAME' else f'FieldCtor_{s:x}' for s in found}
    lines += [f'// match: {s:x} ??0{actual[s]}@@' for s in sorted(found)]
    # The constructor's vtable identifies its size getter, writer and compiler-generated deleting destructor.
    # These are compiled and checked by gen_sources.verify too; folded aliases are not counted twice.
    import struct
    import match_func as M
    claimed = set(im.done)
    # A generation pass may see its previous own claims; allow them to be claimed again.
    path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldConstructors.cpp')
    if os.path.exists(path):
        claimed -= {int(s, 16) for s in re.findall(r'^// match: ([0-9a-f]+)',
                    open(path, encoding='utf-8').read(), re.M)}
    definitions = [f'{actual[s]}::{actual[s]}()' + candidates[s][k].split(
                   f'{names[s]}::{names[s]}()', 1)[1] for s, k in sorted(found.items())]
    extras, writers = [], []
    for s in sorted(found):
        text = im.text(s)
        root = re.search(r'^mov (edi|esi|ebx), ecx$', text, re.M)[1]
        table = F.number(re.findall(r'mov dword ptr \[' + root + r'\], (0x[0-9a-f]+)', text)[-1])
        slots = [v - F.BASE for v in struct.unpack_from('<4I', im.img, table - F.BASE)]
        for rva, symbol in [(slots[2], f'?GetSize@{actual[s]}@@'), (slots[3], f'??_G{actual[s]}@@')]:
            extras.append((rva, symbol))
        if im.text(slots[0]) == 'ret 4':
            extras.append((slots[0], f'?Write@{actual[s]}@@'))
            writers.append(f'void {actual[s]}::Write(PacketTrivialVectorStorage& buffer) {{}}')
    # Aliases have the same acceptance gate as new claims; a nonmatching destructor must not be turned into an
    # unchecked // same: line on a later generation attempt.
    probe = os.path.join(M.OUT, 'field_ctor_extras.cpp')
    with open(probe, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(['#include "../src/gen/FieldClasses.h"'] + definitions + writers) + '\n')
    obj = M.compile_obj(probe, M.FLAGS)
    for rva, symbol in extras:
        try:
            if M.compare(probe, symbol, rva, M.FLAGS, obj)[3] is not None:
                continue
        except SystemExit:
            continue
        tag = 'same' if rva in claimed else 'match'
        lines.append(f'// {tag}: {rva:x} {symbol}')
        claimed.add(rva)
    lines += ['#include "FieldClasses.h"', '']
    lines += definitions
    lines += writers
    if not os.environ.get('KEEP_CANDIDATES'):
        os.remove(probe)
    return lines, len(re.findall(r'^// match:', '\n'.join(lines), re.M))
