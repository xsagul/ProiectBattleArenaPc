"""Writers for nested server -> client packets (13.3 client), learnt from Riot's readers struct by struct.

A packet object and every object inside it (a player record, the match configuration, ...) has a vtable whose entry
1 reads it: header bytes holding each field's mode bits (some tested through rva 0x91cae0, some directly in the
reader's code), then the fields in a fixed order. pkt_tree.py finds the instances in a replay packet and runs each
reader alone on its own bytes; this tool learns, for every struct type, every mode of every field:

  const      a fixed value (no wire bytes)
  fixed      n wire bytes, each through a byte table into one byte of the field
  varint     7-bit groups, low first, each byte through a table
  text       a varint length, then the bytes (order fwd / rev / ends, byte tables)
  seq        a varint count, then the elements in order fwd / rev / ends; an element is a text or a struct
  struct     an object embedded in this one, read by its own reader
  invalid    the reader rejects the packet

  pkt_schema.py learn <id>          -> data/exe133/codec/<id>.tree.json
  pkt_schema.py show <id>           the learnt structure
  pkt_schema.py check <id> [n]      the replay packet decoded, re-encoded with our mode choices and read back by
                                    Riot's reader (must give the same values); then n random variations
  pkt_schema.py dump <id>           the replay packet's values in clear (json) -> data/exe133/codec/<id>.values.json

Values: a struct is {"+0x18": value, ...}; fixed / varint / const fields are hex of the field's bytes; a text is
{"text": hex}; a seq is a list.
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
import pkt_tree as PT  # noqa: E402

OUT = os.path.join(P.RES, 'codec')
PAD = 64
MAXOBJ = 0x800      # a struct's own fields lie within this many bytes of its object
SEQ_SIZE = P.PTR + 8   # Riot's text / vector field: data pointer, u32 count, u32 capacity (12 B on 13.3, 16 B on 16.20)
EMPTY_TEXT = P.EMPTY_TEXT


def seq_head(b):
    """(data pointer, count) of a text / vector field's first bytes"""
    return P.ptr_of(b), struct.unpack_from('<I', b, P.PTR)[0]


def in_heap(v):
    return P.HEAP <= v < P.HEAP + P.HEAP_SIZE


# ------------------------------------------------------------------------------------------------- one run, analysed

class Run:
    """a reader's run with its events split by depth (inside a child reader or not) and its memory in clear"""

    def __init__(self, T, inst, wire, helpers=(), stop=None):
        self.T = T
        self.r = T.run(inst, wire, True, helpers, stop)
        self.ok = self.r['ok']
        self.used = self.r['used']
        self.obj = self.r['obj']
        ev = self.r['ev']
        act = []          # entry esp of the children being read
        for e in ev:
            esp = e[-1]
            if e[0] == 'out':
                # a child returned: its entry esp is just below the esp after its return
                while act and act[-1] < esp:
                    act.pop()
            e.append(len(act))           # depth
            if e[0] == 'in':
                act.append(esp)
        self.ev = ev


# The hiding loops of a field read its bytes and write them back transformed; packet_emu.plain_fields needs the value
# of every store. Tree.run records stores without values, so values are captured here with a second hook.
def _patch_values():
    from unicorn import UC_HOOK_MEM_WRITE
    old_run = PT.Tree.run

    def run(self, inst, wire, trace=True, helpers=(), stop=None):
        if not trace:
            return old_run(self, inst, wire, trace, helpers, stop)
        u = self.emu.u
        vals = []
        last = []

        def settle(u):
            for i, a, s in last:
                vals[i] = int.from_bytes(bytes(u.mem_read(a, s)), 'little')
            last.clear()

        def on_write(u, acc, a, s, v, d):
            settle(u)
            last.append((len(vals), a, s))
            vals.append(0)
        h = u.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=P.HEAP, end=P.HEAP + P.HEAP_SIZE - 1)
        try:
            r = old_run(self, inst, wire, trace, helpers, stop)
        finally:
            settle(u)
            u.hook_del(h)
        # the two hooks fire in the same order for every store; the cursor stores are among them
        k = 0
        for e in r['ev']:
            if e[0] in ('write', 'cur'):
                if e[0] == 'write':
                    e.insert(4, vals[k])     # ['write', addr, size, eip, value, esp]
                k += 1
        return r
    PT.Tree.run = run


_patch_values()


def plain_bytes(run, addr, n):
    """n bytes at addr in clear: the state before each byte's last hiding pass (packet_emu.plain_fields)"""
    u = run.T.emu.u
    blocks = [(run.obj, MAXOBJ)] + list(run.r['blocks'])
    for p, sz in blocks:
        if p <= addr < p + max(sz, 1):
            key = (p, sz)
            cache = run.__dict__.setdefault('_pcache', {})
            if key not in cache:
                state = bytearray(u.mem_read(p, max(sz, 1)))
                local = [(e[3], e[1] - p, e[2], e[4]) for e in run.ev if e[0] == 'write' and p <= e[1] < p + max(sz, 1)]
                for off, raw, hid, w in P.plain_fields(local, max(sz, 1)):
                    state[off:off + len(raw)] = raw
                cache[key] = state
            st = cache[key]
            o = addr - p
            if o + n <= len(st):
                return bytes(st[o:o + n])
    return bytes(u.mem_read(addr, n))


# ------------------------------------------------------------------------------------------------- struct analysis

class StructLearner:
    def __init__(self, T, fn, schema, known=None, k=0):
        self.T = T
        self.fn = fn
        self.schema = schema
        self.inst = T.of(fn)[k]
        self.prefix = P.WIRE_SKIP if fn == T.info['des'] else 0
        wire = T.wire[self.inst['start']:self.inst['end']]
        r = Run(T, self.inst, wire)
        assert r.ok, f'{fn:#x}: its own bytes do not read alone ({r.r["err"]})'
        self.base = wire[:r.used]
        self.rng = random.Random(fn)
        # helpers: every function other than the readers that reads wire bytes
        self.helpers = sorted({PM.fn_of(e[2]) for e in r.ev if e[0] == 'read'} - set(T.readers))
        r = self.run(self.base)
        self.r0 = r
        # header: where the reader first moves its cursor past the header (the packet reader first skips id + net id)
        curs = [e[1] for e in r.ev if e[0] == 'cur' and PM.fn_of(e[2]) == fn and e[-1] == 0]
        curs = [c for c in curs if c > self.prefix]
        self.header = curs[0] - self.prefix
        self.hstart = self.prefix
        self.dstart = self.prefix + self.header
        self.fields = self.split(r)
        if known:
            # bit positions already learnt (saved schema): the fields come in the same order
            assert len(known['fields']) == len(self.fields)
            for f, fl in zip(self.fields, known['fields']):
                f['bit'], f['width'] = fl['bit'], fl['width']
        else:
            self.bitmap()

    def run(self, wire, stop=None):
        return Run(self.T, self.inst, wire, self.helpers, stop)

    # -- fields: where each starts in a run's events
    def starts(self, r):
        """[(event index, ('g', pos, width) | ('i', first eip))] at depth 0"""
        out = []
        cur = None
        last_inline_eip = None
        for i, e in enumerate(r.ev):
            if e[-1] != 0:
                continue
            if e[0] == 'bits' and e[1] == self.hstart and e[5] == self.fn:
                if cur is None or cur != ('g', e[2]):
                    cur = ('g', e[2])
                    out.append((i, ('g', e[2], e[3])))
                last_inline_eip = None
            elif e[0] == 'read' and PM.fn_of(e[2]) == self.fn and self.hstart <= e[1] < self.dstart:
                if last_inline_eip is not None and abs(e[2] - last_inline_eip) < 16 and cur and cur[0] == 'i':
                    last_inline_eip = e[2]
                    continue
                cur = ('i', e[2])
                last_inline_eip = e[2]
                out.append((i, ('i', e[2])))
            elif e[0] in ('read', 'call', 'in', 'bits'):
                last_inline_eip = None
        return out

    def split(self, r):
        st = self.starts(r)
        fields = []
        cursor = self.dstart
        for k, (i, key) in enumerate(st):
            j = st[k + 1][0] if k + 1 < len(st) else len(r.ev)
            seg = r.ev[i:j]
            reads = [e[1] for e in seg if e[0] == 'read' and e[1] >= self.dstart]
            reads += [e[3] for e in seg if e[0] == 'in' and e[-1] == 0]     # a child's header may be read by getbits only
            p = min(reads) if reads else cursor
            q = max(reads) + 1 if reads else cursor
            assert p == cursor, f'{self.fn:#x}: field {k} starts at {p}, expected {cursor}'
            cursor = q
            fields.append({'key': key, 'ev': (i, j), 'span': (p, q)})
        assert cursor == r.used, f'{self.fn:#x}: fields end at {cursor}, the reader used {r.used}'
        return fields

    def bitmap(self):
        """bit positions of every field: getbits fields know theirs; inline ones are found by flipping each remaining
        header bit and seeing which field's events change first"""
        used = set()
        for f in self.fields:
            if f['key'][0] == 'g':
                f['bit'], f['width'] = f['key'][1], f['key'][2]
                used |= set(range(f['bit'], f['bit'] + f['width']))
        # bytes after the struct, so a mode that reads where the replay's mode read nothing shows its reads in its own
        # field (otherwise the reader fails at once and the first difference falls in the next field)
        pad = bytes(random.Random(7).randrange(256) for _ in range(64))
        free = [b for b in range(8 * self.header) if b not in used]
        rng = random.Random(11)
        owner = {}
        # each free bit is flipped against the replay's header and against headers whose other free bits are random:
        # a bit can matter only for some values of its neighbours (a 3-bit mode whose values 1..7 read alike)
        backgrounds = [self.base] + [self.with_free(self.base, free, rng) for _ in range(6)]
        for b in free:
            found = set()
            for bg in backgrounds:
                ra = self.run(bg + pad)
                rb = self.run(self.with_bits(bg, b, 1, 1 - self.get_bits(bg, b, 1)) + pad)
                ka = [self.ekey(e) for e in ra.ev]
                kb = [self.ekey(e) for e in rb.ev]
                d = next((i for i in range(min(len(ka), len(kb))) if ka[i] != kb[i]), None)
                if d is None:
                    if len(ka) != len(kb):
                        d = min(len(ka), len(kb))
                    else:
                        continue
                # the field the first difference belongs to, by the changed run's own field starts (an extra read of
                # the changed field sits where the unchanged run starts the next field)
                st = self.starts(rb) if len(kb) > d else self.starts(ra)
                if not st or st[0][0] > d:
                    continue
                found.add(max(n for n, (i, key) in enumerate(st) if i <= d))
            if found:
                k = min(found)
                if len(found) > 1:
                    print(f'    {self.fn:#x}: header bit {b} changes fields {sorted(found)} (taken as {k})')
                owner.setdefault(k, []).append(b)
        taken = set(used) | {b for bits in owner.values() for b in bits}
        for k, bits in owner.items():
            f = self.fields[k]
            assert f['key'][0] == 'i', f'{self.fn:#x}: header bits {bits} change getbits field {k}'
            span = list(range(bits[0], bits[-1] + 1))
            gaps = [b for b in span if b not in bits]
            # two modes that read the same way hide the bit that tells them apart: a gap no other field owns is this
            # field's too
            assert not any(b in taken for b in gaps), f'{self.fn:#x}: field {k} bits {bits} not contiguous'
            if gaps:
                print(f'    {self.fn:#x} field {k}: bits {bits}, gap {gaps} taken as its own (modes reading alike)')
            f['bit'], f['width'] = span[0], len(span)
        for k, f in enumerate(self.fields):
            assert 'bit' in f, f'{self.fn:#x}: no header bit found for inline field {k}'

    def with_free(self, wire, free, rng):
        h = int.from_bytes(wire[self.hstart:self.dstart], 'little')
        for b in free:
            h = (h & ~(1 << b)) | (rng.randrange(2) << b)
        return wire[:self.hstart] + h.to_bytes(self.header, 'little') + wire[self.dstart:]

    def ekey(self, e):
        obj = self.inst['obj']
        if e[0] == 'write':
            # the value too: two constant modes may store different values with the same instruction
            o = e[1] - obj
            return ('write', e[3], o if 0 <= o < MAXOBJ else -1, e[2], e[4])
        if e[0] == 'bits':
            return ('bits', e[1], e[2], e[3], e[4])
        if e[0] == 'read':
            return ('read', e[1], e[2])
        if e[0] == 'in':
            return ('in', e[1], e[3])
        if e[0] == 'call':
            return ('call', e[1], e[2])
        return (e[0], e[1])

    def get_bits(self, wire, pos, width):
        h = int.from_bytes(wire[self.hstart:self.dstart], 'little')
        return (h >> pos) & ((1 << width) - 1)

    def with_bits(self, wire, pos, width, val):
        h = int.from_bytes(wire[self.hstart:self.dstart], 'little')
        m = ((1 << width) - 1) << pos
        h = (h & ~m) | (val << pos)
        return wire[:self.hstart] + h.to_bytes(self.header, 'little') + wire[self.dstart:]

    # -- probing one field
    def body(self, k, mode, data):
        f = self.fields[k]
        w = self.with_bits(self.base, f['bit'], f['width'], mode)
        p, q = f['span']
        # the fields after this one do not matter: cut the wire there (the next field's mode is still read, which is
        # how a probe knows the field ended; the reader then fails for want of bytes, quickly)
        return w[:p] + bytes(data) + bytes(PAD)

    def probe(self, k, mode, data):
        """-> (run, segment events, completed?)"""
        r = self.run(self.body(k, mode, data), (self.hstart, self.dstart, k + 2))
        st = self.starts(r)
        if len(st) <= k:
            return r, [], False
        i = st[k][0]
        j = st[k + 1][0] if k + 1 < len(st) else len(r.ev)
        done = k + 1 < len(st) or (r.ok == 1)
        return r, r.ev[i:j], done

    def count_probe(self, k, mode, data, res):
        """the element count a seq field reads from `data`, stopping at its first element (None when it fails)"""
        r = self.run(self.body(k, mode, data), (self.hstart, self.dstart, k + 2, True))
        st = self.starts(r)
        if len(st) <= k:
            return None
        i = st[k][0]
        seg = r.ev[i:]
        if not any(e[0] == 'in' and e[-1] == 0 for e in seg) and len(st) < k + 2 and r.ok != 1:
            return None
        return struct.unpack('<I', plain_bytes(r, r.obj + res['off'] + P.PTR, 4))[0]

    def original(self, k):
        p, q = self.fields[k]['span']
        return self.base[p:q]

    def first_probe(self, k, mode):
        tries = [self.original(k) + bytes(self.rng.randrange(256) for _ in range(PAD))]
        tries += [bytes([b]) * 256 for b in range(256)]
        for d in tries:
            r, seg, done = self.probe(k, mode, d)
            if done:
                return r, seg, d
        return None, None, None

    # -- the field's place in the object
    def obj_writes(self, seg, r=None):
        """stores into the object itself (not into blocks the run allocated, which may lie right after it)"""
        obj = self.inst['obj']
        blocks = r.r['blocks'] if r is not None else []

        def in_block(a):
            return any(p <= a < p + n for p, n in blocks)
        return sorted({(e[1] - obj, e[2]) for e in seg if e[0] == 'write' and e[-1] == 0 and 0 <= e[1] - obj < MAXOBJ
                       and not in_block(e[1])})

    def learn(self):
        out = {'reader': f'{self.fn:#x}', 'prefix': self.prefix, 'header': self.header, 'fields': []}
        for k, f in enumerate(self.fields):
            fl = self.learn_field(k)
            out['fields'].append(fl)
            print(f'  {self.fn:#x} field {k}: bits {fl["bit"]}..{fl["bit"] + fl["width"] - 1} +{fl["off"]:#x} {fl["size"]} B ' +
                  ' '.join(f'{m}:{d["kind"]}' + (f'({d.get("elem", {}).get("kind", "")}{d.get("type", "")})' if d['kind'] in ('seq', 'struct') else '')
                           for m, d in sorted(fl['modes'].items())), flush=True)
        used = {b for fl in out['fields'] for b in range(fl['bit'], fl['bit'] + fl['width'])}
        out['spare_bits'] = [b for b in range(8 * self.header) if b not in used]
        return out

    def learn_field(self, k):
        f = self.fields[k]
        res = {'bit': f['bit'], 'width': f['width'], 'inline': f['key'][0] == 'i', 'modes': {}}
        runs = {}
        lo, hi = None, None
        for m in range(1 << f['width']):
            r, seg, d = self.first_probe(k, m)
            runs[m] = (r, seg, d)
            if r is None:
                continue
            for o, s in self.obj_writes(seg, r):
                lo = o if lo is None else min(lo, o)
                hi = o + s if hi is None else max(hi, o + s)
            for e in seg:
                if e[0] == 'in' and e[-1] == 0 and 0 <= e[2] - self.inst['obj'] < MAXOBJ:
                    o = e[2] - self.inst['obj']
                    lo = o if lo is None else min(lo, o)
                    hi = max(hi or 0, o + 4)
        res['off'], res['size'] = (lo, hi - lo) if lo is not None else (None, 0)
        learnt = {}
        for m in range(1 << f['width']):
            r, seg, d = runs[m]
            if r is None:
                res['modes'][m] = {'kind': 'invalid'}
                continue
            reads = [e for e in seg if e[0] == 'read' and e[1] >= self.dstart]
            kids = [e for e in seg if e[0] == 'in' and e[-1] == 0]
            if not reads and not kids:
                res['modes'][m] = self.const(r, res)
                continue
            sig = (tuple(sorted({PM.fn_of(e[2]) for e in reads})), tuple(sorted({e[1] for e in kids})))
            if sig in learnt and self.same(k, m, learnt[sig], res):
                res['modes'][m] = dict(learnt[sig], same_as=learnt[sig]['mode'], mode=m)
                continue
            try:
                mode = self.learn_mode(k, m, r, seg, res, d)
            except (AssertionError, ValueError, IndexError, KeyError, StopIteration) as e:
                # a way of sending the field that the replay's packet does not use and that cannot be worked out
                # from the reader alone: kept as unlearnt (the field can still be sent in its other modes)
                hdr = int.from_bytes(bytes(self.base[self.hstart:self.hstart + self.header]), 'little')
                if (hdr >> f['bit']) & ((1 << f['width']) - 1) == m:
                    raise
                print(f'    {self.fn:#x} field {k} mode {m}: left unlearnt ({type(e).__name__}: {str(e)[:90]})', flush=True)
                res['modes'][m] = {'kind': 'unknown', 'unlearnt': True, 'mode': m}
                continue
            mode['mode'] = m
            learnt[sig] = mode
            res['modes'][m] = mode
        # constants of a seq / struct field are an empty seq / a default struct
        kinds = {d['kind'] for d in res['modes'].values()}
        if 'struct' in kinds:
            for m, d in res['modes'].items():
                if d['kind'] == 'const':
                    res['modes'][m] = {'kind': 'const', 'struct': True, 'mode': m}
        elif kinds & {'seq', 'text'}:
            for m, d in res['modes'].items():
                if d['kind'] == 'const':
                    # run it again: the memory of the earlier run has been overwritten by the runs since
                    r, seg, _ = self.first_probe(k, m)
                    res['modes'][m] = {'kind': 'const', 'seq': self.read_value(r, res, self.active_mode(res)), 'mode': m}
        return res

    @staticmethod
    def active_mode(res):
        return next(d for d in res['modes'].values() if d['kind'] in ('seq', 'text', 'struct', 'fixed', 'varint'))

    def const(self, r, res):
        if res['off'] is None:
            return {'kind': 'const', 'value': ''}
        return {'kind': 'const', 'value': plain_bytes(r, r.obj + res['off'], res['size']).hex()}

    def same(self, k, m, prev, res):
        if prev['kind'] == 'struct' or prev['kind'] == 'seq' and prev['elem']['kind'] == 'struct':
            # one probe with the bytes the other mode was learnt on
            _, _, d = self.first_probe(k, prev['mode'])
            ra, _, oka = self.probe(k, prev['mode'], d)
            rb, _, okb = self.probe(k, m, d)
            return oka and okb and self.read_value(ra, res, prev) == self.read_value(rb, res, prev)
        for _ in range(12):
            v = self.random_value(prev, res)
            data = encode_mode(self.schema, prev, v, res)
            ra, _, oka = self.probe(k, prev['mode'], data)
            rb, _, okb = self.probe(k, m, data)
            if not (oka and okb) or self.read_value(ra, res, prev) != self.read_value(rb, res, prev):
                return False
        return True

    # -- what a field holds after a run
    def read_value(self, r, res, mode):
        return read_field(self.schema, r, r.obj, res, mode)

    def learn_mode(self, k, m, r, seg, res, data=None):
        unknown = {PM.fn_of(e[2]) for e in seg if e[0] == 'read'} - set(self.T.readers) - set(self.T.helpers) - {self.fn}
        if unknown and data is not None:
            new = self.T.learn_roles(unknown, self.inst, self.body(k, m, data))
            if new:
                print(f'    {self.fn:#x} field {k} mode {m}: new struct reader(s) {", ".join(hex(f) for f in new)}', flush=True)
                self.helpers = sorted(set(self.helpers) - new)
                r, seg, _ = self.probe(k, m, data)
        kids = [e for e in seg if e[0] == 'in' and e[-1] == 0]
        obj = self.inst['obj']
        in_block = any(p_ <= kids[0][2] < p_ + n_ for p_, n_ in r.r['blocks']) if kids else False
        if kids and len(kids) == 1 and 0 <= kids[0][2] - obj < MAXOBJ and not in_block:
            # an embedded struct
            child = kids[0][1]
            self.schema.need(child, self.T)
            return {'kind': 'struct', 'type': f'{child:#x}', 'at': kids[0][2] - obj - res['off']}
        ptr0 = P.ptr_of(plain_bytes(r, obj + res['off'], P.PTR)) if res['size'] >= P.PTR else 0
        if res['size'] == SEQ_SIZE and (in_heap(ptr0) or ptr0 == EMPTY_TEXT or kids):
            ptr, n = seq_head(plain_bytes(r, obj + res['off'], P.PTR + 4))
            if kids:
                return self.learn_seq(k, m, res, ('struct', kids))
            if n and in_heap(ptr):
                e0 = seq_head(plain_bytes(r, ptr, SEQ_SIZE)) + (struct.unpack('<I', plain_bytes(r, ptr + P.PTR + 4, 4))[0],)
                if in_heap(e0[0]) and e0[1] <= e0[2] < 0x10000:
                    return self.learn_seq(k, m, res, ('text',))
            try:
                return self.learn_text(k, m, res)
            except AssertionError as e:
                print(f'    {self.fn:#x} field {k} mode {m}: not a text ({e}); trying a seq of numbers', flush=True)
                return self.learn_numbers(k, m, res)
        return self.learn_bytes(k, m, res)

    def learn_fixed_seq(self, k, m, res):
        """a varint count, then that many FIXED-width elements, each wire byte through a table into its own byte of the
        element [16.20's 294: 4-byte elements; 10's nested struct]. Read only: the mode is kept for reading"""
        def head(r):
            ptr, n = seq_head(plain_bytes(r, r.obj + res['off'], P.PTR + 4))
            return ptr, n
        fill = bytes([0x05]) * 300
        C, width = [None] * 256, None
        for c in range(256):
            r, seg, ok = self.probe(k, m, bytes([c]) + fill)
            if not ok:
                continue
            ptr, n = head(r)
            nread = len({e[1] for e in seg if e[0] == 'read' and e[1] >= self.dstart})
            if 0 < n < 128 and (nread - 1) % n == 0:
                w = (nread - 1) // n
                if width is None:
                    width = w
                if w == width:
                    C[c] = n
            elif n == 0 and nread == 1:
                C[c] = 0
        assert width, f'{self.fn:#x} field {k} mode {m}: no fixed element width'
        one = C.index(1)
        # element: which element byte each wire byte sets, through which table (the elements' size from the stride of
        # two elements in the vector)
        r2, seg2, ok2 = self.probe(k, m, bytes([C.index(2)]) + fill) if 2 in C else (None, None, False)
        esize = 4
        out = []
        for j in range(width):
            base = bytearray(fill[:width + 40])
            vals = []
            for v in range(256):
                w = bytearray(base)
                w[j] = v
                r, seg, ok = self.probe(k, m, bytes([one]) + bytes(w))
                if not ok:
                    vals.append(None)
                    continue
                ptr, n = head(r)
                vals.append(plain_bytes(r, ptr, esize) if n == 1 else None)
            good = [x for x in vals if x is not None]
            changed = [i for i in range(esize) if len({x[i] for x in good}) > 1]
            assert len(changed) == 1, f'{self.fn:#x} field {k} mode {m}: element wire byte {j} moves bytes {changed}'
            out.append([changed[0], [x[changed[0]] if x is not None else None for x in vals]])
        return {'kind': 'seq', 'C': C, 'order': 'fwd', 'read_only': True,
                'elem': {'kind': 'fixed', 'n': width, 'size': esize, 'map': out}}

    def learn_numbers(self, k, m, res):
        """a varint count, then that many varint numbers (u32 or u16 each in the vector: the stride is the one under
        which a run of equal one-byte elements reads back as that many equal numbers)"""
        stride = [4]

        def vec(r):
            ptr, n = seq_head(plain_bytes(r, r.obj + res['off'], P.PTR + 4))
            w = stride[0]
            return [int.from_bytes(plain_bytes(r, ptr + w * i, w), 'little') for i in range(min(n, 400))]
        # a count byte and an element byte that make several one-byte elements
        found = None
        for e0 in range(256):
            for c in range(256):
                r, seg, ok = self.probe(k, m, bytes([c]) + bytes([e0]) * 300)
                if ok:
                    nread = len([e for e in seg if e[0] == 'read' and e[1] >= self.dstart])
                    for w in (4, 2, 1):
                        stride[0] = w
                        v = vec(r)
                        if len(v) >= 2 and nread == 1 + len(v) and len(set(v)) == 1:
                            found = e0
                            break
                    if found is not None:
                        break
            if found is not None:
                break
        if found is None:
            return self.learn_fixed_seq(k, m, res)
        many = bytes([found]) * 300
        C = [None] * 256
        for v in range(256):
            r, seg, ok = self.probe(k, m, bytes([v]) + many)
            if ok and 0 < len(vec(r)) < 128:
                C[v] = len(vec(r))
        one = C.index(1)
        for v in range(256):
            if C[v] is None:
                r, seg, ok = self.probe(k, m, bytes([v, one]) + many)
                if ok and len(vec(r)) >= 128:
                    C[v] = 0x80 | (len(vec(r)) - 128)
        left = [v for v in range(256) if C[v] is None]
        missing = sorted(set(range(256)) - {x for x in C if x is not None})
        assert len(left) == len(missing) <= 1 and missing in ([], [0]), f'{self.fn:#x} field {k} mode {m}: count table'
        if left:
            C[left[0]] = 0
        # the element: a varint through a table (count 1, then its bytes)
        S = [None] * 256
        for v in range(256):
            r, seg, ok = self.probe(k, m, bytes([one, v]) + many)
            nread = len([e for e in seg if e[0] == 'read' and e[1] >= self.dstart])
            if ok and nread == 2:
                S[v] = vec(r)[0]
        z = S.index(0)
        for v in range(256):
            if S[v] is None:
                r, seg, ok = self.probe(k, m, bytes([one, v, z]) + many)
                assert ok, f'{self.fn:#x} field {k} mode {m}: element byte {v:#x}'
                S[v] = 0x80 | vec(r)[0]
        assert sorted(S) == list(range(256))
        Sinv = {x: w for w, x in enumerate(S)}
        Cinv = {x: w for w, x in enumerate(C)}
        r, seg, ok = self.probe(k, m, bytes([Cinv[3], Sinv[1], Sinv[2], Sinv[3]]))
        got = vec(r)
        order = next(o for o in ('fwd', 'rev', 'ends') if [got.index(i + 1) for i in range(3)] == text_order(o, 3))
        return {'kind': 'seq', 'C': C, 'elem': {'kind': 'varint', 'S': S}, 'order': order, 'stride': stride[0]}

    # -- fixed / varint (as pkt_codec, on this struct's own bytes)
    def field_bytes(self, r, res):
        return plain_bytes(r, r.obj + res['off'], res['size'])

    def learn_bytes(self, k, m, res):
        fill = bytes(self.rng.randrange(256) for _ in range(PAD))
        counts = set()
        for v in range(256):
            r, seg, ok = self.probe(k, m, bytes([v]) + fill[1:])
            counts.add(len([e for e in seg if e[0] == 'read' and e[1] >= self.dstart and e[-1] == 0]) if ok else -1)
        if len(counts) == 1 and -1 not in counts:
            return self.learn_fixed(k, m, res, counts.pop())
        if counts == {1, -1}:
            return self.learn_fixed(k, m, res, 1, partial=True)
        if res['size'] >= 8 and res['size'] % 4 == 0:
            try:
                return self.learn_varints(k, m, res)
            except AssertionError as e:
                print(f'    not an array of varints: {e}', flush=True)
        return self.learn_varint(k, m, res)

    def learn_varints(self, k, m, res):
        """a fixed array of u32, each travelling as a varint through one byte table (16.20's 905: the perk ids, the
        cosmetic ids). A wire byte ends an element when the element's value does not depend on what follows it."""
        count = res['size'] // 4
        last = None
        # the element each wire varint goes to: text_order (905: the cosmetics 'rev', the perk ids 'ends')
        for order in ('rev', 'ends', 'fwd'):
            try:
                return self._learn_varints(k, m, res, count, order)
            except AssertionError as e:
                last = e
        raise last

    def _learn_varints(self, k, m, res, count, order):
        at = 4 * text_order(order, count)[0]

        def first(data):
            r, seg, ok = self.probe(k, m, data)
            return int.from_bytes(self.field_bytes(r, res)[at:at + 4], 'little') if ok else None
        S = [None] * 256
        more = []
        for v in range(256):
            got = set()
            for _ in range(6):
                x = first(bytes([v]) + bytes(self.rng.randrange(256) for _ in range(PAD - 1)))
                if x is not None:
                    got.add(x)
                if len(got) > 1:
                    break
            if len(got) == 1 and next(iter(got)) < 0x80:
                S[v] = got.pop()
            else:
                more.append(v)
        assert 0 in S, f'{self.fn:#x} field {k} mode {m}: no byte for an element of 0'
        z = S.index(0)
        for v in more:
            x = first(bytes([v]) + bytes([z]) * (PAD - 1))
            assert x is not None and x < 0x80, f'{self.fn:#x} field {k} mode {m}: varint byte {v:#x}'
            S[v] = 0x80 | x
        assert sorted(S) == list(range(256)), f'{self.fn:#x} field {k} mode {m}: the elements\' byte table'
        # every element through the same table: a known array read back
        want = [(i * 2654435761 + 12345) & 0xffffffff for i in range(count)]
        inv = _inv(S)
        wire = [want[i] for i in text_order(order, count)]
        r, seg, ok = self.probe(k, m, b''.join(_varint(x, inv) for x in wire) + bytes(PAD))
        assert ok and self.field_bytes(r, res) == b''.join(x.to_bytes(4, 'little') for x in want), \
            f'{self.fn:#x} field {k} mode {m}: the array does not read back ({order})'
        return {'kind': 'varints', 'count': count, 'S': S, 'order': order}

    def learn_fixed(self, k, m, res, n, partial=False):
        out = []
        size = res['size']
        for j in range(n):
            base = bytes(self.rng.randrange(256) for _ in range(n + PAD))
            vals = []
            for v in range(256):
                w = bytearray(base)
                w[j] = v
                r, seg, ok = self.probe(k, m, w)
                if not ok:
                    assert partial, f'{self.fn:#x} field {k} mode {m}: byte {j} value {v:#x} rejected'
                    vals.append(None)
                    continue
                vals.append(self.field_bytes(r, res))
            good = [x for x in vals if x is not None]
            changed = [i for i in range(size) if len({x[i] for x in good}) > 1]
            assert len(changed) == 1, f'{self.fn:#x} field {k} mode {m}: wire byte {j} moves field bytes {changed}'
            o = changed[0]
            tab = [x[o] if x is not None else None for x in vals]
            if len({t for t in tab if t is not None}) != len(good):
                # several wire bytes give the same field byte (16.20's 10, instance +0x2c mode 1): enough to READ the
                # field, not to write it - the mode is kept for reading only
                self.read_only = True
                out.append([o, tab])
                continue
            # same table with other bytes around
            base2 = bytes(self.rng.randrange(256) for _ in range(n + PAD))
            for v in self.rng.sample(range(256), 8):
                w = bytearray(base2)
                w[j] = v
                r, seg, ok = self.probe(k, m, w)
                if tab[v] is None:
                    assert not ok
                else:
                    assert ok and self.field_bytes(r, res)[o] == tab[v]
            out.append([o, tab])
        mode = {'kind': 'fixed', 'n': n, 'map': out, 'covers': sorted(o for o, t in out)}
        if getattr(self, 'read_only', False):
            self.read_only = False
            mode['read_only'] = True
        return mode

    def learn_varint(self, k, m, res):
        fill = bytes(self.rng.randrange(256) for _ in range(PAD))
        S = [None] * 256
        two = [False] * 256      # this wire byte says another byte follows
        size = res['size']
        for v in range(256):
            r, seg, ok = self.probe(k, m, bytes([v]) + fill[1:])
            # wire positions read (a reader may look at the same byte twice: 16.20's 905)
            n = len({e[1] for e in seg if e[0] == 'read' and e[1] >= self.dstart and e[-1] == 0})
            if ok and n == 1:
                S[v] = int.from_bytes(self.field_bytes(r, res), 'little')
        # the byte that adds nothing as a second byte: plain 0 (a net id field reads it as 0x40000000)
        z = S.index(0) if 0 in S else S.index(min(x for x in S if x is not None))
        for v in range(256):
            if S[v] is None:
                r, seg, ok = self.probe(k, m, bytes([v, z]) + fill[2:])
                assert ok, f'{self.fn:#x} field {k} mode {m}: varint byte {v:#x}'
                two[v] = True
                S[v] = 0x80 | int.from_bytes(self.field_bytes(r, res), 'little')
        if sorted(S) != list(range(256)) and size == 4:
            # 16.20: a net id inside a packet travels like the packet's own (netid16.py): the number on the wire is
            # the id with bit 30 flipped, unless its low 24 bits are zero
            N = [(nid_number(x & ~0x80) & 0x7f) | (0x80 if i_two else 0) for x, i_two in zip(S, two)]
            if sorted(N) == list(range(256)):
                return {'kind': 'varint', 'S': N, 'nid': True}
        assert sorted(S) == list(range(256)), f'{self.fn:#x} field {k} mode {m}: varint table'
        return {'kind': 'varint', 'S': S}

    # -- a text field (a seq of bytes)
    def text_of(self, r, res):
        ptr, n = seq_head(plain_bytes(r, r.obj + res['off'], P.PTR + 4))
        if n == 0:
            return b''
        if n > 0x10000:
            return None
        return plain_bytes(r, ptr, n)

    def learn_text(self, k, m, res, wrap=None):
        """a varint length then that many bytes, each through a table (some values may be rejected by the reader: a
        list of player slots takes 1..51 only). wrap: (prefix bytes, getter) when the text is an element of a seq"""
        pre, get = wrap if wrap else (b'', lambda r: self.text_of(r, res))
        orig = self.original(k)
        # a byte the reader accepts: the replay's own second byte when it has one, else any byte that reads
        good = None
        for cand in ([orig[1]] if len(orig) > 1 and not wrap else []) + list(range(256)):
            for lb in range(256):
                r, seg, ok = self.probe(k, m, pre + bytes([lb]) + bytes([cand]) * 300)
                s = get(r) if ok else None
                if s:
                    good = cand
                    break
            if good is not None:
                break
        assert good is not None, f'{self.fn:#x} field {k} mode {m}: no byte the reader accepts'
        fill = bytes([good]) * 300
        L = [None] * 256
        for v in range(256):
            r, seg, ok = self.probe(k, m, pre + bytes([v]) + fill)
            s = get(r) if ok else None
            if s is not None and len(s) < 128:
                nread = len([e for e in seg if e[0] == 'read' and e[1] >= self.dstart])
                if nread == len(pre) + 1 + len(s):
                    L[v] = len(s)
        assert 1 in L, f'{self.fn:#x} field {k} mode {m}: no length-1 byte; lengths read {sorted({x for x in L if x is not None})[:12]}'
        one = L.index(1)
        for v in range(256):
            if L[v] is None:
                r, seg, ok = self.probe(k, m, pre + bytes([v, one]) + fill)
                s = get(r) if ok else None
                if s is not None and len(s) >= 128:
                    L[v] = 0x80 | (len(s) - 128)
        left = [v for v in range(256) if L[v] is None]
        missing = sorted(set(range(256)) - {x for x in L if x is not None})
        assert len(left) == len(missing) <= 1 and missing in ([], [0]), f'{self.fn:#x} field {k} mode {m}: length table {left} {missing}'
        if left:
            L[left[0]] = 0
        Linv = {x: w for w, x in enumerate(L)}

        def text(n, j, v):
            w = bytearray(pre + bytes([Linv[n]]) + fill)
            w[len(pre) + 1 + j] = v
            r, seg, ok = self.probe(k, m, w)
            s = get(r) if ok else None
            if s is None:
                return None
            assert len(s) == n, f'{self.fn:#x} field {k} mode {m}: text of length {n}'
            return s
        # a second accepted byte that reads differently, to see where each wire byte lands
        other = next(v for v in range(256) if v != good and text(1, 0, v) not in (None, text(1, 0, good)))
        layout = {}
        for n in range(1, 8):
            lay = []
            for j in range(n):
                a, b = text(n, j, good), text(n, j, other)
                ch = [i for i in range(n) if a[i] != b[i]]
                assert len(ch) == 1, f'{self.fn:#x} field {k} mode {m}: length {n} byte {j} -> {ch}'
                lay.append(ch[0])
            layout[n] = lay
        order = next((o for o in ('fwd', 'rev', 'ends') if all(layout[n] == text_order(o, n) for n in layout)), None)
        assert order, f'{self.fn:#x} field {k} mode {m}: text layout {layout}'
        S = []
        for v in range(256):
            t = text(2, 0, v)
            S.append(t[layout[2][0]] if t is not None else None)
        assert len({x for x in S if x is not None}) == len([x for x in S if x is not None])
        mid = None
        if order == 'ends':
            mid = []
            for v in range(256):
                t = text(3, 2, v)
                mid.append(t[1] if t is not None else None)
        for n in layout:
            for j, i in enumerate(layout[n]):
                tab = mid if order == 'ends' and n % 2 and i == n // 2 else S
                for v in self.rng.sample([x for x in range(256) if tab[x] is not None], 4):
                    assert text(n, j, v)[i] == tab[v]
        mode = {'kind': 'text', 'order': order, 'L': L, 'S': S}
        if None in S:
            mode['accepts'] = sorted(x for x in S if x is not None)
        if mid:
            mode['mid'] = mid
        return mode

    def helper_count_table(self, k, m, seg):
        """the count's byte table when a varint helper reads it: call the helper alone on each byte (no element
        needed). None when the count is not read by one helper call at the field's first byte."""
        p = self.fields[k]['span'][0]
        call = next((e for e in seg if e[0] == 'call' and e[-1] == 0), None)
        if call is None or call[2] != p:
            return None
        h = call[1]
        emu = self.T.emu
        S = [None] * 256
        for v in range(256):
            self.T.emu.u.mem_write(PT.WIRE, bytes([v, 0]))
            dst = emu.alloc(8)
            cur = emu.alloc(P.PTR)
            emu.u.mem_write(cur, P.pack_ptr(PT.WIRE))
            ret, err = P.call_helper(emu, h, dst, cur, PT.WIRE + 1)
            if err:
                return None
            used = P.read_ptr(emu.u, cur) - PT.WIRE
            val = struct.unpack('<I', bytes(emu.u.mem_read(dst, 4)))[0]
            if ret & 0xff == 1 and used == 1 and val < 128:
                S[v] = val
            elif ret & 0xff == 0 and used == 1 and val < 128:
                S[v] = 0x80 | val      # wanted another byte: a continuation byte
            else:
                return None
        if sorted(S) != list(range(256)):
            return None
        print(f'    {self.fn:#x} field {k} mode {m}: count table from helper {h:#x} called alone', flush=True)
        return S

    def finish_struct_seq(self, k, m, res, mode, ctype, enc, stride):
        Cinv = {x: w for w, x in enumerate(mode['C'])}
        if stride is None:
            # one element in the replay: two copies show the distance between elements
            r, seg, ok = self.probe(k, m, bytes([Cinv[2]]) + enc[0] * 2)
            objs = [e[2] for e in seg if e[0] == 'in' and e[-1] == 0]
            assert ok and len(objs) == 2, f'{self.fn:#x} field {k} mode {m}: two elements do not read'
            stride = abs(objs[1] - objs[0])
        mode['elem'] = {'kind': 'struct', 'type': f'{ctype:#x}'}
        three = (enc + enc)[:3]
        if len(set(three)) < 3:
            three = None
        order = 'fwd'
        if three:
            r, seg, ok = self.probe(k, m, bytes([Cinv[3]]) + b''.join(three))
            assert ok
            kids = [e for e in seg if e[0] == 'in' and e[-1] == 0]
            ptr = P.ptr_of(plain_bytes(r, r.obj + res['off'], P.PTR))
            slots = [(e[2] - ptr) // stride for e in kids]
            order = next(o for o in ('fwd', 'rev', 'ends') if slots == text_order(o, 3))
        else:
            print(f'    {self.fn:#x} field {k}: fewer than three different elements in the replay, order taken as fwd (unverified)')
            mode['order_unverified'] = True
        mode['order'] = order
        mode['stride'] = stride
        return mode

    # -- a seq of texts or structs
    def learn_seq(self, k, m, res, elem):
        """count (a varint through a table), then the elements"""
        obj = self.inst['obj']
        r0, seg0, _ = self.probe(k, m, self.original(k))
        p = self.fields[k]['span'][0]
        if elem[0] == 'struct':
            ctype = elem[1][0][1]
            self.schema.need(ctype, self.T)
            kids = [e for e in seg0 if e[0] == 'in' and e[-1] == 0]
            if not kids or not self.T.of(ctype):
                # the replay never sends an element of this type: nothing to learn the count and elements from; the
                # writer can only send this seq empty (a constant mode)
                print(f'    {self.fn:#x} field {k} mode {m}: seq of {ctype:#x}, never filled in the replay: left unlearnt', flush=True)
                return {'kind': 'seq', 'elem': {'kind': 'struct', 'type': f'{ctype:#x}'}, 'unlearnt': True}
            starts = [e[3] for e in kids] + [self.fields[k]['span'][1]]
            enc = [self.base[starts[i]:starts[i + 1]] for i in range(len(kids))]
            # the elements' order on the wire may differ from their place in the vector: sort by wire offset
            count_len = starts[0] - p
            objs = [e[2] for e in kids]
            ptr = P.ptr_of(plain_bytes(r0, obj + res['off'], P.PTR))
            stride = min(abs(a - b) for a in objs for b in objs if a != b) if len(objs) > 1 else None
            filler_one = enc[0]
        else:
            # vector of texts: the count, then [length, bytes] per element. A one-letter text is two bytes, found by
            # trying (an empty one would do, but a fresh vector holding empty texts trips the emulated allocator)
            stride = SEQ_SIZE
            count_byte = self.original(k)[0]
            filler_one = None
            for z in range(256):
                r, seg, ok = self.probe(k, m, bytes([count_byte]) + bytes([z, 0x41]) * 300)
                if ok:
                    v = self.read_value(r, res, {'kind': 'seq', 'elem': {'kind': 'text'}})
                    if v and len({x['text'] for x in v}) == 1 and len(v[0]['text']) == 2:
                        filler_one = bytes([z, 0x41])
                        break
            assert filler_one is not None, f'{self.fn:#x} field {k} mode {m}: no one-letter element found'
            count_len = 1
            enc = None
        # count table: [v] + elements. A count of 0 in this mode can crash the reader (Riot's loop over the elements
        # starts at the vector's end - 1 element, which underflows for a never-filled vector): the server sends an
        # empty seq with a constant mode instead; its table entry is the one byte left over.
        def count_of(r):
            return struct.unpack('<I', plain_bytes(r, r.obj + res['off'] + P.PTR, 4))[0]
        C = self.helper_count_table(k, m, seg0) if elem[0] == 'struct' else None
        if C is not None:
            Cinv = {x: w for w, x in enumerate(C)}
            mode = {'kind': 'seq', 'C': C}
            return self.finish_struct_seq(k, m, res, mode, ctype, enc, stride)
        C = [None] * 256
        # enough bytes that the reader's count <= bytes left check passes for any count up to 255
        many = filler_one * ((300 // len(filler_one) + 2) if elem[0] == 'struct' else 260)
        for v in range(256):
            if elem[0] == 'struct':
                c = self.count_probe(k, m, bytes([v]) + many, res)
                if not c:
                    # a vector filled one element at a time shows 0 at its first element: read it whole instead
                    r, seg, ok = self.probe(k, m, bytes([v]) + filler_one * 2)
                    c = len([e for e in seg if e[0] == 'in' and e[-1] == 0]) if ok else None
            else:
                r, seg, ok = self.probe(k, m, bytes([v]) + many)
                c = count_of(r) if ok else None
            if c is not None and 0 < c < 128:
                C[v] = c
        one = C.index(1)
        for v in range(256):
            if C[v] is None:
                if elem[0] == 'struct':
                    c = self.count_probe(k, m, bytes([v, one]) + many, res)
                    if c is not None and c < 128:
                        c = None
                else:
                    r, seg, ok = self.probe(k, m, bytes([v, one]) + many)
                    c = count_of(r) if ok else None
                if c is not None and c >= 128:
                    C[v] = 0x80 | (c - 128)
        left = [v for v in range(256) if C[v] is None]
        missing = sorted(set(range(256)) - {c for c in C if c is not None})
        assert 1 <= len(left) <= 3 and len(left) == len(missing) and 0 in missing, \
            f'{self.fn:#x} field {k} mode {m}: count table, {len(left)} unknown {missing[:4]}'
        if len(left) == 1:
            C[left[0]] = 0
        else:      # a count the reader would not take in the probe: those bytes stay unknown (never written by us)
            print(f'    {self.fn:#x} field {k} mode {m}: count bytes {left} for counts {missing} left unknown', flush=True)
        Cinv = {x: w for w, x in enumerate(C)}
        mode = {'kind': 'seq', 'C': C}
        if elem[0] == 'struct':
            return self.finish_struct_seq(k, m, res, mode, ctype, enc, stride)
        if False:
            mode['elem'] = {'kind': 'struct', 'type': f'{ctype:#x}'}
            # order: three different elements (the replay's first three, else the first one with a changed byte)
            three = (enc + enc)[:3]
            if len(set(three)) < 3:
                three = None
            order = 'fwd'
            if three:
                r, seg, ok = self.probe(k, m, bytes([Cinv[3]]) + b''.join(three))
                assert ok
                kids = [e for e in seg if e[0] == 'in' and e[-1] == 0]
                ptr = P.ptr_of(plain_bytes(r, r.obj + res['off'], P.PTR))
                slots = [(e[2] - ptr) // stride for e in kids]
                order = next(o for o in ('fwd', 'rev', 'ends') if slots == text_order(o, 3))
            else:
                print(f'    {self.fn:#x} field {k}: fewer than three different elements in the replay, order taken as fwd')
            mode['order'] = order
            mode['stride'] = stride
        else:
            # the element text: learnt with count 1
            ek = self.learn_text(k, m, res, (bytes([Cinv[1]]), lambda r: self.elem_text(r, res, 0)))
            mode['elem'] = dict(ek, kind='text')
            # order: three texts of different lengths
            Linv = {x: w for w, x in enumerate(ek['L'])}
            data = bytes([Cinv[3]]) + bytes([Linv[1], 0x41]) + bytes([Linv[2], 0x42, 0x42]) + bytes([Linv[3], 0x43, 0x43, 0x43])
            r, seg, ok = self.probe(k, m, data)
            assert ok
            lens = [len(self.elem_text(r, res, i)) for i in range(3)]
            order = next(o for o in ('fwd', 'rev', 'ends') if [lens.index(i + 1) for i in range(3)] == text_order(o, 3))
            mode['order'] = order
            mode['stride'] = SEQ_SIZE
        return mode

    def elem_text(self, r, res, i):
        ptr, n = seq_head(plain_bytes(r, r.obj + res['off'], P.PTR + 4))
        if i >= n:
            return None
        p, cnt = seq_head(plain_bytes(r, ptr + SEQ_SIZE * i, P.PTR + 4))
        return plain_bytes(r, p, cnt) if cnt else b''

    def random_value(self, mode, res):
        k = mode['kind']
        if k == 'fixed':
            v = bytearray(res['size'])
            for o, tab in mode['map']:
                v[o] = self.rng.choice([t for t in tab if t is not None])
            return bytes(v).hex()
        if k == 'varint':
            return self.rng.getrandbits(8 * res['size']).to_bytes(res['size'], 'little').hex()
        if k == 'text':
            pool = mode.get('accepts') or list(range(256))
            return {'text': bytes(self.rng.choice(pool) for _ in range(self.rng.randrange(1, 20))).hex()}
        if k == 'seq' and mode['elem']['kind'] == 'varint':
            return [self.rng.getrandbits(32).to_bytes(4, 'little').hex() for _ in range(self.rng.randrange(1, 5))]
        if k == 'seq' and mode['elem']['kind'] == 'text':
            return [{'text': bytes(self.rng.randrange(256) for _ in range(self.rng.randrange(1, 8))).hex()}
                    for _ in range(self.rng.randrange(1, 4))]
        return None


def text_order(name, n):
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


# ------------------------------------------------------------------------------------------------- reading values

def read_field(schema, r, obj, res, mode):
    """a field's value from a run's memory in clear"""
    k = mode['kind']
    if res['off'] is None:
        return None
    a = obj + res['off']
    if k in ('fixed', 'varint', 'const') and 'seq' not in mode:
        return plain_bytes(r, a, res['size']).hex()
    if k == 'text':
        ptr, n = seq_head(plain_bytes(r, a, P.PTR + 4))
        return {'text': (plain_bytes(r, ptr, n) if n else b'').hex()}
    if k == 'struct':
        if mode['type'] not in schema.structs:
            return {'default': True}
        # an embedded struct sent in its constant mode is copied from a default instance, never read: its bytes are
        # stored hidden as they are; only a struct whose reader ran has values to read
        read = r.__dict__.setdefault('_read_objs', {e[2] for e in r.ev if e[0] == 'in'})
        if a + mode.get('at', 0) not in read:
            return {'default': True}
        return read_struct(schema, r, a + mode.get('at', 0), schema.structs[mode['type']])
    if k == 'seq' or 'seq' in mode:
        ptr, n = seq_head(plain_bytes(r, a, P.PTR + 4))
        el = mode.get('elem') or {}
        out = []
        for i in range(n):
            if el.get('kind') == 'varint':
                w = mode.get('stride') or 4
                out.append(plain_bytes(r, ptr + w * i, w).hex())
                continue
            if el.get('kind') == 'struct':
                if el['type'] not in schema.structs:
                    out.append({'default': True})
                    continue
                out.append(read_struct(schema, r, ptr + mode['stride'] * i, schema.structs[el['type']]))
            else:
                p, c = seq_head(plain_bytes(r, ptr + SEQ_SIZE * i, P.PTR + 4))
                out.append({'text': (plain_bytes(r, p, c) if c else b'').hex()})
        return out
    return None


def field_kind(fl):
    """the mode that tells how the field's value looks (any non-constant one)"""
    for d in fl['modes'].values():
        if d['kind'] in ('seq', 'text', 'struct'):
            return d
    for d in fl['modes'].values():
        if d['kind'] in ('fixed', 'varint', 'const'):
            return d
    return {'kind': 'invalid'}


def read_struct(schema, r, obj, st):
    out = {}
    for fl in st['fields']:
        if fl['off'] is None:
            continue
        out[f'+{fl["off"]:#x}'] = read_field(schema, r, obj, fl, field_kind(fl))
    return out


# ------------------------------------------------------------------------------------------------- writing

KEEP_INVERSES = False     # a server sets it: a schema's byte tables do not change there, their inverses are kept
_inverses = {}


def _inv(tab):
    if KEEP_INVERSES:
        hit = _inverses.get(id(tab))
        if hit is not None and hit[0] is tab:
            return hit[1]
    inv = [None] * 256
    for w, x in enumerate(tab):
        if x is not None:
            inv[x] = w
    if KEEP_INVERSES:
        _inverses[id(tab)] = (tab, inv)      # the table itself is held: its id cannot pass to another list
    return inv


def nid_number(v):
    """net id <-> the number that travels for it (the same operation both ways)"""
    return v if v & 0xffffff == 0 else v ^ 0x40000000


def _varint(n, inv):
    out = bytearray()
    while True:
        b = n & 0x7f
        n >>= 7
        out.append(inv[b | (0x80 if n else 0)])
        if not n:
            return bytes(out)


def encode_text(mode, data):
    out = bytearray(_varint(len(data), _inv(mode['L'])))
    S = _inv(mode['S'])
    mid = _inv(mode['mid']) if mode.get('mid') else None
    n = len(data)
    for i in text_order(mode['order'], n):
        t = mid if mid and n % 2 and i == n // 2 else S
        out.append(t[data[i]])
    return bytes(out)


def encode_mode(schema, mode, v, fl):
    k = mode['kind']
    if k == 'const':
        if mode.get('struct'):
            return b''
        if 'seq' in mode:
            if v != mode['seq']:
                raise ValueError('constant')
            return b''
        if v != mode['value']:
            raise ValueError('constant')
        return b''
    if k == 'fixed':
        b = bytes.fromhex(v)
        out = bytearray(mode['n'])
        for j, (o, tab) in enumerate(mode['map']):
            out[j] = _inv(tab)[b[o]]
        return bytes(out)
    if k == 'varint':
        n = int.from_bytes(bytes.fromhex(v), 'little')
        return _varint(nid_number(n) if mode.get('nid') else n, _inv(mode['S']))
    if k == 'text':
        return encode_text(mode, bytes.fromhex(v['text']))
    if k == 'varints':
        b = bytes.fromhex(v)
        inv = _inv(mode['S'])
        el = [int.from_bytes(b[i:i + 4], 'little') for i in range(0, 4 * mode['count'], 4)]
        return b''.join(_varint(el[i], inv) for i in text_order(mode.get('order', 'fwd'), mode['count']))
    if k == 'struct':
        return schema.encode_struct(mode['type'], v, schema.forced)
    if k == 'seq':
        out = bytearray(_varint(len(v), _inv(mode['C'])))
        el = mode['elem']
        for i in text_order(mode['order'], len(v)):
            if el['kind'] == 'struct':
                out += schema.encode_struct(el['type'], v[i], schema.forced)
            elif el['kind'] == 'varint':
                out += _varint(int.from_bytes(bytes.fromhex(v[i]), 'little'), _inv(el['S']))
            elif el['kind'] == 'fixed':
                # the reader's tables backwards: each wire byte sets one byte of the element
                b = bytes.fromhex(v[i])
                w = bytearray(el['n'])
                for j, (o, tab) in enumerate(el['map']):
                    x = _inv(tab)[b[o]]
                    if x is None:
                        raise ValueError('fixed element byte outside the table')
                    w[j] = x
                out += w
            else:
                out += encode_text(el, bytes.fromhex(v[i]['text']))
        return bytes(out)
    raise ValueError(k)


# ------------------------------------------------------------------------------------------------- reading without the client

def _unvarint(body, at, tab):
    n = shift = 0
    while True:
        g = tab[body[at]]
        at += 1
        if g is None:
            raise ValueError('byte outside the table')
        n |= (g & 0x7f) << shift
        shift += 7
        if not g & 0x80:
            return n, at


def _untext(mode, body, at):
    n, at = _unvarint(body, at, mode['L'])
    data = bytearray(n)
    S = mode['S']
    mid = mode.get('mid')
    for i in text_order(mode['order'], n):
        t = mid if mid and n % 2 and i == n // 2 else S
        x = t[body[at]]
        if x is None:
            raise ValueError('text byte outside the table')
        data[i] = x
        at += 1
    return bytes(data), at


def parse_mode(schema, mode, fl, body, at):
    k = mode['kind']
    if k == 'const':
        if mode.get('struct'):
            return {'default': True}, at
        return (mode['seq'] if 'seq' in mode else mode['value']), at
    if k == 'fixed':
        b = bytearray(fl['size'])
        for j, (o, tab) in enumerate(mode['map']):
            x = tab[body[at + j]]
            if x is None:
                raise ValueError('fixed byte outside the table')
            b[o] = x
        return bytes(b).hex(), at + mode['n']
    if k == 'varint':
        n, at = _unvarint(body, at, mode['S'])
        n &= (1 << (8 * fl['size'])) - 1
        return (nid_number(n) if mode.get('nid') else n).to_bytes(fl['size'], 'little').hex(), at
    if k == 'text':
        data, at = _untext(mode, body, at)
        return {'text': data.hex()}, at
    if k == 'varints':
        el = [b''] * mode['count']
        for i in text_order(mode.get('order', 'fwd'), mode['count']):
            x, at = _unvarint(body, at, mode['S'])
            el[i] = (x & 0xffffffff).to_bytes(4, 'little')
        return b''.join(el).ljust(fl['size'], b'\0').hex(), at
    if k == 'struct':
        return parse_struct(schema, mode['type'], body, at)
    if k == 'seq':
        n, at = _unvarint(body, at, mode['C'])
        el = mode['elem']
        out = [None] * n
        for i in text_order(mode['order'], n):
            if el['kind'] == 'struct':
                out[i], at = parse_struct(schema, el['type'], body, at)
            elif el['kind'] == 'varint':
                x, at = _unvarint(body, at, el['S'])
                w = mode.get('stride') or 4
                out[i] = (x & ((1 << (8 * w)) - 1)).to_bytes(w, 'little').hex()
            elif el['kind'] == 'fixed':
                b = bytearray(el['size'])
                for j, (o, tab) in enumerate(el['map']):
                    x = tab[body[at + j]]
                    if x is None:
                        raise ValueError('fixed element byte outside the table')
                    b[o] = x
                at += el['n']
                out[i] = bytes(b).hex()
            else:
                data, at = _untext(el, body, at)
                out[i] = {'text': data.hex()}
        return out, at
    raise ValueError(f'mode {k} cannot be read')


def parse_struct(schema, key, body, at=0):
    st = schema.structs[key]
    bits = int.from_bytes(body[at:at + st['header']], 'little')
    at += st['header']
    out = {}
    for fl in st['fields']:
        m = (bits >> fl['bit']) & ((1 << fl['width']) - 1)
        mode = fl['modes'].get(m)
        if mode is None:
            raise ValueError(f'{key} +{fl["off"]:#x}: mode {m} not learnt')
        v, at = parse_mode(schema, mode, fl, body, at)
        if fl['off'] is not None:
            out[f'+{fl["off"]:#x}'] = v
    return out, at


def parse(schema, body):
    """a packet body (after the id and the net id) -> values, in plain Python (the inverse of Schema.encode);
    raises ValueError when the body does not fit the learnt format"""
    v, at = parse_struct(schema, schema.root, body, 0)
    if at != len(body):
        raise ValueError(f'{len(body) - at} bytes left')
    return v


def fits(mode, v, fl):
    k = mode['kind']
    if mode.get('read_only') and not (k == 'seq' and mode['elem']['kind'] == 'fixed'):
        return False                     # a mode learnt for reading only (a byte table that is not one-to-one); a seq of
                                         # fixed elements is written backwards through its tables (a byte with no wire
                                         # byte raises)
    if k == 'const':
        if mode.get('struct'):
            return v == {'default': True}
        return v == (mode['seq'] if 'seq' in mode else mode['value'])
    if k == 'fixed':
        b = bytes.fromhex(v)
        return all(_inv(t)[b[o]] is not None for o, t in mode['map']) and \
            all(b[i] == 0 for i in range(len(b)) if i not in mode['covers'])
    if k == 'text' and 'accepts' in mode:
        return set(bytes.fromhex(v['text'])) <= set(mode['accepts'])
    if mode.get('unlearnt'):
        return False
    return k in ('varint', 'varints', 'text', 'struct', 'seq')


class Schema:
    def __init__(self, pid, structs=None):
        self.pid = pid
        self.structs = structs or {}
        self.todo = []
        self.unlearnt = set()
        self.forced = None     # {struct key: {header bit: mode}} to force while encoding (tests)

    def need(self, fn, T=None):
        """queue a struct type for learning; one the replay never reads (only ever sent in a constant mode) has no
        bytes to learn from: it stays in `unlearnt` and is only ever written in its constant (default) mode"""
        key = f'{fn:#x}'
        if T is not None and not T.of(fn):
            self.unlearnt.add(key)
            return
        if key not in self.structs and fn not in self.todo:
            self.todo.append(fn)

    def choose(self, fl, v):
        for kinds in (('const',), ('fixed', 'varint', 'varints', 'text', 'struct', 'seq')):
            for m in sorted(fl['modes'], key=int):
                d = fl['modes'][m]
                if d['kind'] in kinds and fits(d, v, fl):
                    return int(m)
        raise ValueError(f'no mode for +{fl["off"]:#x} = {v}')

    def encode_struct(self, key, value, modes=None):
        st = self.structs[key]
        bits = 0
        data = bytearray()
        forced = (modes or {}).get(key, {})
        bits = forced.get('spare', 0)
        for fl in st['fields']:
            v = value.get(f'+{fl["off"]:#x}') if fl['off'] is not None else ''
            m = forced.get(fl['bit'])
            if m is None:
                m = self.choose(fl, v)
            bits |= m << fl['bit']
            data += encode_mode(self, fl['modes'][m], v, fl)
        return bits.to_bytes(st['header'], 'little') + bytes(data)

    def encode(self, value, modes=None):
        """the packet body (after [u16 id][u32 net id]); modes: {struct key: {header bit: mode}} forces modes"""
        self.forced = modes
        try:
            return self.encode_struct(self.root, value, modes)
        finally:
            self.forced = None

    def save(self):
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, f'{self.pid}.tree.json'), 'w') as f:
            json.dump({'id': self.pid, 'root': self.root, 'structs': self.structs, 'unlearnt': sorted(self.unlearnt)}, f)

    @staticmethod
    def load(pid, borrow=True):
        d = json.load(open(os.path.join(OUT, f'{pid}.tree.json')))
        s = Schema(pid, d['structs'])
        s.root = d['root']
        s.unlearnt = set(d.get('unlearnt', []))
        if borrow:
            # a struct reader is shared by several packet ids (16.20: 51 and 134 carry 1215's cast struct): one not learnt
            # in this id's format is taken from another id's format that learnt it
            todo = [s.root]
            seen = set()
            while todo:
                key = todo.pop()
                if key in seen:
                    continue
                seen.add(key)
                st = _library().get(key)
                if key not in s.structs:
                    if st is None:
                        continue
                    s.structs[key] = json.loads(json.dumps(st))
                elif st is not None and _unknowns(st) < _unknowns(s.structs[key]):
                    # the same reader learnt better from another id's samples (223's cast struct never held a target
                    # list in its own samples; 1215's did)
                    s.structs[key] = json.loads(json.dumps(st))
                for fl in s.structs[key]['fields']:
                    for x in fl['modes'].values():
                        t = x.get('type') or (x.get('elem') or {}).get('type')
                        if t:
                            todo.append(t)
        for st in s.structs.values():
            for fl in st['fields']:
                fl['modes'] = {int(m): x for m, x in fl['modes'].items()}
        return s


_lib = None


def _library():
    """every struct learnt in any format: {struct key: struct}"""
    global _lib
    if _lib is None:
        _lib = {}
        for f in sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []:
            if f.endswith('.tree.json') and not f.startswith('c2s'):
                try:
                    d = json.load(open(os.path.join(OUT, f)))
                except Exception:
                    continue
                for key, st in d.get('structs', {}).items():
                    if key not in _lib or _unknowns(st) < _unknowns(_lib[key]):
                        _lib[key] = st            # of several formats that hold a struct, the one that learnt it best
    return _lib


def _unknowns(st):
    """how many modes of a struct's fields were not learnt (the samples of that packet id never used them)"""
    return sum(1 for fl in st['fields'] for x in fl['modes'].values() if x.get('kind') == 'unknown' or x.get('unlearnt'))


def learn(pid, again=False):
    T = PT.Tree(pid)
    path = os.path.join(OUT, f'{pid}.tree.json')
    if len(T.wire) == P.WIRE_SKIP and all(len(b) == 0 for b in PM.packets(pid)):
        # a packet with no body at all (16.20: 384, 548, 658, ...): nothing to learn, its format is empty
        key = f'{T.info["des"]:#x}'
        os.makedirs(OUT, exist_ok=True)
        json.dump({'id': pid, 'root': key, 'structs': {key: {'header': 0, 'fields': [], 'spare_bits': 0}}, 'unlearnt': []},
                  open(path, 'w'))
        print('empty packet ->', path)
        return
    sc = Schema.load(pid) if os.path.exists(path) and not again else Schema(pid)
    sc.root = f'{T.info["des"]:#x}'
    # structs learnt in an earlier run are kept; the ones they need and nobody learnt yet are queued again
    for key, st in sc.structs.items():
        for fl in st['fields']:
            for d in fl['modes'].values():
                t = d.get('type') or d.get('elem', {}).get('type')
                if t:
                    sc.need(int(t, 16), T)
    sc.need(T.info['des'])
    while sc.todo:
        fn = sc.todo.pop(0)
        print(f'struct {fn:#x}', flush=True)
        # a struct is learnt on its first instance in the sample; when that one cannot be split into fields (a live
        # 618: the human player's entry), on the next instances (the bots' entries)
        insts = len(T.of(fn)) or 1
        for k in range(insts):
            try:
                sc.structs[f'{fn:#x}'] = StructLearner(T, fn, sc, k=k).learn()
                break
            except AssertionError as e:
                print(f'  instance {k} of {insts}: {e}', flush=True)
                if k == insts - 1:
                    raise
        sc.save()
    print('->', os.path.join(OUT, f'{pid}.tree.json'))
    fix_strides(pid)
    verify_orders(pid)


def _variants(value, n):
    """n copies of a struct value that differ in their first text (or first number) field, or None"""
    import copy

    def paths(x, path=()):
        if isinstance(x, dict):
            if 'text' in x:
                yield ('text', path)
                return
            for k, v in x.items():
                yield from paths(v, path + (k,))
        elif isinstance(x, str) and x and len(x) <= 16:
            yield ('hex', path)
    for kind, path in paths(value):
        out = []
        for i in range(n):
            v = copy.deepcopy(value)
            node = v
            for k in path[:-1]:
                node = node[k]
            if kind == 'text':
                node[path[-1]] = {'text': (bytes([0x61 + i]) * (i + 1)).hex()}
            else:
                b = bytearray.fromhex(node[path[-1]])
                b[0] = (b[0] + i + 1) & 0x7f
                node[path[-1]] = b.hex()
            out.append(v)
        return out, path
    return None, None


def fix_consts(pid):
    """constant modes of text / seq fields learnt before the fix above: their value again, from a run of their own"""
    sc = Schema.load(pid)
    T = PT.Tree(pid)
    for key, st in sc.structs.items():
        L = None
        for fl in st['fields']:
            kinds = {d['kind'] for d in fl['modes'].values()}
            if not kinds & {'seq', 'text'}:
                continue
            for m, d in fl['modes'].items():
                if d['kind'] != 'const' or 'seq' not in d:
                    continue
                L = L or StructLearner(T, int(key, 16), sc, known=st)
                k = next(i for i, f in enumerate(L.fields) if f['bit'] == fl['bit'])
                r, seg, _ = L.first_probe(k, m)
                new = L.read_value(r, fl, StructLearner.active_mode(fl))
                if new != d['seq']:
                    print(f'{key} +{fl["off"]:#x} mode {m}: {d["seq"]} -> {new}')
                    d['seq'] = new
    sc.save()


def fix_strides(pid):
    """seqs of structs learnt from a single replay element before strides were measured"""
    sc = Schema.load(pid)
    T = PT.Tree(pid)
    changed = False
    for key, st in sc.structs.items():
        for fl in st['fields']:
            for m, d in fl['modes'].items():
                if d['kind'] == 'seq' and d['elem']['kind'] == 'struct' and not d.get('unlearnt') and d.get('stride') is None:
                    L = StructLearner(T, int(key, 16), sc, known=st)
                    k = next(i for i, f in enumerate(L.fields) if f['bit'] == fl['bit'])
                    Cinv = {x: w for w, x in enumerate(d['C'])}
                    r0, seg0, _ = L.probe(k, m, L.original(k)) if L.original(k) else (None, [], False)
                    kids = [e for e in seg0 if e[0] == 'in' and e[-1] == 0]
                    if not kids:
                        print(f'{key} field {k}: no element in the replay to measure the stride from')
                        continue
                    starts = [e[3] for e in kids] + [L.fields[k]['span'][1]]
                    one = L.base[starts[0]:starts[1]]
                    r, seg, ok = L.probe(k, m, bytes([Cinv[2]]) + one * 2)
                    objs = [e[2] for e in seg if e[0] == 'in' and e[-1] == 0]
                    d['stride'] = abs(objs[1] - objs[0])
                    print(f'{key} field {k} mode {m}: stride {d["stride"]:#x}')
                    changed = True
    if changed:
        sc.save()


def verify_orders(pid):
    """seqs of structs whose order the replay could not show (fewer than three different elements): three different
    elements, made from the replay's own with a field changed, through Riot's reader in the whole packet"""
    import copy
    sc = Schema.load(pid)
    T = PT.Tree(pid)
    base = decode(T, sc, T.wire)

    def find(v, st, path=()):
        for fl in st['fields']:
            key = f'+{fl["off"]:#x}' if fl['off'] is not None else None
            if key is None or key not in v:
                continue
            for m, d in fl['modes'].items():
                if d['kind'] == 'seq' and d['elem']['kind'] == 'struct' and d.get('order_unverified'):
                    yield path + (key,), d
                    break
            fk = field_kind(fl)
            if fk['kind'] == 'struct' and fk['type'] in sc.structs and isinstance(v[key], dict) and not v[key].get('default'):
                yield from find(v[key], sc.structs[fk['type']], path + (key,))
            if fk['kind'] == 'seq' and fk['elem'].get('kind') == 'struct' and fk['elem']['type'] in sc.structs:
                for i, e in enumerate(v[key][:1]):
                    yield from find(e, sc.structs[fk['elem']['type']], path + (key, i))
    for path, d in list(find(base, sc.structs[sc.root])):
        node = base
        for k in path:
            node = node[k]
        if not node:
            print(f'{path}: empty in the replay, order left unverified')
            continue
        three, leaf = _variants(node[0], 3)
        if three is None:
            print(f'{path}: no field to tell elements apart, order left unverified')
            continue
        v = copy.deepcopy(base)
        tgt = v
        for k in path[:-1]:
            tgt = tgt[k]
        tgt[path[-1]] = three
        got = None
        for order in ('fwd', 'rev', 'ends'):
            for m, x in d.items() if False else []:
                pass
            # every seq mode of this field reads the same way: set them all and try
            for st in sc.structs.values():
                for fl in st['fields']:
                    for mm, dd in fl['modes'].items():
                        if dd is d or (dd.get('same_as') is not None and dd.get('elem') == d.get('elem') and dd.get('C') == d.get('C')):
                            dd['order'] = order
            try:
                back = decode(T, sc, T.wire[:P.WIRE_SKIP] + sc.encode(v))
            except Exception as e:
                back = None
            if back == v:
                got = order
                break
        print(f'{path}: order {got}')
        if got:
            for st in sc.structs.values():
                for fl in st['fields']:
                    for dd in fl['modes'].values():
                        if dd is d or (dd.get('elem') == d.get('elem') and dd.get('C') == d.get('C') and dd.get('kind') == 'seq'):
                            dd['order'] = got
                            dd.pop('order_unverified', None)
    sc.save()


def decode_replay(pid, sc=None):
    sc = sc or Schema.load(pid)
    T = PT.Tree(pid)
    return decode(T, sc, T.wire)


def decode(T, sc, wire):
    """a whole packet (id + net id + body) through Riot's reader -> values, or None"""
    root = T.of(T.info['des'])[0]
    # the tree knows the struct readers its own sample packet ran; the format knows them all (a struct the sample
    # sent as its default is read in other packets): without this a filled struct came back as "default"
    for name in sc.structs:
        fn = int(name, 16)
        if fn not in T.readers:
            T.readers.add(fn)
            T.snaps.setdefault(fn, None)
    r = Run(T, root, wire)
    if r.ok != 1 or r.used != len(wire):
        return None
    return read_struct(sc, r, r.obj, sc.structs[sc.root])


def check(pid, n):
    sc = Schema.load(pid)
    T = PT.Tree(pid)
    v = decode(T, sc, T.wire)
    body = sc.encode(v)
    back = decode(T, sc, T.wire[:P.WIRE_SKIP] + body)
    print(f'replay packet: {len(T.wire) - P.WIRE_SKIP} B; ours {len(body)} B; read back {"identical" if back == v else "DIFFERENT"}')
    if back != v and back is not None:
        diff(v, back, '')
    rng = random.Random(5)
    good = 0
    for t in range(n):
        w = mutate(sc, v, sc.structs[sc.root], rng)
        try:
            body = sc.encode(w)
        except ValueError as e:
            print(f'variation {t}: cannot encode: {e}')
            continue
        back = decode(T, sc, T.wire[:P.WIRE_SKIP] + body)
        if back == w:
            good += 1
        else:
            print(f'variation {t}: {"rejected by the reader" if back is None else "read back different"}')
            if back is not None:
                diff(w, back, '')
    if n:
        print(f'{good} of {n} random variations read back identical')
    return v, back


def mutate(sc, v, st, rng, p=0.3):
    """a copy of a struct value with some fields changed to random values a mode can carry"""
    import copy
    v = copy.deepcopy(v)
    for fl in st['fields']:
        if fl['off'] is None:
            continue
        key = f'+{fl["off"]:#x}'
        fk = field_kind(fl)
        active = [d for d in fl['modes'].values() if d['kind'] in ('fixed', 'varint', 'text', 'seq', 'struct') and not d.get('unlearnt')]
        if not active or key not in v:
            continue
        d = active[0]
        if d['kind'] == 'struct':
            if d['type'] in sc.structs and isinstance(v[key], dict) and not v[key].get('default'):
                v[key] = mutate(sc, v[key], sc.structs[d['type']], rng, p)
            continue
        if rng.random() > p:
            continue
        if d['kind'] == 'fixed':
            b = bytearray(fl['size'])
            for o, tab in d['map']:
                b[o] = rng.choice([t for t in tab if t is not None])
            v[key] = b.hex()
        elif d['kind'] == 'varint':
            v[key] = rng.getrandbits(8 * fl['size']).to_bytes(fl['size'], 'little').hex()
        elif d['kind'] == 'text':
            pool = d.get('accepts') or list(range(256))
            v[key] = {'text': bytes(rng.choice(pool) for _ in range(rng.randrange(1, 30))).hex()}
        elif d['kind'] == 'seq':
            el = d['elem']
            cur = v[key]
            if el['kind'] == 'struct':
                if cur and el['type'] in sc.structs:
                    # drop one, repeat one, change one
                    cur = list(cur)
                    op = rng.randrange(3)
                    if op == 0 and len(cur) > 1:
                        cur.pop(rng.randrange(len(cur)))
                    elif op == 1:
                        cur.append(copy.deepcopy(rng.choice(cur)))
                    else:
                        i = rng.randrange(len(cur))
                        cur[i] = mutate(sc, cur[i], sc.structs[el['type']], rng, 0.5)
                    v[key] = cur
            elif el['kind'] == 'varint':
                v[key] = [rng.getrandbits(32).to_bytes(4, 'little').hex() for _ in range(rng.randrange(1, 6))]
            else:
                pool = el.get('accepts') or list(range(256))
                v[key] = [{'text': bytes(rng.choice(pool) for _ in range(rng.randrange(1, 12))).hex()}
                          for _ in range(rng.randrange(1, 5))]
    return v


def check_many(pid, n):
    """n replay packets of the id spread over the stream (keyframe 1 and chunks): decoded through Riot's reader,
    re-encoded by us, read back; also counts packets the learnt structure cannot carry"""
    sc = Schema.load(pid)
    T = PT.Tree(pid)
    allp = []
    P.KINDS, P.ENTRY = (2,), 1
    allp += [(obj, b) for t, ch, p_, obj, b in P.packets(P.ROFL, pid)]
    P.KINDS, P.ENTRY = (1,), None
    allp += [(obj, b) for t, ch, p_, obj, b in P.packets(P.ROFL, pid)]
    step = max(1, len(allp) // n)
    sample = allp[::step][:n]
    same = undecodable = unencodable = 0
    for i, (obj, body) in enumerate(sample):
        wire = P.wire(pid, obj, body)
        v = decode(T, sc, wire)
        if v is None:
            undecodable += 1
            continue
        try:
            ours = sc.encode(v)
        except ValueError as e:
            unencodable += 1
            print(f'packet {i}: cannot encode: {e}')
            continue
        back = decode(T, sc, wire[:len(wire) - len(body)] + ours)
        if back == v:
            same += 1
        else:
            print(f'packet {i}: read back different')
            diff(v, back or {}, '')
    print(f'{len(sample)} of {len(allp)} replay packets: {same} read back identical, {unencodable} not encodable, '
          f'{undecodable} not read by the reader alone')


def diff(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            diff(a[k], b.get(k), path + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            print(f'  {path}: {len(a)} vs {len(b)} elements')
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f'{path}[{i}]')
    elif a != b:
        print(f'  {path}: {a} vs {b}')


def show(pid):
    sc = Schema.load(pid)
    for key, st in sc.structs.items():
        print(f'struct {key}: header {st["header"]} B, unused bits {st["spare_bits"]}')
        for fl in st['fields']:
            off = f'+{fl["off"]:#x}' if fl['off'] is not None else '-'
            print(f'  {off:6} {fl["size"]:3} B bits {fl["bit"]}..{fl["bit"] + fl["width"] - 1}{" inline" if fl["inline"] else ""}')
            for m, d in sorted(fl['modes'].items()):
                k = d['kind']
                extra = ''
                if k == 'const':
                    extra = f'= {d.get("value", d.get("seq"))}'
                elif k == 'fixed':
                    extra = f'{d["n"]} B -> {[o for o, t in d["map"]]}'
                elif k == 'text':
                    extra = d['order']
                elif k == 'seq':
                    extra = f'{d["order"]} of {d["elem"]["kind"]} {d["elem"].get("type", "")}'
                elif k == 'struct':
                    extra = d['type']
                print(f'      {m}: {k} {extra}' + (f' (as {d["same_as"]})' if 'same_as' in d else ''))


if __name__ == '__main__':
    cmd, pid = sys.argv[1], int(sys.argv[2])
    if cmd == 'learn':
        learn(pid)
    elif cmd == 'show':
        show(pid)
    elif cmd == 'many':
        check_many(pid, int(sys.argv[3]) if len(sys.argv) > 3 else 300)
    elif cmd == 'consts':
        fix_consts(pid)
    elif cmd == 'orders':
        fix_strides(pid)
        verify_orders(pid)
    elif cmd == 'check':
        check(pid, int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    elif cmd == 'dump':
        v = decode_replay(pid)
        with open(os.path.join(OUT, f'{pid}.values.json'), 'w') as f:
            json.dump(v, f, indent=1)
        print('->', os.path.join(OUT, f'{pid}.values.json'))
