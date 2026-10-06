"""Client -> server packets of the 13.3 client, read by our server: learnt from the client's own writer.

For these packets the reader in the vtable is a stub (rva 0x146910: `xor al, al; ret 8`), the mirror of the server
packets' writer stubs. The writer (vtable[0]) has the readers' shape: header bytes with a mode per field, the
fields after; it picks among equivalent modes at random (rand() % 6, rand state in the CRT per-thread data).

How values get into an object: the constructor sets each field to 0 and then hides it with a byte loop; a value
written into the field right after the zero store (before the loop) comes out hidden exactly as the game would hold
it. So: construct with our values, run the writer (rand seeded by us), look at the bytes.

  c2s_codec.py fields <ctor rva>               the constructor's fields (offset, size)
  c2s_codec.py write <ctor> <writer> <seed> <off=hex,...>   one packet's bytes for given field values
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import c2s_emu as C  # noqa: E402
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_CODE  # noqa: E402
from unicorn.x86_const import UC_X86_REG_EIP  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

_md = Cs(CS_ARCH_X86, CS_MODE_32)
PTD_HOLDRAND = 0x18     # the rand() state in the CRT per-thread data (rand at rva 0xf6ab25 reads [ptd + 0x18])


def ins_len(rva):
    i = next(_md.disasm(P.IMG[rva:rva + 16], P.BASE + rva))
    return i.size


def fields(ctor, size=0x200):
    """[(offset, size, inject rva)]: a run of zero stores into the object followed by its hiding loop"""
    e = C.machine()
    obj = e.alloc(size)
    ws = []
    h = e.u.hook_add(UC_HOOK_MEM_WRITE, lambda u, a, ad, s, v, d: ws.append((u.reg_read(UC_X86_REG_EIP) - P.BASE, ad - obj, s, v)),
                     begin=obj, end=obj + size - 1)
    e.call(ctor, obj, [])
    e.u.hook_del(h)
    out = []
    i = 0
    while i < len(ws):
        eip, off, s, v = ws[i]
        if v != 0 or off < 0xa:
            i += 1
            continue
        lo, hi, last = off, off + s, eip
        j = i + 1
        while j < len(ws) and ws[j][3] == 0 and ws[j][1] == hi:
            hi += ws[j][2]
            last = ws[j][0]
            j += 1
        # the hiding loop: byte stores over [lo, hi) by one instruction
        loop = [w for w in ws[j:j + (hi - lo)] if w[2] == 1 and lo <= w[1] < hi]
        if loop and len({w[0] for w in loop}) == 1:
            out.append((lo, hi - lo, last + ins_len(last)))
        i = j
    return out


class Writer:
    def __init__(self, ctor, writer, size=0x200):
        self.ctor, self.writer, self.size = ctor, writer, size
        self.fields = fields(ctor, size)
        self.e = C.machine()
        self.values = {}
        self.obj = None
        e = self.e
        for off, n, at in self.fields:
            def inject(u, a, s, d, off=off, n=n):
                v = self.values.get(off)
                if v is not None:
                    u.mem_write(self.obj + off, bytes(v).ljust(n, b'\0')[:n])
            e.u.hook_add(UC_HOOK_CODE, inject, begin=P.BASE + at, end=P.BASE + at)
        # the CRT per-thread data block c2s_emu hands rand(): find it once
        self.ptd = None

    def run(self, values, seed=1):
        """values {offset: bytes} -> the packet's wire bytes after [u16 id][u32 net id]"""
        e = self.e
        if e.heap > P.HEAP + P.HEAP_SIZE - 0x100000:
            e.heap = P.HEAP + 0x10000
        self.values = values
        self.obj = obj = e.alloc(self.size)
        self.obj_holder = obj
        _, err = e.call(self.ctor, obj, [])
        if err:
            raise RuntimeError('ctor: ' + err)
        if self.ptd is None:
            self.ptd = self._find_ptd()
        e.u.mem_write(self.ptd + PTD_HOLDRAND, struct.pack('<I', seed))
        data = e.alloc(0x1000)
        buf = e.alloc(16)
        e.u.mem_write(buf, struct.pack('<III', data, 0, 0x1000))
        _, err = e.call(self.writer, obj, [buf])
        if err:
            raise RuntimeError('writer: ' + err)
        p, n, _ = struct.unpack('<III', e.u.mem_read(buf, 12))
        return bytes(e.u.mem_read(p, n))[6:]

    def _find_ptd(self):
        """c2s_emu answers the CRT's getptd with a block of its own: call the hook's target once to learn it"""
        from unicorn.x86_const import UC_X86_REG_EAX
        _, err = self.e.call(C.GETPTD, 0, [])
        return self.e.u.reg_read(UC_X86_REG_EAX)


if __name__ == '__main__':
    if sys.argv[1] == 'fields':
        for off, n, at in fields(int(sys.argv[2], 16)):
            print(f'+{off:#x} {n} B (value goes in before rva {at:#x})')
    elif sys.argv[1] == 'write':
        w = Writer(int(sys.argv[2], 16), int(sys.argv[3], 16))
        vals = {}
        for item in sys.argv[5:]:
            k, v = item.split('=')
            vals[int(k, 16)] = bytes.fromhex(v)
        print(w.run(vals, int(sys.argv[4])).hex())


# ------------------------------------------------------------------------------------------------- learning

def _bits(h, pos, width):
    return (h >> pos) & ((1 << width) - 1)


def learn(ctor, writer, pid, header=3, seeds=48, rand=0):
    """every field: its header bits, its modes (const value / fixed tables / varint table), its place on the wire.
    rand: leading bytes the writer fills with rand() (491: one), left out of the header's mode bits"""
    import json
    import random
    W = Writer(ctor, writer)
    rng = random.Random(pid)
    hb = lambda out: int.from_bytes(out[rand:header], 'little') << (8 * rand)
    h0 = hb(W.run({}, 1))
    spec = {'id': pid, 'ctor': ctor, 'writer': writer, 'header': header, 'rand': rand, 'fields': []}
    for off, n, _ in W.fields:
        samples = []
        for t in range(seeds):
            k = t % 5
            if k == 0:
                v = bytes(rng.randrange(256) for _ in range(n))
            elif k == 1:
                v = (1).to_bytes(n, 'little')
            elif k == 2:
                v = b'\xff' * n
            elif k == 3:
                v = (2).to_bytes(n, 'little')
            else:
                v = struct.pack('<f', rng.choice([1.0, -1.0, 2.0, 0.5])).ljust(n, b'\0')[:n] if n >= 4 else bytes([rng.randrange(256)])
            s = rng.randrange(1, 1 << 30)
            out = W.run({off: v}, s)
            samples.append((v, s, hb(out), out[header:]))
        diff = 0
        for v, s, h, d in samples:
            diff |= h ^ h0
        bits = [b for b in range(8 * header) if diff >> b & 1]
        if not bits:   # the value never shows in the header: one mode only
            bits = []
        pos, width = (bits[0], bits[-1] - bits[0] + 1) if bits else (0, 0)
        f = {'off': off, 'size': n, 'bit': pos, 'width': width, 'modes': {}}
        # the all-zero value's mode is a constant
        f['modes'][_bits(h0, pos, width)] = {'kind': 'const', 'value': bytes(n).hex()}
        for v, s, h, d in samples:
            m = _bits(h, pos, width)
            if m in f['modes']:
                continue
            if not d:
                f['modes'][m] = {'kind': 'const', 'value': v.hex()}
            else:
                f['modes'][m] = _learn_read(W, off, n, v, s, header, pos, width, m, rand)
        # a constant mode's value: the simplest value that gives it (a bool takes any non-zero byte for 1)
        cands = [bytes(n), (1).to_bytes(n, 'little'), (2).to_bytes(n, 'little'), bytes([255]) * n]
        if n >= 4:
            cands += [struct.pack('<f', x).ljust(n, bytes(1)) for x in (1.0, -1.0, 2.0, 0.5)]
        for m, d in f['modes'].items():
            if d['kind'] != 'const':
                continue
            for c in cands:
                out = W.run({off: c}, 1)
                if _bits(hb(out), pos, width) == m and len(out) == len(W.run({}, 1)):
                    d['value'] = c.hex()
                    break
        spec['fields'].append(f)
        print(f'+{off:#x} {n} B bits {pos}..{pos + width - 1}: ' + ', '.join(f'{m}:{d["kind"]}' for m, d in sorted(f['modes'].items())), flush=True)
    spec['order'] = _order(W, spec)
    print('wire order:', [hex(o) for o in spec['order']])
    path = os.path.join(P.RES, 'codec', f'c2s_{pid}.json')
    with open(path, 'w') as fh:
        json.dump(spec, fh)
    print('->', path)
    return spec


def _learn_read(W, off, n, v0, seed, header, pos, width, m, rand=0):
    """the read mode m of a field: fixed (each value byte -> one wire byte through a table) or varint"""
    def run(v):
        out = W.run({off: v}, seed)
        if _bits(int.from_bytes(out[rand:header], 'little') << (8 * rand), pos, width) != m:
            return None
        return out[header:]
    lens = set()
    for b in range(0, 256, 17):
        for v in (bytearray(v0), bytearray(n)):
            v[0] = b
            if v == bytearray(n):
                continue
            d = run(bytes(v))
            if d is not None:
                lens.add(len(d))
    if len(lens) == 1 and lens.pop() == n:
        tabs = []
        for j in range(n):
            tab = [None] * 256
            where = None
            for b in range(256):
                v = bytearray(v0)
                v[j] = b
                d = run(bytes(v))
                if d is None:
                    continue
                if where is None:
                    ref = run(bytes(v0))
                    cand = [i for i in range(n) if d[i] != ref[i]]
                    if len(cand) == 1:
                        where = cand[0]
                    else:
                        continue
                tab[b] = d[where]
            tabs.append([where, tab])
        return {'kind': 'fixed', 'n': n, 'map': tabs}
    # varint: value x < 128 is one byte; the byte for a continuation group comes from two-byte values
    S = [None] * 256
    for x in range(128):
        d = run(x.to_bytes(n, 'little'))
        if d is not None and len(d) == 1:
            S[d[0]] = x
        d = run(((x << 7) | 3).to_bytes(n, 'little')) if x else None
        if d is not None and len(d) == 2:
            S[d[1]] = x
        d = run(((5 << 7) | x).to_bytes(n, 'little'))
        if d is not None and len(d) == 2:
            S[d[0]] = 0x80 | x
    return {'kind': 'varint', 'S': S}


def _order(W, spec):
    """the fields' order on the wire: all fields with a read value at once, one field's byte changed at a time"""
    import random
    rng = random.Random(9)
    vals = {f['off']: bytes(rng.randrange(1, 255) for _ in range(f['size'])) for f in spec['fields']}
    seed = 12345
    base = W.run(vals, seed)
    where = {}
    for f in spec['fields']:
        v = bytearray(vals[f['off']])
        v[0] ^= 0x01
        out = W.run({**vals, f['off']: bytes(v)}, seed)
        diff = [i for i in range(min(len(out), len(base))) if out[i] != base[i] and i >= spec['header']]
        where[f['off']] = diff[0] if diff else 10 ** 6
    return [o for o, _ in sorted(where.items(), key=lambda kv: kv[1])]


# ------------------------------------------------------------------------------------------------- reading

def load(pid):
    import json
    spec = json.load(open(os.path.join(P.RES, 'codec', f'c2s_{pid}.json')))
    for f in spec['fields']:
        f['modes'] = {int(m): d for m, d in f['modes'].items()}
    return spec


def decode(spec, body, end=None):
    """body after [u16 id][u32 net id] -> {field offset: value bytes} (None when a mode is unknown); end: a list
    that receives the offset where the learnt fields stop (491: its path follows)"""
    H = spec['header']
    R = spec.get('rand', 0)
    h = int.from_bytes(body[R:H], 'little') << (8 * R)
    at = H
    out = {}
    by_off = {f['off']: f for f in spec['fields']}
    for off in spec['order']:
        f = by_off[off]
        m = _bits(h, f['bit'], f['width'])
        d = f['modes'].get(m)
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
            S = d['S']
            x, shift = 0, 0
            while True:
                g = S[body[at]]
                at += 1
                x |= (g & 0x7f) << shift
                shift += 7
                if not g & 0x80:
                    break
            out[off] = x.to_bytes(f['size'], 'little')
        if end is not None and off == spec['order'][-1]:
            pass
    if end is not None:
        end.append(at)
    return out


def check(pid, n=300):
    """packets the client's writer makes from random values and seeds, read back by decode()"""
    import random
    spec = load(pid)
    W = Writer(spec['ctor'], spec['writer'])
    rng = random.Random(1)
    good = bad = 0
    for t in range(n):
        vals = {}
        for f in spec['fields']:
            k = rng.randrange(4)
            if k == 0:
                v = bytes(f['size'])
            elif k == 1:
                v = bytes(rng.randrange(256) for _ in range(f['size']))
            elif k == 2:
                v = rng.randrange(0, 300 if f['size'] > 1 else 256).to_bytes(f['size'], 'little')
            else:
                v = struct.pack('<f', rng.uniform(-15000, 15000)).ljust(f['size'], bytes(1))[:f['size']] if f['size'] >= 4 else bytes([rng.randrange(256)])
            if all(d['kind'] == 'const' for d in f['modes'].values()):
                v = bytes([rng.randrange(2)]).ljust(f['size'], bytes(1))
            if f['size'] == 8:
                v = struct.pack('<ff', rng.uniform(0, 15000), rng.uniform(0, 15000))
            vals[f['off']] = v
        body = W.run(vals, rng.randrange(1, 1 << 30))
        try:
            back = decode(spec, body)
        except Exception as e:
            back = None
        if back == vals:
            good += 1
        else:
            bad += 1
            if bad <= 3:
                print('differs:', {hex(o): (vals[o].hex(), back[o].hex() if back else None) for o in vals if not back or back[o] != vals[o]})
    print(f'{good} of {n} packets written by the client from random values read back identical')


if __name__ == '__main__' and sys.argv[1] == 'learn':
    learn(int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4]),
          header=int(sys.argv[5]) if len(sys.argv) > 5 else 3, rand=int(sys.argv[6]) if len(sys.argv) > 6 else 0)
if __name__ == '__main__' and sys.argv[1] == 'check':
    check(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 300)
