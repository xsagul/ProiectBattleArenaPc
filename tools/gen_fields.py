"""Sources for the client's packet field readers, written from the client itself (used by tools/gen_sources.py).

A packet field is kept encoded: every byte read from the wire goes through a chain of one-byte steps of its own (add a
constant, exclusive-or a constant, rotate, reverse the bits, subtract from a constant, look up in a 256-byte table,
swap neighbouring bits or bit pairs, complement). Steps of one kind in a row (two additions, two exclusive-ors)
come out of the compiler as one, so they are read as one.
The chain of a function is read from its code: the function is run for all 256 input bytes, and each time an
instruction leaves a new one-to-one byte value in the register it writes, the step that leads there from the value
before is named. A function whose code has a step this file does not know is left out; every generated function is
compiled and compared with the client like any other (gen_sources.verify).

Names of the generated functions are ours: <kind>_<rva>.
"""
import re

BASE = 0x580000
CURSOR_AT, CURSOR, OUT, END = 0x60000000, 0x40000000, 0x50000000, 0x70000000
R32 = ('eax', 'ecx', 'edx', 'ebx', 'esi', 'edi', 'ebp')
R8 = {'al': 'eax', 'cl': 'ecx', 'dl': 'edx', 'bl': 'ebx',
      'ah': 'eax', 'ch': 'ecx', 'dh': 'edx', 'bh': 'ebx'}
R8_SHIFT = {'ah': 8, 'ch': 8, 'dh': 8, 'bh': 8}
REV = [int(f'{b:08b}'[::-1], 2) for b in range(256)]


def swap(v, n, mask):
    """Neighbouring groups of n bits change places."""
    return (v >> n) & mask | (v & mask) << n


class Unknown(Exception):
    pass


def number(t):
    return int(t, 16) if t.startswith('0x') else int(t)


def run(lines, img, x, args, init=None, lenient=False):
    """Run straight-line code for input byte x. args: stack offset -> value of that argument; init: register values
    at the start; lenient: a line this does not know is passed over (code around the chain that does not feed it).
    -> (value of every register after each line, the byte stored through the output pointer)."""
    reg = dict.fromkeys(R32, 0)
    reg.update(init or {})
    out = [None]
    trace = []

    def get(o):
        if o in R32:
            return reg[o]
        if o in R8:
            return (reg[R8[o]] >> R8_SHIFT.get(o, 0)) & 0xff
        m = re.fullmatch(r'(byte|dword) ptr \[(\w+)(?: \+ (\w+))?\]', o)
        if m:
            base, disp = m[2], number(m[3]) if m[3] else 0
            if base == 'esp' and disp in args:
                return args[disp]
            if base in R32:
                a = reg[base]
                if m[1] == 'dword' and a == CURSOR_AT and not disp:
                    return CURSOR
                if m[1] == 'byte' and a == CURSOR and not disp:
                    return x
                if m[1] == 'byte' and disp >= BASE and a < 256:         # a table of the client's own data
                    return img[disp - BASE + a]
            raise Unknown(o)
        return number(o)

    def put(o, v):
        if o in R32:
            reg[o] = v & 0xffffffff
        elif o in R8:
            shift = R8_SHIFT.get(o, 0)
            reg[R8[o]] = reg[R8[o]] & ~(0xff << shift) | (v & 0xff) << shift
        else:
            m = re.fullmatch(r'(byte|dword) ptr \[(\w+)\]', o)
            if m and m[1] == 'byte' and reg.get(m[2]) in (OUT, CURSOR):
                out[0] = v & 0xff
            elif not (m and m[1] == 'dword' and reg.get(m[2]) == CURSOR_AT):
                raise Unknown(o)

    def step(line):
        _step(line, reg, get, put)

    for line in lines:
        try:
            step(line)
        except (Unknown, ValueError):
            if not lenient:
                raise Unknown(line)
        trace.append(dict(reg))
    return trace, out[0]


def _step(line, reg, get, put):
    if True:
        op, _, rest = line.partition(' ')
        o = [t.strip() for t in rest.split(',')] if rest else []
        bits = 8 if o and o[0] in R8 else 32
        if op in ('cmp', 'test') or op.startswith('j'):
            pass                                                    # the bounds check: the read is taken
        elif op in ('mov', 'movzx'):
            put(o[0], get(o[1]))
        elif op in ('add', 'sub', 'xor', 'and', 'or'):
            a, b = get(o[0]), get(o[1])
            put(o[0], {'add': a + b, 'sub': a - b, 'xor': a ^ b, 'and': a & b, 'or': a | b}[op])
        elif op == 'imul' and len(o) == 3:
            put(o[0], get(o[1]) * get(o[2]))
        elif op in ('shr', 'shl'):
            a, n = get(o[0]), get(o[1])
            put(o[0], a >> n if op == 'shr' else a << n)
        elif op in ('rol', 'ror') and bits == 8:
            a, n = get(o[0]), get(o[1]) % 8
            n = n if op == 'rol' else 8 - n
            put(o[0], a << n | a >> (8 - n))
        elif op == 'not':
            put(o[0], ~get(o[0]))
        elif op == 'neg':
            put(o[0], -get(o[0]))
        elif op in ('inc', 'dec'):
            put(o[0], get(o[0]) + (1 if op == 'inc' else -1))
        else:
            raise Unknown(line)


def chain_of(lines, img, args, init=None, result=None, lenient=False):
    """The chain of byte steps of straight-line code, as (step, operand) pairs, or None when a step is not known.
    result: the register that holds the chain's value at the end (default: the byte stored through the output
    pointer)."""
    try:
        runs = [run(lines, img, x, args, init, lenient) for x in range(256)]
    except (Unknown, ValueError, KeyError, IndexError):
        return None
    cur = list(range(256))
    steps = []
    for k, line in enumerate(lines):
        op, _, rest = line.partition(' ')
        dest = rest.split(',')[0].strip()
        r = R8.get(dest, dest)
        if r not in R32 or op in ('cmp', 'test') or op.startswith('j'):
            continue
        new = [(runs[x][0][k][r] >> R8_SHIFT.get(dest, 0)) & 0xff for x in range(256)]
        if new == cur or len(set(new)) != 256:
            continue
        table = re.search(r'byte ptr \[\w+ \+ (0x[0-9a-f]+)\]', line)
        add = (new[0] - cur[0]) & 0xff
        rsub = (new[0] + cur[0]) & 0xff
        if table and all(new[x] == img[int(table[1], 16) - BASE + cur[x]] for x in range(256)):
            steps.append(('table', int(table[1], 16)))
        elif op in ('rol', 'ror'):
            n = number(rest.split(',')[1].strip())
            s = n if op == 'rol' else 8 - n
            if not all(new[x] == (cur[x] << s | cur[x] >> (8 - s)) & 0xff for x in range(256)):
                return None
            steps.append((op, n))
        elif all(new[x] == REV[cur[x]] for x in range(256)):
            steps.append(('rev', 0))
        elif all(new[x] == cur[x] ^ (new[0] ^ cur[0]) for x in range(256)):
            k = new[0] ^ cur[0]
            # the complement has two codes in the client: `not` for one step, `xor r8, 0xff` where two exclusive-or
            # steps in a row have constants that make 0xff together (the compiler joins them late)
            steps.append(('not', 0) if op == 'not' else ('xor2', k) if k == 0xff else ('xor', k))
        elif all(new[x] == (cur[x] + add) & 0xff for x in range(256)):
            steps.append(('sub', 256 - add) if op == 'sub' else ('add', add))
        elif all(new[x] == (rsub - cur[x]) & 0xff for x in range(256)):
            steps.append(('rsub', rsub))
        elif all(new[x] == swap(cur[x], 1, 0x55) for x in range(256)):
            steps.append(('swap', 1))
        elif all(new[x] == swap(cur[x], 2, 0x33) for x in range(256)):
            steps.append(('swap', 2))
        else:                       # a one-to-one value on the way to a step: not a step by itself
            continue
        cur = new
    final = [runs[x][0][-1][result] & 0xff if result else runs[x][1] for x in range(256)]
    return steps if final == cur else None


def pick(candidates, tables, prelude=(), symbol='?Try_{rva:x}_{k}@'):
    """candidates: rva -> list of function texts, each with the name NAME. All are compiled in one file and compared
    with the client; -> rva -> index of the first text that gives the client's function. prelude: lines the texts
    need before them; symbol: the text that names candidate k of a function among the object's symbols."""
    import os
    import match_func as M
    path = os.path.join(M.OUT, 'field_candidates.cpp')
    lines = ['#include "../src/FieldCodec.h"'] + [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)]
    lines += list(prelude)
    for rva, texts in sorted(candidates.items()):
        lines += [t.replace('NAME', f'Try_{rva:x}_{k}') for k, t in enumerate(texts)]
    with open(path, 'w', newline=chr(10), encoding='utf-8') as f:
        f.write(chr(10).join(lines) + chr(10))
    obj = M.compile_obj(path, M.FLAGS)
    found = {}
    for rva, texts in sorted(candidates.items()):
        for k in range(len(texts)):
            try:
                query = symbol(rva, k) if callable(symbol) else symbol.format(rva=rva, k=k)
                if M.compare(path, query, rva, M.FLAGS, obj)[3] is None:
                    found[rva] = k
                    break
            except SystemExit:
                pass
    if not os.environ.get('KEEP_CANDIDATES'):          # kept for looking at a candidate that does not come out
        os.remove(path)
    return found


def statement_list(steps):
    """The C++ statements of a chain on the byte x, one text per step."""
    return [statements([step]) for step in steps]


def statements(steps):
    """The C++ statements of a chain on the byte x."""
    out = []
    for step, v in steps:
        out.append({'add': f'x += {v:#x};', 'sub': f'x -= {v:#x};', 'xor': f'x ^= {v:#x};',
                    'rol': f'x = Rol(x, {v});', 'ror': f'x = Ror(x, {v});', 'rev': 'x = Rev(x);',
                    'rsub': f'x = (u8)({v:#x} - x);', 'table': f'x = g_{v:x}[x];',
                    'swap': f'x = Swap{v}(x);', 'not': 'x = ~x;',
                    # which two constants the client's source has is not known: any two that make 0xff give its code
                    'xor2': 'x ^= 0xf; x ^= 0xf0;'}[step])
    return ' '.join(out)


def equivalent_bit_chains(steps, limit=16):
    """Move XORs across bit permutations without changing any byte value.

    The optimizer sometimes moves the XOR into one arm of a swap. Reading that instruction order can recover
    an equivalent chain whose source schedules differently; compile both orders rather than assuming either.
    """
    from collections import deque
    start = tuple(steps)
    queue, seen = deque([start]), {start}
    result = []
    def permute(value, op, operand, inverse=False):
        if op == 'rev':
            return REV[value]
        if op == 'swap':
            return swap(value, operand, 0x55 if operand == 1 else 0x33)
        shift = operand if op == 'rol' else 8 - operand
        if inverse:
            shift = 8 - shift
        shift %= 8
        return (value << shift | value >> ((8 - shift) % 8)) & 0xff
    while queue and len(result) < limit:
        chain = queue.popleft()
        result.append(list(chain))
        for k in range(len(chain) - 1):
            a, b = chain[k:k + 2]
            if a[0] in ('xor', 'xor2', 'not') and b[0] in ('rev', 'swap', 'rol', 'ror'):
                value = 255 if a[0] == 'not' else a[1]
                moved = (b, (a[0], 0 if a[0] == 'not' else permute(value, *b)))
            elif b[0] in ('xor', 'xor2', 'not') and a[0] in ('rev', 'swap', 'rol', 'ror'):
                value = 255 if b[0] == 'not' else b[1]
                moved = ((b[0], 0 if b[0] == 'not' else permute(value, *a, inverse=True)), a)
            else:
                continue
            candidate = chain[:k] + moved + chain[k + 2:]
            if candidate not in seen:
                seen.add(candidate)
                queue.append(candidate)
    return result


def reverse_source_forms(steps):
    """Byte and promoted-byte parameter forms of the same reverse operation, independently per occurrence."""
    code = statements(steps)
    count = sum(op == 'rev' for op, _ in steps)
    for mask in range(1 << count):
        index = [0]
        def select(match):
            promoted = mask & (1 << index[0])
            index[0] += 1
            return 'RevPromoted((u8)x)' if promoted else match[0]
        yield re.sub(r'Rev\(x\)', select, code)


HEAD = ['mov edx, dword ptr [esp + 8]', 'mov eax, dword ptr [edx]', 'cmp eax, dword ptr [esp + 0xc]']
TAIL = ['mov al, 1', 'ret', 'xor al, al', 'ret']


def byte_readers(im):
    """bool Read(u8* out, const u8** cursor, const u8* end): one byte taken from the cursor, through the field's
    chain, into *out; false when the cursor is at the end."""
    defs, matches, tables, seen, candidates, chains = [], [], set(), 0, {}, {}
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000:
            continue
        n = im.size(s)
        if not 30 <= n <= 400:
            continue
        text = im.text(s)
        if not text:
            continue
        lines = text.split(chr(10))
        head = re.fullmatch(r'mov (ecx|edx), dword ptr \[esp \+ 8\]', lines[0])
        if (not head or lines[1:3] != [f'mov eax, dword ptr [{head[1]}]', HEAD[2]]
                or lines[-4:] != TAIL or not lines[3].startswith('jae ')):
            continue
        seen += 1
        steps = chain_of(lines[:-4], im.img, {4: OUT, 8: CURSOR_AT, 0xc: END})
        if steps is None:
            continue
        tables.update(v for step, v in steps if step == 'table')
        chains[s] = steps
        # where among the chain's statements the cursor is written back shows in the code: every place is tried
        st = statement_list(steps)
        candidates[s] = [
            'bool NAME(u8* out, const u8** cursor, const u8* end) { const u8* p = *cursor; if (p < end) { u8 x = *p; '
            + ' '.join(st[:k] + ['*cursor = p + 1;'] + st[k:]) + ' *out = x; return true; } return false; }'
            for k in range(len(st) + 1)]
    found = pick(candidates, tables)
    alternatives = {}
    for s in candidates.keys() - found.keys():
        forms = []
        for variant in equivalent_bit_chains(chains[s]):
            for typ in ('u8', 'u32'):
                if variant == chains[s] and typ == 'u8':
                    continue
                # A wide temporary keeps the original MOVZX load. Table indexes still refer to one byte;
                # permutations take u8 and output assignment truncates, so all intermediate low bytes agree.
                st = [line.replace('[x]', '[(u8)x]') if typ == 'u32' else line
                      for line in statement_list(variant)]
                forms += ['bool NAME(u8* out, const u8** cursor, const u8* end) { const u8* p = *cursor; '
                          f'if (p < end) {{ {typ} x = *p; '
                          + ' '.join(st[:k] + ['*cursor = p + 1;'] + st[k:])
                          + ' *out = x; return true; } return false; }' for k in range(len(st) + 1)]
        if forms:
            alternatives[s] = forms
    for s, k in pick(alternatives, tables).items() if alternatives else ():
        found[s] = len(candidates[s]) + k
        candidates[s] += alternatives[s]
    for s, k in sorted(found.items()):
        defs.append(candidates[s][k].replace('NAME', f'ReadByte_{s:x}') + f'    // @{s:x}')
        matches.append(f'// match: {s:x} ?ReadByte_{s:x}@@YA_NPAEPAPBEPBE@Z')
    out = ['// Readers of one encoded byte of a packet field (generated by tools/gen_sources.py, tools/gen_fields.py, from',
           '// the client: each function\'s chain of byte steps is read from its code). Function names are ours:',
           f'// ReadByte_<rva>. {len(matches)} of the {seen} functions of this shape are written.']
    out += matches + ['#include "../FieldCodec.h"', '']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + [''] + defs
    return out, len(matches)


VARINT_TAIL = ['mov eax, dword ptr [edi]', 'add esi, 7', 'cmp eax, ebx', 'jb', 'pop edi', 'pop esi', 'pop ebp',
               'xor al, al', 'pop ebx', 'ret', 'pop edi', 'pop esi', 'pop ebp', 'mov al, 1', 'pop ebx', 'ret']


def varint_readers(im):
    """bool Read(T* out, const u8** cursor, const u8* end): a number of 7 bits per byte, lowest first, the top bit of
    a byte saying another follows; every byte goes through the field's chain first."""
    defs, matches, tables, seen, candidates, kinds = [], [], set(), 0, {}, {}
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000:
            continue
        if not 60 <= im.size(s) <= 600:
            continue
        text = im.text(s)
        if not text:
            continue
        lines = text.split(chr(10))
        tail = [re.sub(r'^(j\w+) .*', r'\1', x) for x in lines[-16:]]
        if tail != VARINT_TAIL or len(lines) < 30 or not re.fullmatch(r'jns 0x[0-9a-f]+', lines[-17]):
            continue
        test = re.fullmatch(r'test (\wl), \1', lines[-18])
        loads = [k for k, x in enumerate(lines) if re.fullmatch(r'mov \wl, byte ptr \[eax\]', x)]
        head = lines[:loads[0]] if loads else []
        kind = (32 if 'mov dword ptr [ebp], 0' in head else 16 if 'mov word ptr [ebp], ax' in head else 0)
        if not test or len(loads) != 1 or not kind or 'mov edi, dword ptr [esp + 0x18]' not in head:
            continue
        seen += 1
        steps = chain_of(lines[loads[0]:-18], im.img, {}, {'eax': CURSOR, 'edi': CURSOR_AT}, R8[test[1]], True)
        if steps is None:
            continue
        tables.update(v for step, v in steps if step == 'table')
        st = statement_list(steps)
        head = f'bool NAME(u{kind}* out, const u8** cursor, const u8* end) {{ *out = 0; for (int i = 0; *cursor < end; ++i) {{ '
        tail = f' *out |= (u{kind})((x & 0x7f) << (i * 7)); if (!(x & 0x80)) return true; }} return false; }}'
        # the cursor moved on in the read itself, or written back at some place among the chain's statements
        candidates[s] = [head + 'u8 x = *(*cursor)++; ' + ' '.join(st) + tail] + [
            head + 'const u8* p = *cursor; u8 x = *p; ' + ' '.join(st[:k] + ['*cursor = p + 1;'] + st[k:]) + tail
            for k in range(len(st) + 1)]
        kinds[s] = kind
    for s, k in sorted(pick(candidates, tables).items()):
        defs.append(candidates[s][k].replace('NAME', f'ReadVarint{kinds[s]}_{s:x}') + f'    // @{s:x}')
        matches.append(f'// match: {s:x} ?ReadVarint{kinds[s]}_{s:x}@')
    out = ['// Readers of an encoded variable-length number of a packet field (generated by tools/gen_sources.py,',
           "// tools/gen_fields.py, from the client: each function's chain of byte steps is read from its code). Function",
           f'// names are ours: ReadVarint<bits>_<rva>. {len(matches)} of the {seen} functions of this shape are written.']
    out += matches + ['#include "../FieldCodec.h"', '']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + [''] + defs
    return out, len(matches)


def known_readers():
    """rva -> (name, type of *out) of the readers the generated field files define."""
    import glob
    import os
    out = {}
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client-src', 'src', 'gen', 'Field*.cpp')
    for path in glob.glob(here):
        with open(path, encoding='utf-8') as f:
            for m in re.finditer(r'^(?:bool|char) (Read\w+_([0-9a-f]+))\((u\d+)\* out', f.read(), re.M):
                out[int(m[2], 16)] = (m[1], m[3])
    return out


def field_wrappers(im):
    """bool Read(T* out, const u8** cursor, const u8* end): the value is read by another reader, then every byte of
    it is put through the field's second chain where it lies - the form the field keeps in memory."""
    known = {k: v for k, v in known_readers().items() if not v[0].startswith('ReadField')}
    defs, matches, tables, decls, seen = [], [], set(), {}, 0
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000:
            continue
        if not 60 <= im.size(s) <= 900:
            continue
        text = im.text(s)
        if not text:
            continue
        lines = text.split(chr(10))
        calls = [k for k, x in enumerate(lines) if x.startswith('call ')]
        if (len(calls) != 1 or calls[0] > 9 or lines[0] not in ('push ebx', 'push esi')
                or 'push esi' not in lines[:calls[0]]):
            continue
        c = calls[0]
        lea = re.fullmatch(r'lea (edi|edx), \[esi \+ (\d+)\]', lines[c + 1])
        status = re.fullmatch(r'mov (bl|ah|cl|dl), al', lines[c + 3])
        if (not lea or lines[c + 2] != 'add esp, 0xc' or not status
                or lines[c + 4] != f'cmp esi, {lea[1]}'):
            continue
        loop = c + 6
        if lines[loop] == 'push ebx':
            loop += 1
        if not lines[c + 5].startswith('je ') or not re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[esi\]', lines[loop]):
            continue
        stores = [k for k, x in enumerate(lines) if re.fullmatch(r'mov byte ptr \[esi\], \wl', x)]
        if len(stores) != 1 or lines[stores[0] + 1:stores[0] + 3] != ['inc esi', f'cmp esi, {lea[1]}']:
            continue
        rest = [x for x in lines[stores[0] + 4:] if not x.startswith('pop ')]
        if not lines[stores[0] + 3].startswith('jne ') or rest != [f'mov al, {status[1]}', 'ret']:
            continue
        seen += 1
        size = int(lea[2])
        steps = chain_of(lines[loop:stores[0] + 1], im.img, {}, {'esi': CURSOR})
        if steps is None or size not in (1, 2, 4, 8):
            continue
        target = int(lines[c].split()[1], 16)
        name, typ = known.get(target, (f'Read_{target:x}', f'u{size * 8}'))
        if int(typ[1:]) != size * 8:
            continue
        if target not in known:
            decls[target] = f'bool {name}({typ}* out, const u8** cursor, const u8* end);'
        tables.update(v for step, v in steps if step == 'table')
        # the packet readers turn what these give back into a bool (`test al, al; setne al`): it is not a bool
        defs.append(f'char ReadField{size * 8}_{s:x}({typ}* out, const u8** cursor, const u8* end) {{ '
                    f'char ok = {name}(out, cursor, end); '
                    f'for (u8* b = (u8*)out; b != (u8*)out + sizeof(*out); ++b) {{ u8 x = *b; {statements(steps)} *b = x; }} '
                    f'return ok; }}    // @{s:x}')
        matches.append(f'// match: {s:x} ?ReadField{size * 8}_{s:x}@')
    out = ['// Readers of a packet field in its in-memory form (generated by tools/gen_sources.py, tools/gen_fields.py, from',
           '// the client): the value comes from another reader, then each of its bytes goes through a second chain in',
           f'// place. Function names are ours: ReadField<bits>_<rva>. {len(matches)} of the {seen} functions of this shape',
           '// are written.']
    out += matches + ['#include "../FieldCodec.h"', '']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + ['']
    out += sorted(f'bool {n}({t}* out, const u8** cursor, const u8* end);' for k, (n, t) in known.items()) + ['']
    out += [decls[k] for k in sorted(decls)] + [''] + defs
    return out, len(matches)


def validated_field_wrappers(im):
    """An encoded one-byte enum: read its wire value, validate its range, substitute a global default on failure,
    then encode its memory value in either case. The successful path's tests describe the range; only tests
    branching to the default are used. First measured on rva 0x79c490."""
    known, cands, tables, decls, seen = known_readers(), {}, set(), set(), 0
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000 or not 70 <= im.size(s) <= 700:
            continue
        text = im.text(s) or ''
        lines = text.split('\n')
        calls = [k for k, x in enumerate(lines) if re.fullmatch(r'call 0x[0-9a-f]+', x)]
        globals_ = [k for k, x in enumerate(lines) if re.fullmatch(r'mov al, byte ptr \[0x[0-9a-f]+\]', x)]
        if len(calls) != 1 or len(globals_) != 1 or not text.startswith('push ebx\npush esi\n'):
            continue
        call, default = calls[0], globals_[0]
        if call > 12 or default < call or 'lea edi, [esi + 1]' not in lines[default:] \
                or not text.endswith('mov al, bl\npop ebx\nret'):
            continue
        loads = [k for k in range(default + 1, len(lines))
                 if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[esi\]', lines[k])]
        stores = [k for k in range(default + 1, len(lines))
                  if re.fullmatch(r'mov byte ptr \[esi\], \wl', lines[k])]
        if len(loads) != 1 or len(stores) != 2 or stores[-1] < loads[0]:
            continue
        instructions = list(im.md.disasm(im.img[s:s + im.size(s)], s))
        fail = instructions[default].address
        conditions, valid = [], True
        for k in range(call + 1, default - 1):
            branch = re.fullmatch(r'j(\w+) (0x[0-9a-f]+)', lines[k + 1])
            if not branch or number(branch[2]) != fail:
                continue
            if lines[k] == 'test al, al' and branch[1] == 'e':
                conditions.append('ok' if not conditions else '*out != 0')
            else:
                limit = re.fullmatch(r'cmp al, (0x[0-9a-f]+|\d+)', lines[k])
                sign = {'ae': '<', 'a': '<=', 'b': '>=', 'be': '>', 'e': '!=', 'ne': '=='}.get(branch[1])
                if not limit or not sign:
                    valid = False
                    break
                conditions.append(f'*out {sign} {number(limit[1]):#x}')
        if not valid or not conditions or conditions[0] != 'ok':
            continue
        seen += 1
        steps = chain_of(lines[loads[0]:stores[-1] + 1], im.img, {}, {'esi': CURSOR})
        if steps is None:
            continue
        tables.update(v for step, v in steps if step == 'table')
        glob = number(re.search(r'\[(0x[0-9a-f]+)\]', lines[default])[1])
        target = number(lines[call].split()[1])
        name, typ = known.get(target, (f'Read_{target:x}', 'u8'))
        if typ != 'u8':
            continue
        decls.update([f'bool {name}(u8* out, const u8** cursor, const u8* end);', f'extern u8 g_{glob:x};'])
        condition = ' && '.join(conditions).replace('ok', f'{name}(out, cursor, end)', 1)
        cands[s] = [f'char NAME(u8* out, const u8** cursor, const u8* end) {{ bool ok = {condition}; '
                    f'if (!ok) *out = g_{glob:x}; '
                    f'for (u8* b = out; b != out + sizeof(*out); ++b) {{ u8 x = *b; {statements(steps)} *b = x; }} '
                    'return ok; }']
    found = pick(cands, tables, sorted(decls))
    out = ['// Enum field readers: validate the wire value, substitute its default on failure, then encode its',
           '// in-memory value (generated by tools/gen_sources.py, tools/gen_fields.py, from the client).',
           f'// {len(found)} of {seen} candidates are identical. Names are ours: ReadValidated8_<rva>.']
    out += [f'// match: {s:x} ?ReadValidated8_{s:x}@' for s in sorted(found)]
    out += ['#include "../FieldCodec.h"', '']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + sorted(decls) + ['']
    out += [cands[s][k].replace('NAME', f'ReadValidated8_{s:x}') for s, k in sorted(found.items())]
    return out, len(found)


def inline_field_wrappers(im):
    """One-byte stored fields whose wire reader was inlined before the memory-encoding loop."""
    cands, tables = {}, set()
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000 or not 45 <= im.size(s) <= 700:
            continue
        text = im.text(s) or ''
        if (not text.startswith('mov eax, dword ptr [esp + 4]\npush ebx\npush esi\n') or 'call ' in text
                or re.search(r'byte ptr \[0x[0-9a-f]+\]', text)):
            continue
        lines = text.splitlines()
        stores = [k for k, line in enumerate(lines) if re.fullmatch(r'mov byte ptr \[eax\], \wl', line)]
        if len(stores) != 2 or not re.search(r'lea \w+, \[eax \+ 1\]', text):
            continue
        wire_load = next((k for k in range(stores[0])
                          if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[ecx\]', lines[k])), None)
        memory_load = next((k for k in range(stores[0] + 1, stores[1])
                            if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[eax\]', lines[k])), None)
        if wire_load is None or memory_load is None:
            continue
        wire = chain_of(lines[wire_load:stores[0] + 1], im.img, {},
                        {'ecx': CURSOR, 'eax': OUT, 'esi': CURSOR_AT})
        memory = chain_of(lines[memory_load:stores[1] + 1], im.img, {}, {'eax': CURSOR})
        if wire is None or memory is None:
            continue
        tables.update(v for op, v in wire + memory if op == 'table')
        cands[s] = []
        for typ in ('u8', 'u32'):
            st = [line.replace('[x]', '[(u8)x]') if typ == 'u32' else line for line in statement_list(wire)]
            for k in range(len(st) + 1):
                helper = ('__forceinline bool Wire_NAME(u8* out, const u8** cursor, const u8* end) { '
                          f'const u8* p = *cursor; if (p < end) {{ {typ} x = *p; '
                          + ' '.join(st[:k] + ['*cursor = p + 1;'] + st[k:])
                          + ' *out = x; return true; } return false; }')
                body = ('char NAME(u8* out, const u8** cursor, const u8* end) { '
                        'bool ok = Wire_NAME(out, cursor, end); '
                        f'for (u8* b = out; b != out + sizeof(*out); ++b) {{ u8 x = *b; {statements(memory)} *b = x; }} '
                        'return ok; }')
                cands[s].append(helper + '\n' + body)
    found = pick(cands, tables)
    lines = ['// One-byte fields with an inlined wire reader and a separate memory-encoding loop.',
             '// Generated by tools/gen_sources.py, tools/gen_fields.py; both byte codecs come from the client.',
             f'// {len(found)} of {len(cands)} readers are identical. Names are ours: ReadField8_<rva>.']
    lines += [f'// match: {s:x} ?ReadField8_{s:x}@' for s in sorted(found)]
    lines += ['#include "../FieldCodec.h"'] + [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + ['']
    lines += [cands[s][k].replace('NAME', f'ReadField8_{s:x}') for s, k in sorted(found.items())]
    return lines, len(found)


def inline_validated_field_wrappers(im):
    """Enum validation with the wire reader inlined; both byte codecs are extracted independently."""
    cands, tables, decls = {}, set(), set()
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000 or not 70 <= im.size(s) <= 700:
            continue
        text = im.text(s) or ''
        if not text.startswith('mov eax, dword ptr [esp + 4]\npush ebx\npush esi\n') or 'call ' in text:
            continue
        lines = text.splitlines()
        defaults = [k for k, line in enumerate(lines)
                    if re.fullmatch(r'mov \wl, byte ptr \[0x[0-9a-f]+\]', line)]
        stores = [k for k, line in enumerate(lines) if re.fullmatch(r'mov byte ptr \[eax\], \wl', line)]
        wire_loads = [k for k, line in enumerate(lines) if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[ecx\]', line)]
        if len(defaults) != 1 or len(stores) != 3 or not wire_loads:
            continue
        default, wire_store, memory_store = defaults[0], stores[0], stores[-1]
        if not wire_loads[0] < wire_store < default < stores[1] < memory_store:
            continue
        memory_load = next((k for k in range(default + 1, memory_store)
                            if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[eax\]', lines[k])), None)
        if memory_load is None or not re.search(r'cmp ecx, dword ptr \[esp \+ (?:0x14|0x18)\]\njae ', text):
            continue
        ins = list(im.md.disasm(im.img[s:s + im.size(s)], s))
        fail, output_reg = ins[default].address, lines[wire_store].split(', ')[1]
        tests = []
        valid = True
        for k in range(wire_store + 1, default):
            branch = re.fullmatch(r'j(\w+) (0x[0-9a-f]+)', lines[k])
            if not branch or number(branch[2]) != fail:
                continue
            if branch[1] == 'e' and (k == wire_store + 1 or lines[k - 1] == f'test {output_reg}, {output_reg}'):
                tests.append('*out != 0')
                continue
            limit = re.fullmatch(r'cmp ' + output_reg + r', (0x[0-9a-f]+|\d+)', lines[k - 1])
            sign = {'ae': '<', 'a': '<=', 'b': '>=', 'be': '>', 'e': '!=', 'ne': '=='}.get(branch[1])
            if not limit or not sign:
                valid = False
                break
            tests.append(f'*out {sign} {number(limit[1]):#x}')
        if not valid or not tests:
            continue
        wire = chain_of(lines[wire_loads[0]:wire_store + 1], im.img, {},
                        {'ecx': CURSOR, 'eax': OUT, 'esi': CURSOR_AT})
        memory = chain_of(lines[memory_load:memory_store + 1], im.img, {}, {'eax': CURSOR})
        if wire is None or memory is None:
            continue
        glob = number(re.search(r'\[(0x[0-9a-f]+)\]', lines[default])[1])
        decls.add(f'extern u8 g_{glob:x};')
        tables.update(v for op, v in wire + memory if op == 'table')
        st = statement_list(wire)
        cands[s] = []
        for typ in ('u8', 'u32'):
            wire_statements = [line.replace('[x]', '[(u8)x]') if typ == 'u32' else line for line in st]
            for k in range(len(st) + 1):
                helper = ('__forceinline bool Wire_NAME(u8* out, const u8** cursor, const u8* end) { '
                          f'const u8* p = *cursor; if (p < end) {{ {typ} x = *p; '
                          + ' '.join(wire_statements[:k] + ['*cursor = p + 1;'] + wire_statements[k:])
                          + ' *out = x; return true; } return false; }')
                condition = ' && '.join(['Wire_NAME(out, cursor, end)'] + tests)
                body = (f'char NAME(u8* out, const u8** cursor, const u8* end) {{ bool ok = {condition}; '
                        f'if (!ok) *out = g_{glob:x}; '
                        f'for (u8* b = out; b != out + sizeof(*out); ++b) {{ u8 x = *b; {statements(memory)} *b = x; }} '
                        'return ok; }')
                cands[s].append(helper + '\n' + body)
    found = pick(cands, tables, sorted(decls))
    lines = ['// Enum readers with an inlined wire codec, range checks and a separately encoded stored value.',
             '// Generated by tools/gen_sources.py, tools/gen_fields.py; both codecs come from the client.',
             f'// {len(found)} of {len(cands)} readers are identical. Names are ours: ReadValidated8_<rva>.']
    lines += [f'// match: {s:x} ?ReadValidated8_{s:x}@' for s in sorted(found)]
    lines += ['#include "../FieldCodec.h"'] + sorted(decls)
    lines += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + ['']
    lines += [cands[s][k].replace('NAME', f'ReadValidated8_{s:x}') for s, k in sorted(found.items())]
    return lines, len(found)


UINT = {1: 'u8', 2: 'u16', 4: 'u32', 8: 'u64'}
READ_HEAD = ('if (!Packet::Read(cursor, end)) return false; const u8* p = *cursor; '
             'if ((u32)(end - p) < 1) return false; *cursor = p + 1;')


def vector_destructors(im):
    """Vectors of objects destroyed through virtual slot 3, alone or inside an object whose compiler-generated
    scalar deleting destructor destroys the vector and conditionally frees the enclosing object. Layout comes
    from the element stride, the three storage members and the sized delete; no destructor is written by hand
    to imitate the compiler's deleting destructor."""
    cands, symbols, seen = {}, {}, 0
    for s in im.starts:
        if s in im.done or not 0x1000 <= s < 0xbc0000 or not 45 <= im.size(s) <= 160:
            continue
        text = im.text(s) or ''
        deleting = 'call 0x9bb940' in text
        loops = text.count('call dword ptr [eax + 0xc]')
        if loops not in (0, 1) or 'call 0x9bb930' not in text or (not loops and not deleting):
            continue
        stride = re.findall(r'^add esi, (0x[0-9a-f]+|\d+)$', text, re.M)
        data = re.search(r'^mov esi, dword ptr \[(ebx|edi)(?: \+ (0x[0-9a-f]+|\d+))?\]$', text, re.M)
        if loops:
            if len(stride) != 1 or not data:
                continue
            size, off = number(stride[0]), number(data[2]) if data[2] else 0
            if size <= 4 or size > 4096:
                continue
            reg = data[1]
            addr = lambda n: f'{reg} + {str(n) if n < 10 else hex(n)}' if n else reg
            # The free must refer to the data member, with the sign bit of capacity governing ownership.
            if f'cmp dword ptr [{addr(off + 8)}], 0' not in text or f'push dword ptr [{addr(off)}]' not in text:
                continue
        else:
            this = re.search(r'^mov (esi|edi), ecx$', text, re.M)
            if not this:
                continue
            reg, off, size = this[1], None, None
        vtables = re.findall(r'mov dword ptr \[' + reg + r'\], (0x[0-9a-f]+)', text)
        if vtables and vtables != ['0x1533474']:
            continue
        bin_base = bool(vtables)
        seen += 1
        if deleting:
            total = re.search(r'push (0x[0-9a-f]+|\d+)\npush ' + reg + r'\ncall 0x9bb940', text)
            if not total or (loops and (off < 4 or number(total[1]) < off + 12)):
                continue
            members = {off: (f'PacketVectorStorage<{size}>', 12)} if loops else {}
            initializers, understood = [], True
            calls = re.findall(r'lea ecx, \[' + reg + r' \+ (0x[0-9a-f]+|\d+)\]\ncall (0x[0-9a-f]+)', text)
            for loc, target in calls:
                loc, target = number(loc), number(target)
                if target == 0x9bab90:
                    members[loc] = ('RString', 12)
                    initializers.append(f'member{loc:x}("")')
                else:
                    dt = im.text(target) or ''
                    step = re.search(r'^add esi, (0x[0-9a-f]+|\d+)$', dt, re.M)
                    if not step or 'call dword ptr [eax + 0xc]' not in dt or not dt.endswith('ret'):
                        understood = False
                        break
                    members[loc] = (f'PacketVectorExternal<{number(step[1])}>', 12)
            # Additional frees without element destruction are vectors of trivial values.
            for cap, loc in re.findall(r'cmp dword ptr \[' + reg + r' \+ (0x[0-9a-f]+|\d+)\], 0\n'
                                       r'jl 0x[0-9a-f]+\npush dword ptr \[' + reg +
                                       r' \+ (0x[0-9a-f]+|\d+)\]\ncall 0x9bb930', text):
                if number(cap) == number(loc) + 8 and number(loc) != off:
                    members[number(loc)] = ('PacketTrivialVectorStorage', 12)
            if not understood or not members or text.count('call ') != loops + 1 + len(calls) + sum(
                    typ != 'RString' and not typ.startswith('PacketVectorExternal') for typ, _ in members.values()):
                continue
            fields, pos = [], 4
            for loc, (typ, length) in sorted(members.items()):
                if loc < pos or loc + length > number(total[1]):
                    understood = False
                    break
                if loc > pos:
                    fields.append(f'u8 gap{pos:x}[{loc - pos}];')
                fields.append(f'{typ} member{loc:x};')
                pos = loc + length
            if not understood:
                continue
            if pos < number(total[1]):
                fields.append(f'u8 gap{pos:x}[{number(total[1]) - pos}];')
            fields = ' '.join(fields)
            constructor = ' NAME() : ' + ', '.join(initializers) + ' {}' if initializers else ''
            prefix = ('struct NAME : BinObject { const MetaClass* GetClass() const override; ~NAME() = default; '
                      if bin_base else 'struct NAME { virtual void Slot0(); virtual void Slot1(); '
                      'virtual void Slot2(); virtual ~NAME() = default; ')
            body = ('#pragma pack(push, 1)\n' + prefix + fields + constructor + ' };\n#pragma pack(pop)\n'
                    'NAME* Make_NAME() { return new NAME; }')
            symbols[s] = '??_GVectorOwner_{s:x}@@'
            cands[s] = [body]
        elif off == 0 and text.endswith('ret') and text.count('call ') == 2:
            # Clear() and a destructor share the loop; Clear() also zeroes storage afterwards.
            clear = f'mov dword ptr [{reg}], 0' in text
            ending = ' data = nullptr; count = 0; capacity = 0;' if clear else ''
            body = (f'struct NAME {{ PacketVectorElement<{size}>* data; u32 count; u32 capacity; '
                    + ('void Clear();' if clear else '~NAME();') + ' };\n'
                    + ('void NAME::Clear()' if clear else 'NAME::~NAME()') + ' { '
                    f'for (auto p = data, end = data + count; p < end; ++p) p->~PacketVectorElement<{size}>(); '
                    'if ((int)capacity >= 0) ::operator delete(data);' + ending + ' }')
            if clear:
                symbols[s] = '?Clear@VectorOwner_{s:x}@@'
            else:
                # MSVC's template integer decoration: 1..10 as 0..9, others as hexadecimal A..P.
                encoded = str(size - 1) if size <= 10 else ''.join(chr(65 + int(c, 16)) for c in f'{size:X}') + '@'
                symbols[s] = '??1?$PacketVectorExternal@$0' + encoded + '@@'
                body = (f'template <> PacketVectorExternal<{size}>::~PacketVectorExternal() {{ '
                        f'for (auto p = data, end = data + count; p < end; ++p) p->~PacketVectorElement<{size}>(); '
                        'if ((int)capacity >= 0) ::operator delete(data); }')
            cands[s] = [body]
    # These are classes, so pick's ordinary function-name prefix is replaced by their own destructor or Clear.
    import os
    import match_func as M
    path = os.path.join(M.OUT, 'vector_candidates.cpp')
    prelude = ['#include "../src/PacketVector.h"', '#include "../src/Meta.h"']
    lines = prelude + list(dict.fromkeys(texts[0].replace('NAME', f'VectorOwner_{s:x}')
                                        for s, texts in sorted(cands.items())))
    with open(path, 'w', newline='\n', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    obj = M.compile_obj(path, M.FLAGS)
    found = []
    for s in sorted(cands):
        sym = symbols[s].format(s=s)
        try:
            if M.compare(path, sym, s, M.FLAGS, obj)[3] is None:
                found.append(s)
        except SystemExit:
            pass
    out = ['// Destructors of vectors and objects containing one vector (generated by tools/gen_sources.py,',
           '// tools/gen_fields.py, from the element stride and storage layout in the client). Names are ours.',
           f'// {len(found)} of {seen} candidates are identical.']
    out += [f'// match: {s:x} {symbols[s].format(s=s)}' for s in found]
    out += ['#include "../PacketVector.h"', '#include "../Meta.h"', '']
    out += list(dict.fromkeys(cands[s][0].replace('NAME', f'VectorOwner_{s:x}') for s in found))
    if not os.environ.get('KEEP_CANDIDATES'):
        os.remove(path)
    return out, len(found)


def packet_readers(im):
    """Readers of whole packets of the simplest kinds: the header, one byte of bits, one field. Either a bit says
    the field is on the wire (a field reader is called) and otherwise it takes a default kept in a global, or the
    bit is the field's value; a value set by the reader is put through the field's in-memory chain where it lies."""
    known = known_readers()
    cands, texts, tables, prelude, seen = {}, {}, set(), set(), 0
    for s in im.starts:
        if s in im.done or not 0x780000 <= s < 0x940000 or not 100 <= im.size(s) <= 600:
            continue
        text = im.text(s)
        if not text or 'cmp eax, 6' not in text or not text.endswith('ret 8'):
            continue
        lines = text.split(chr(10))
        tests = [k for k, x in enumerate(lines) if re.fullmatch(r'test byte ptr \[\w+\], (0x[0-9a-f]+|\d+)', x)]
        calls = [x for x in lines if x.startswith('call ')]
        if len(tests) != 1 or len(calls) > 1:
            continue
        t = tests[0]
        mask = number(lines[t].split(', ')[1])
        lea = [re.fullmatch(r'lea eax, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x) for x in lines[t - 3:t]]
        lea = [m for m in lea if m and number(m[1]) >= 10]
        jump = next((x for x in lines[t + 1:t + 3] if re.match(r'j(e|ne) ', x)), None)
        loads = [k for k, x in enumerate(lines) if k > t and re.fullmatch(r'mov(zx)? \w+, byte ptr \[eax\]', x)]
        stores = [k for k, x in enumerate(lines) if k > t and re.fullmatch(r'mov byte ptr \[eax\], \wl', x)]
        stores = [k for k in stores if loads and k > loads[0]]
        size = next((number(m[1]) for m in (re.fullmatch(r'lea \w+, \[eax \+ (\d+)\]', x) for x in lines[t:t + 8])
                     if m), None)
        if not lea or not jump or not loads or not stores or size not in UINT:
            continue
        seen += 1
        steps = chain_of(lines[loads[0]:stores[0] + 1], im.img, {}, {'eax': CURSOR}, None, True)
        if steps is None:
            continue
        off, typ = number(lea[0][1]), UINT[size]
        tables.update(v for step, v in steps if step == 'table')
        pad = f'u8 pad[{off - 10}]; ' if off > 10 else ''
        head = (f'inline void Set_NAME(TYPE& field, const TYPE& value) {{ field = value; '
                f'for (u8* b = (u8*)&field; b != (u8*)&field + sizeof(field); ++b) {{ u8 x = *b; {statements(steps)} '
                f'*b = x; }} }}' + chr(10) + '#pragma pack(push, 1)' + chr(10) +
                f'struct NAME : Packet {{ {pad}TYPE field{off:x}; bool Read(const u8** cursor, const u8* end); }};'
                + chr(10) + '#pragma pack(pop)' + chr(10) +
                f'bool NAME::Read(const u8** cursor, const u8* end) {{ {READ_HEAD} ')
        field, bit = f'field{off:x}', f'*p & {mask:#x}'
        glob = [m for m in (re.fullmatch(r'mov \w+, (?:byte|word|dword) ptr \[(0x[0-9a-f]+)\]', x)
                            for x in lines[t:loads[0]]) if m]
        if len(calls) == 1 and glob and calls[0].startswith('call 0x'):
            # a bit says the field is on the wire; else the default, a global
            target = int(calls[0].split()[1], 16)
            name, rtyp = known.get(target, (f'Read_{target:x}', typ))
            if rtyp != typ:
                continue
            g = int(glob[0][1], 16)
            prelude.add(f'char {name}({typ}* out, const u8** cursor, const u8* end);')
            prelude.add(f'extern {typ} g_{g:x};')
            read = f'return {name}(&{field}, cursor, end) != 0;'
            default = f'Set_NAME({field}, g_{g:x}); return true;'
            wire_if_set = jump.startswith('jne')
            cands[s] = [(head + (f'if (!({bit})) {{ {default} }} {read} }}' if wire_if_set
                                 else f'if ({bit}) {{ {default} }} {read} }}')).replace('TYPE', typ),
                        (head + (f'if ({bit}) {{ {read} }} {default} }}' if wire_if_set
                                 else f'if (!({bit})) {{ {read} }} {default} }}')).replace('TYPE', typ)]
        elif not calls and len(loads) == 2 and size == 1:
            # the bit is the field's value
            cands[s] = [(head + body + ' return true; }').replace('TYPE', t2) for t2 in ('bool', 'u8') for body in (
                f'Set_NAME({field}, ({bit}) != 0);',
                f'if ({bit}) Set_NAME({field}, true); else Set_NAME({field}, false);',
                f'const bool on = ({bit}) != 0; Set_NAME({field}, on);')]
    found = pick(cands, tables, ['#include "../src/Packet.h"'] + sorted(prelude), '?Read@Try_{rva:x}_{k}@@')
    out = ['// Readers of whole packets with one field after the header (generated by tools/gen_sources.py,',
           '// tools/gen_fields.py, from the client; see ../Packet.h, ../Packet72.cpp for the form). Class names are ours:',
           f'// Packet_<rva of the reader>. {len(found)} of the {seen} readers of these kinds are written.']
    out += [f'// match: {s:x} ?Read@Packet_{s:x}@@' for s in sorted(found)]
    out += ['#include "../Packet.h"', '#include "../FieldCodec.h"', '']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + sorted(prelude) + ['']
    for s, k in sorted(found.items()):
        out += [f'// @{s:x}', cands[s][k].replace('NAME', f'Packet_{s:x}'), '']
    return out, len(found)


def packet_vector_readers(im):
    """Readers of whole packets with one field that is an object with a reader of its own (slot 1 of its table of
    virtual functions). A bit says the field is on the wire; else it takes a default that is a local static of an
    inline function (its destructor is registered at first use). Three kinds, by what the client's code does:
      value   the object's value (at +4, a vector of the client's own kind: its copy assignment walks elements) is
              assigned from a static value
      object  the whole object is assigned from a static object
      words   the object's value, n plain dwords, is copied from a static object's value"""
    cands, types, defaults, thunks, seen, prelude_extra, tables = {}, [], [], {}, 0, set(), set()
    import os
    import match_func as M
    shared_path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldClasses.h')
    shared = {int(s, 16): name for s, name in re.findall(r'^// ctor: ([0-9a-f]+) (\w+)',
              open(shared_path, encoding='utf-8').read(), re.M)} if os.path.exists(shared_path) else {}
    object_path = os.path.join(M.ROOT, 'client-src', 'src', 'gen', 'FieldObjectAliases.h')
    shared_objects = {int(s, 16): name for s, name in re.findall(r'^// object: ([0-9a-f]+) (\w+)',
                     open(object_path, encoding='utf-8').read(), re.M)} if os.path.exists(object_path) else {}
    for s in im.starts:
        if s in im.done or not 0x780000 <= s < 0x940000 or not 150 <= im.size(s) <= 400:
            continue
        text = im.text(s)
        if not text or 'fs:[0x2c]' not in text or 'cmp eax, 6' not in text or 'call eax' not in text:
            continue
        lines = text.split(chr(10))
        tests = [k for k, x in enumerate(lines) if re.fullmatch(r'test byte ptr \[\w+\], (0x[0-9a-f]+|\d+)', x)]
        if len(tests) != 1 or not re.match(r'j(e|ne) ', lines[tests[0] + 1]):
            continue
        seen += 1
        t = tests[0]
        mask = number(lines[t].split(', ')[1])
        assign = virt = thunk = ctor = None
        assignments = []
        copies = []
        for k, x in enumerate(lines[:-2]):
            a = re.fullmatch(r'push (0x[0-9a-f]+)', x)
            if re.fullmatch(r'call 0x[0-9a-f]+', x):
                before = []
                for prev in reversed(lines[max(0, k - 6):k]):
                    if prev.startswith(('call ', 'j')):
                        break
                    before.append(prev)
                arg = next((re.fullmatch(r'push (0x[0-9a-f]+)', prev) for prev in before
                            if re.fullmatch(r'push (0x[0-9a-f]+)', prev)), None)
                obj = next((re.fullmatch(r'lea ecx, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', prev) for prev in before
                            if re.fullmatch(r'lea ecx, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', prev)), None)
                if arg and obj:
                    assign = (int(arg[1], 16), number(obj[1]), int(x.split()[1], 16))
                    assignments.append(assign)
            if a and lines[k + 1] == 'call 0xf411a5':
                thunk = int(a[1], 16) - BASE
            v = re.fullmatch(r'mov eax, dword ptr \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x)
            if v and 'mov eax, dword ptr [eax + 4]' in lines[k + 1:k + 6] and 'call eax' in lines[k + 1:k + 7]:
                virt = number(v[1])
            c = re.fullmatch(r'mov ecx, (0x[0-9a-f]+)', x)
            if c and re.fullmatch(r'call 0x[0-9a-f]+', lines[k + 1]) and lines[k + 1] != 'call 0xf411a5':
                ctor = (int(c[1], 16), int(lines[k + 1].split()[1], 16))
            g = re.fullmatch(r'mov(?:zx)? (\w+), (byte|word|dword) ptr \[(0x[0-9a-f]+)\]', x)
            if g and k > t:
                stored_reg = g[1]
                if stored_reg in ('eax', 'ebx', 'ecx', 'edx') and g[2] != 'dword':
                    stored_reg = stored_reg[1] + ('l' if g[2] == 'byte' else 'x')
                for after in lines[k + 1:k + 4]:
                    d = re.fullmatch(r'mov ' + g[2] + r' ptr \[\w+ \+ (0x[0-9a-f]+|\d+)\], ' + stored_reg, after)
                    if d:
                        copies.append((int(g[3], 16), number(d[1]), {'byte': 1, 'word': 2, 'dword': 4}[g[2]]))
                        break
                    if after.startswith('mov ' + g[1] + ','):
                        break
        # A fixed array inside the value is copied as a block, unlike its scalar neighbours.
        for k, line in enumerate(lines):
            if line != 'rep movsd dword ptr es:[edi], dword ptr [esi]' or k < t:
                continue
            before = list(reversed(lines[max(t, k - 40):k]))
            src = next((re.fullmatch(r'mov esi, (0x[0-9a-f]+)', x) for x in before
                        if re.fullmatch(r'mov esi, (0x[0-9a-f]+)', x)), None)
            dst = next((re.fullmatch(r'lea edi, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x) for x in before
                        if re.fullmatch(r'lea edi, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x)), None)
            count = next((re.fullmatch(r'mov ecx, (0x[0-9a-f]+|\d+)', x) for x in before
                          if re.fullmatch(r'mov ecx, (0x[0-9a-f]+|\d+)', x)), None)
            if src and dst and count:
                copies.append((number(src[1]), number(dst[1]), 4 * number(count[1])))
        copies.sort(key=lambda c: c[1])
        if virt is None or thunk is None or virt < 10:
            continue
        guard = re.search(r'mov eax, dword ptr \[(0x[0-9a-f]+)\]\ncmp eax, dword ptr \[ecx \+ 0x90\]', text)
        if ctor and ctor[1] in shared:
            kind, static, fn = 'shared', ctor[0], ctor[1]
            typ = shared[fn]
            decl = ''
            ftyp, stat_typ, default = typ, typ, f'field{virt:x} = Default_{static:x}();'
        elif assign and assign[1] == virt + 4 and not ctor:
            kind, static, fn = 'value', assign[0], assign[2]
            typ = f'Vec_{fn:x}'
            # Read the element's stride from the default's destructor (or the destructor it jumps to).
            dtor_text = im.text(thunk) or ''
            jump = re.fullmatch(r'mov ecx, 0x[0-9a-f]+\njmp (0x[0-9a-f]+)', dtor_text)
            if jump:
                dtor_text = im.text(int(jump[1], 16)) or ''
            stride = re.search(r'^add esi, (0x[0-9a-f]+|\d+)$', dtor_text, re.M)
            if stride and 'call dword ptr [eax + 0xc]' in dtor_text:
                storage = 'PacketVectorExternal' if jump else 'PacketVectorStorage'
                value_decl = f'using {typ} = {storage}<{number(stride[1])}>;'
            else:
                value_decl = (f'struct {typ} {{ void* data = nullptr; u32 count = 0; u32 capacity = 0; '
                              f'constexpr {typ}() {{}} {typ}& operator=(const {typ}& other); ~{typ}(); }};')
            decl = (value_decl + chr(10) +
                    f'struct Field{typ} {{ virtual void Slot0(); virtual char Read(const u8** cursor, '
                    f'const u8* end); {typ} value; }};')
            ftyp, stat_typ, default = f'Field{typ}', typ, f'field{virt:x}.value = Default_{static:x}();'
        elif assign and assign[1] == virt and ctor and ctor[0] == assign[0]:
            kind, static, fn = 'object', assign[0], assign[2]
            typ = f'FieldObj_{fn:x}'
            extent = number(guard[1]) - static if guard else 4
            opaque = f'u8 fields[{extent - 4}]; ' if 4 < extent <= 4096 else ''
            decl = (f'struct {typ} {{ virtual void Slot0(); virtual char Read(const u8** cursor, const u8* end); '
                    f'{opaque}{typ}(); {typ}& operator=(const {typ}& other); ~{typ}(); }};')
            if fn in shared_objects:
                typ, decl = shared_objects[fn], ''
            ftyp, stat_typ, default = typ, typ, f'field{virt:x} = Default_{static:x}();'
        elif not assign and ctor and copies and all(c[2] == 4 for c in copies) \
                and not re.search(r'mov eax, dword ptr \[0x[0-9a-f]+\]\nmov ecx, dword ptr \[0x[0-9a-f]+\]\n'
                                  r'mov dword ptr', text) \
                and [c[1] for c in copies] == [virt + 4 + 4 * i for i in range(len(copies))] \
                and [c[0] for c in copies] == [ctor[0] + 4 + 4 * i for i in range(len(copies))]:
            kind, static, fn = 'words', ctor[0], ctor[1]
            typ = f'FieldWords{len(copies)}_{fn:x}'
            # the value's own copy assignment goes word by word (a plain struct would be copied 8 + 4 bytes)
            n = len(copies)
            decl = (f'struct Words{n} {{ u32 word[{n}]; Words{n}& operator=(const Words{n}& other) {{ '
                    f'for (int i = 0; i < {n}; ++i) word[i] = other.word[i]; return *this; }} }};' + chr(10) +
                    f'struct {typ} {{ virtual void Slot0(); virtual char Read(const u8** cursor, const u8* end); '
                    f'Words{len(copies)} value; {typ}(); ~{typ}(); }};')
            ftyp, stat_typ, default = typ, typ, f'field{virt:x}.value = Default_{static:x}().value;'
        elif not assign and ctor and copies and all(g - ctor[0] == dst - virt for g, dst, width in copies):
            # The value's own assignment copies members rather than padding. Preserve member widths: adjacent
            # loads followed by adjacent stores are a 64-bit member, not two separate 32-bit assignments.
            kind, static, fn = 'members', ctor[0], ctor[1]
            fields = [(dst - virt - 4, width) for _, dst, width in copies]
            merged, i = [], 0
            while i < len(fields):
                off, width = fields[i]
                if width == 4 and i + 1 < len(fields) and fields[i + 1] == (off + 4, 4):
                    g = copies[i][0]
                    pair = re.search(r'mov eax, dword ptr \[' + hex(g) + r'\]\nmov ecx, dword ptr \[' +
                                     hex(g + 4) + r'\]\nmov dword ptr', text)
                    if pair:
                        width, i = 8, i + 1
                merged.append((off, width))
                i += 1
            members, assigns, blocks, pos, valid = [], [], [], 0, True
            for off, width in merged:
                if off < pos:
                    valid = False
                    break
                if off > pos:
                    members.append(f'u8 gap{pos:x}[{off - pos}];')
                if width in UINT:
                    ctyp = UINT[width]
                else:
                    ctyp = f'Block_{width}'
                    blocks.append(f'struct {ctyp} {{ u8 bytes[{width}]; }};')
                members.append(f'{ctyp} member{off:x};')
                assigns.append(f'member{off:x} = other.member{off:x};')
                pos = off + width
            if valid:
                typ, val = f'FieldMembers_{fn:x}', f'Value_{fn:x}'
                extent = number(guard[1]) - static if guard else pos + 4
                tail = f'u8 tail[{extent - pos - 4}]; ' if pos + 4 < extent <= 4096 else ''
                decl = ('#pragma pack(push, 1)\n' + f'struct {val} {{ ' + ' '.join(members) +
                        f' __forceinline {val}& operator=(const {val}& other) {{ ' + ' '.join(assigns) + ' return *this; } };\n'
                        f'struct {typ} {{ virtual void Slot0(); virtual char Read(const u8** cursor, const u8* end); '
                        f'{val} value; {tail}{typ}(); ~{typ}(); }};\n#pragma pack(pop)')
                ftyp, stat_typ, default = typ, typ, f'field{virt:x}.value = Default_{static:x}().value;'
                # Keep #pragma pairs together; deduplicating individual pragma lines breaks packed layouts.
                for block in blocks:
                    if block not in types:
                        types.append(block)
                if decl not in types:
                    types.append(decl)
                decl = ''
            else:
                continue
        elif ctor and assignments and all(g - ctor[0] == dst - virt for g, dst, target in assignments) \
                and all(g - ctor[0] == dst - virt for g, dst, width in copies):
            # A value may combine a string, encoded scalars and other vectors. Their own assignments remain
            # calls, while the value's assignment is inline, copying members in declaration order.
            kind, static, fn = 'composite', ctor[0], ctor[1]
            components, extra_types, valid = [], [], True
            for g, dst, target in assignments:
                if target == 0x9be7d0:
                    ctyp = 'RString'
                else:
                    at = im.text(target) or ''
                    if 'call 0x9bb8d0' not in at or 'and eax, 0x7fffffff' not in at:
                        valid = False
                        break
                    ctyp = f'AssignedVector_{target:x}'
                    extra_types.append(f'struct {ctyp} {{ void* data; u32 count; u32 capacity; '
                                       f'{ctyp}& operator=(const {ctyp}& other); }};')
                components.append((dst - virt - 4, 12, ctyp))
            components += [(dst - virt - 4, width, UINT[width]) for g, dst, width in copies]
            members, assigns, pos = [], [], 0
            for off, width, ctyp in sorted(components):
                if off < pos:
                    valid = False
                    break
                if off > pos:
                    members.append(f'u8 gap{pos:x}[{off - pos}];')
                members.append(f'{ctyp} member{off:x};')
                assigns.append(f'member{off:x} = other.member{off:x};')
                pos = off + width
            if not valid:
                continue
            typ, val = f'FieldComposite_{fn:x}', f'Value_{fn:x}'
            extent = number(guard[1]) - static if guard else pos + 4
            tail = f'u8 tail[{extent - pos - 4}]; ' if pos + 4 < extent <= 4096 else ''
            decl = ('#pragma pack(push, 1)\n' + f'struct {val} {{ ' + ' '.join(members) +
                    f' __forceinline {val}& operator=(const {val}& other) {{ ' + ' '.join(assigns) + ' return *this; } };\n'
                    f'struct {typ} {{ virtual void Slot0(); virtual char Read(const u8** cursor, const u8* end); '
                    f'{val} value; {tail}{typ}(); ~{typ}(); }};\n#pragma pack(pop)')
            for line in extra_types:
                if line not in types:
                    types.append(line)
            if decl not in types:
                types.append(decl)
            decl = ''
            ftyp, stat_typ, default = typ, typ, f'field{virt:x}.value = Default_{static:x}().value;'
        else:
            continue
        for line in decl.split(chr(10)):
            if line and line not in types:
                types.append(line)
        # every reader has the default's function inside (the client never calls it): with many users in one file
        # plain inline stops that
        line = f'__forceinline const {stat_typ}& Default_{static:x}() {{ static const {stat_typ} def; return def; }}'
        if line not in defaults:
            defaults.append(line)
        # the function registered for the end of the program destroys the static: a jump to the type's destructor
        # or, for most types, the destructor itself (inline in the client; the types here only declare it, so only
        # the first kind is claimed)
        body = (im.text(thunk) or '').split(chr(10))
        if (len(body) == 2 and body[0] == f'mov ecx, {static:#x}' and body[1].startswith('jmp 0x')) \
                or (kind == 'value' and 'call dword ptr [eax + 0xc]' in '\n'.join(body)) or kind == 'shared':
            thunks[s] = (thunk, static)
        pad = f'u8 pad[{virt - 10}]; ' if virt > 10 else ''
        head = ('#pragma pack(push, 1)' + chr(10) + f'struct NAME : Packet {{ {pad}{ftyp} field{virt:x}; '
                'bool Read(const u8** cursor, const u8* end); };' + chr(10) + '#pragma pack(pop)' + chr(10) +
                f'bool NAME::Read(const u8** cursor, const u8* end) {{ {READ_HEAD} ')
        bit = f'*p & {mask:#x}'
        read = f'return field{virt:x}.Read(cursor, end) != 0;'
        default += ' return true;'
        bits_call = re.search(r'push (0x[0-9a-f]+|\d+)\npush (0x[0-9a-f]+|\d+)\npush \w+\ncall 0x91cae0', text)
        if bits_call:
            # A scalar precedes the object; its bit is inline, the object's bit is extracted by GetBits.
            bc = lines.index('call 0x91cae0')
            loc = next((re.fullmatch(r'lea esi, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x)
                        for x in lines[:t] if re.fullmatch(r'lea esi, \[\w+ \+ (0x[0-9a-f]+|\d+)\]', x)), None)
            glob = next((re.fullmatch(r'mov al, byte ptr \[(0x[0-9a-f]+)\]', x)
                         for x in lines[t:bc] if re.fullmatch(r'mov al, byte ptr \[(0x[0-9a-f]+)\]', x)), None)
            loads = [k for k in range(t, bc) if re.fullmatch(r'mov(?:zx)? \w+, byte ptr \[esi\]', lines[k])]
            stores = [k for k in range(t, bc) if re.fullmatch(r'mov byte ptr \[esi\], \wl', lines[k])]
            target = next((int(x.split()[1], 16) for x in lines[t:bc] if re.fullmatch(r'call 0x[0-9a-f]+', x)), None)
            if not loc or not glob or not loads or not stores or not target:
                continue
            off = number(loc[1])
            steps = chain_of(lines[loads[0]:stores[-1] + 1], im.img, {}, {'esi': CURSOR}, None, True)
            if steps is None or off < 10 or virt <= off:
                continue
            tables.update(v for step, v in steps if step == 'table')
            name, rtyp = known_readers().get(target, (f'Read_{target:x}', 'u8'))
            if rtyp != 'u8':
                continue
            prelude_extra.update([f'char {name}(u8* out, const u8** cursor, const u8* end);',
                                  f'extern u8 g_{number(glob[1]):x};',
                                  'u8 GetBits_91cae0(const u8* bits, u8 first, u8 count);'])
            pad = f'u8 pad[{off - 10}]; ' if off > 10 else ''
            gap = f'u8 gap[{virt - off - 1}]; ' if virt > off + 1 else ''
            head = (f'__forceinline void Set_NAME(u8& field, const u8& value) {{ field = value; '
                    f'for (u8* b = &field; b != &field + sizeof(field); ++b) {{ u8 x = *b; '
                    f'{statements(steps)} *b = x; }} }}\n#pragma pack(push, 1)\n'
                    f'struct NAME : Packet {{ {pad}u8 field{off:x}; {gap}{ftyp} field{virt:x}; '
                    'bool Read(const u8** cursor, const u8* end); };\n#pragma pack(pop)\n'
                    f'bool NAME::Read(const u8** cursor, const u8* end) {{ {READ_HEAD} '
                    f'if (!(*p & {mask:#x})) Set_NAME(field{off:x}, g_{number(glob[1]):x}); '
                    f'else if (!{name}(&field{off:x}, cursor, end)) return false; '
                    f'u8 present = GetBits_91cae0(p, {number(bits_call[2])}, {number(bits_call[1])}); ')
            read = f'if (present != 1) return false; if (!field{virt:x}.Read(cursor, end)) return false; return true;'
            cands[s] = [head + f'if (!present) {{ {default} }} {read} }}',
                        head + f'if (present) {{ {read} }} {default} }}',
                        head + 'switch (present) { case 0: ' + default.removesuffix(' return true;') +
                        f' break; case 1: if (!field{virt:x}.Read(cursor, end)) return false; break; '
                        'default: return false; } return true; }']
            continue
        wire_if_set = lines[t + 1].startswith('jne')
        cands[s] = [head + (f'if (!({bit})) {{ {default} }} {read} }}' if wire_if_set
                            else f'if ({bit}) {{ {default} }} {read} }}'),
                    head + (f'if ({bit}) {{ {read} }} {default} }}' if wire_if_set
                            else f'if (!({bit})) {{ {read} }} {default} }}')]
    prelude = ['#include "../src/Packet.h"', '#include "../src/PacketVector.h"']
    if shared:
        prelude += ['#include "../src/gen/FieldClasses.h"']
    if shared_objects:
        prelude += ['#include "../src/gen/FieldObjectAliases.h"']
    prelude += sorted(prelude_extra) + types + defaults
    found = pick(cands, tables, prelude, '?Read@Try_{rva:x}_{k}@@')
    out = ['// Readers of whole packets whose one field is an object with a reader of its own; the default value is a local',
           '// static of an inline function (generated by tools/gen_sources.py, tools/gen_fields.py, from the client;',
           '// first one by hand: rva 0x8b7c80). Names are ours: Packet_<rva of the reader>, the types after the rva of',
           '// their copy assignment or constructor, Default_<address of the static>.',
           f'// {len(found)} of the {seen} readers of this kind are written.']
    out += [f'// match: {s:x} ?Read@Packet_{s:x}@@' for s in sorted(found)]
    for thunk, static in sorted(set(thunks[s] for s in found if s in thunks)):
        out.append(f'// match: {thunk:x} ??__Fdef@?1??Default_{static:x}@')
    out += ['#include "../Packet.h"', '#include "../PacketVector.h"', '']
    if shared:
        out += ['#include "FieldClasses.h"']
    if shared_objects:
        out += ['#include "FieldObjectAliases.h"']
    out += [f'extern const u8 g_{t:x}[256];' for t in sorted(tables)] + sorted(prelude_extra) + ['']
    out += types + [''] + defaults + ['']
    for s, k in sorted(found.items()):
        out += [f'// @{s:x}', cands[s][k].replace('NAME', f'Packet_{s:x}'), '']
    return out, len(found)
