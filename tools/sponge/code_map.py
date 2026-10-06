"""Every byte of the 13.3 client's .text accounted for: code reached from known entry points, pointer tables,
padding, code nothing points at, data. The measure of "how much of the executable is understood" per page.

  code_map.py build        walk the image, write research/exe133/code_map.bin (one class byte per .text byte) and
                           research/exe133/functions.txt (every function start found), print the totals
  code_map.py pages        per page: bytes of each class; lists the pages that are not all explained
  code_map.py gaps [n]     the n largest unexplained runs, with a hex sample
  code_map.py audit        the check on the map itself: every instruction marked as code is decoded again and
                           the ones compiled code never has are listed (data that was decoded by mistake shows
                           up as runs of them)
  code_map.py what <rva>   the class of the bytes around an address

How it walks:
  seeds     the entry point, the export table, and every relocated dword of .rdata / .data that points into .text
            (vtables, callbacks, SEH tables). The packer relocates .text itself: the image's relocation table has
            no entry inside .text, so tables kept in .text are found from the code that uses them (below)
  descent   decode from each seed, follow jumps and calls, stop at ret / jmp / int3 and after a call to a function
            that does not return (noreturn_targets); bytes decoded = CODE.
            What the decoded code refers to inside .text is followed too:
              `jmp [reg*4 + A]`, `mov r, [reg*4 + A]`      a table of code pointers at A = PTR, its targets = seeds
              `movzx r, byte ptr [reg + A]`                 a switch's byte index table at A = IDX
              any other memory operand at A                 a constant kept in .text = DATA (its operand size)
              an immediate that is an address in .text      a function pointer = seed, when it lands on the
                                                            first byte after padding or a return (a plain number
                                                            such as 0x00C00000 lands in the middle of code)
  padding   0xCC / 0x90 / multi-byte nop runs between functions = PAD; all-zero pages = ZERO
  islands   what is left, starts where something explained ends, and decodes cleanly to a ret / jmp with nothing a
            compiler would not emit = ISLAND: code nothing reachable refers to (dead functions, or functions
            only called through pointers computed at run time)
  data      tables identified by their content (KNOWN, and the signatures in SIGNED) = DATA
  the rest  UNKNOWN
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import exe_dis as E
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

OUT = os.path.join(HERE, '..', '..', 'research', 'exe133')
T0, T1 = E.TEXT
T1P = (T1 + 0xfff) & ~0xfff
d = E.data
BASE = E.BASE
UNKNOWN, CODE, PTR, PAD, ISLAND, DATA, IDX, ZERO = range(8)
NAMES = ['unknown', 'code', 'ptr-table', 'padding', 'island', 'data', 'idx-table', 'zero']
RELOC = (0x31e1000, 0x940c0)
EXPORT = 0x1748750
ENTRY = 0x3276000

# data kept in .text that was identified: (rva from, rva to, what, how it was recognised). The hand-written OpenSSL
# assembly reaches its tables relative to the program counter, so no address in the image points at them; they
# are recognised by their constants (the hex in the last column is checked at `from` before the range is taken)
KNOWN = [
    (0x1c000, 0x41000, 'OpenSSL ecp_nistz256_precomputed: 37 x 64 P-256 points, byte-transposed',
     'recomputed from the curve (tools/sponge/nistz256_table.py): 37 of 37 pages equal', ''),
    (0x41000, 0x41130, 'OpenSSL ecp_nistz256 constants (RR = 3,0,-1,-5,-2,-1,-3,4; ONE_mont; ONE)', 'constants',
     '0300000000000000fffffffffbffffff'),
    (0x48b00, 0x49b50, 'OpenSSL Whirlpool: the C table (256 x 16 bytes) and the round constants', 'constants',
     '18186018c07830d8'),
    (0x13dc0, 0x14e00, 'OpenSSL Camellia: SIGMA and the four S-box tables', 'constants', '7f669ea08b90cc3b'),
    (0x11e80, 0x126c0, 'OpenSSL DES: the CBC jump table and DES_SPtrans (8 x 64 dwords)', 'shape and position', ''),
    (0x11c80, 0x11cc0, 'OpenSSL cbc.pl jump table (16 relative offsets)', 'shape: same 16 dwords as the DES one',
     '000000002e0000002b000000'),
    (0x46940, 0x46980, 'OpenSSL cbc.pl jump table (16 relative offsets)', 'shape: same 16 dwords as the DES one',
     '000000002e0000002b000000'),
    (0x0ff00, 0x10200, 'OpenSSL SHA-512: K512 and the byte-swap mask', 'constants', '22ae28d7982f8a42'),
    (0x086c0, 0x08820, 'OpenSSL SHA-256: K256 and the shuffle masks', 'constants', '982f8a4291443771'),
    (0x1a480, 0x1a780, 'OpenSSL GHASH: byte-swap mask, the polynomial, rem_4bit / rem_8bit', 'constants',
     '0f0e0d0c0b0a0908'),
    (0x19197, 0x19240, 'OpenSSL SHA-1: the four round constants, vector form', 'constants', ''),
    (0x158c0, 0x15984, 'OpenSSL ChaCha20: rotate masks and counters', 'constants', '0203000106070405'),
    (0x45e40, 0x45f00, 'OpenSSL assembly constants (vectors of 1, 0)', 'shape and position', ''),
    (0x08340, 0x083c0, 'OpenSSL AES-NI: key schedule shuffle masks', 'constants', '0d0e0f0c0d0e0f0c'),
    (0x4dcb5, 0x4dcf5, 'codec assembly: 16 relative jump offsets', 'shape', ''),
    (0x51f51, 0x51f91, 'codec assembly: 16 relative jump offsets', 'shape', ''),
    (0x1bc99, 0x1bd00, 'text "Montgomery Multiplication for x86, CRYPTOGAMS by <appro@openssl.org>"', 'text',
     '4d6f6e74676f6d657279'),
    (0x12b00, 0x12c20, 'text "rc4(4x,int)", "rc4(1x,char)", "RC4 for x86, CRYPTOGAMS..."', 'text', '726334283478'),
    (0x1513a, 0x15180, 'text "Camellia for x86 by <appro@openssl.org>"', 'text', '43616d656c6c6961'),
    (0x4827a, 0x482c0, 'text "GF(2^m) Multiplication for x86, CRYPTOGAMS..."', 'text', '474628325e6d29'),
    (0x69310, 0x6a3c0, 'DirectInput data formats: c_dfDIMouse2 (11 objects) and c_dfDIKeyboard (256 keys), 16 bytes each',
     'their GUID pointers (GUID_XAxis / YAxis / ZAxis / Key in .rdata); .data rva 0x1720460 and 0x1720668 point at them',
     ''),
]
# code no path reaches and the island rule refuses because it holds privileged instructions on purpose
FORCED = [
    (0x4200, 0x4320, 'OpenSSL x86cpuid: OPENSSL_rdtsc / OPENSSL_instrument_halt / OPENSSL_far_spin (hlt, cli, sti)'),
    (0x4550, 0x4980, 'OpenSSL x86cpuid: OPENSSL_wipe_cpu / atomic_add / cleanse / ia32_rdrand / rdseed ...'),
]

# tables recognised by a run of their constants: (what, the bytes, how far before them the table starts, its length)
SIGNED = []

md = Cs(CS_ARCH_X86, CS_MODE_32)
ODD = {'in', 'out', 'insb', 'insd', 'insw', 'outsb', 'outsd', 'outsw', 'hlt', 'cli', 'sti', 'iretd', 'iret', 'into',
       'aaa', 'aas', 'daa', 'das', 'aam', 'aad', 'arpl', 'bound', 'les', 'lds', 'lcall', 'ljmp', 'retf', 'salc',
       'xlatb', 'loop', 'loope', 'loopne', 'int', 'int1', 'pushal', 'popal'}


def relocs():
    out = []
    at, end = RELOC[0], RELOC[0] + RELOC[1]
    while at < end:
        page, size = struct.unpack_from('<II', d, at)
        if size == 0:
            break
        for i in range((size - 8) // 2):
            e = struct.unpack_from('<H', d, at + 8 + 2 * i)[0]
            if e >> 12 == 3:
                out.append(page + (e & 0xfff))
        at += size
    return out


def exports():
    n_fn, = struct.unpack_from('<I', d, EXPORT + 0x14)
    tab, = struct.unpack_from('<I', d, EXPORT + 0x1c)
    return [struct.unpack_from('<I', d, tab + 4 * i)[0] for i in range(n_fn)]


MEM = re.compile(r'(byte|word|dword|qword|xmmword|ymmword|tbyte|fword) ptr (?:\w\w:)?\[([^\]]*)\]')
HEX = re.compile(r'0x[0-9a-f]+')
CMP = re.compile(r', (0x[0-9a-f]+|\d+)$')
SIZE = {'byte': 1, 'word': 2, 'dword': 4, 'qword': 8, 'xmmword': 16, 'ymmword': 32, 'tbyte': 10, 'fword': 6}


def noreturn_targets():
    """functions that do not return: the compiler leaves int3 after a call to one (nothing follows it). A target
    counts when at least 3 of its call sites, and a quarter of them, are followed by 0xCC."""
    total, cc = {}, {}
    at = T0
    while True:
        at = d.find(bytes([0xe8]), at, T1 - 5)
        if at < 0:
            break
        t = at + 5 + struct.unpack_from('<i', d, at + 1)[0]
        if T0 <= t < T1:
            total[t] = total.get(t, 0) + 1
            if d[at + 5] == 0xcc:
                cc[t] = cc.get(t, 0) + 1
        at += 1
    return {t for t, n in cc.items() if n >= 3 and 4 * n >= total[t]}


NORETURN = set()
INS = bytearray(T1P - T0)  # 1 where a decoded instruction starts
CONFLICTS = []


def descend(mark, seeds, cls, starts, refs):
    """recursive descent from the seeds; returns the number of bytes newly marked. refs collects what the decoded
    code points at inside .text: ('ptr' | 'idx' | 'data', address, size)"""
    todo = list(seeds)
    done = 0
    lo, hi = BASE + T0, BASE + T1
    while todo:
        at = todo.pop()
        if not (T0 <= at < T1) or mark[at - T0] != UNKNOWN:
            continue
        while T0 <= at < T1 and mark[at - T0] == UNKNOWN:
            stop = False
            n = 0
            prev_call = False
            bound = idx = None  # the last `cmp x, N` (a switch has N + 1 cases) and the last byte index table
            for a, size, mn, ops in md.disasm_lite(d[at:at + 0x200], BASE + at):
                a -= BASE
                if mark[a - T0] != UNKNOWN:
                    if mark[a - T0] in (CODE, ISLAND) and not INS[a - T0]:
                        CONFLICTS.append(a)  # this path enters the middle of an instruction decoded earlier
                    stop = True
                    break
                # an instruction that runs into bytes already taken is not one
                if any(mark[a - T0 + k] != UNKNOWN for k in range(1, size)):
                    CONFLICTS.append(a)
                    stop = True
                    break
                # after a call that does not return the compiler may put a switch table (with alignment nops
                # before it): two code pointers in a row are a table, not instructions
                if n and prev_call and mn != 'nop' and lo <= struct.unpack_from('<I', d, a)[0] < hi                         and lo <= struct.unpack_from('<I', d, a + 4)[0] < hi:
                    stop = True
                    break
                prev_call = mn == 'call' or (prev_call and mn == 'nop')
                INS[a - T0] = 1
                for k in range(size):
                    mark[a - T0 + k] = cls
                done += size
                n += size
                c = mn[0]
                branch = c == 'j' or mn == 'call' or mn.startswith('loop')
                if branch and ops.startswith('0x'):
                    t = int(ops, 16) - BASE
                    if T0 <= t < T1:
                        todo.append(t)
                        if mn == 'call':
                            starts.add(t)
                            if t in NORETURN:
                                stop = True  # nothing runs after it: what follows is reached some other way
                                break
                elif mn == 'cmp':
                    c = CMP.search(ops)
                    bound = int(c.group(1), 0) + 1 if c else None
                    if bound is not None and bound > 4096:
                        bound = None
                elif '0x' in ops and size >= 5:
                    m = MEM.search(ops)
                    inner = m.group(2) if m else ''
                    for h in HEX.findall(ops):
                        v = int(h, 16)
                        if not lo <= v < hi:
                            continue
                        v -= BASE
                        if m and h in inner:
                            if '*4' in inner and m.group(1) == 'dword':
                                # how many entries: one per value of the index table, else one per case
                                refs.append(('ptr', v, 4, idx if idx else bound))
                                bound = idx = None
                            elif m.group(1) == 'byte' and mn == 'movzx':
                                refs.append(('idx', v, 1, bound))
                                idx = (v, bound)
                            else:
                                refs.append(('data', v, SIZE[m.group(1)], None))
                        elif mn == 'lea':
                            refs.append(('data', v, 1, None))
                        else:
                            refs.append(('imm', v, 0, None))
                if mn == 'jmp' or mn == 'ret' or mn == 'int3' or mn == 'retf':
                    stop = True
                    break
            if stop or n == 0:
                break
            at += n
    return done


def take_refs(mark, refs, known):
    """mark the tables / constants the code referred to; returns the code addresses found in pointer tables.
    A table's length comes from its switch (`cmp reg, N` before it: N + 1 entries; a pointer table read through a
    byte index table has one entry per index value); without one, it runs while its entries look like entries."""
    seeds = []
    lo, hi = BASE + T0, BASE + T1
    order = {'idx': 0, 'ptr': 1, 'data': 2, 'imm': 3}
    for kind, a, size, extra in sorted(refs, key=lambda r: order[r[0]]):
        if not T0 <= a < T1:
            continue
        if kind in ('ptr', 'idx') and mark[a - T0] == PAD and mark[a + 1 - T0] == UNKNOWN:
            mark[a - T0] = UNKNOWN  # a table's first byte that happens to be 0xCC was taken for padding
        if mark[a - T0] != UNKNOWN:
            continue
        if kind == 'imm':
            # an immediate that is an address in .text: a function pointer only when it lands on a function's
            # first byte (after padding or a return); a plain number (0x00C00000, 0x00FFFF00...) lands anywhere
            prev = d[a - 1]
            if prev in (0xcc, 0xc3, 0x90) or d[a - 3] == 0xc2 or mark[a - 1 - T0] in (PAD, PTR, IDX):
                seeds.append(a)
        elif kind == 'ptr':
            count = None
            if isinstance(extra, tuple):
                ia, n = extra
                if n:
                    count = max(d[ia:ia + n]) + 1
            elif extra:
                count = extra
            at = a
            while at + 4 <= T1 and mark[at - T0] == UNKNOWN and (at == a or at not in known):
                if count is not None and (at - a) // 4 >= count:
                    break
                v = struct.unpack_from('<I', d, at)[0]
                # a switch's cases lie in the function next to its table: a dword that points megabytes away is
                # the first instruction of the next function (`sub esp, n` reads as an address), not an entry
                if not lo <= v < hi or (count is None and abs(v - BASE - a) > 0x20000):
                    break
                for k in range(4):
                    mark[at - T0 + k] = PTR
                seeds.append(v - BASE)
                at += 4
        elif kind == 'idx':
            at = a
            while at < T1 and mark[at - T0] == UNKNOWN and (at == a or at not in known) and at - a < 1024:
                if extra:
                    if at - a >= extra:
                        break
                elif d[at] == 0xcc:
                    break
                mark[at - T0] = IDX
                at += 1
        else:
            for k in range(size):
                if a + k < T1 and mark[a + k - T0] == UNKNOWN:
                    mark[a + k - T0] = DATA
    return seeds


def nop_len(at):
    """length of the padding instruction at `at` (int3, nop, the multi-byte nops and the lea / mov fillers), or 0"""
    b = d[at]
    if b in (0xcc, 0x90):
        return 1
    for pat in (b'\x66\x90', b'\x0f\x1f\x00', b'\x0f\x1f\x40\x00', b'\x0f\x1f\x44\x00\x00', b'\x66\x0f\x1f\x44\x00\x00',
                b'\x0f\x1f\x80\x00\x00\x00\x00', b'\x0f\x1f\x84\x00\x00\x00\x00\x00',
                b'\x66\x0f\x1f\x84\x00\x00\x00\x00\x00', b'\x8d\x49\x00', b'\x8d\x64\x24\x00', b'\x8b\xff', b'\x8b\xc0',
                b'\x8d\xa4\x24\x00\x00\x00\x00', b'\x8d\x9b\x00\x00\x00\x00', b'\x8d\xb6\x00\x00\x00\x00',
                b'\x8d\x76\x00', b'\x8d\x74\x26\x00', b'\x8d\xbc\x27\x00\x00\x00\x00', b'\x8d\xb4\x26\x00\x00\x00\x00',
                b'\x89\xf6', b'\x8d\x7f\x00', b'\x66\x66\x90', b'\x66\x66\x66\x90'):
        if d.startswith(pat, at):
            return len(pat)
    return 0


def runs(mark, cls=UNKNOWN):
    i, n = 0, T1P - T0
    while True:
        i = mark.find(bytes([cls]), i)
        if i < 0 or i >= n:
            return
        j = i
        while j < n and mark[j] == cls:
            j += 1
        yield T0 + i, T0 + j
        i = j


def island(a, b):
    """does [a, b) decode cleanly as compiled code? -> (bytes decoded up to its last ret / jmp, targets)"""
    last, at, tg = a, a, []
    for x, size, mn, ops in md.disasm_lite(d[a:b], BASE + a):
        x -= BASE
        if x != at or mn in ODD or (size == 2 and d[x] == 0 and d[x + 1] == 0):
            break
        at = x + size
        if (mn[0] == 'j' or mn == 'call') and ops.startswith('0x'):
            tg.append(int(ops, 16) - BASE)
        if mn in ('ret', 'jmp'):
            last = at
    if at == b:
        last = b  # decodes cleanly right up to code already explained: it runs into it
    return last - a, tg


def signed(mark):
    """tables recognised by their content inside what is still unknown"""
    found = []
    for name, sig, back, length in SIGNED:
        at = T0
        while True:
            at = d.find(sig, at, T1)
            if at < 0:
                break
            a = at - back
            if all(mark[k - T0] in (UNKNOWN, DATA) for k in range(a, a + length, 64)):
                for k in range(a, a + length):
                    mark[k - T0] = DATA
                found.append((a, a + length, name))
            at += 1
    return found


def build():
    mark = bytearray(T1P - T0)
    seeds, starts = [ENTRY], set()
    for a in relocs():
        v = struct.unpack_from('<I', d, a)[0] - BASE
        if T0 <= v < T1:
            seeds.append(v)
            starts.add(v)
    for r in exports():
        if T0 <= r < T1:
            seeds.append(r)
            starts.add(r)
    for a, b, what, how, sig in KNOWN:
        assert d[a:a + len(sig) // 2] == bytes.fromhex(sig), f'{what}: constants not at {a:#x}'
        for k in range(a, b):
            mark[k - T0] = DATA
    for a, b, what in FORCED:
        at = a
        while at < b:
            n = 0
            for x, size, mn, ops in md.disasm_lite(d[at:b], BASE + at):
                for k in range(size):
                    mark[x - BASE - T0 + k] = ISLAND
                n += size
            at += n
            if at < b:  # a byte that is no instruction (alignment filler between two functions): step over it
                mark[at - T0] = PAD
                at += 1
    for p in range(T0, T1P, 4096):
        if d[p:p + 4096] == bytes(4096):
            for k in range(p, p + 4096):
                mark[k - T0] = ZERO
    for k in range(T1, T1P):
        mark[k - T0] = PAD  # the slack between the section's size and its last page's end
    NORETURN.update(noreturn_targets())
    print('seeds from .rdata / .data / exports:', len(seeds), '; functions that do not return:', len(NORETURN), file=sys.stderr)
    known = set()
    for rnd in range(12):
        refs = []
        got = descend(mark, seeds, CODE, starts, refs)
        known.update(r[1] for r in refs)
        seeds = take_refs(mark, refs, known)
        print(f'descent round {rnd}: {got} code bytes, {len(refs)} references into .text, {len(seeds)} table targets', file=sys.stderr)
        if not got and not seeds:
            break
    for a, b, name in signed(mark):
        print(f'table by content: {a:#x}..{b:#x} {name}', file=sys.stderr)
    # padding, then islands (repeat: an island's calls and tables reach more)
    for rnd in range(400):
        changed = 0
        for a, b in list(runs(mark)):
            at = a
            while at < b:
                n = nop_len(at)
                if not n or at + n > b:
                    break
                for k in range(n):
                    mark[at - T0 + k] = PAD
                at += n
                changed += n
            if at >= b or mark[at - T0] != UNKNOWN:
                continue
            got, tg = island(at, b)
            if got >= 1:
                refs = []
                changed += descend(mark, [at], ISLAND, starts, refs)
                starts.add(at)
                known.update(r[1] for r in refs)
                changed += descend(mark, take_refs(mark, refs, known), ISLAND, starts, refs)
        if not changed:
            print(f'islands: settled after {rnd} rounds', file=sys.stderr)
            break
    # what is left of tables found only in part: code pointers at any alignment, then small index bytes; padding
    # at a run's end
    lo, hi = BASE + T0, BASE + T1
    for a, b in list(runs(mark)):
        if b - a > 256:
            continue
        at = a
        while at + 4 <= b:
            v = struct.unpack_from('<I', d, at)[0]
            if lo <= v < hi and mark[v - BASE - T0] in (CODE, ISLAND) and abs(v - BASE - at) < 0x20000:
                for k in range(4):
                    mark[at - T0 + k] = PTR
                at += 4
            else:
                at += 1
        for k in range(a, b):
            if mark[k - T0] == UNKNOWN and (d[k] == 0xcc or (d[k] < 0x40 and (mark[k - 1 - T0] in (PTR, IDX)
                                                                         or mark[k + 1 - T0] in (PTR, IDX)))):
                mark[k - T0] = PAD if d[k] == 0xcc else IDX
        for k in range(b - 1, a - 1, -1):
            if mark[k - T0] == UNKNOWN and d[k] < 0x40 and mark[k + 1 - T0] == IDX:
                mark[k - T0] = IDX
    # zero runs between items are padding too
    for a, b in list(runs(mark)):
        if d[a:b] == bytes(b - a) and b - a < 64:
            for k in range(a, b):
                mark[k - T0] = PAD
    open(os.path.join(OUT, 'code_map.bin'), 'wb').write(bytes(mark))
    open(os.path.join(OUT, 'code_map_ins.bin'), 'wb').write(bytes(INS))
    with open(os.path.join(OUT, 'functions.txt'), 'w') as f:
        for s in sorted(starts):
            if mark[s - T0] in (CODE, ISLAND):
                f.write(f'{s:#x}\n')
    return mark, starts


def load():
    return bytearray(open(os.path.join(OUT, 'code_map.bin'), 'rb').read())


def totals(mark):
    n = T1P - T0
    cnt = [mark.count(bytes([c])) for c in range(8)]
    print(f'.text rva {T0:#x}..{T1P:#x}: {n} bytes, {n // 4096} pages')
    for c in (CODE, ISLAND, PTR, IDX, PAD, DATA, ZERO, UNKNOWN):
        print(f'  {NAMES[c]:10} {cnt[c]:9}  {100 * cnt[c] / n:6.2f}%')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'build':
        mark, starts = build()
        totals(mark)
        print('decode conflicts (a path entering the middle of an earlier instruction):', len(set(CONFLICTS)))
        with open(os.path.join(OUT, 'code_map_conflicts.txt'), 'w') as f:
            for c in sorted(set(CONFLICTS)):
                f.write(f'{c:#x}\n')
        print('function starts:', sum(1 for s in starts if mark[s - T0] in (CODE, ISLAND)))
    elif cmd == 'pages':
        mark = load()
        totals(mark)
        full = part = 0
        rows = []
        for p in range(T0, T1P, 4096):
            m = mark[p - T0:p - T0 + 4096]
            u = m.count(bytes([UNKNOWN]))
            if u == 0:
                full += 1
            else:
                part += 1
                rows.append((p, u, [m.count(bytes([c])) for c in range(8)]))
        print(f'pages with every byte explained: {full}; with unexplained bytes: {part}')
        for p, u, c in rows:
            print(f'  {p:#09x}  unknown {u:4}  code {c[CODE] + c[ISLAND]:4}  tables {c[PTR] + c[IDX]:4}  pad {c[PAD]:4}  data {c[DATA]:4}')
    elif cmd == 'gaps':
        mark = load()
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
        gs = sorted(runs(mark), key=lambda r: r[0] - r[1])
        print(f'{len(gs)} unexplained runs, {sum(b - a for a, b in gs)} bytes')
        for a, b in gs[:n]:
            print(f'{a:#09x}..{b:#09x}  {b - a:6} bytes  {d[a:a + 32].hex()}')
    elif cmd == 'audit':
        mark = load()
        ins = open(os.path.join(OUT, 'code_map_ins.bin'), 'rb').read()
        seg = re.compile(r'^(cs|ds|es|ss|fs|gs)$')
        odd = []
        total = 0
        at = 0
        n = T1 - T0
        while True:
            at = ins.find(b'\x01', at)
            if at < 0 or at >= n:
                break
            a = T0 + at
            for x, size, mn, ops in md.disasm_lite(d[a:a + 16], BASE + a):
                total += 1
                if mn in ODD or mn in ('wait', 'jecxz', 'jcxz', 'enter') and False or \
                        (mn in ('push', 'pop') and seg.match(ops)) or (size == 2 and d[a] == 0 and d[a + 1] == 0):
                    odd.append((a, mn, ops))
                break
            at += 1
        print(f'{total} instructions marked as code; {len(odd)} of a kind compiled code does not have')
        # runs of them close together = data decoded by mistake
        groups = []
        for a, mn, ops in odd:
            if groups and a - groups[-1][-1][0] < 64:
                groups[-1].append((a, mn, ops))
            else:
                groups.append([(a, mn, ops)])
        for g in groups:
            kinds = sorted({x[1] + (' ' + x[2] if x[1] in ('push', 'pop') else '') for x in g})
            print(f'  {g[0][0]:#09x}..{g[-1][0]:#09x}  {len(g):3} instructions: {", ".join(kinds)[:70]}')
    elif cmd == 'what':
        mark = load()
        a = int(sys.argv[2], 16) & ~0xf
        for r in range(a - 32, a + 64, 16):
            print(f'{r:#09x}  ' + ' '.join(NAMES[mark[r - T0 + k]][:4] for k in range(16)))
