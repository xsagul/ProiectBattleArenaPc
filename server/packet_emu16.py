"""The 16.20 client's own packet readers run on bytes of our choice: the 64-bit counterpart of packet_emu.py, with
the same names, so the learners (pkt_modes, pkt_codec, pkt_schema, pkt_tree) run on either (emu_backend.py picks).

What differs from 13.3:
  - the factory (rva 0xe678c0) builds the object for an id (constructor included); vtable slot 1 is the reader;
  - the reader gets a cursor that points AFTER the packet id: at the net id (netid16.py), then the body;
  - arguments travel in rcx, rdx, r8, r9; pointers in objects are 8 bytes.

  packet_emu16.py table                 id -> object size, reader; -> data/exe1620/packet_table.json
  packet_emu16.py check [max per id]    every packet kind of the replay through its reader -> data/exe1620/emu_check.txt
  packet_emu16.py fields <id> [n]       the first n packets of an id, fields in clear
"""
import bisect
import collections
import json
import os
import struct
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UcError, UC_HOOK_MEM_UNMAPPED, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import x86_const as X

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe1620')
sys.path.insert(0, HERE)
import rofl2      # noqa: E402
import netid16    # noqa: E402

PATCH = '16.20'
# exe_image_live.bin = the image of a client in a match from our server, taken by tools/snapshot16.py together with the
# pages outside the image that the readers touch (live_pages/): singletons the dump only holds pointers to
_LIVE = os.path.join(RES, 'exe_image_live.bin')
_IMG_PATH = os.environ.get('BA_EXE_IMG') or (_LIVE if os.path.exists(_LIVE) else os.path.join(RES, 'exe_image_t0.bin'))
PAGES = os.path.join(RES, 'live_pages')
ISA_AVAILABLE = 0x1e6cd98         # the C runtime's CPU level: below 3 its memset / memcpy stay off AVX
IMG = open(_IMG_PATH, 'rb').read()
BASE = int(open(_IMG_PATH[:-4] + '_pages.txt').readline().split()[1], 16)
FACTORY = 0xe678c0
ALLOCS = (0x1125b70,)             # operator new
FREES = (0x1125ba0,)
GETBITS, GETBITS_RET = 0xec69b0, 0xec6a2e      # header bits: (buffer in rcx, bit position in dl, width in r8b) -> al
GETBITS_READS = (0xec69d9, 0xec6a16)           # its own loads of header bytes
STACK, STACK_SIZE = 0x7000_0000_0000, 0x100000
HEAP, HEAP_SIZE = 0x6000_0000_0000, 0x4000000
BUF = 0x6800_0000_0000
TEB = 0x7200_0000_0000
STOP = 0x7100_0000_0000
PTR = 8
WIRE_SKIP = 1                     # bytes of the reader's input before the body: the net id (0 -> one byte)
ROFL = os.environ.get('BA_ROFL') or os.path.join(os.path.expanduser('~'), 'Documents', 'League of Legends', 'Replays',
                                                 'EUN1-4013530370.rofl')


def u32(r): return struct.unpack_from('<I', IMG, r)[0]


def _sections():
    pe = u32(0x3c)
    n, opt = struct.unpack_from('<H', IMG, pe + 6)[0], struct.unpack_from('<H', IMG, pe + 20)[0]
    return {IMG[pe + 24 + opt + i * 40:][:8].rstrip(b'\0').decode(): struct.unpack_from('<II', IMG, pe + 24 + opt + i * 40 + 8)
            for i in range(n)}


_SECS = _sections()
_fs = []
_fn_root = {}


def fn_of(rva):
    """start of the function that holds rva, from the exception table. The compiler splits a function into pieces,
    each with its own entry in the table; a piece's unwind data chains to its parent (flag 4), followed here to the
    function's first piece."""
    if not _fs:
        size, at = _SECS['.pdata']
        for o in range(at, at + size, 12):
            b, e, uw = struct.unpack_from('<III', IMG, o)
            if not b:
                break
            _fs.append(b)
            while IMG[uw] >> 3 & 4:                      # chained: the parent's table entry follows the unwind codes
                codes = IMG[uw + 2]
                pb, pe, uw = struct.unpack_from('<III', IMG, uw + 4 + 2 * (codes + (codes & 1)))
                _fn_root[b] = pb
        _fs.sort()
    start = _fs[max(bisect.bisect_right(_fs, rva) - 1, 0)]
    return _fn_root.get(start, start)


def ip(u): return u.reg_read(X.UC_X86_REG_RIP) - BASE
def retval(u): return u.reg_read(X.UC_X86_REG_RAX)


def getbits_call(u):
    """at the helper's first instruction -> (bit position, width, caller rva)"""
    ret = struct.unpack('<Q', bytes(u.mem_read(u.reg_read(X.UC_X86_REG_RSP), 8)))[0]
    return u.reg_read(X.UC_X86_REG_RDX) & 0xff, u.reg_read(X.UC_X86_REG_R8) & 0xff, ret - BASE


def sp(u): return u.reg_read(X.UC_X86_REG_RSP)
def read_ptr(u, a): return struct.unpack('<Q', bytes(u.mem_read(a, 8)))[0]
def pack_ptr(v): return struct.pack('<Q', v)
def ptr_of(b, off=0): return struct.unpack_from('<Q', b, off)[0]
def getbits_buf(u): return u.reg_read(X.UC_X86_REG_RCX)
def wire(pid, netid, body): return netid16.encode(netid) + body


def reader_entry(u):
    """at a struct reader's first instruction -> (return address, object, cursor pointer, end)"""
    return (read_ptr(u, sp(u)), u.reg_read(X.UC_X86_REG_RCX), u.reg_read(X.UC_X86_REG_RDX), u.reg_read(X.UC_X86_REG_R8))


def entry_kind(u, fn, is_cursor):
    """Both a struct reader and a helper get (rcx, cursor in rdx, end): a struct reader is slot 1 of the vtable of
    the object in rcx. Helpers that take the cursor first (rcx) are helpers too."""
    rcx, rdx = u.reg_read(X.UC_X86_REG_RCX), u.reg_read(X.UC_X86_REG_RDX)
    if is_cursor(rdx):
        try:
            vt = read_ptr(u, rcx)
            if BASE <= vt < BASE + len(IMG) - 16 and read_ptr(u, vt + 8) == BASE + fn:
                return 'reader'
        except Exception:
            pass
        return 'helper'
    return 'helper' if is_cursor(rcx) else None


def helper_cursor(u, is_cursor=None):
    rdx = u.reg_read(X.UC_X86_REG_RDX)
    return rdx if is_cursor is None or is_cursor(rdx) else u.reg_read(X.UC_X86_REG_RCX)



EMPTY_TEXT = BASE + 0x1a0e41c     # where an empty text's data pointer points (seen in a fresh object of packet 222)


def call_helper(emu, h, dst, cur, end):
    """a field helper: (destination, cursor, end) in rcx, rdx, r8"""
    return emu.call(h, dst, [cur, end])



def table():
    path = os.path.join(RES, 'packet_table.json')
    if not os.path.exists(path):
        make_table()
    return {int(k): v for k, v in json.load(open(path)).items()}


def make_table():
    emu = Emu()
    t = {}
    for pid in range(0x4e9 + 1):
        sizes = []
        emu.on_alloc = lambda p, n: sizes.append((p, n))
        out = emu.alloc(8)
        _, err = emu.call(FACTORY, out, [pid])
        emu.on_alloc = None
        obj = struct.unpack('<Q', emu.u.mem_read(out, 8))[0]
        if err or not obj:
            continue
        vt = struct.unpack('<Q', emu.u.mem_read(obj, 8))[0]
        if not BASE <= vt < BASE + len(IMG):
            continue
        des = struct.unpack('<Q', emu.u.mem_read(vt + 8, 8))[0] - BASE
        size = next((n for p, n in sizes if p == obj), 0)
        t[pid] = {'size': size, 'vt': vt - BASE, 'des': des, 'id': pid}
    json.dump(t, open(os.path.join(RES, 'packet_table.json'), 'w'))
    print(len(t), 'packet kinds with an object and a reader')
    return t


class Emu:
    def __init__(self):
        u = self.u = Uc(UC_ARCH_X86, UC_MODE_64)
        u.mem_map(BASE, (len(IMG) + 0xfff) & ~0xfff)
        u.mem_write(BASE, IMG)
        u.mem_map(STACK, STACK_SIZE)
        u.mem_map(HEAP, HEAP_SIZE)
        u.mem_map(BUF, 0x100000)
        u.mem_map(TEB, 0x10000)
        u.mem_map(STOP, 0x1000)
        u.mem_write(STOP, b'\xf4')
        # gs:[0x58] -> thread-local slots -> one block; +0x150 = the epoch that "initialise once" guards compare with:
        # a high value reads every static the dump already holds as initialised
        u.reg_write(X.UC_X86_REG_GS_BASE, TEB)
        u.mem_write(TEB + 0x58, struct.pack('<Q', TEB + 0x1000))
        u.mem_write(TEB + 0x1000, struct.pack('<Q', TEB + 0x2000) * 128)
        u.mem_write(TEB + 0x2000, struct.pack('<I', 0x7fffffff) * 0x800)
        u.mem_write(BASE + ISA_AVAILABLE, struct.pack('<I', 1))
        self.heap = HEAP
        self.unmapped = []
        self.on_alloc = None
        self.live = None
        self.extra = set()
        if _IMG_PATH == _LIVE and os.path.isdir(PAGES):
            for name in os.listdir(PAGES):
                self._map_page(int(name[:-4], 16), open(os.path.join(PAGES, name), 'rb').read())
        if os.environ.get('BA_LIVE_PID'):       # snapshot16.py: fetch missing pages from the running client and keep them
            import ctypes
            k32 = ctypes.WinDLL('kernel32')
            k32.OpenProcess.restype = ctypes.c_void_p
            self.live = (k32, k32.OpenProcess(0x0410, False, int(os.environ['BA_LIVE_PID'])))
        u.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        for f in ALLOCS + FREES:
            u.hook_add(UC_HOOK_CODE, self._stub, begin=BASE + f, end=BASE + f)

    def _map_page(self, page, data):
        if page not in self.extra:
            self.u.mem_map(page, 0x1000)
            self.extra.add(page)
        self.u.mem_write(page, data)

    def _unmapped(self, u, access, addr, size, value, data):
        if self.live and addr > 0x10000:
            import ctypes
            k32, h = self.live
            done = True
            for page in {addr & ~0xfff, (addr + size - 1) & ~0xfff}:
                if page in self.extra:
                    continue
                buf, got = ctypes.create_string_buffer(0x1000), ctypes.c_size_t()
                k32.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_ulonglong, ctypes.c_void_p, ctypes.c_size_t,
                                                  ctypes.POINTER(ctypes.c_size_t)]
                if not k32.ReadProcessMemory(h, page, buf, 0x1000, ctypes.byref(got)):
                    done = False
                    break
                os.makedirs(PAGES, exist_ok=True)
                open(os.path.join(PAGES, f'{page:x}.bin'), 'wb').write(buf.raw)
                self._map_page(page, buf.raw)
            if done:
                return True
        self.unmapped.append((ip(u), addr))
        return False

    def _stub(self, u, addr, size, data):
        sp = u.reg_read(X.UC_X86_REG_RSP)
        ret = struct.unpack('<Q', u.mem_read(sp, 8))[0]
        if addr - BASE in ALLOCS:
            n = u.reg_read(X.UC_X86_REG_RCX) & 0xffffffff
            p = self.alloc(n)
            if self.on_alloc:
                self.on_alloc(p, n)
            u.reg_write(X.UC_X86_REG_RAX, p)
        u.reg_write(X.UC_X86_REG_RSP, sp + 8)
        u.reg_write(X.UC_X86_REG_RIP, ret)

    def alloc(self, n):
        p = (self.heap + 15) & ~15
        self.heap = p + max(n, 1)
        if self.heap > HEAP + HEAP_SIZE - 0x1000:
            p = HEAP + 0x1000
            self.heap = p + n
        self.u.mem_write(p, b'\0' * max(n, 1))
        return p

    def call(self, fn_rva, this, args, limit=20_000_000):
        """fn(this, *args) with up to three more register arguments -> (rax, None) or (None, error)"""
        u = self.u
        sp = STACK + STACK_SIZE - 0x2000
        u.mem_write(sp, struct.pack('<Q', STOP))
        u.reg_write(X.UC_X86_REG_RSP, sp)
        for reg, v in zip((X.UC_X86_REG_RCX, X.UC_X86_REG_RDX, X.UC_X86_REG_R8, X.UC_X86_REG_R9), [this] + list(args)):
            u.reg_write(reg, v)
        self.unmapped = []
        try:
            u.emu_start(BASE + fn_rva, STOP, count=limit)
        except UcError as e:
            return None, f'{e} at {ip(u):#x} {self.unmapped[-1:]}'
        if u.reg_read(X.UC_X86_REG_RIP) != STOP:
            return None, f'did not return (rip {ip(u):#x})'
        return u.reg_read(X.UC_X86_REG_RAX), None

    def new_object(self, pid, trace=None):
        out = self.alloc(8)
        sizes = []
        self.on_alloc = lambda p, n: sizes.append((p, n))
        _, err = self.call(FACTORY, out, [pid])
        self.on_alloc = None
        obj = struct.unpack('<Q', self.u.mem_read(out, 8))[0]
        if err or not obj:
            return None, err or 'no object for this id'
        if trace is not None:
            trace['blocks'] = [(obj, next((n for p, n in sizes if p == obj), 0))] + [(p, n) for p, n in sizes if p != obj]
        return obj, None

    def deserialize(self, info, pid, netid, body, trace=None):
        """-> (reader's answer, bytes left over (0 = read exactly), object bytes) or (None, error, None).
        trace receives 'writes': [(writer rva, address, size, value)] for every store into the heap during the read,
        'blocks': [(address, size)] with the object first, 'wire': what the reader was given."""
        buf = netid16.encode(netid) + body
        self.u.mem_write(BUF, buf + bytes(64))
        obj, err = self.new_object(pid, trace)
        if obj is None:
            return None, 'factory: ' + str(err), None
        cursor = self.alloc(8)
        self.u.mem_write(cursor, struct.pack('<Q', BUF))
        hook = None
        if trace is not None:
            trace['wire'] = buf
            trace['writes'] = writes = []
            self.on_alloc = lambda p, n: trace['blocks'].append((p, n))
            last = []      # the hook runs before the store and gets no value for vector stores: read back afterwards

            def settle(u):
                for i, a, s in last:
                    writes[i] = (writes[i][0], a, s, int.from_bytes(bytes(u.mem_read(a, s)), 'little'))
                last.clear()

            def on_write(u, access, addr, size, value, data):
                settle(u)
                last.append((len(writes), addr, size))
                writes.append((ip(u), addr, size, 0))
            hook = self.u.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=HEAP, end=HEAP + HEAP_SIZE - 1)
        ok, err = self.call(info['des'], obj, [cursor, BUF + len(buf)])
        self.on_alloc = None
        if hook is not None:
            settle(self.u)
            self.u.hook_del(hook)
        if err:
            return None, err, None
        used = struct.unpack('<Q', self.u.mem_read(cursor, 8))[0] - BUF
        return (ok & 0xff), used - len(buf), bytes(self.u.mem_read(obj, info['size']))


KINDS = (1,)   # which records of the replay to read: 1 = chunks (the stream), 2 = keyframes (and the start record)
ENTRY = None   # only the record with this id


LIVE = os.environ.get('BA_LIVE')   # data/live/<gameId>: learn from a recorded live match instead of the replay
_live = None


def live_packets():
    """{record kind: [(t, ch, pid, net id, body)]} of the live recording's server packets, in the replay's kinds:
    3 = the answer to the client's first packets (game info), 2 = the start state, 1 = the match"""
    global _live
    if _live is None:
        import live16
        cap = live16.Capture(LIVE)
        _live = {3: [], 2: [], 1: []}
        for t, way, ch, pid, net, body in live16.rows(cap.path):
            if way == 'S2C':
                _live[3 if t < cap.gates[1] else 2 if t < cap.gates[2] else 1].append((t, ch, pid, net, body))
    return _live


def packets(path, only=None):
    if LIVE:
        kinds = KINDS + ((3,) if 2 in KINDS and ENTRY in (None, 1) else ())
        for k in kinds:
            for t, ch, pid, obj, body in live_packets()[k]:
                if only is None or pid == only:
                    yield t, ch, pid, obj, body
        return
    r = rofl2.Rofl2(path)
    kinds = KINDS + ((3,) if 2 in KINDS and ENTRY in (None, 1) else ())
    for e, (t, ch, pid, obj, body) in rofl2.stream(r, kinds):
        if ENTRY is not None and e['id'] != ENTRY:
            continue
        if only is None or pid == only:
            yield t, ch, pid, obj, body


_md = None
_obf_cache = {}


def is_obfuscation_store(rip):
    """A byte store inside an in-place loop: the loop loads `byte ptr [r]`, transforms it and stores it back through
    the same register, then steps and jumps back. That is how the client hides a field once it has read it."""
    global _md
    if rip in _obf_cache:
        return _obf_cache[rip]
    if _md is None:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_64
        _md = Cs(CS_ARCH_X86, CS_MODE_64)
    ins = list(_md.disasm(IMG[rip:rip + 80], BASE + rip))[:9]
    res = False
    if ins and ins[0].mnemonic == 'mov' and ins[0].op_str.startswith('byte ptr [') and '+' not in ins[0].op_str.split(']')[0]:
        reg = ins[0].op_str[len('byte ptr ['):].split(']')[0]
        for i in ins[1:]:
            if i.mnemonic in ('jne', 'jb', 'jnz') and i.op_str.startswith('0x'):
                start = int(i.op_str, 16) - BASE
                if 0 < rip - start < 0x200:
                    body = list(_md.disasm(IMG[start:rip], BASE + start))
                    res = any(b.mnemonic in ('mov', 'movzx', 'movsx') and b.op_str.endswith(f'byte ptr [{reg}]') for b in body)
                break
            if i.mnemonic in ('ret', 'jmp', 'call'):
                break
    _obf_cache[rip] = res
    return res


def plain_fields(trace, size, wire=None):
    """[(offset, plaintext bytes, hidden bytes, hiding store rva or None)] from a read's write trace (as packet_emu's)"""
    state = bytearray(size)
    plain, obf_by = {}, {}
    dirty = set(range(size))
    for w, off, n, val in trace:
        obf = is_obfuscation_store(w)
        for b in range(n):
            o = off + b
            if not 0 <= o < size:
                continue
            if obf:
                if o in dirty:
                    plain[o] = state[o]
                    obf_by[o] = w
                    dirty.discard(o)
            else:
                dirty.add(o)
            state[o] = (val >> (8 * b)) & 0xff
    for o in dirty:
        plain.pop(o, None)
        obf_by.pop(o, None)
    written = sorted({off + b for w, off, n, val in trace for b in range(n) if 0 <= off + b < size})
    out, cur = [], None
    for off in written:
        key = obf_by.get(off)
        if cur and cur[3] == key and key is not None and cur[0] + len(cur[1]) == off:
            cur[1].append(plain[off]); cur[2].append(state[off])
            continue
        cur = [off, bytearray([plain.get(off, state[off])]), bytearray([state[off]]), key]
        out.append(cur)
    merged = []
    for f in out:
        if merged and f[3] is None and merged[-1][3] is None and merged[-1][0] + len(merged[-1][1]) == f[0] and \
                _same_store(trace, merged[-1][0], f[0]):
            merged[-1][1] += f[1]; merged[-1][2] += f[2]
        else:
            merged.append(f)
    out = [(o, bytes(p), bytes(h), k) for o, p, h, k in merged]
    if wire:
        body = bytes(wire[WIRE_SKIP:])
        out = [(o, h, h, None) if k is not None and len(p) >= 8 and p in body else (o, p, h, k) for o, p, h, k in out]
    return out


def _same_store(trace, a, b):
    for w, off, n, val in reversed(trace):
        if off <= b < off + n:
            return off <= a < off + n
    return False


def decoded_blocks(emu, tr):
    """[(label, fields)] for the object and every block reachable from it through pointers"""
    blocks = tr['blocks']
    mem = [bytes(emu.u.mem_read(p, n)) for p, n in blocks]

    def owner(v):
        for j, (p, n) in enumerate(blocks):
            if p <= v < p + n:
                return j, v - p
        return None, 0
    order, label, start, seen = [0], {0: 'object'}, {0: 0}, {0}
    k = 0
    while k < len(order):
        i = order[k]
        k += 1
        m = mem[i]
        for off in range(start[i], len(m) - 7):
            v = struct.unpack_from('<Q', m, off)[0]
            if not HEAP <= v < HEAP + HEAP_SIZE:
                continue
            j, inner = owner(v)
            if j is not None and j not in seen and blocks[j][1] > 0:
                seen.add(j)
                order.append(j)
                start[j] = inner
                label[j] = f'block {blocks[j][1] - inner} B, pointed to by {label[i].split(",")[0]} +{off - start[i]:#x}'
    out = []
    for i in order:
        p, n = blocks[i]
        p += start[i]
        n -= start[i]
        local = [(w, a - p, s, v) for w, a, s, v in tr['writes'] if p <= a < p + n]
        out.append((label[i], plain_fields(local, n, tr.get('wire'))))
    return out


def meaningful(flds):
    return [f for f in flds if f[3] is not None or any(f[1])]


def print_fields(flds):
    for off, raw, hidden, w in meaningful(flds):
        num = int.from_bytes(raw, 'little')
        fl = struct.unpack('<f', raw)[0] if len(raw) == 4 else None
        shown = raw.hex() if len(raw) <= 8 else raw[:8].hex() + f'... ({len(raw)} B)'
        print(f'   +{off:#04x} {len(raw)}B {shown:16} = {num if len(raw) <= 8 else "":<11}' + (f' ({fl:.6g} as float)' if fl is not None else '') +
              (f'   hidden by {w:#x}' if w else '   (kept in clear)'))


def check(per_id):
    t = table()
    emu = Emu()
    seen = collections.Counter()
    res = collections.defaultdict(collections.Counter)
    errs = {}
    global KINDS
    for KINDS in ((2,), (1,)):
        for tm, ch, pid, obj, body in packets(ROFL):
            if seen[pid] >= per_id:
                continue
            seen[pid] += 1
            if pid not in t:
                res[pid]['no class'] += 1
                continue
            ok, left, _ = emu.deserialize(t[pid], pid, obj, body)
            if ok is None:
                res[pid]['error'] += 1
                errs.setdefault(pid, left)
            elif not ok:
                res[pid]['rejected'] += 1
            elif left != 0:
                res[pid][f'left {left}'] += 1
            else:
                res[pid]['exact'] += 1
    KINDS = (1,)
    with open(os.path.join(RES, 'emu_check.txt'), 'w') as f:
        exact = sum(1 for p in res if set(res[p]) == {'exact'})
        f.write(f'{exact} of {len(res)} packet kinds: every sampled packet read exactly to its last byte\n')
        for pid in sorted(res):
            f.write(f'{pid:4d} {dict(res[pid])} {errs.get(pid, "")}\n')
    lines = open(os.path.join(RES, 'emu_check.txt')).read().splitlines()
    print(lines[0])
    for line in lines[1:]:
        if "'exact'" not in line or ',' in line:
            print(line[:200])


def fields(pid, n):
    t = table()
    emu = Emu()
    global KINDS
    k = 0
    for KINDS in ((2,), (1,)):
        for tm, ch, p, obj, body in packets(ROFL, pid):
            tr = {}
            ok, left, o = emu.deserialize(t[pid], pid, obj, body, tr)
            print(f'{tm:9.3f} obj {obj:08x} ok {ok} left {left} body {body[:64].hex()}{"..." if len(body) > 64 else ""}')
            for name, flds in decoded_blocks(emu, tr):
                print(f'  {name}')
                print_fields(flds)
            k += 1
            if k >= n:
                return


if __name__ == '__main__':
    if sys.argv[1] == 'table':
        make_table()
    elif sys.argv[1] == 'check':
        check(int(sys.argv[2]) if len(sys.argv) > 2 else 200)
    elif sys.argv[1] == 'fields':
        fields(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3)
