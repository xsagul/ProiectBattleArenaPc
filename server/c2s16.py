"""Client -> server packets of the 16.20 client, read by our server: learnt from the client's own writers
(the 16.20 counterpart of c2s_codec.py, whose learning code it reuses).

What differs from 13.3: a client packet is built in place where it is sent (on the stack), not by a constructor:
vtable, id at +8, then every field stored and hidden by a short byte loop right there. So:
  - the class list comes from the writers (tools/c2s_classes16.py -> data/exe1620/c2s_classes.txt);
  - a field's hiding is taken from its loop at the building site: the loop is run alone on every byte value
    (`hide_tables`); a field hidden by straight-line code (one byte) has no table and is learnt as it lies in memory;
  - the fields themselves are the object bytes the writer reads.
The writer picks among equivalent modes with rand() (rva 0x199b9c8), answered here from a seed.

  c2s16.py fields <id>          object fields the writer reads, and which have a hiding table
  c2s16.py learn <id>           -> data/exe1620/codec/c2s_<id>.json   (header length and random bytes found by trying)
  c2s16.py check <id> [n]       packets written by the client's writer from random values, read back
  c2s16.py decode <id> <hex>    a captured packet body (after the id and the net id)
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['BA_PATCH'] = '1620'
import packet_emu16 as P   # noqa: E402
import netid16             # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UcError   # noqa: E402
from unicorn import x86_const as X   # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_64   # noqa: E402

RAND = 0x199b9c8
OBJ_SIZE = 0x200
_md = Cs(CS_ARCH_X86, CS_MODE_64)
GPR = [getattr(X, 'UC_X86_REG_' + r) for r in ('RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'RBP', 'R8', 'R9', 'R10', 'R11', 'R12',
                                                'R13', 'R14', 'R15')]
REG64 = {r.lower(): getattr(X, 'UC_X86_REG_' + r) for r in ('RAX', 'RBX', 'RCX', 'RDX', 'RSI', 'RDI', 'RBP', 'R8', 'R9', 'R10', 'R11',
                                                             'R12', 'R13', 'R14', 'R15')}


def classes():
    out = {}
    for line in open(os.path.join(P.RES, 'c2s_classes.txt')):
        w = line.split()
        if w and w[0].isdigit():
            out[int(w[0])] = {'writer': int(w[2], 16), 'vtable': int(w[4], 16), 'site': int(w[7], 16) if w[7] != '-' else None}
    return out


def _fn_range(rva):
    """(start, end) of the piece of code that holds rva"""
    size, at = P._SECS['.pdata']
    for o in range(at, at + size, 12):
        b, e, _ = struct.unpack_from('<III', P.IMG, o)
        if b <= rva < e:
            return b, e
    return rva - 0x100, rva + 0x400


def hide_tables(site, emu=None):
    """{object offset: [256 hidden bytes]} for the fields hidden by a byte loop near the building site"""
    emu = emu or P.Emu()
    lo, hi = _fn_range(site)
    start = max(lo, site - 0x60)
    ins = None
    for back in range(16):
        cand = list(_md.disasm(P.IMG[start + back:hi + 0x40], P.BASE + start + back))
        if any(i.address - P.BASE <= site < i.address - P.BASE + i.size and i.mnemonic == 'lea' for i in cand):
            ins = cand
            break
    if ins is None:
        return {}
    # the object's base: the vtable store that follows the lea at the site
    k = next(n for n, i in enumerate(ins) if i.address - P.BASE <= site < i.address - P.BASE + i.size)
    base = None
    for i in ins[k + 1:k + 4]:
        m = re.match(r'qword ptr \[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\], (\w+)$', i.op_str)
        if i.mnemonic == 'mov' and m:
            base = (m.group(1), (int(m.group(3), 0) if m.group(3) else 0) * (-1 if m.group(2) == '-' else 1))
            break
    if base is None:
        return {}

    # other registers that hold the object's address (`mov r8, rcx` after the vtable store)
    alias = {base[0]}
    for i in ins[k:]:
        m = re.match(r'(\w+), (\w+)$', i.op_str)
        if i.mnemonic == 'mov' and m and m.group(2) in alias and base[1] == 0:
            alias.add(m.group(1))

    def rel(op):
        m = re.match(r'\w+, \[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$', op)
        if m and m.group(1) in alias:
            return (int(m.group(3), 0) if m.group(3) else 0) * (-1 if m.group(2) == '-' else 1) - base[1]
        return None
    out = {}
    for n, i in enumerate(ins):
        if i.mnemonic not in ('jne', 'jb') or not i.op_str.startswith('0x'):
            continue
        head = int(i.op_str, 16)
        if not 0 < i.address - head < 0x100:
            continue
        body = [x for x in ins if head <= x.address <= i.address]
        store = next((x for x in body if x.mnemonic == 'mov' and re.match(r'byte ptr \[(\w+)\], \w+$', x.op_str)), None)
        if store is None:
            continue
        reg = re.match(r'byte ptr \[(\w+)\]', store.op_str).group(1)
        # where the pointer starts: the nearest `lea reg, [base + d]` before the loop
        first = None
        for x in reversed([x for x in ins if x.address < head]):
            if x.mnemonic == 'lea' and x.op_str.startswith(reg + ','):
                first = rel(x.op_str)
                break
        if first is None or not 0x0c <= first < OBJ_SIZE:
            continue
        # where it stops: the lea of the register the pointer is compared with
        last = None
        cmp = next((x for x in body if x.mnemonic == 'cmp' and x.op_str.startswith(reg + ',')), None)
        if cmp is not None:
            other = cmp.op_str.split(', ')[1]
            for x in reversed([x for x in ins if x.address <= cmp.address]):
                if x.mnemonic == 'lea' and x.op_str.startswith(other + ','):
                    last = rel(x.op_str)
                    break
        size = last - first if last is not None and 0 < last - first <= 64 else 1
        # registers loaded with an address before the loop (a table used through `[index + reg]`)
        preset = {}
        for x in ins:
            if x.address >= head:
                break
            if x.mnemonic == 'lea' and 'rip' in x.op_str:
                r64 = x.op_str.split(',')[0]
                if r64 in REG64:
                    preset[r64] = x.address + x.size + int(x.op_str.split('rip')[1].split(']')[0].replace(' ', ''), 16)
        table = _run_loop(emu, head - P.BASE, reg, preset)
        if table is not None:
            for b in range(size):
                out[first + b] = table
    return out


def sub_objects(site):
    """[(object offset, constructor rva)]: `lea rcx, [object + d]` followed by a direct call, after the vtable store"""
    lo, hi = _fn_range(site)
    start = max(lo, site - 0x60)
    ins = None
    for back in range(16):
        cand = list(_md.disasm(P.IMG[start + back:hi + 0x40], P.BASE + start + back))
        if any(i.address - P.BASE <= site < i.address - P.BASE + i.size and i.mnemonic == 'lea' for i in cand):
            ins = cand
            break
    if ins is None:
        return []
    k = next(n for n, i in enumerate(ins) if i.address - P.BASE <= site < i.address - P.BASE + i.size)
    base = None
    for i in ins[k + 1:k + 4]:
        m = re.match(r'qword ptr \[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\], (\w+)$', i.op_str)
        if i.mnemonic == 'mov' and m:
            base = (m.group(1), (int(m.group(3), 0) if m.group(3) else 0) * (-1 if m.group(2) == '-' else 1))
            break
    if base is None:
        return []
    # a frame pointer: `lea rbp, [rsp - X]` then `sub rsp, Y` in the prologue -> rbp = rsp + (Y - X) afterwards
    # (707, the cast request, builds its embedded struct through rbp)
    frame = None
    lea_x = None
    root = P.fn_of(site)             # the function's first piece holds the prologue (the site may be in a later one)
    for i in _md.disasm(P.IMG[root:root + 0x60], P.BASE + root):
        m = re.match(r'rbp, \[rsp(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$', i.op_str)
        if i.mnemonic == 'lea' and m:
            lea_x = (int(m.group(2), 0) if m.group(2) else 0) * (-1 if m.group(1) == '-' else 1)
        if i.mnemonic == 'sub' and i.op_str.startswith('rsp, ') and lea_x is not None:
            frame = int(i.op_str.split(', ')[1], 0) + lea_x
            break
    out = []
    window = [i for i in ins if site - 0x30 <= i.address - P.BASE <= site + 0x60]
    for n, i in enumerate(window):
        m = re.match(r'rcx, \[(\w+)(?: ([+-]) (0x[0-9a-f]+|\d+))?\]$', i.op_str)
        rel = None
        if i.mnemonic == 'lea' and m:
            d = (int(m.group(3), 0) if m.group(3) else 0) * (-1 if m.group(2) == '-' else 1)
            if m.group(1) == base[0]:
                rel = d
            elif m.group(1) == 'rbp' and base[0] == 'rsp' and frame is not None:
                rel = d + frame
        if rel is not None:
            off = rel - base[1]
            # the next call, as long as rcx is not loaded again before it
            call = None
            for x in window[n + 1:n + 12]:
                if x.mnemonic == 'call':
                    call = x
                    break
                if x.op_str.startswith(('rcx,', 'ecx,')):
                    break
            if 0x10 <= off < OBJ_SIZE and call is not None and call.op_str.startswith('0x'):
                out.append((off, int(call.op_str, 16) - P.BASE))
    return out


def _run_loop(emu, head, reg, preset=None):
    """the loop's body run once per byte value: what it stores back"""
    u = emu.u
    buf = emu.alloc(16)
    table = []
    done = []
    h = u.hook_add(UC_HOOK_MEM_WRITE, lambda u, a, ad, s, v, d: (done.append(1), u.emu_stop()), begin=buf, end=buf)
    try:
        for v in range(256):
            u.mem_write(buf, bytes([v]))
            for r in GPR:
                u.reg_write(r, P.BASE)       # tables are indexed from the image base kept in some register
            for r64, addr in (preset or {}).items():
                u.reg_write(REG64[r64], addr)
            u.reg_write(REG64[reg], buf)
            u.reg_write(X.UC_X86_REG_RSP, P.STACK + P.STACK_SIZE - 0x4000)
            done.clear()
            try:
                u.emu_start(P.BASE + head, 0, count=400)
            except UcError:
                return None
            if not done:
                return None
            table.append(u.mem_read(buf, 1)[0])
    finally:
        u.hook_del(h)
    return table if len(set(table)) == 256 else None


class Writer:
    """the client's writer for one packet id, run on an object we fill (c2s_codec.Writer's interface)"""

    def __init__(self, pid):
        self.pid = pid
        self.c = classes()[pid]
        self.e = P.Emu()
        self.seed = 1
        self.e.u.hook_add(UC_HOOK_CODE, self._rand, begin=P.BASE + RAND, end=P.BASE + RAND)
        self.hide = hide_tables(self.c['site'], self.e) if self.c['site'] else {}
        # structs inside the packet (built at the site by their own constructor): the writer sends one only when it
        # differs from a default instance; here that test always says "differs", so the layout stays the same
        self.subs = sub_objects(self.c['site']) if self.c['site'] else []
        self.sub_addr = set()
        lo, hi = _fn_range(self.c['writer'])
        for i in _md.disasm(P.IMG[lo:hi], P.BASE + lo):
            if i.mnemonic == 'call' and i.op_str.startswith('0x'):
                self.e.u.hook_add(UC_HOOK_CODE, self._maybe_compare, begin=int(i.op_str, 16), end=int(i.op_str, 16))
        self.fields = [(off, n, None) for off, n in self._fields()]
        # a count of a list (the writer follows the list's pointer when it is not zero) is not a plain field
        self.lists = []
        keep = []
        for f in self.fields:
            try:
                self._write({f[0]: b'' + bytes(f[1] - 1)}, 1)
                keep.append(f)
            except RuntimeError:
                self.lists.append(f[0])
        self.fields = keep

    def _rand(self, u, addr, size, data):
        if self.lcg:
            self.seed = (self.seed * 214013 + 2531011) & 0xffffffff     # the C runtime's rand()
            value = (self.seed >> 16) & 0x7fff
        else:
            value = self.seed & 0x7fff        # every call the same: the choice among equivalent modes is the caller's
        sp = u.reg_read(X.UC_X86_REG_RSP)
        u.reg_write(X.UC_X86_REG_RAX, value)
        u.reg_write(X.UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
        u.reg_write(X.UC_X86_REG_RSP, sp + 8)

    def _maybe_compare(self, u, addr, size, data):
        rcx, rdx = u.reg_read(X.UC_X86_REG_RCX), u.reg_read(X.UC_X86_REG_RDX)
        if self.force and rcx in self.sub_addr and P.BASE <= rdx < P.BASE + len(P.IMG):
            sp = u.reg_read(X.UC_X86_REG_RSP)
            u.reg_write(X.UC_X86_REG_RAX, 0)
            u.reg_write(X.UC_X86_REG_RIP, struct.unpack('<Q', u.mem_read(sp, 8))[0])
            u.reg_write(X.UC_X86_REG_RSP, sp + 8)

    force = True
    lcg = False

    def _write(self, mem, seed, netid=0):
        e = self.e
        if e.heap > P.HEAP + P.HEAP_SIZE - 0x200000:
            e.heap = P.HEAP + 0x10000
        self.seed = seed
        obj = e.alloc(OBJ_SIZE)
        e.u.mem_write(obj, struct.pack('<QHHI', P.BASE + self.c['vtable'], self.pid, 0, netid))
        self.sub_addr = {obj + off for off, ctor in self.subs}
        for off, ctor in self.subs:
            _, err = e.call(ctor, obj + off, [])
            if err:
                raise RuntimeError('sub-object constructor: ' + err)
        for off, v in mem.items():
            e.u.mem_write(obj + off, bytes(v))
        data = e.alloc(0x2000)
        buf = e.alloc(32)
        e.u.mem_write(buf, struct.pack('<QII', data, 0, 0x2000))
        self.obj = obj
        _, err = e.call(self.c['writer'], obj, [buf])
        if err:
            raise RuntimeError('writer: ' + err)
        p, n, _ = struct.unpack('<QII', e.u.mem_read(buf, 16))
        return bytes(e.u.mem_read(p, n))

    def _fields(self):
        """object bytes from +0x10 on that the writer reads, as (offset, size) runs"""
        reads = set()

        def rd(u, access, addr, size, value, data):
            for k in range(size):
                reads.add(addr + k)
        e = self.e
        h = None
        out = set()
        for seed in (1, 7, 99):
            reads.clear()
            # hook the whole heap: the object's address is only known inside _write
            h = e.u.hook_add(UC_HOOK_MEM_READ, rd, begin=P.HEAP, end=P.HEAP + P.HEAP_SIZE - 1)
            try:
                self._write({}, seed)
            finally:
                e.u.hook_del(h)
            out |= {a - self.obj for a in reads if self.obj + 0x10 <= a < self.obj + OBJ_SIZE}
        for off, ctor in self.subs:
            out -= set(range(off, off + 8))
        runs, cur = [], None
        for o in sorted(out):
            # a field ends where the hiding changes (another loop) or the bytes stop
            # bytes with no hiding loop were hidden one by one (straight-line code): each is a field of its own
            same = (cur and o == cur[0] + cur[1] and self.hide.get(o) is not None and
                    (self.hide.get(o) is self.hide.get(cur[0])) and cur[1] < 16)
            if same:
                cur[1] += 1
            else:
                cur = [o, 1]
                runs.append(cur)
        return [(o, n) for o, n in runs]

    def run(self, values, seed=1):
        """values {offset: plain bytes} -> the packet's bytes after the id and the net id"""
        mem = {}
        for off, n, _ in self.fields:
            v = bytes(values.get(off, bytes(n))).ljust(n, b'\0')[:n]
            mem[off] = bytes(self.hide[off + k][b] if off + k in self.hide else b for k, b in enumerate(v))
        out = self._write(mem, seed)
        return out[(1 if self.pid < 251 else 2) + 1:]          # id, then net id 0 = one byte


class EmbeddedWriter(Writer):
    """the writer of a struct embedded in a client packet (707: the cast request's struct at +0x10, built through
    its own constructor; the packet's writer sends one header byte, then calls the struct's own writer = slot 0 of
    its vtable). Run alone: the struct at an object of ours (its vtable at +0, its fields after), the hiding tables
    of the packet's building site moved to the struct's offsets."""

    def __init__(self, pid, off, ctor):
        self.pid = pid
        self.c = dict(classes()[pid])
        self.e = P.Emu()
        self.seed = 1
        self.e.u.hook_add(UC_HOOK_CODE, self._rand, begin=P.BASE + RAND, end=P.BASE + RAND)
        site_hide = hide_tables(self.c['site'], self.e) if self.c['site'] else {}
        self.hide = {k - off: t for k, t in site_hide.items() if k >= off}
        self.subs, self.sub_addr = [], set()
        self.ctor = ctor
        obj = self.e.alloc(OBJ_SIZE)
        _, err = self.e.call(ctor, obj, [])
        if err:
            raise RuntimeError('constructor: ' + err)
        self.default = bytes(self.e.u.mem_read(obj, OBJ_SIZE))
        vt = struct.unpack_from('<Q', self.default, 0)[0]
        self.c['vtable'] = vt - P.BASE
        self.c['writer'] = struct.unpack('<Q', bytes(self.e.u.mem_read(vt, 8)))[0] - P.BASE
        # the struct's writer reads each field (`mov reg, size ptr [rsi + off]`) and un-hides its bytes one at a time
        # through a function of its own (`call unhide` with the byte in cl): the fields and their hiding come from
        # that code, not from the building site (whose loops store the same bytes hidden)
        static = self._static_fields()
        if static:
            self.hide = {}
            for off, n, fn in static:
                tab = [None] * 256
                for b in range(256):
                    r, err = self.e.call(fn, b, [])
                    tab[b] = r & 0xff if not err else None
                inv = [None] * 256
                for b, x in enumerate(tab):
                    if x is not None:
                        inv[x] = b
                for k in range(n):
                    self.hide[off + k] = inv          # plain value byte -> the byte kept in memory
            self.fields = [(o, n, None) for o, n, fn in static]
        else:
            self.fields = [(o, n, None) for o, n in self._fields()]
        self.lists = []
        keep = []
        for f in self.fields:
            try:
                self._write({f[0]: bytes(f[1])}, 1)
                keep.append(f)
            except RuntimeError:
                self.lists.append(f[0])
        self.fields = keep

    def _static_fields(self):
        lo = self.c['writer']
        ins = list(_md.disasm(P.IMG[lo:lo + 0x1400], P.BASE + lo))
        sizes = {'byte': 1, 'word': 2, 'dword': 4, 'qword': 8}
        out = {}
        for n, i in enumerate(ins):
            if i.mnemonic == 'ret':
                break
            m = re.match(r'\w+, (byte|word|dword|qword) ptr \[rsi(?: \+ (0x[0-9a-f]+|\d+))?\]$', i.op_str)
            if i.mnemonic in ('mov', 'movzx') and m:
                off = int(m.group(2), 0) if m.group(2) else 0
                for x in ins[n + 1:n + 14]:
                    if x.mnemonic == 'call' and x.op_str.startswith('0x'):
                        fn = int(x.op_str, 16) - P.BASE
                        if off >= 8:
                            out.setdefault(off, (off, sizes[m.group(1)], fn))
                        break
        return sorted(out.values())

    def _write(self, mem, seed, netid=0):
        e = self.e
        if e.heap > P.HEAP + P.HEAP_SIZE - 0x200000:
            e.heap = P.HEAP + 0x10000
        self.seed = seed
        obj = e.alloc(OBJ_SIZE)
        e.u.mem_write(obj, self.default)
        for o, v in mem.items():
            e.u.mem_write(obj + o, bytes(v))
        data = e.alloc(0x2000)
        buf = e.alloc(32)
        e.u.mem_write(buf, struct.pack('<QII', data, 0, 0x2000))
        self.obj = obj
        _, err = e.call(self.c['writer'], obj, [buf])
        if err:
            raise RuntimeError('writer: ' + err)
        p, n, _ = struct.unpack('<QII', e.u.mem_read(buf, 16))
        return bytes(e.u.mem_read(p, n))

    def _fields(self):
        reads = set()

        def rd(u, access, addr, size, value, data):
            for k in range(size):
                reads.add(addr + k)
        out = set()
        for seed in (1, 7, 99):
            reads.clear()
            h = self.e.u.hook_add(UC_HOOK_MEM_READ, rd, begin=P.HEAP, end=P.HEAP + P.HEAP_SIZE - 1)
            try:
                self._write({}, seed)
            finally:
                self.e.u.hook_del(h)
            out |= {a - self.obj for a in reads if self.obj + 8 <= a < self.obj + OBJ_SIZE}
        runs, cur = [], None
        for o in sorted(out):
            same = (cur and o == cur[0] + cur[1] and self.hide.get(o) is not None and
                    (self.hide.get(o) is self.hide.get(cur[0])) and cur[1] < 16)
            if same:
                cur[1] += 1
            else:
                cur = [o, 1]
                runs.append(cur)
        return [(o, n) for o, n in runs]

    def run(self, values, seed=1):
        mem = {}
        for off, n, _ in self.fields:
            v = bytes(values.get(off, bytes(n))).ljust(n, bytes(1))[:n]
            mem[off] = bytes(self.hide[off + k][b] if off + k in self.hide else b for k, b in enumerate(v))
        return self._write(mem, seed)


def _codec():
    """c2s_codec's learning code on this module's Writer and folders"""
    import c2s_codec as CC
    CC.Writer = lambda ctor, writer, size=0x200: Writer(ctor)
    CC.P = P
    return CC


def learn(pid, embedded=None):
    """every field: its header bits, its modes, its place on the wire -> codec/c2s_<id>.json (c2s_codec's format).
    The writer picks among equivalent modes with rand(): every pick is tried by answering rand() with 0..7.
    embedded = (offset, constructor rva): learn the packet's embedded struct instead (-> c2s_<id>.<offset>.json); the
    packet itself is then [one header byte][the struct's bytes]."""
    import random
    CC = _codec()
    W = EmbeddedWriter(pid, *embedded) if embedded else Writer(pid)
    rng = random.Random(pid)
    PICKS = range(8)
    zero = {k: W.run({}, k) for k in PICKS}
    # fields always on the wire (no mode): the value changes bytes, never the length
    always = []
    for off, n, _ in W.fields:
        outs = [W.run({off: bytes(rng.randrange(1, 255) for _ in range(n))}, 0) for _ in range(6)]
        if all(len(o) == len(zero[0]) for o in outs) and len({o for o in outs}) > 1 and all(o[:1] == zero[0][:1] for o in outs):
            changed = {i for o in outs for i in range(len(o)) if o[i] != zero[0][i]}
            if changed and min(changed) >= len(zero[0]) - sum(x[1] for x in W.fields):
                always.append((off, n, min(changed)))
    header = len(zero[0]) - sum(n for off, n, at in always if at >= 1)
    if any(len(z) != len(zero[0]) for z in zero.values()):
        raise RuntimeError('the empty packet changes length with the mode picked')
    hb = lambda out: int.from_bytes(out[:header], 'little')
    tail = sum(n for off, n, at in always)       # the always-sent fields come last on the wire

    class Cut:
        """the writer with the always-sent fields' bytes cut off: what is left after the header is one field's bytes"""
        fields = W.fields

        @staticmethod
        def run(values, seed=1):
            out = W.run(values, seed)
            return out[:len(out) - tail] if tail else out
    spec = {'id': pid, 'ctor': pid, 'writer': W.c['writer'], 'header': header, 'rand': 0, 'fields': [],
            'lists': W.lists, 'subs': [o for o, c in W.subs], 'no_table': [o for o, n, _ in W.fields if o not in W.hide]}
    pending = []
    for off, n, _ in W.fields:
        samples = []
        for k in PICKS:
            for t in range(6):
                if t == 0:
                    v = bytes(rng.randrange(256) for _ in range(n))
                elif t == 1:
                    v = (1).to_bytes(n, 'little')
                elif t == 2:
                    v = b'\xff' * n
                elif t == 3:
                    v = (2).to_bytes(n, 'little')
                elif t == 4:
                    v = struct.pack('<f', rng.choice([1.0, -1.0, 2.0, 0.5])).ljust(n, bytes(1))[:n]
                else:
                    v = (rng.randrange(1, 60000)).to_bytes(4, 'little').ljust(n, bytes(1))[:n]
                out = Cut.run({off: v}, k)
                samples.append((v, k, hb(out), out[header:]))
        diff = 0
        for v, k, h, d in samples:
            diff |= h ^ hb(zero[k])
        bits = [b for b in range(8 * header) if diff >> b & 1]
        pos, width = (bits[0], bits[-1] - bits[0] + 1) if bits else (0, 0)
        f = {'off': off, 'size': n, 'bit': pos, 'width': width, 'modes': {}}
        if width == 0:
            pending.append(f)        # its bits (if any) only move with the writer's pick: found below
            spec['fields'].append(f)
            continue
        else:
            for k in PICKS:
                f['modes'].setdefault(CC._bits(hb(zero[k]), pos, width), {'kind': 'const', 'value': bytes(n).hex()})
            for v, k, h, d in samples:
                m = CC._bits(h, pos, width)
                if m in f['modes']:
                    continue
                if not d:
                    f['modes'][m] = {'kind': 'const', 'value': v.hex()}
                else:
                    d2 = CC._learn_read(Cut, off, n, v, k, header, pos, width, m, 0)
                    if d2['kind'] == 'varint' and None in d2['S'] and n == 4:
                        d2 = _learn_nid(Cut, off, k, header, pos, width, m) or d2
                    f['modes'][m] = d2
        spec['fields'].append(f)
        print(f'+{off:#x} {n} B bits {pos}..{pos + width - 1}: ' + ', '.join(f'{m}:{d["kind"]}' for m, d in sorted(f['modes'].items())), flush=True)
    # header bits that change with the pick alone and belong to no field yet: the modes of a field that is always
    # sent (several equivalent ways of sending it, no constant mode reached by our values)
    owned = set()
    for f in spec['fields']:
        owned |= set(range(f['bit'], f['bit'] + f['width']))
    moving = 0
    for k in PICKS:
        moving |= hb(zero[k]) ^ hb(zero[0])
    free = [b for b in range(8 * header) if moving >> b & 1 and b not in owned]
    for f in pending:
        off, n = f['off'], f['size']
        if free and len(pending) == 1:
            f['bit'], f['width'] = free[0], free[-1] - free[0] + 1
        v0 = bytes(rng.randrange(1, 255) for _ in range(n))
        for k in PICKS:
            m = CC._bits(hb(W.run({off: v0}, k)), f['bit'], f['width'])
            if m not in f['modes']:
                f['modes'][m] = CC._learn_read(W, off, n, v0, k, header, f['bit'], f['width'], m, 0)
        if n == 1 and f['width']:
            # every value: some are sent by a constant mode (no byte on the wire)
            for k in PICKS:
                for x in range(256):
                    out = W.run({off: bytes([x])}, k)
                    m = CC._bits(hb(out), f['bit'], f['width'])
                    if m in f['modes']:
                        continue
                    if len(out) < len(zero[k]):
                        f['modes'][m] = {'kind': 'const', 'value': bytes([x]).hex()}
                    else:
                        f['modes'][m] = CC._learn_read(W, off, n, bytes([x]), k, header, f['bit'], f['width'], m, 0)
        print(f'+{off:#x} {n} B bits {f["bit"]}..{f["bit"] + f["width"] - 1} (always sent): ' +
              ', '.join(f'{m}:{d["kind"]}' for m, d in sorted(f['modes'].items())), flush=True)
    spec['order'] = CC._order(W, spec)
    print('header', header, 'B; wire order:', [hex(o) for o in spec['order']])
    name = f'c2s_{pid}.{embedded[0]:x}.json' if embedded else f'c2s_{pid}.json'
    if embedded:
        spec['embedded'] = {'off': embedded[0], 'ctor': embedded[1]}
    json.dump(spec, open(os.path.join(P.RES, 'codec', name), 'w'))
    return check(pid, 300)


def nid_number(v):
    """net id <-> the number that travels for it (netid16.py; the same operation both ways)"""
    return v if v & 0xffffff == 0 else v ^ 0x40000000


def _learn_nid(W, off, seed, header, pos, width, m):
    """a varint field that holds a net id: the byte table, found with ids whose wire numbers are small"""
    def run(number):
        out = W.run({off: nid_number(number).to_bytes(4, 'little')}, seed)
        if ((int.from_bytes(out[:header], 'little') >> pos) & ((1 << width) - 1)) != m:
            return None
        return out[header:]
    S = [None] * 256
    for x in range(128):
        d = run(x) if x else None
        if d is not None and len(d) == 1:
            S[d[0]] = x
        d = run((x << 7) | 3) if x else None
        if d is not None and len(d) == 2:
            S[d[1]] = x
        d = run((5 << 7) | x)
        if d is not None and len(d) == 2:
            S[d[0]] = 0x80 | x
    left = [i for i in range(256) if S[i] is None]
    missing = sorted(set(range(256)) - {x for x in S if x is not None})
    if len(left) == 1 and len(missing) == 1:       # the byte of the number 0 (zero is sent by a constant mode)
        S[left[0]] = missing[0]
        left = []
    return {'kind': 'varint', 'S': S, 'nid': True} if not left else None


def check(pid, n=300, quiet=False):
    """packets the client's writer makes from random values, with its own random picks, read back by decode()"""
    import random
    spec = load(pid)
    W = Writer(pid)
    W.lcg = True
    rng = random.Random(1)
    good = bad = 0
    for t in range(n):
        vals = {}
        for f in spec['fields']:
            k = rng.randrange(4)
            size = f['size']
            if k == 0:
                v = bytes(size)
            elif k == 1:
                v = bytes(rng.randrange(256) for _ in range(size))
            elif k == 2:
                v = rng.randrange(0, 300 if size > 1 else 256).to_bytes(size, 'little')
            else:
                v = struct.pack('<f', rng.uniform(-15000, 15000)).ljust(size, bytes(1))[:size] if size >= 4 else bytes([rng.randrange(256)])
            if size == 8:
                v = struct.pack('<ff', rng.uniform(0, 15000), rng.uniform(0, 15000))
            vals[f['off']] = v
        body = W.run(vals, rng.randrange(1, 1 << 30))
        try:
            back = decode(spec, body)
        except Exception:
            back = None
        if back is not None:
            back.pop('rest', None)
        if back == vals:
            good += 1
        else:
            bad += 1
            if bad <= 3 and not quiet:
                print('differs:', body.hex(), {hex(o): (vals[o].hex(), back[o].hex() if back else None) for o in vals if not back or back[o] != vals[o]})
    if not quiet:
        print(f'{good} of {n} packets written by the client from random values read back identical')
    return good


def load(pid):
    return _codec().load(pid)


def decode(spec, body):
    """a packet's bytes after the id and the net id -> {field offset: value bytes}, or None"""
    H = spec['header']
    h = int.from_bytes(body[:H], 'little')
    at = H
    out = {}
    by_off = {f['off']: f for f in spec['fields']}
    for off in spec['order']:
        f = by_off[off]
        d = f['modes'].get((h >> f['bit']) & ((1 << f['width']) - 1))
        if d is None:
            return None
        if d['kind'] == 'const':
            out[off] = bytes.fromhex(d['value'])
        elif d['kind'] == 'fixed':
            v = bytearray(f['size'])
            for j, (where, tab) in enumerate(d['map']):
                inv = {w: b for b, w in enumerate(tab) if w is not None}
                v[j] = inv[body[at + where]]
            out[off] = bytes(v)
            at += d['n']
        else:
            x, shift = 0, 0
            while True:
                g = d['S'][body[at]]
                at += 1
                x |= (g & 0x7f) << shift
                shift += 7
                if not g & 0x80:
                    break
            x &= (1 << (8 * f['size'])) - 1
            out[off] = (nid_number(x) if d.get('nid') else x).to_bytes(f['size'], 'little')
    out['rest'] = body[at:]
    return out


if __name__ == '__main__':
    cmd, pid = sys.argv[1], int(sys.argv[2])
    if cmd == 'fields':
        W = Writer(pid)
        print(f'packet {pid}: writer {W.c["writer"]:#x}, built at {W.c["site"]:#x}' if W.c['site'] else f'packet {pid}')
        for off, n, _ in W.fields:
            print(f'  +{off:#04x} {n:2} B  {"hidden by a loop (table found)" if off in W.hide else "no table: as it lies in memory"}')
        for off in W.lists:
            print(f'  +{off:#04x}       the count of a list (not learnt)')
        for off, ctor in W.subs:
            print(f'  +{off:#04x}       a struct of its own (constructor rva {ctor:#x})')
    elif cmd == 'learn':
        if len(sys.argv) > 4:
            learn(pid, (int(sys.argv[3], 16), int(sys.argv[4], 16)))      # learn <id> <struct offset> <constructor rva>
        else:
            learn(pid)
    elif cmd == 'check':
        check(pid, int(sys.argv[3]) if len(sys.argv) > 3 else 300)
    elif cmd == 'decode':
        v = decode(load(pid), bytes.fromhex(sys.argv[3]))
        if v:
            print('  bytes left after the fields:', v.pop('rest').hex() or '-')
        for off, b in (v or {}).items():
            print(f'  +{off:#04x} {b.hex()}' + (f'  floats {struct.unpack("<" + "f" * (len(b) // 4), b)}' if len(b) in (4, 8, 12) else ''))
        if v is None:
            print('not decodable')


def repair_varints(pid):
    """fill the varint tables the learner left with holes (1135, the shop's buy request: 2 of 256 entries): the
    writer is run on values whose wire bytes are known by construction (one byte for 3..127, two for 128 + x) and
    the byte seen on the wire is the table's entry -> codec/c2s_<id>.json rewritten"""
    path = os.path.join(P.RES, 'codec', f'c2s_{pid}.json')
    spec = json.load(open(path))
    W = Writer(pid)
    header = spec['header']
    for f in spec['fields']:
        for m, d in f['modes'].items():
            if d['kind'] != 'varint' or None not in d['S']:
                continue
            S = [None] * 256

            def wire(v):
                for k in range(8):
                    out = W.run({f['off']: v.to_bytes(f['size'], 'little')}, k)
                    if ((int.from_bytes(out[:header], 'little') >> f['bit']) & ((1 << f['width']) - 1)) == int(m):
                        return out[header:]
                return None
            for b in range(3, 128):
                w = wire(b)
                if w:
                    S[w[-1]] = b
            for x in range(128):
                w = wire(128 + x)
                if w and len(w) >= 2:
                    S[w[-2]] = 0x80 | x
                    S[w[-1]] = 1
            d['S'] = S
            print(f'{pid} +{f["off"]:#x} mode {m}: {sum(1 for s in S if s is not None)} of 256 table entries')
    json.dump(spec, open(path, 'w'))
