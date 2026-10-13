"""Packet readers whose one scalar field is selected by a small format in the presence byte.

The ordered format tests, constant values and wire-reader targets are extracted from control flow. Separate
out-of-line format functions preserve the client's distinct format calls to one address; every alias has its
own compiled body checked against that address. Source variants concern setter bounds only, not semantics.
"""
import os
import re
import struct

import gen_fields as F
import gen_field_classes as C
import match_func as M


def functions_in_wrappers():
    functions, declarations = {}, set()
    for filename in ('FieldWrappers.cpp', 'FieldInline.cpp'):
        path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', filename)
        if not os.path.exists(path):
            continue
        source = open(path, encoding='utf-8').read()
        for m in re.finditer(r'^char (ReadField\d+_([0-9a-f]+))\((u\d+)\* out.*$', source, re.M):
            wire = re.search(r'^__forceinline bool Wire_' + m[1] + r'\(.*$', source, re.M)
            body = (wire[0] + '\n' if wire else '') + m[0]
            functions[int(m[2], 16)] = (m[1], m[3], body)
        declarations.update(line for line in source.splitlines() if line.startswith(('extern ', 'bool '))
                            and line.endswith(';'))
    return functions, sorted(declarations)


def scalar_specs(im):
    header = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldClasses.h')
    wrappers, _ = functions_in_wrappers()
    own_path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'PacketScalars.cpp')
    own = {int(x, 16) for x in re.findall(r'^// match: ([0-9a-f]+)',
           open(own_path, encoding='utf-8').read(), re.M)} if os.path.exists(own_path) else set()
    result = {}
    for ctor, name in re.findall(r'^// ctor: ([0-9a-f]+) (\w+)', open(header, encoding='utf-8').read(), re.M):
        ctor = int(ctor, 16)
        schema = C.constructor_schema(im, ctor)
        if not schema or not schema[2] or len(schema[0]) != 3 or schema[0][2][3] is None:
            continue
        fields, declared, packet, extent = schema
        off, size, seed, steps = fields[2]
        text = im.text(ctor)
        root = re.search(r'^mov (edi|esi|ebx), ecx$', text, re.M)[1]
        table = F.number(re.findall(r'mov dword ptr \[' + root + r'\], (0x[0-9a-f]+)', text)[-1])
        rva = struct.unpack_from('<I', im.img, table - F.BASE + 4)[0] - F.BASE
        if rva in im.done and rva not in own:
            continue
        instructions = list(im.md.disasm(im.img[rva:rva + im.size(rva)], rva))
        lines = [f'{i.mnemonic} {i.op_str}'.strip() for i in instructions]
        by_address = {i.address: k for k, i in enumerate(instructions)}
        # These readers use one presence byte and a scalar format, with explicit comparisons in source order.
        bit_test = next((k for k, line in enumerate(lines)
                         if re.fullmatch(r'test byte ptr \[\w+\], (0x[0-9a-f]+|\d+)', line)), None)
        if size == 1 and bit_test is not None:
            calls = [F.number(line.split()[1]) for line in lines if re.fullmatch(r'call 0x[0-9a-f]+', line)]
            globals_ = [F.number(m[1]) for line in lines[bit_test + 1:]
                        if (m := re.fullmatch(r'mov \wl, byte ptr \[(0x[0-9a-f]+)\]', line))]
            known = F.known_readers()
            jump = re.fullmatch(r'(jne|je) (0x[0-9a-f]+)', lines[bit_test + 1])
            if (jump and len(calls) == 1 and calls[0] in known and known[calls[0]][1] == 'u8'
                    and len(globals_) == 1 and lines[bit_test].endswith(', 1')):
                first = 0 if jump[1] == 'jne' else 1
                cases = [(first, 'global', globals_[0]), (1 - first, 'direct_read', calls[0])]
                result[rva] = dict(name=name, ctor=ctor, schema=schema, off=off, size=size, steps=steps,
                                   mask=1, shift=0, cases=cases, boolean=True)
                continue
        if size == 1 and bit_test is not None and not any(line.startswith('call ') for line in lines):
            jump_index = bit_test + 1
            while lines[jump_index].startswith(('lea ', 'push ')):
                jump_index += 1
            jump = re.fullmatch(r'(jne|je) (0x[0-9a-f]+)', lines[jump_index])
            stores = [F.number(m[1]) for line in lines[bit_test + 1:]
                      if (m := re.fullmatch(r'mov byte ptr \[\w+\], (0x[0-9a-f]+|\d+)', line))]
            bit = F.number(lines[bit_test].split(', ')[1])
            if (jump and len(stores) == 2 and bit and bit & (bit - 1) == 0
                    and 'cmp eax, 6' in lines[:bit_test] and 'cmp esi, 1' in lines[:bit_test]):
                first = 0 if jump[1] == 'jne' else bit
                cases = [(first, 'constant', stores[0]), (bit - first, 'constant', stores[1])]
                result[rva] = dict(name=name, ctor=ctor, schema=schema, off=off, size=size, steps=steps,
                                   mask=bit, shift=0, cases=cases, boolean=True)
            continue
        masks = [k for k, line in enumerate(lines) if re.fullmatch(r'and al, (0x[0-9a-f]+|\d+)', line)]
        if not masks:
            continue
        start = masks[0]
        mask = F.number(lines[start].split(', ')[1])
        shift = F.number(lines[start - 1].split(', ')[1]) if lines[start - 1].startswith('shr al, ') else 0
        if mask not in (1, 3, 7) or 'cmp eax, 6' not in lines[:start] or 'cmp eax, 1' not in lines[:start]:
            continue
        k, cases, valid = start + 1, [], True
        while k + 1 < len(lines):
            compare = re.fullmatch(r'cmp al, (0x[0-9a-f]+|\d+)', lines[k])
            implicit_zero = k == start + 1 and lines[k].startswith('jne ')
            if compare:
                tag = F.number(compare[1])
            elif lines[k] == 'test al, al':
                tag = 0
            elif implicit_zero:
                # AND writes ZF: a following JNE is the first format-zero test.
                tag = 0
            else:
                break
            branch = k if implicit_zero else k + 1
            jump = re.fullmatch(r'jne (0x[0-9a-f]+)', lines[branch])
            if not jump or tag > mask:
                valid = False
                break
            end = by_address.get(F.number(jump[1]))
            if end is None or end <= branch:
                valid = False
                break
            body = lines[branch + 1:end]
            calls = [F.number(x.split()[1]) for x in body if re.fullmatch(r'call 0x[0-9a-f]+', x)]
            if len(calls) == 1 and calls[0] in wrappers and wrappers[calls[0]][1] == F.UINT[size]:
                cases.append((tag, 'read', calls[0]))
            elif not calls:
                value = constant_store(body, size, tag)
                if value is None:
                    valid = False
                    break
                cases.append((tag, 'constant', value))
            else:
                valid = False
                break
            k = end
        if not valid or len(cases) < 2 or len({case[0] for case in cases}) != len(cases):
            continue
        if not all(tag in {c[0] for c in cases} for tag in range(mask + 1)):
            continue
        result[rva] = dict(name=name, ctor=ctor, schema=schema, off=off, size=size, steps=steps,
                           mask=mask, shift=shift, cases=cases)
    return result


def constant_store(lines, size, format_value=None):
    width = {1: 'byte', 2: 'word', 4: 'dword', 8: 'qword'}[size]
    for k, line in enumerate(lines):
        store = re.fullmatch(r'mov ' + width + r' ptr \[\w+(?: \+ (?:0x[0-9a-f]+|\d+))?\], (.+)', line)
        if not store:
            continue
        operand = store[1]
        if re.fullmatch(r'0x[0-9a-f]+|\d+', operand):
            return F.number(operand) & ((1 << (size * 8)) - 1)
        if operand == 'al' and size == 1 and format_value is not None:
            # An equality case can assign its already-loaded format value. Only
            # instructions proved not to modify AL are allowed before that store.
            unchanged = True
            for previous in lines[:k]:
                op, _, args = previous.partition(' ')
                dest = args.split(',')[0]
                if op not in ('mov', 'lea', 'cmp', 'test', 'push', 'nop') or \
                        (op in ('mov', 'lea') and dest in ('eax', 'ax', 'al', 'ah')):
                    unchanged = False
                    break
            if unchanged:
                return format_value
        reg = {'ax': 'eax', 'bx': 'ebx', 'cx': 'ecx', 'dx': 'edx'}.get(operand, operand)
        for previous in reversed(lines[:k]):
            if previous == f'xor {reg}, {reg}':
                return 0
            if previous in (f'or {reg}, 0xffffffff', f'or {reg}, -1'):
                return (1 << (size * 8)) - 1
            literal = re.fullmatch(r'mov ' + reg + r', (0x[0-9a-f]+|\d+)', previous)
            if literal:
                return F.number(literal[1]) & ((1 << (size * 8)) - 1)
            if previous.startswith(('mov ' + reg + ',', 'lea ' + reg + ',')):
                break
    return None


def alias_name(target, tag):
    return f'FieldFormat_{target:x}_{tag}'


def needed_aliases(im):
    import gen_packet_multi as multi
    stages = list(scalar_specs(im).values())
    stages += [stage for spec in multi.multi_specs(im).values() for stage in spec['stages']]
    return sorted({(target, tag) for spec in stages for tag, kind, target in spec['cases'] if kind == 'read'})


def format_alias_header(im):
    functions, _ = functions_in_wrappers()
    aliases = needed_aliases(im)
    lines = ['// Verified out-of-line reader bodies, named per scalar format. Shared client addresses are compatible',
             '// with linker folding; packet readers keep distinct ordered format calls. Names are ours.',
             '#pragma once', '#include "../types.h"', '']
    lines += [f'char {alias_name(target, tag)}({functions[target][1]}* out, const u8** cursor, const u8* end);'
              for target, tag in aliases]
    return lines, len(aliases)


def format_aliases(im):
    functions, declarations = functions_in_wrappers()
    aliases = needed_aliases(im)
    lines = ['// Source bodies duplicated per format, each verified at the shared client address.',
             '// Generated by tools/gen_sources.py, tools/gen_packet_scalars.py. No extra functions are counted.']
    lines += [f'// same: {target:x} ?{alias_name(target, tag)}@' for target, tag in aliases]
    lines += ['#include "FieldFormatAliases.h"', '#include "../FieldCodec.h"'] + declarations + ['']
    lines += [functions[target][2].replace(functions[target][0], alias_name(target, tag)) for target, tag in aliases]
    # // same: aliases receive the same byte/target check as // match:, before they can affect other files.
    probe = os.path.join(M.OUT, 'field_formats.cpp')
    source = '\n'.join(lines).replace('#include "FieldFormatAliases.h"', '#include "../src/gen/FieldFormatAliases.h"')
    source = source.replace('#include "../FieldCodec.h"', '#include "../src/FieldCodec.h"')
    with open(probe, 'w', encoding='utf-8', newline='\n') as f:
        f.write(source + '\n')
    obj = M.compile_obj(probe, M.FLAGS)
    for target, tag in aliases:
        r = M.compare(probe, '?' + alias_name(target, tag) + '@', target, M.FLAGS, obj)
        if r[3] is not None:
            raise RuntimeError(f'format alias {alias_name(target, tag)} is not identical: {r[4]}')
    if not os.environ.get('KEEP_CANDIDATES'):
        os.remove(probe)
    return lines, len(aliases)


HEADER = ('__forceinline bool Header_NAME(C2S_Base& object, const u8** cursor, const u8* end) { '
          'const u8* p = *cursor; if ((u32)(end - p) < 6) return false; object.header4 = *(const u16*)p; '
          'object.header6 = *(const u32*)(p + 2); *cursor += 6; return true; }')

BITS = '''__forceinline u8 Bits_NAME(const u8* data, u8 first, u8 count) {
    u8 byte = first >> 3; u8 bit = first & 7; u8 mask = (u8)((1 << count) - 1);
    u8 result = (data[byte] & (u8)(mask << bit)) >> bit;
    if (bit + count > 8) { ++byte; mask >>= 8 - bit; result |= (data[byte] & mask) << (8 - bit); }
    return result;
}'''


def reader_source(spec, bounds, declaration=True, signed_word=False, codec=None, wide_byte=False,
                  presence_style='copy', format_style='direct'):
    off, typ, size, steps = spec['off'], F.UINT[spec['size']], spec['size'], spec['steps']
    fields, declared, packet, extent = spec['schema']
    value_type = 'short' if signed_word else typ
    value_field = f'(short&)field{off:x}.value' if signed_word else f'field{off:x}.value'
    decl = C.constructor_source(fields, 'members', True, 'NAME', extent).split('NAME::NAME()', 1)[0]
    codec = codec if codec is not None else F.statements(steps)
    if wide_byte:
        codec = codec.replace('[x]', '[(u8)x]')
    byte_type = 'u32' if wide_byte else 'u8'
    setter = (f'__forceinline void Set_NAME({value_type}& field, const {value_type}& value) {{ field = value; '
              f'for (u8* b = (u8*)&field; b != (u8*)&field + sizeof(field); ++b) {{ {byte_type} x = *b; '
              f'{codec} *b = x; }} }}')
    ranged = setter.replace('const ' + value_type + '& value)', 'const ' + value_type + '& value, u8* finish)')
    ranged = ranged.replace('b != (u8*)&field + sizeof(field)', 'b != finish').replace('Set_NAME', 'Range_NAME')
    external = []
    for tag, kind, operand in spec['cases']:
        if kind == 'global':
            external.append(f'extern {typ} g_{operand:x};')
        elif kind == 'direct_read':
            external.append(f'char {F.known_readers()[operand][0]}({typ}*, const u8**, const u8*);')
    lines = external + ([decl] if declaration else []) + [HEADER, setter, ranged]
    prefix = ('if ((u32)(end - *cursor) < 1) return false; const u8* p = (*cursor)++; '
              if presence_style == 'postincrement' else
              'const u8* p = *cursor; if ((u32)(end - p) < 1) return false; *cursor = p + 1; ')
    format_expr = f'(*p >> {spec["shift"]}) & {spec["mask"]}'
    if format_style == 'helper' and spec['mask'] in (1, 3, 7):
        count = (spec['mask'] + 1).bit_length() - 1
        format_expr = f'Bits_NAME(p, {spec["shift"]}, {count})'
        lines.append(BITS)
    body = (f'char NAME::Read(const u8** cursor, const u8* end) {{ if (!Header_NAME(*this, cursor, end)) return false; '
            + prefix + f'u8 format = {format_expr}; ')
    for k, (tag, kind, operand) in enumerate(spec['cases']):
        if k and spec.get('boolean'):
            body += 'else { '
        else:
            body += ('if' if not k else 'else if') + f' (format == {tag}) {{ '
        if kind == 'read':
            body += f'if (!{alias_name(operand, tag)}(&field{off:x}.value, cursor, end)) return false; '
        elif kind == 'direct_read':
            body += f'if (!{F.known_readers()[operand][0]}(&field{off:x}.value, cursor, end)) return false; '
        else:
            literal = (f'g_{operand:x}' if kind == 'global' else
                       value_type + '(' + hex(operand) + ('ULL' if size == 8 else '') + ')')
            ranged_case = bounds == 'range' or (bounds == 'nonzero' and operand != 0)
            if ranged_case:
                body += f'Range_NAME({value_field}, {literal}, (u8*)this + {off + size}); '
            else:
                body += f'Set_NAME({value_field}, {literal}); '
        body += '} '
    body += ('return true; }' if spec.get('boolean') else 'else return false; return true; }')
    return '\n'.join(lines + [body])


def packet_scalars(im):
    specs = scalar_specs(im)
    variants = {rva: [(bounds, steps, signed, codec, wide, presence, format_style)
                      for steps in F.equivalent_bit_chains(spec['steps'])
                      for codec in F.reverse_source_forms(steps)
                      for wide in (False, True)
                      for signed in ((False, True) if spec['size'] == 2 else (False,))
                      for bounds in ('field', 'range', 'nonzero')
                      for presence in ('copy', 'postincrement')
                      for format_style in ('direct', 'helper')] for rva, spec in specs.items()}
    cands = {rva: [reader_source(dict(spec, steps=steps), bounds, signed_word=signed, codec=codec, wide_byte=wide,
                               presence_style=presence, format_style=format_style)
                  for bounds, steps, signed, codec, wide, presence, format_style in variants[rva]]
             for rva, spec in specs.items()}
    # Declarations shared with constructors ensure the emitted methods belong to the same complete C++ type.
    found = F.pick(cands, (), ['#include "../src/gen/FieldClasses.h"',
                               '#include "../src/gen/FieldFormatAliases.h"'], '?Read@Try_{rva:x}_{k}@@')
    lines = ['// Packet readers with one scalar selected by a presence-byte format. Defaults and source-order',
             '// format tests are read from the client; each surviving function has identical compiled bytes.',
             '// Generated by tools/gen_sources.py, tools/gen_packet_scalars.py.',
             f'// {len(found)} of {len(specs)} readers are identical.']
    lines += [f'// match: {rva:x} ?Read@{specs[rva]["name"]}@@' for rva in sorted(found)]
    lines += ['#include "FieldClasses.h"', '#include "FieldFormatAliases.h"', '']
    for rva, k in sorted(found.items()):
        bounds, steps, signed, codec, wide, presence, format_style = variants[rva][k]
        lines += [reader_source(dict(specs[rva], steps=steps), bounds, False, signed, codec, wide, presence, format_style)
                  .replace('NAME', specs[rva]['name'])]
    return lines, len(found)
