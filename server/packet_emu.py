"""Run the 13.3 client's own packet deserializers (from its in-memory image) on the packets of a .rofl replay.

The receive path (rva 0x351c60) hands vtable[1] of the packet object a cursor that points at the packet's u16 id,
followed by the u32 net id of the object it is about, then the body; the deserializer returns true and moves the cursor
past what it read. The replay stores id and net id in the block header, so the buffer is rebuilt as id + netid + body.

  packet_emu.py check [max per id]     every packet kind: does Riot's deserializer accept the replay's packets, and does it
                                       read exactly the whole body? -> data/exe133/emu_check.txt
  packet_emu.py one <id> [n]           the first n packets of an id: object bytes after deserialization, memory written
  packet_emu.py fields <id> [n]        the first n packets of an id, fields in clear
  packet_emu.py decode <out.jsonl.gz> [limit | k/N]   the whole stream, fields in clear
  packet_emu.py key <entry id> <command ...>          the same on one keyframe (a full state; the first is entry 1)
"""
import os
import struct
import sys
import collections
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UcError, UC_HOOK_MEM_UNMAPPED, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_GDTR, UC_X86_REG_FS, UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS, UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_FS_BASE

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe133')
sys.path.insert(0, HERE)
import rofl_packets  # noqa: E402

BASE = 0x580000
# the image with every code page unlocked (the keyframes' packet kinds are read by code the replay's first 900 s
# never ran); BA_EXE_IMG overrides
IMG = open(os.environ.get('BA_EXE_IMG') or os.path.join(RES, '..', '..', 'client-src', 'exe_image_unpacked.bin'), 'rb').read()
NEW, DELETE1, DELETE2 = 0x9bb8d0, 0x9bb940, 0x9bb930
POOL_FREE = 0x9d42e0   # the pool allocator's free (its state lives outside the image too): a no-op here
ALLOCS = (NEW, 0x9d4570)  # operator new; the game's own pool allocator (its state lives outside the image)
STACK, STACK_SIZE = 0x10000000, 0x100000
HEAP, HEAP_SIZE = 0x20000000, 0x4000000
BUF = 0x30000000
TEB = 0x40000000
STOP = 0x0BAD0000  # return address: emulation ends when it is reached


def table():
    t = {}
    for line in open(os.path.join(RES, 'packet_table.txt')):
        if line.startswith('#'):
            continue
        p = line.split()
        t[int(p[0])] = {'size': int(p[1], 16), 'ctor': int(p[2], 16), 'vt': int(p[3], 16), 'des': int(p[4], 16)}
    return t


class Emu:
    def __init__(self):
        u = self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        size = (len(IMG) + 0xfff) & ~0xfff
        u.mem_map(BASE, size)
        u.mem_write(BASE, IMG)
        u.mem_map(STACK, STACK_SIZE)
        u.mem_map(HEAP, HEAP_SIZE)
        u.mem_map(BUF, 0x100000)
        u.mem_map(TEB, 0x10000)
        u.mem_map(STOP, 0x1000)
        u.mem_write(STOP, b'\xf4')  # hlt
        self._teb(u)
        self.heap = HEAP
        self.unmapped = []
        u.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        for f in ALLOCS + (DELETE1, DELETE2, POOL_FREE):
            u.hook_add(UC_HOOK_CODE, self._stub, begin=BASE + f, end=BASE + f)
        self.on_alloc = None

    @staticmethod
    def _teb(u):
        """fs -> a TEB whose TLS slots all point at one block of 0x7fffffff: MSVC's thread-safe statics then read every
        static the dump already holds as initialised (the guard is never above the thread's epoch)."""
        def seg(base, lim, access):  # 4 KiB granularity, 32-bit
            return (lim & 0xffff) | ((base & 0xffffff) << 16) | (access << 40) | (((lim >> 16) & 0xf) << 48) | (0xc << 52) | ((base >> 24) << 56)
        gdt = TEB + 0x8000
        u.mem_write(gdt + 8 * 2, struct.pack('<Q', seg(0, 0xfffff, 0x93)))   # flat data, ring 0
        u.mem_write(gdt + 8 * 4, struct.pack('<Q', seg(TEB, 0xf, 0x93)))     # fs: the TEB
        u.reg_write(UC_X86_REG_GDTR, (0, gdt, 8 * 16 - 1, 0))
        for r in (UC_X86_REG_DS, UC_X86_REG_ES, UC_X86_REG_SS):
            u.reg_write(r, 2 << 3)
        u.reg_write(UC_X86_REG_FS, 4 << 3)
        u.mem_write(TEB + 0x18, struct.pack('<I', TEB))
        u.mem_write(TEB + 0x2c, struct.pack('<I', TEB + 0x100))
        u.mem_write(TEB + 0x100, struct.pack('<I', TEB + 0x2000) * 64)
        u.mem_write(TEB + 0x2000, struct.pack('<I', 0x7fffffff) * 0x800)

    def _unmapped(self, u, access, addr, size, value, data):
        self.unmapped.append((u.reg_read(UC_X86_REG_EIP) - BASE, addr))
        return False

    def _stub(self, u, addr, size, data):
        esp = u.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack('<I', u.mem_read(esp, 4))[0]
        if addr - BASE in ALLOCS:
            n = struct.unpack('<I', u.mem_read(esp + 4, 4))[0]
            p = self.alloc(n)
            if self.on_alloc:
                self.on_alloc(p, n)
            u.reg_write(UC_X86_REG_EAX, p)
        # cdecl: caller pops the arguments
        u.reg_write(UC_X86_REG_ESP, esp + 4)
        u.reg_write(UC_X86_REG_EIP, ret)

    def alloc(self, n):
        p = (self.heap + 15) & ~15
        self.heap = p + max(n, 1)
        if self.heap > HEAP + HEAP_SIZE - 0x1000:
            self.heap = HEAP + 0x1000
            p = HEAP + 0x1000
            self.heap = p + n
        self.u.mem_write(p, b'\0' * max(n, 1))
        return p

    def call(self, fn_rva, ecx, args, limit=2_000_000):
        u = self.u
        esp = STACK + STACK_SIZE - 0x1000
        frame = struct.pack('<I', STOP) + b''.join(struct.pack('<I', a) for a in args)
        esp -= len(frame)
        u.mem_write(esp, frame)
        u.reg_write(UC_X86_REG_ESP, esp)
        u.reg_write(UC_X86_REG_ECX, ecx)
        self.unmapped = []
        try:
            u.emu_start(BASE + fn_rva, STOP, count=limit)
        except UcError as e:
            return None, f'{e} at {u.reg_read(UC_X86_REG_EIP) - BASE:#x} {self.unmapped[-1:]}'
        if u.reg_read(UC_X86_REG_EIP) != STOP:
            return None, f'did not return (eip {u.reg_read(UC_X86_REG_EIP) - BASE:#x})'
        return u.reg_read(UC_X86_REG_EAX), None

    def deserialize(self, info, pid, netid, body, trace=None):
        """trace: a dict that receives 'writes': [(writer rva, address, size, value)] for every store into the heap
        (the object and whatever the deserializer allocates), 'blocks': [(address, size)] with the object first."""
        buf = struct.pack('<HI', pid, netid) + body
        self.u.mem_write(BUF, buf)
        obj = self.alloc(info['size'] + 64)
        _, err = self.call(info['ctor'], obj, [])
        if err:
            return None, 'ctor: ' + err, None
        cursor = self.alloc(4)
        self.u.mem_write(cursor, struct.pack('<I', BUF))
        hook = None
        if trace is not None:
            trace['blocks'] = [(obj, info['size'])]
            trace['wire'] = buf
            trace['writes'] = writes = []
            self.on_alloc = lambda p, n: trace['blocks'].append((p, n))

            # the hook runs before the store and does not get SSE stores' values (it reports 0 for each 8-byte half):
            # every store's value is read back from memory when the next store comes, or at the end
            last = []

            def settle(u):
                for i, a, s in last:
                    writes[i] = (writes[i][0], a, s, int.from_bytes(bytes(u.mem_read(a, s)), 'little'))
                last.clear()

            def on_write(u, access, addr, size, value, data):
                settle(u)
                last.append((len(writes), addr, size))
                writes.append((u.reg_read(UC_X86_REG_EIP) - BASE, addr, size, 0))
            hook = self.u.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=HEAP, end=HEAP + HEAP_SIZE - 1)
        ok, err = self.call(info['des'], obj, [cursor, BUF + len(buf)])
        self.on_alloc = None
        if hook is not None:
            settle(self.u)
            self.u.hook_del(hook)
        if err:
            return None, err, None
        used = struct.unpack('<I', self.u.mem_read(cursor, 4))[0] - BUF
        return (ok & 0xff), used - len(buf), bytes(self.u.mem_read(obj, info['size']))


KINDS = (1,)   # which entries of the replay to read: 1 = chunks (the stream), 2 = keyframes (full states)
ENTRY = None   # only the entry with this id


def packets(path, only=None):
    r = rofl_packets.Rofl(path)
    for e, (t, ch, pid, obj, body) in rofl_packets.stream(r, KINDS):
        if ENTRY is not None and e['id'] != ENTRY:
            continue
        if only is None or pid == only:
            yield t, ch, pid, obj, body


ROFL = os.path.join(HERE, '..', 'data', 'rofl', 'KR-6363178603_13.3.rofl')


def check(per_id):
    t = table()
    emu = Emu()
    seen = collections.Counter()
    res = collections.defaultdict(collections.Counter)
    errs = {}
    for tm, ch, pid, obj, body in packets(ROFL):
        if seen[pid] >= per_id:
            continue
        seen[pid] += 1
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
    with open(os.path.join(RES, 'emu_check.txt'), 'w') as f:
        exact = sum(1 for p in res if set(res[p]) == {'exact'})
        f.write(f'{exact} of {len(res)} packet kinds: every sampled packet read exactly to its last byte\n')
        for pid in sorted(res):
            f.write(f'{pid:4d} {dict(res[pid])} {errs.get(pid, "")}\n')
    print(open(os.path.join(RES, 'emu_check.txt')).read()[:3000])


def one(pid, n):
    t = table()
    emu = Emu()
    k = 0
    for tm, ch, p, obj, body in packets(ROFL, pid):
        ok, left, o = emu.deserialize(t[pid], pid, obj, body)
        print(f'{tm:9.3f} obj {obj:08x} body {body.hex()}\n   ok {ok} left {left} object {o.hex() if o else None}')
        k += 1
        if k >= n:
            break


_md = None
_obf_cache = {}


def is_obfuscation_store(eip):
    """A byte store inside an in-place loop: the loop loads `byte ptr [r]`, transforms it, stores `byte ptr [r]`, then
    `inc r`, `cmp r, ...` and jumps back. That is how the 13.3 client hides a field once it has read it. (A loop that
    stores through r but loads from elsewhere, the wire, is a reader decoding a byte buffer.)"""
    global _md
    if eip in _obf_cache:
        return _obf_cache[eip]
    if _md is None:
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        _md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(_md.disasm(IMG[eip:eip + 64], BASE + eip))[:6]
    res = False
    if ins and ins[0].mnemonic == 'mov' and ins[0].op_str.startswith('byte ptr [') and '+' not in ins[0].op_str.split(']')[0]:
        reg = ins[0].op_str[len('byte ptr ['):].split(']')[0]
        seen_inc = seen_cmp = False
        for i in ins[1:]:
            if i.mnemonic == 'inc' and i.op_str == reg:
                seen_inc = True
            if i.mnemonic == 'cmp' and i.op_str.startswith(reg + ','):
                seen_cmp = True
            if i.mnemonic in ('jne', 'jb', 'jnz') and seen_inc and seen_cmp:
                # the loop's body, from the jump's target to the store: does it load the byte it stores?
                start = int(i.op_str, 16) - BASE if i.op_str.startswith('0x') else None
                if start is not None and 0 < eip - start < 0x200:
                    body = list(_md.disasm(IMG[start:eip], BASE + start))
                    res = any(b.mnemonic in ('mov', 'movzx', 'movsx') and b.op_str.endswith(f'byte ptr [{reg}]') for b in body)
                break
    _obf_cache[eip] = res
    return res


def plain_fields(trace, size, wire=None):
    """[(offset, plaintext bytes, hidden bytes, obfuscating store rva or None)] from a deserialization's write trace"""
    state = bytearray(size)
    # byte offset -> value in clear: the state just before the LAST hiding pass over it. Vector fields are hidden once
    # while still empty (an init pass), then read and hidden again; a pass starts again when a plain store came between.
    plain = {}
    obf_by = {}
    dirty = set(range(size))  # bytes stored in clear since their last hiding store
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
    for o in dirty:  # stored in clear after the last hiding pass: the final value is the value
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
    # stores with no obfuscation: merge bytes written by one store instruction into one field
    merged = []
    for f in out:
        if merged and f[3] is None and merged[-1][3] is None and merged[-1][0] + len(merged[-1][1]) == f[0] and \
                _same_store(trace, merged[-1][0], f[0]):
            merged[-1][1] += f[1]; merged[-1][2] += f[2]
        else:
            merged.append(f)
    out = [(o, bytes(p), bytes(h), k) for o, p, h, k in merged]
    if wire:
        # a byte buffer is copied raw off the wire and the loop over it then DECODES it in place: when what stood
        # before the loop is a piece of the packet's body, the value in clear is what the loop left
        body = bytes(wire[6:])
        out = [(o, h, h, None) if k is not None and len(p) >= 8 and p in body else (o, p, h, k) for o, p, h, k in out]
    return out


def _same_store(trace, a, b):
    for w, off, n, val in reversed(trace):
        if off <= b < off + n:
            return off <= a < off + n
    return False


def fields(pid, n):
    """Per packet: every store into the object, grouped by the instruction that made it. A field's value in clear is
    the first store into its bytes; the stores that follow in a loop over the same bytes are the in-place obfuscation."""
    t = table()
    emu = Emu()
    k = 0
    for tm, ch, p, obj, body in packets(ROFL, pid):
        tr = {}
        ok, left, o = emu.deserialize(t[pid], pid, obj, body, tr)
        print(f'{tm:9.3f} obj {obj:08x} ok {ok} left {left} body {body[:64].hex()}{"..." if len(body) > 64 else ""}')
        for name, flds in decoded_blocks(emu, tr):
            print(f'  {name}')
            print_fields(flds)
        k += 1
        if k >= n:
            break


def decoded_blocks(emu, tr):
    """[(label, fields)] for the object and every block reachable from it through pointers (vectors' storage)"""
    blocks = tr['blocks']
    mem = [bytes(emu.u.mem_read(p, n)) for p, n in blocks]
    def owner(v):  # large allocations are aligned inside a bigger block, so a pointer may land past its start
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
        for off in range(start[i], len(m) - 3):
            v = struct.unpack_from('<I', m, off)[0]
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
    """drop what the constructors zero-filled: stores kept in clear whose value is 0 (fields the packet really carries
    are hidden after reading, or hold something)"""
    return [f for f in flds if f[3] is not None or any(f[1])]


def decode(out_path, limit=None, shard=None):
    """the whole replay, every packet as its fields in clear -> gzip jsonl:
    {"t", "id", "obj", "f": [[block, offset, hex in clear, hidden?], ...]}; block 0 is the packet object, then the
    blocks reachable from it in the order decoded_blocks finds them"""
    import gzip
    import json
    t = table()
    emu = Emu()
    n = bad = 0
    with gzip.open(out_path, 'wt') as f:
        for index, (tm, ch, pid, obj, body) in enumerate(packets(ROFL)):
            if shard and index % shard[1] != shard[0]:
                continue
            tr = {}
            ok, left, o = emu.deserialize(t[pid], pid, obj, body, tr)
            if ok is None or not ok or left:
                bad += 1
                f.write(json.dumps({'i': index, 't': round(tm, 4), 'id': pid, 'obj': obj, 'error': str(left)}) + '\n')
                continue
            fl = []
            for bi, (name, flds) in enumerate(decoded_blocks(emu, tr)):
                for off, raw, hidden, w in meaningful(flds):
                    if bi == 0 and off < 0xa:
                        continue  # id and net id, already in the record
                    fl.append([bi, off, raw.hex(), 1 if w else 0])
            f.write(json.dumps({'i': index, 't': round(tm, 4), 'id': pid, 'obj': obj, 'f': fl}, separators=(',', ':')) + '\n')
            n += 1
            if n % 50000 == 0:
                print(n, 'packets', flush=True)
            if limit and n >= limit:
                break
    print(n, 'packets decoded,', bad, 'failed ->', out_path)


def print_fields(flds):
    for off, raw, hidden, w in meaningful(flds):
        num = int.from_bytes(raw, 'little')
        fl = struct.unpack('<f', raw)[0] if len(raw) == 4 else None
        shown = raw.hex() if len(raw) <= 8 else raw[:8].hex() + f'... ({len(raw)} B)'
        print(f'   +{off:#04x} {len(raw)}B {shown:16} = {num if len(raw) <= 8 else "":<11}' + (f' ({fl:.6g} as float)' if fl is not None else '') +
              (f'   hidden by {w:#x}' if w else '   (kept in clear)'))


if __name__ == '__main__':
    # `key <entry id> <command...>`: the same commands on one keyframe instead of the chunks
    if sys.argv[1] == 'key':
        KINDS, ENTRY = (2,), int(sys.argv[2])
        del sys.argv[1:3]
    if sys.argv[1] == 'fields':
        fields(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3)
        sys.exit()
    if sys.argv[1] == 'decode':
        # decode <out.jsonl.gz> [limit | k/N: only the packets whose index in the stream % N == k]
        arg = sys.argv[3] if len(sys.argv) > 3 else None
        if arg and '/' in arg:
            decode(sys.argv[2], None, tuple(int(x) for x in arg.split('/')))
        else:
            decode(sys.argv[2], int(arg) if arg else None)
        sys.exit()
    if sys.argv[1] == 'check':
        check(int(sys.argv[2]) if len(sys.argv) > 2 else 200)
    elif sys.argv[1] == 'one':
        one(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 5)
