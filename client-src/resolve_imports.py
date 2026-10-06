"""The 13.3 client's import table, rebuilt: which system function each of its import slots stands for.

The packer removed the executable's import list; at start it points every slot (rva 0xfab000..) at a stub of its own
that computes the function's address (`push eax; mov eax, K; a few rol / bswap / add; push eax; mov eax, [esp + 4];
ret 4`). This runs each stub (read from the live process by read_stubs.py) in the emulator to get the address, finds
the module it lies in (module list in imports.txt) and the export at that place in the module's file on disk.

  resolve_imports.py      -> client-src/import_table.txt: slot rva, module, function
"""
import os
import re
import struct
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EAX, UC_X86_REG_EIP

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe133')
GAME = r'C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game'
SYS = r'C:\Windows\SysWOW64'

text = open(os.path.join(RES, 'imports.txt')).read()
modules = [(m.group(1), int(m.group(2), 16), int(m.group(3), 16)) for m in re.finditer(r'^module (.+) (\w+) (0x\w+)$', text, re.M)]
stubs = [(int(m.group(1), 16), int(m.group(2), 16)) for m in re.finditer(r'^stub (\w+) -> (\w+)', text, re.M)]
direct = [(int(m.group(1), 16), m.group(2), m.group(3)) for m in re.finditer(r'^slot (\w+) (\S+) (\S+)', text, re.M)]
regions = [l.split() for l in open(os.path.join(RES, 'import_stubs.txt'))]
blob = open(os.path.join(RES, 'import_stubs.bin'), 'rb').read()


def target(addr):
    u = Uc(UC_ARCH_X86, UC_MODE_32)
    for base, size, off, _ in regions:
        b, s, o = int(base, 16), int(size, 16), int(off, 16)
        u.mem_map(b, s)
        u.mem_write(b, blob[o:o + s])
    u.mem_map(0x100000, 0x10000)
    sp = 0x108000
    u.mem_write(sp, struct.pack('<I', 0xdead0000))
    u.reg_write(UC_X86_REG_ESP, sp)
    u.reg_write(UC_X86_REG_EAX, 0x11223344)
    try:
        u.emu_start(addr, 0, count=64)
    except Exception:
        pass
    # `ret 4` took the address pushed last and dropped the saved eax: execution stopped at the function
    return u.reg_read(UC_X86_REG_EIP)


_exports = {}


def exports(name):
    if name in _exports:
        return _exports[name]
    out = {}
    for folder in (GAME, SYS, os.path.join(SYS, 'downlevel')):  # a module beside the game wins, as when loading
        p = os.path.join(folder, name)
        if not os.path.exists(p):
            continue
        d = open(p, 'rb').read()
        pe = struct.unpack_from('<I', d, 0x3c)[0]
        nsec = struct.unpack_from('<H', d, pe + 6)[0]
        opt = struct.unpack_from('<H', d, pe + 20)[0]
        if struct.unpack_from('<H', d, pe + 24)[0] != 0x10b:
            continue  # not a 32-bit module
        secs = [struct.unpack_from('<IIII', d, pe + 24 + opt + 40 * i + 8) for i in range(nsec)]

        def off(rva):
            for vs, va, rs, ro in secs:
                if va <= rva < va + max(vs, rs):
                    return ro + rva - va
            return None
        erva = struct.unpack_from('<I', d, pe + 24 + 96)[0]
        if not erva:
            break
        e = off(erva)
        base, nf, nn, af, an, ao = struct.unpack_from('<IIIIII', d, e + 16)
        funcs = struct.unpack_from(f'<{nf}I', d, off(af))
        named = {}
        for i in range(nn):
            nrva = struct.unpack_from('<I', d, off(an) + 4 * i)[0]
            o = struct.unpack_from('<H', d, off(ao) + 2 * i)[0]
            no = off(nrva)
            named[o] = d[no:d.index(b'\0', no)].decode('latin1')
        for i, rva in enumerate(funcs):
            if rva:
                out.setdefault(rva, named.get(i, f'#{base + i}'))
        break
    _exports[name] = out
    return out


rows, unknown = [], 0
for slot, stub in stubs:
    t = target(stub)
    mod = next(((n, b) for n, b, s in modules if b <= t < b + s), None)
    if not mod:
        rows.append((slot, '?', f'{t:#x}'))
        unknown += 1
        continue
    name = exports(mod[0]).get(t - mod[1])
    if not name:
        unknown += 1
    rows.append((slot, mod[0], name or f'+{t - mod[1]:#x}'))
with open(os.path.join(RES, '..', '..', 'client-src', 'import_table.txt'), 'w') as f:
    f.write('# slot rva  module  function   (stubs of the packer, resolved)\n')
    for slot, m, n in sorted(rows):
        f.write(f'{slot:08x} {m} {n}\n')
print(len(rows), 'stub slots,', unknown, 'not named')
import collections
c = collections.Counter(m for _, m, _ in rows)
print(c.most_common(40))
print([r for r in rows if r[2].startswith('+') or r[1] == '?'][:12])
print('slots from', hex(min(s for s, _, _ in rows)), 'to', hex(max(s for s, _, _ in rows)))
