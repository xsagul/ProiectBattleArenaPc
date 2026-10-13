"""Readers with several numeric fields and ordered presence-byte formats."""
import bisect
import itertools
import os
import re
import struct

import gen_fields as F
import gen_field_classes as C
import gen_packet_scalars as S
import match_func as M


def packet_instructions(im, rva):
    """Follow local control flow, allowing unnamed index entries inside a packet reader.

    Calls are not followed. A named function bounds the search. Indirect jumps and conditional branches out of
    this region are unsupported, rather than evidence that arbitrary neighbouring bytes belong to this reader.
    """
    known = M.known_names()
    limit = next((s for s in im.starts[bisect.bisect_right(im.starts, rva):] if known.get(s)), rva + 16384)
    limit = min(limit, rva + 16384)
    pending, decoded = [rva], {}
    while pending:
        address = pending.pop()
        if address in decoded:
            continue
        if not rva <= address < limit:
            return None
        instruction = next(im.md.disasm(im.img[address:min(address + 15, limit)], address, count=1), None)
        if instruction is None or instruction.mnemonic in ('int3', 'ud2'):
            return None
        decoded[address] = instruction
        op, operand = instruction.mnemonic, instruction.op_str
        if op.startswith('ret'):
            continue
        if op.startswith('j'):
            if not re.fullmatch(r'0x[0-9a-f]+|\d+', operand):
                return None
            target = F.number(operand)
            if op == 'jmp' and not rva <= target < limit:
                continue                         # external tail call, not a neighbouring body
            pending.append(target)
            if op == 'jmp':
                continue
        pending.append(address + instruction.size)
    return [decoded[s] for s in sorted(decoded)]


def object_registers(lines):
    regs = {'ecx': 0}
    for line in lines:
        move = re.fullmatch(r'mov (\w+), (\w+)', line)
        if move:
            regs[move[1]] = regs.get(move[2])
        else:
            dest = re.match(r'(?:mov|movzx|lea|xor|add|sub|shr|shl|and|or|imul) (\w+),', line)
            if dest:
                regs[dest[1]] = None
    return {reg: value for reg, value in regs.items() if value is not None}


def output_offset(body, initial, width):
    regs = dict(initial)
    output = None
    for line in body:
        lea = re.fullmatch(r'lea (\w+), \[(\w+)(?: \+ (0x[0-9a-f]+|\d+))?\]', line)
        move = re.fullmatch(r'mov (\w+), (\w+)', line)
        add = re.fullmatch(r'add (\w+), (0x[0-9a-f]+|\d+)', line)
        if lea:
            base = regs.get(lea[2])
            regs[lea[1]] = None if base is None else base + (F.number(lea[3]) if lea[3] else 0)
        elif move:
            regs[move[1]] = regs.get(move[2])
        elif add and regs.get(add[1]) is not None:
            regs[add[1]] += F.number(add[2])
        elif line.startswith('push '):
            output = regs.get(line.split()[1])
        elif re.fullmatch(r'call 0x[0-9a-f]+', line):
            return output
        else:
            store = re.fullmatch(r'mov ' + width + r' ptr \[(\w+)(?: \+ (0x[0-9a-f]+|\d+))?\], .+', line)
            if store and regs.get(store[1]) is not None:
                return regs[store[1]] + (F.number(store[2]) if store[2] else 0)
            dest = re.match(r'(?:mov|movzx|lea|xor|add|sub|shr|shl|and|or|imul) (\w+),', line)
            if dest:
                regs[dest[1]] = None
    return None


def multi_specs(im):
    header = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldClasses.h')
    wrappers, _ = S.functions_in_wrappers()
    own_path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'PacketMultiScalars.cpp')
    own = {int(x, 16) for x in re.findall(r'^// match: ([0-9a-f]+)',
           open(own_path, encoding='utf-8').read(), re.M)} if os.path.exists(own_path) else set()
    result = {}
    for ctor, name in re.findall(r'^// ctor: ([0-9a-f]+) (\w+)', open(header, encoding='utf-8').read(), re.M):
        ctor = int(ctor, 16)
        schema = C.constructor_schema(im, ctor)
        if (not schema or not schema[2] or not 4 <= len(schema[0]) <= 6
                or any(size not in F.UINT or steps is None for off, size, seed, steps in schema[0][2:])):
            continue
        fields = {off: (size, steps) for off, size, seed, steps in schema[0][2:]}
        ctor_text = im.text(ctor)
        root = re.search(r'^mov (edi|esi|ebx), ecx$', ctor_text, re.M)[1]
        table = F.number(re.findall(r'mov dword ptr \[' + root + r'\], (0x[0-9a-f]+)', ctor_text)[-1])
        rva = struct.unpack_from('<I', im.img, table - F.BASE + 4)[0] - F.BASE
        if rva in im.done and rva not in own:
            continue
        instructions = packet_instructions(im, rva)
        if not instructions:
            continue
        lines = [f'{i.mnemonic} {i.op_str}'.strip() for i in instructions]
        addresses = {i.address: k for k, i in enumerate(instructions)}
        masks = []
        for k, line in enumerate(lines):
            mask = re.fullmatch(r'and al, (1|3|7)', line)
            if not mask:
                continue
            load = k - 2 if lines[k - 1].startswith('shr al, ') else k - 1
            if re.fullmatch(r'mov al, byte ptr \[\w+\]', lines[load]):
                masks.append((k, load, int(mask[1])))
        if len(masks) != len(fields):
            continue
        roots = object_registers(lines[:masks[0][1]])
        stages, valid = [], True
        for stage, (start, load, mask) in enumerate(masks):
            finish = masks[stage + 1][1] if stage + 1 < len(masks) else len(lines)
            shift = F.number(lines[start - 1].split(', ')[1]) if start - load == 2 else 0
            k, cases, field_offset = start + 1, [], None
            while k + 1 < finish:
                compare = re.fullmatch(r'cmp al, (0x[0-9a-f]+|\d+)', lines[k])
                tag = F.number(compare[1]) if compare else 0 if lines[k] == 'test al, al' else None
                jump = re.fullmatch(r'jne (0x[0-9a-f]+)', lines[k + 1])
                if tag is None or not jump or tag > mask:
                    break
                next_case = addresses.get(F.number(jump[1]))
                if next_case is None or next_case <= k + 1:
                    valid = False
                    break
                body = lines[k + 2:min(next_case, finish)]
                calls = [F.number(x.split()[1]) for x in body if re.fullmatch(r'call 0x[0-9a-f]+', x)]
                if len(calls) == 1 and calls[0] in wrappers:
                    size = int(wrappers[calls[0]][1][1:]) // 8
                    off = output_offset(body, roots, {1: 'byte', 2: 'word', 4: 'dword', 8: 'qword'}[size])
                    case = (tag, 'read', calls[0])
                elif not calls:
                    stores = re.findall(r'mov (byte|word|dword|qword) ptr \[.+?\], .+', '\n'.join(body))
                    if not stores:
                        valid = False
                        break
                    size = {'byte': 1, 'word': 2, 'dword': 4, 'qword': 8}[stores[0]]
                    off = output_offset(body, roots, stores[0])
                    value = S.constant_store(body, size)
                    if value is None:
                        valid = False
                        break
                    case = (tag, 'constant', value)
                else:
                    valid = False
                    break
                if off not in fields or fields[off][0] != size or (field_offset is not None and off != field_offset):
                    valid = False
                    break
                field_offset = off
                cases.append(case)
                k = next_case
            if not valid or {c[0] for c in cases} != set(range(mask + 1)) or len(cases) != mask + 1:
                valid = False
                break
            size, steps = fields[field_offset]
            stages.append(dict(off=field_offset, size=size, steps=steps, mask=mask, shift=shift, cases=cases))
        if valid and {s['off'] for s in stages} == set(fields):
            result[rva] = dict(name=name, ctor=ctor, schema=schema, stages=stages,
                               end=max(i.address + i.size for i in instructions))
    return result


BITS = S.BITS


def reader_source(spec, bounds, declaration=True, codecs=None, presence_style='copy'):
    fields, declared, packet, extent = spec['schema']
    decl = C.constructor_source(fields, 'members', True, 'NAME', extent).split('NAME::NAME()', 1)[0]
    lines = ([decl] if declaration else []) + [S.HEADER, BITS]
    prefix = ('if ((u32)(end - *cursor) < 1) return false; const u8* presence = (*cursor)++; '
              if presence_style == 'postincrement' else
              'const u8* presence = *cursor; if ((u32)(end - presence) < 1) return false; *cursor = presence + 1; ')
    body = ('char NAME::Read(const u8** cursor, const u8* end) { if (!Header_NAME(*this, cursor, end)) return false; '
            + prefix)
    for index, stage in enumerate(spec['stages']):
        off, size, steps = stage['off'], stage['size'], stage['steps']
        typ = F.UINT[size]
        setter = (f'__forceinline void Set_NAME_{off:x}({typ}& field, const {typ}& value) {{ field = value; '
                  f'for (u8* b = (u8*)&field; b != (u8*)&field + sizeof(field); ++b) {{ u8 x = *b; '
                  f'{codecs[index] if codecs else F.statements(steps)} *b = x; }} }}')
        ranged = setter.replace('const ' + typ + '& value)', 'const ' + typ + '& value, u8* finish)')
        ranged = ranged.replace('b != (u8*)&field + sizeof(field)', 'b != finish').replace('Set_NAME_', 'Range_NAME_')
        lines += [setter, ranged]
        count = (stage['mask'] + 1).bit_length() - 1
        body += f'u8 format{index} = Bits_NAME(presence, {stage["shift"]}, {count}); '
        for k, (tag, kind, operand) in enumerate(stage['cases']):
            body += ('if' if not k else 'else if') + f' (format{index} == {tag}) {{ '
            if kind == 'read':
                body += f'if (!{S.alias_name(operand, tag)}(&field{off:x}.value, cursor, end)) return false; '
            else:
                literal = f'{typ}({hex(operand)}' + ('ULL' if size == 8 else '') + ')'
                use_range = bounds[index] == 'range' or (bounds[index] == 'nonzero' and operand != 0)
                if use_range:
                    body += f'Range_NAME_{off:x}(field{off:x}.value, {literal}, (u8*)this + {off + size}); '
                else:
                    body += f'Set_NAME_{off:x}(field{off:x}.value, {literal}); '
            body += '} '
        body += 'else return false; '
    body += 'return true; }'
    return '\n'.join(lines + [body])


def packet_multi_scalars(im):
    specs = multi_specs(im)
    variants = {r: [(bounds, codecs, presence)
                   for bounds in itertools.product(('field', 'range', 'nonzero'), repeat=len(s['stages']))
                   for codecs in itertools.product(*(tuple(F.reverse_source_forms(stage['steps']))
                                                     for stage in s['stages']))
                   for presence in ('copy', 'postincrement')] for r, s in specs.items()}
    candidates = {r: [reader_source(s, bounds, codecs=codecs, presence_style=presence)
                     for bounds, codecs, presence in variants[r]]
                  for r, s in specs.items()}
    found = F.pick(candidates, (), ['#include "../src/gen/FieldClasses.h"',
                                   '#include "../src/gen/FieldFormatAliases.h"'], '?Read@Try_{rva:x}_{k}@@')
    lines = ['// Packet readers with several numeric fields and ordered presence-byte formats.',
             '// Generated by tools/gen_sources.py, tools/gen_packet_multi.py; complete local control flow is used.',
             f'// {len(found)} of {len(specs)} readers are identical.']
    lines += [f'// match: {r:x} ?Read@{specs[r]["name"]}@@' for r in sorted(found)]
    lines += ['#include "FieldClasses.h"', '#include "FieldFormatAliases.h"', '']
    for r, k in sorted(found.items()):
        bounds, codecs, presence = variants[r][k]
        lines.append(reader_source(specs[r], bounds, False, codecs, presence).replace('NAME', specs[r]['name']))
    return lines, len(found)
