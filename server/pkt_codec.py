"""Server -> client packet writers for the 13.3 client, learned from Riot's own readers (run in the emulator).

The client holds no writer for what the server sends (docs/MIGRARE_12.23.md "Scriitoarele de pachete lipsesc"), so
every writer is the inverse of a reader. The readers share one shape (measured on packet 79, see the doc section
"Pachetul 79"): a block of header bits, then the fields in a fixed order; for every field a few header bits give its
"mode": either a constant (no wire bytes) or a way of reading it off the wire. This tool learns every mode of every
field by running the reader on bodies it builds, and keeps what it learnt in data/exe133/codec/<id>.json:

  const    the field takes a fixed value
  fixed    n wire bytes, each one going through a byte table into one byte of the field
  varint   7-bit groups, low first, each byte through a table (continuation = bit 7 after the table)
  string   a varint length then the bytes, in one of three orders: fwd, rev, ends (first, last, second, ...)
  invalid  the reader rejects the packet

  pkt_codec.py learn <id> [k]      learn from the replay's k-th packet of that id (keyframe 1 first) -> codec/<id>.json
  pkt_codec.py show <id>           the learnt structure, one line per mode
  pkt_codec.py check <id> [n]      every replay packet: decode with Riot's reader, re-encode with the replay's own modes
                                   (must give the same bytes), re-encode with our mode choice (Riot's reader must give
                                   the same fields); then n packets of random field values through the reader
  pkt_codec.py fields <id> [k]     the fields of a replay packet, in clear

Use from Python: `spec = load(id)`, `body = encode(spec, values)`, `values = decode(id, body)`; values is
{field offset: bytes} (fixed / varint / const fields: the field's bytes in the object, little-endian; strings: the
text bytes).
"""
import json
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emu_backend import P  # noqa: E402
import pkt_modes as PM  # noqa: E402

OUT = os.path.join(P.RES, 'codec')
PAD = 400
# header bits a reader tests inline, without the getbits helper: (bit, width, object offset, size). Found by reading
# the reader's code (79: rva 0x8759de, `shr al, 6; and al, 1` on header byte 5 -> the bool at +0x0a).
INLINE = {79: [(46, 1, 0x0a, 1)]} if P.PATCH == '13.3' else {}
STRING_SIZE = 12   # Riot's string in a packet object: data pointer, size, capacity (no inline buffer)


class Reader:
    def __init__(self, pid):
        self.pid = pid
        self.info = P.table()[pid]
        self.emu = P.Emu()
        self.size = self.info['size']

    def run(self, body):
        """-> dict(ok, left, ev (timeline), obj (object bytes in clear), strings {object offset: bytes})"""
        (ok, left, obj), ev, tr = PM.timeline(self.emu, self.info, self.pid, body)
        r = {'ok': ok, 'left': left, 'ev': ev}
        if not tr.get('blocks'):
            r['obj'] = None
            return r
        blocks = tr['blocks']
        objp = blocks[0][0]
        final = bytearray(self.emu.u.mem_read(objp, self.size))
        plain = bytearray(final)
        for off, raw, hid, w in P.plain_fields([(w, a - objp, s, v) for w, a, s, v in tr['writes']
                                                if objp <= a < objp + self.size], self.size):
            plain[off:off + len(raw)] = raw
        r['obj'] = plain
        r['blocks'] = blocks
        r['tr'] = tr
        return r

    def string_at(self, r, off):
        """the text of a string field (its block's bytes in clear)"""
        ptr, n = struct.unpack_from('<II', r['obj'], off)
        if n == 0:
            return b''
        if n > 4096:
            return None
        for p, sz in r['blocks']:
            if p <= ptr < p + sz:
                state = bytearray(self.emu.u.mem_read(p, sz))
                for o, raw, hid, w in P.plain_fields([(w, a - p, s, v) for w, a, s, v in r['tr']['writes'] if p <= a < p + sz], sz):
                    state[o:o + len(raw)] = raw
                return bytes(state[ptr - p:ptr - p + n])
        return bytes(self.emu.u.mem_read(ptr, n))


def segment(ev, bit, nxt_bits=None):
    """events of one field: from its first header read to the next field's first header read"""
    start = next((i for i, e in enumerate(ev) if e[0] == 'bits' and e[1] == bit), None)
    if start is None:
        return None, False
    for i in range(start + 1, len(ev)):
        if ev[i][0] == 'bits' and ev[i][1] != bit:
            return ev[start:i], True
    return ev[start:], False


def reads_of(seg):
    return [e[1] for e in seg if e[0] == 'read' and e[1] >= 0]


def field_order(ev):
    order = []
    for e in ev:
        if e[0] == 'bits' and not any(o[0] == e[1] for o in order):
            order.append((e[1], e[2]))
    return order


# ---------------------------------------------------------------------------------------------------------- learning

class Learner:
    def __init__(self, pid, k):
        self.R = Reader(pid)
        self.pid = pid
        self.base = PM.packets(pid)[k]
        self.r0 = self.R.run(self.base)
        assert self.r0['ok'] and self.r0['left'] == 0, 'the replay packet does not read cleanly'
        ev = self.r0['ev']
        self.order = field_order(ev)
        # where each field's wire bytes start in the base body, and how many it has there
        self.pos = {}
        # the header ends where the first field's wire bytes start (reads before the first header-bit read are the
        # reader testing header bits inline)
        first = next(i for i, e in enumerate(ev) if e[0] == 'bits')
        self.header = min(e[1] for e in ev[first:] if e[0] == 'read' and e[1] >= 0)
        cur = self.header
        for bit, width in self.order:
            seg, _ = segment(ev, bit)
            rd = reads_of(seg)
            self.pos[bit] = (cur, len(rd))
            if rd:
                assert rd[0] == cur, f'field at bit {bit}: reads start at {rd[0]}, expected {cur}'
                cur = rd[-1] + 1
        self.rng = random.Random(79)

    def body_with(self, bit, width, mode, wire):
        """the base body with one field switched to `mode` and its wire bytes replaced by `wire` (+ padding)"""
        p, n = self.pos[bit]
        b = PM.set_bits(self.base, bit, width, mode)
        return b[:p] + bytes(wire) + b[p + n:] + bytes(PAD)

    def probe(self, bit, width, mode, wire):
        r = self.R.run(self.body_with(bit, width, mode, wire))
        seg, done = segment(r['ev'], bit)
        is_last = self.order[-1][0] == bit
        if seg is None:
            return r, None, False
        completed = done or (is_last and r['ok'])
        return r, reads_of(seg), completed

    def field_range(self, bit, width):
        lo, hi = None, None
        for m in range(1 << width):
            r, rd, ok, fill = self.first_probe(bit, width, m)
            seg, _ = segment(r['ev'], bit)
            if seg is None:
                continue
            for e in seg:
                if e[0] == 'write' and 0 <= e[1] < self.R.size:
                    lo = e[1] if lo is None else min(lo, e[1])
                    hi = e[1] + e[2] if hi is None else max(hi, e[1] + e[2])
        return lo, hi - lo

    def original(self, bit):
        p, n = self.pos[bit]
        return self.base[p:p + n]

    def first_probe(self, bit, width, m):
        """a probe in which the field reads to its end: the replay's own bytes, else a run of one repeated byte (a
        length read from random bytes is mostly too long)"""
        tries = [self.original(bit) + self._filler()] + [bytes([b]) * PAD for b in range(256)]
        for fill in tries:
            r, rd, ok = self.probe(bit, width, m, fill)
            if rd is not None and ok:
                return r, rd, ok, fill
        return r, rd, ok, tries[0]

    def _filler(self, n=PAD):
        return bytes(self.rng.randrange(256) for _ in range(n))

    def is_string(self, r, off, size):
        if size != STRING_SIZE or r['obj'] is None:
            return False
        ptr, n, cap = struct.unpack_from('<III', r['obj'], off)
        return P.HEAP <= ptr < P.HEAP + P.HEAP_SIZE and n <= cap

    def learn_field(self, bit, width, off=None, size=None):
        if off is None:
            off, size = self.field_range(bit, width)
        f = {'bit': bit, 'width': width, 'off': off, 'size': size, 'modes': {}}
        done_kinds = {}   # (wire bytes read, helpers) -> learnt mode, shared by modes that read the same way
        for m in range(1 << width):
            r, rd, ok, fill = self.first_probe(bit, width, m)
            if rd is None or not ok:
                f['modes'][m] = {'kind': 'invalid'}
                continue
            string = self.is_string(r, off, size)
            if not rd:
                val = self.R.string_at(r, off) if string else bytes(r['obj'][off:off + size])
                f['modes'][m] = {'kind': 'const', 'string' if string else 'value': val.hex()}
                continue
            seg, _ = segment(r['ev'], bit)
            helpers = tuple(sorted({PM.fn_of(e[2]) for e in seg if e[0] == 'read' and e[1] >= 0}))
            key = (helpers, string)
            if key in done_kinds:
                prev = done_kinds[key]
                mode = dict(prev, same_as=prev['mode'])
                if self.verify_same(bit, width, m, f, prev):
                    mode['mode'] = m
                    f['modes'][m] = mode
                    continue
            mode = self.learn_string(bit, width, m, off) if string else self.learn_bytes(bit, width, m, off, size)
            mode['mode'] = m
            mode['helpers'] = [f'{h:#x}' for h in helpers]
            done_kinds[key] = mode
            f['modes'][m] = mode
        if any(d['kind'] == 'string' for d in f['modes'].values()):
            # a text field: its constant modes hold a text (the object bytes are only a pointer, size, capacity)
            for m, d in f['modes'].items():
                if d['kind'] == 'const':
                    r, rd, ok, fill = self.first_probe(bit, width, m)
                    f['modes'][m] = {'kind': 'const', 'string': self.R.string_at(r, off).hex(), 'mode': m}
        return f

    def verify_same(self, bit, width, m, f, prev):
        """does mode m read exactly like an already learnt mode? (64 random values through both)"""
        for _ in range(64):
            v = self.random_value(prev, f['size'])
            w = encode_mode(prev, v, f['size'])
            ra, _, oka = self.probe(bit, width, prev['mode'], w)
            rb, _, okb = self.probe(bit, width, m, w)
            if not (oka and okb):
                return False
            if prev['kind'] == 'string':
                if self.R.string_at(ra, f['off']) != self.R.string_at(rb, f['off']):
                    return False
            elif ra['obj'][f['off']:f['off'] + f['size']] != rb['obj'][f['off']:f['off'] + f['size']]:
                return False
        return True

    def random_value(self, mode, size):
        if mode['kind'] == 'string':
            return bytes(self.rng.randrange(256) for _ in range(self.rng.randrange(0, 40)))
        if mode['kind'] == 'varint':
            return self.rng.getrandbits(8 * size).to_bytes(size, 'little')
        if mode['kind'] == 'fixed':
            v = bytearray(size)
            for k, tab in mode['map']:
                v[k] = self.rng.choice([x for x in tab if x is not None])
            return bytes(v)
        return bytes.fromhex(mode.get('value', ''))

    def learn_bytes(self, bit, width, m, off, size):
        """fixed or varint: vary the first wire byte; if the number of bytes read changes it is a varint"""
        fill = self._filler()
        counts = set()
        for v in range(256):
            _, rd, ok = self.probe(bit, width, m, bytes([v]) + fill[1:])
            counts.add(len(rd) if ok else -1)
        if len(counts) == 1 and -1 not in counts:
            return self.learn_fixed(bit, width, m, off, size, counts.pop())
        if len(counts) == 2 and -1 in counts and 1 in counts:
            # one byte, but the reader rejects some values (a range check after reading)
            return self.learn_fixed(bit, width, m, off, size, 1, partial=True)
        return self.learn_varint(bit, width, m, off, size)

    def learn_fixed(self, bit, width, m, off, size, n, partial=False):
        """partial: the reader rejects some wire bytes; their table entries stay None (values it does not accept)"""
        out = []
        for j in range(n):
            maps = []
            for check, base in ((False, self._filler()), (True, self._filler())):
                if check:
                    # the same table under other values of the other bytes (16 samples)
                    k, tab = maps[0]
                    for v in self.rng.sample(range(256), 16):
                        w = bytearray(base)
                        w[j] = v
                        r, rd, ok = self.probe(bit, width, m, w)
                        if tab[v] is None:
                            assert not ok
                        else:
                            assert ok and r['obj'][off + k] == tab[v], f'bit {bit} mode {m}: wire byte {j} depends on the other bytes'
                    break
                vals = []
                for v in range(256):
                    w = bytearray(base)
                    w[j] = v
                    r, rd, ok = self.probe(bit, width, m, w)
                    if partial and not ok:
                        vals.append(None)
                        continue
                    assert ok and len(rd) == n
                    vals.append(bytes(r['obj'][off:off + size]))
                good = [x for x in vals if x is not None]
                changed = [k for k in range(size) if len({x[k] for x in good}) > 1]
                assert len(changed) == 1, f'bit {bit} mode {m}: wire byte {j} moves object bytes {changed}'
                k = changed[0]
                tab = [x[k] if x is not None else None for x in vals]
                assert len(set(good)) == len(good), f'bit {bit} mode {m}: wire byte {j} is not a byte table'
                assert partial or len(good) == 256
                maps.append((k, tab))
            out.append(list(maps[0]))
        covered = sorted(k for k, t in out)
        return {'kind': 'fixed', 'n': n, 'map': out, 'covers': covered}

    def learn_varint(self, bit, width, m, off, size):
        fill = self._filler()
        S = [None] * 256
        for v in range(256):
            r, rd, ok = self.probe(bit, width, m, bytes([v]) + fill[1:])
            if ok and len(rd) == 1:
                S[v] = int.from_bytes(r['obj'][off:off + size], 'little')
        z = S.index(0)
        for v in range(256):
            if S[v] is None:
                r, rd, ok = self.probe(bit, width, m, bytes([v, z]) + fill[2:])
                assert ok and len(rd) == 2, f'bit {bit} mode {m}: varint byte {v:#x}'
                S[v] = 0x80 | int.from_bytes(r['obj'][off:off + size], 'little')
        assert sorted(S) == list(range(256)), f'bit {bit} mode {m}: varint table is not a permutation'
        return {'kind': 'varint', 'S': S}

    def learn_string(self, bit, width, m, off):
        fill = bytes(self.rng.randrange(256) for _ in range(PAD))
        L = [None] * 256   # wire byte -> length byte value (after the table)
        for v in range(256):
            r, rd, ok = self.probe(bit, width, m, bytes([v]) + fill[1:])
            if ok:
                s = self.R.string_at(r, off)
                if s is not None and len(rd) == 1 + len(s) and len(s) < 128:
                    L[v] = len(s)
        z = L.index(0)
        for v in range(256):
            if L[v] is None:
                r, rd, ok = self.probe(bit, width, m, bytes([v, z]) + fill[2:])
                s = self.R.string_at(r, off) if ok else None
                assert s is not None and len(rd) == 2 + len(s), f'bit {bit} mode {m}: length byte {v:#x}'
                L[v] = 0x80 | len(s)
        assert sorted(L) == list(range(256)), f'bit {bit} mode {m}: length table is not a permutation'
        Linv = {x: w for w, x in enumerate(L)}
        # the text: for lengths 1..7 find which wire byte lands at which index (two values per byte), then the byte
        # table in full at one place, checked with random values at every other place
        def text(n, j, v):
            w = bytearray([Linv[n]]) + bytearray(fill[1:])
            w[1 + j] = v
            r, rd, ok = self.probe(bit, width, m, w)
            s = self.R.string_at(r, off) if ok else None
            assert s is not None and len(s) == n, f'bit {bit} mode {m}: text of length {n}'
            return s
        layout = {}
        for n in range(1, 8):
            lay = []
            for j in range(n):
                a, b = text(n, j, 0x11), text(n, j, 0xee)
                changed = [k for k in range(n) if a[k] != b[k]]
                assert len(changed) == 1, f'bit {bit} mode {m}: length {n} wire byte {j} -> {changed}'
                lay.append(changed[0])
            layout[n] = lay
        order = None
        for name in ('fwd', 'rev', 'ends'):
            if all(layout[n] == text_order(name, n) for n in layout):
                order = name
        assert order, f'bit {bit} mode {m}: text layout {layout}'
        S = [text(2, 0, v)[layout[2][0]] for v in range(256)]
        assert len(set(S)) == 256
        mid = None
        if order == 'ends':
            mid = [text(3, 2, v)[1] for v in range(256)]
            assert len(set(mid)) == 256
        for n in layout:
            for j, k in enumerate(layout[n]):
                tab = mid if order == 'ends' and n % 2 and k == n // 2 else S
                for v in self.rng.sample(range(256), 8):
                    assert text(n, j, v)[k] == tab[v], f'bit {bit} mode {m}: text table at length {n} index {k}'
        mode = {'kind': 'string', 'order': order, 'L': L, 'S': S}
        if order == 'ends':
            mode['mid'] = mid
        return mode

    def learn_inline(self, bit, width, off, size):
        f = {'bit': bit, 'width': width, 'off': off, 'size': size, 'inline': True, 'modes': {}}
        for m in range(1 << width):
            r = self.R.run(PM.set_bits(self.base, bit, width, m))
            if not r['ok']:
                f['modes'][m] = {'kind': 'invalid'}
            else:
                f['modes'][m] = {'kind': 'const', 'value': bytes(r['obj'][off:off + size]).hex(), 'mode': m}
        return f


def text_order(name, n):
    """index in the text of the j-th text byte on the wire"""
    if name == 'fwd':
        return list(range(n))
    if name == 'rev':
        return list(range(n - 1, -1, -1))
    out, lo, hi = [], 0, n - 1
    while lo < hi:
        out += [lo, hi]
        lo += 1
        hi -= 1
    if lo == hi:
        out.append(lo)
    return out


def learn(pid, k=0):
    Lr = Learner(pid, k)
    spec = {'id': pid, 'size': Lr.R.size, 'header': Lr.header, 'fields': []}
    for bit, width, off, size in INLINE.get(pid, []):
        spec['fields'].append(Lr.learn_inline(bit, width, off, size))
        print(f'inline bit {bit}: +{off:#x}', flush=True)
    for bit, width in Lr.order:
        f = Lr.learn_field(bit, width)
        spec['fields'].append(f)
        print(f'bits {bit}..{bit + width - 1}: +{f["off"]:#x} {f["size"]} B  ' +
              ' '.join(f'{m}:{d["kind"]}' for m, d in f['modes'].items()), flush=True)
    used = sorted(b for f in spec['fields'] for b in range(f['bit'], f['bit'] + f['width']))
    spec['spare_bits'] = [b for b in range(8 * spec['header']) if b not in used]
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'{pid}.json'), 'w') as fh:
        json.dump(spec, fh)
    print('->', os.path.join(OUT, f'{pid}.json'))
    return spec


# ---------------------------------------------------------------------------------------------------------- writing

def load(pid):
    spec = json.load(open(os.path.join(OUT, f'{pid}.json')))
    for f in spec['fields']:
        f['modes'] = {int(m): d for m, d in f['modes'].items()}
    return spec


def _inv(tab):
    inv = [None] * 256
    for w, x in enumerate(tab):
        if x is not None:
            inv[x] = w
    return inv


def _varint(n, inv):
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        out.append(inv[b | (0x80 if n else 0)])
        if not n:
            return bytes(out)


def encode_mode(mode, v, size):
    k = mode['kind']
    if k == 'const':
        want = bytes.fromhex(mode.get('value', mode.get('string', '')))
        if v != want:
            raise ValueError(f'constant mode {mode.get("mode")} holds {want.hex()}, not {v.hex()}')
        return b''
    if k == 'fixed':
        out = bytearray(mode['n'])
        for j, (obj, tab) in enumerate(mode['map']):
            out[j] = _inv(tab)[v[obj]]
        return bytes(out)
    if k == 'varint':
        return _varint(int.from_bytes(v, 'little'), _inv(mode['S']))
    if k == 'string':
        out = bytearray(_varint(len(v), _inv(mode['L'])))
        S, mid = _inv(mode['S']), _inv(mode['mid']) if mode.get('mid') else None
        n = len(v)
        for idx in text_order(mode['order'], n):
            t = mid if mid and n % 2 and idx == n // 2 else S
            out.append(t[v[idx]])
        return bytes(out)
    raise ValueError(f'mode kind {k} cannot be written')


def fits(mode, v, size):
    k = mode['kind']
    if k == 'const':
        return v == bytes.fromhex(mode.get('value', mode.get('string', '')))
    if k == 'fixed':
        if any(_inv(tab)[v[obj]] is None for obj, tab in mode['map']):
            return False   # a value the reader rejects
        return sorted(mode['covers']) == list(range(size)) or all(v[i] == 0 for i in range(size) if i not in mode['covers'])
    return k in ('varint', 'string')


def choose(f, v):
    """the server's choice: a constant mode when one holds the value, else the first mode that can carry it"""
    for kinds in (('const',), ('fixed', 'varint', 'string')):
        for m in sorted(f['modes']):
            d = f['modes'][m]
            if d['kind'] in kinds and fits(d, v, f['size']):
                return m
    raise ValueError(f'no mode of the field at +{f["off"]:#x} can carry {v.hex()}')


def encode(spec, values, modes=None, spare=0):
    """values: {field offset: bytes}; modes: {header bit: mode} to force; spare: value of the unused header bits"""
    bits = spare
    wire = bytearray()
    for f in spec['fields']:
        v = values[f['off']]
        m = (modes or {}).get(f['bit'])
        if m is None:
            m = choose(f, v)
        bits |= m << f['bit']
        wire += encode_mode(f['modes'][m], v, f['size'])
    return bits.to_bytes(spec['header'], 'little') + bytes(wire)


def header_modes(spec, body):
    v = int.from_bytes(body[:spec['header']], 'little')
    modes = {f['bit']: (v >> f['bit']) & ((1 << f['width']) - 1) for f in spec['fields']}
    spare = sum(v & (1 << b) for b in spec['spare_bits'])
    return modes, spare


_readers = {}


def decode(pid, body, spec=None):
    """Riot's reader in the emulator -> {field offset: bytes}, or None when the reader rejects the body"""
    spec = spec or load(pid)
    R = _readers.get(pid) or _readers.setdefault(pid, Reader(pid))
    r = R.run(body)
    if not r['ok'] or r['left'] != 0:
        return None
    out = {}
    for f in spec['fields']:
        is_str = any(d['kind'] == 'string' or 'string' in d for d in f['modes'].values())
        out[f['off']] = R.string_at(r, f['off']) if is_str else bytes(r['obj'][f['off']:f['off'] + f['size']])
    return out


# ---------------------------------------------------------------------------------------------------------- checking

def check(pid, n_random):
    spec = load(pid)
    bodies = PM.packets(pid)
    same = fields_ok = 0
    for i, body in enumerate(bodies):
        vals = decode(pid, body, spec)
        modes, spare = header_modes(spec, body)
        again = encode(spec, vals, modes, spare)
        if again == body:
            same += 1
        else:
            print(f'packet {i}: re-encoded with its own modes differs\n  {body.hex()}\n  {again.hex()}')
        ours = encode(spec, vals)
        if decode(pid, ours, spec) == vals:
            fields_ok += 1
        else:
            print(f'packet {i}: our encoding reads back different fields')
    print(f'{len(bodies)} replay packets: {same} byte-identical with their own modes, {fields_ok} read back identical with ours')
    rng = random.Random(1)
    good = 0
    for t in range(n_random):
        vals = {}
        for f in spec['fields']:
            usable = [d for d in f['modes'].values() if d['kind'] != 'invalid']
            d = rng.choice(usable)
            if d['kind'] == 'const':
                v = bytes.fromhex(d.get('value', d.get('string', '')))
            elif d['kind'] == 'string':
                v = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 60)))
            elif d['kind'] == 'varint':
                v = rng.getrandbits(8 * f['size']).to_bytes(f['size'], 'little')
            else:
                v = bytearray(f['size'])
                for k, tab in d['map']:
                    v[k] = rng.choice([x for x in tab if x is not None])
                v = bytes(v)
            vals[f['off']] = v
        body = encode(spec, vals)
        back = decode(pid, body, spec)
        if back == vals:
            good += 1
        else:
            bad = [f'+{o:#x}' for o in vals if back is None or back.get(o) != vals[o]]
            print(f'random {t}: fields differ {bad if back else "(rejected)"}')
    print(f'{good} of {n_random} random packets read back identical')


def show(pid):
    spec = load(pid)
    print(f'packet {pid}: object {spec["size"]:#x} B, header {spec["header"]} B, unused header bits {spec["spare_bits"]}')
    for f in spec['fields']:
        print(f'+{f["off"]:#04x} {f["size"]:2d} B  bits {f["bit"]}..{f["bit"] + f["width"] - 1}' + ('  (inline)' if f.get('inline') else ''))
        for m, d in sorted(f['modes'].items()):
            k = d['kind']
            if k == 'const':
                s = f'= {d["value"]}' if 'value' in d else f'= "{bytes.fromhex(d["string"]).decode("utf8", "replace")}"'
            elif k == 'fixed':
                s = f'{d["n"]} wire bytes -> object bytes {[x[0] for x in d["map"]]}'
            elif k == 'string':
                s = f'text, order {d["order"]}'
            else:
                s = ''
            same = f' (reads like mode {d["same_as"]})' if 'same_as' in d else ''
            helpers = f' by {",".join(d["helpers"])}' if d.get('helpers') else ''
            print(f'     mode {m}: {k} {s}{helpers}{same}')


def fields(pid, k):
    spec = load(pid)
    body = PM.packets(pid)[k]
    vals = decode(pid, body, spec)
    modes, spare = header_modes(spec, body)
    for f in spec['fields']:
        v = vals[f['off']]
        print(f'+{f["off"]:#04x} mode {modes[f["bit"]]} ({f["modes"][modes[f["bit"]]]["kind"]}): {v.hex()}  {v!r}' if len(v) < 40 else f'+{f["off"]:#04x}: {v!r}')


if __name__ == '__main__':
    cmd, pid = sys.argv[1], int(sys.argv[2])
    arg = int(sys.argv[3]) if len(sys.argv) > 3 else None
    if cmd == 'learn':
        learn(pid, arg or 0)
    elif cmd == 'show':
        show(pid)
    elif cmd == 'check':
        check(pid, 200 if arg is None else arg)
    elif cmd == 'fields':
        fields(pid, arg or 0)
