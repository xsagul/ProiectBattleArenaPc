"""Nested server -> client packets of the 13.3 client (574 and the like): the packet object holds sub-objects (a vector
of player records, a match configuration, ...). Every sub-object has a vtable whose entry 1 reads it off the wire with
the same shape as a whole packet: header bits, then fields (server/pkt_codec.py). This tool finds the instances
in a replay packet and runs each reader on its own, so a struct type can be learnt on its own bytes.

  pkt_tree.py tree <id>             the instances: reader, object, wire span, nesting
  pkt_tree.py fields <id> <reader>  one instance of a reader run alone: its header reads, field segments, child instances
"""
import os
import struct
import sys
import bisect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import pkt_modes as PM  # noqa: E402
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE  # noqa: E402
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EIP  # noqa: E402

GETBITS, GETBITS_RET = 0x91cae0, 0x91cb44
GETBITS_READS = (0x91cb10, 0x91cb30)
# readers that test their header bits only inline (no getbits call), found in the reader map of 574
EXTRA_READERS = {0x8fe8b0}
WIRE = P.BUF + 0x10000     # where a struct's own bytes go when it is run alone (room: 0xf0000 bytes)


class Tree:
    """one full run of the packet's reader, with every struct reader's entry"""

    def __init__(self, pid, k=0):
        self.pid = pid
        self.info = P.table()[pid]
        self.body = PM.packets(pid)[k]
        self.emu = P.Emu()
        u = self.emu.u
        # pass 1: every function that reads wire bytes
        readfns = set()
        h = u.hook_add(UC_HOOK_MEM_READ, lambda u, acc, a, s, v, d: readfns.add(
            PM.fn_of(u.reg_read(UC_X86_REG_EIP) - P.BASE)), begin=P.BUF, end=P.BUF + 0x10000)
        tr = {}
        ok, left, _ = self.emu.deserialize(self.info, pid, 0, self.body, tr)
        u.hook_del(h)
        assert ok and left == 0
        readfns.discard(PM.fn_of(GETBITS))
        # a struct reader gets (this = object, cursor, end); a helper gets (destination, cursor, end): tell them apart
        # by where the cursor is when they start
        kind = {}

        def classify(u, a, s, d):
            esp = u.reg_read(UC_X86_REG_ESP)
            a1, a2 = struct.unpack('<II', bytes(u.mem_read(esp + 4, 8)))

            def is_cursor(p):
                if not P.HEAP <= p < P.HEAP + P.HEAP_SIZE - 4:
                    return False
                return P.BUF <= struct.unpack('<I', bytes(u.mem_read(p, 4)))[0] <= P.BUF + 0x10000
            fn = a - P.BASE
            if is_cursor(a1):
                kind.setdefault(fn, set()).add('reader')
            elif is_cursor(a2):
                kind.setdefault(fn, set()).add('helper')
        hs = [u.hook_add(UC_HOOK_CODE, classify, begin=P.BASE + f, end=P.BASE + f) for f in readfns]
        self.emu.heap = P.HEAP + 0x1000
        self.emu.deserialize(self.info, pid, 0, self.body, {})
        for x in hs:
            u.hook_del(x)
        readers = {f for f, k in kind.items() if 'reader' in k} | {self.info['des']}
        self.readers = readers
        self.helpers = {f for f, k in kind.items() if k == {'helper'}}
        # pass 2: entries (obj, cursor) and every wire read, in order
        ev = []

        snaps = {}

        def entry(u, a, s, d):
            esp = u.reg_read(UC_X86_REG_ESP)
            ret, cur, end = struct.unpack('<III', bytes(u.mem_read(esp, 12)))
            c = struct.unpack('<I', bytes(u.mem_read(cur, 4)))[0]
            ev.append(('in', a - P.BASE, u.reg_read(UC_X86_REG_ECX), c - P.BUF, esp))
            fn = a - P.BASE
            if fn not in snaps:   # the heap as the first instance of this reader finds it: a freshly built object
                top = (self.emu.heap + 0xfff) & ~0xfff
                snaps[fn] = (bytes(u.mem_read(P.HEAP, top - P.HEAP)), top)

        def rd(u, acc, a, s, v, d):
            ev.append(('r', a - P.BUF, s))
        hs = [u.hook_add(UC_HOOK_CODE, entry, begin=P.BASE + r, end=P.BASE + r) for r in readers]
        self.emu.heap = P.HEAP + 0x1000
        hs.append(u.hook_add(UC_HOOK_MEM_READ, rd, begin=P.BUF, end=P.BUF + 0x10000))
        ok, left, _ = self.emu.deserialize(self.info, pid, 0, self.body, {})
        for x in hs:
            u.hook_del(x)
        self.wire = struct.pack('<HI', pid, 0) + self.body    # as the reader sees it (offset 0 = the packet id)
        # nesting by stack depth: an instance is inside the previous ones whose esp is above its own
        stack, out = [], []
        for x in ev:
            if x[0] == 'r':
                for s in stack:
                    s['end'] = max(s['end'], x[1] + x[2])
                continue
            _, fn, obj, cur, esp = x
            while stack and stack[-1]['esp'] <= esp:
                stack.pop()
            inst = {'fn': fn, 'obj': obj, 'start': cur, 'end': cur, 'esp': esp, 'parent': stack[-1] if stack else None,
                    'children': []}
            if stack:
                stack[-1]['children'].append(inst)
            out.append(inst)
            stack.append(inst)
        self.instances = out
        # objects keep living in the emulator's heap: later runs must not allocate over them
        self.ret_sites = set()    # return addresses of child readers (an 'out' event marks a child's end)
        # every run of a reader starts from the heap its first instance found (its object freshly built, nothing read
        # into it yet): same objects, same addresses, so runs can be compared event by event
        self.snaps = snaps
        self.emu.floor = P.HEAP + 0x1000

    def learn_roles(self, fns, inst, wire):
        """functions seen reading the wire for the first time (a mode the replay never used): run `inst` on `wire`
        with their entries hooked and sort them into readers and helpers like pass 2 does"""
        u = self.emu.u
        kind = {}

        def classify(u, a, s, d):
            esp = u.reg_read(UC_X86_REG_ESP)
            a1, a2 = struct.unpack('<II', bytes(u.mem_read(esp + 4, 8)))

            def is_cursor(p):
                if not P.HEAP <= p < P.HEAP + P.HEAP_SIZE - 4:
                    return False
                return WIRE <= struct.unpack('<I', bytes(u.mem_read(p, 4)))[0] <= WIRE + 0xf0000
            fn = a - P.BASE
            if is_cursor(a1):
                kind.setdefault(fn, set()).add('reader')
            elif is_cursor(a2):
                kind.setdefault(fn, set()).add('helper')
        hs = [u.hook_add(UC_HOOK_CODE, classify, begin=P.BASE + f, end=P.BASE + f) for f in fns]
        self.run(inst, wire, trace=False)
        for x in hs:
            u.hook_del(x)
        for f, k in kind.items():
            if 'reader' in k:
                self.readers.add(f)
                self.snaps.setdefault(f, None)
            else:
                self.helpers.add(f)
        return {f for f, k in kind.items() if 'reader' in k}

    def of(self, fn):
        return [i for i in self.instances if i['fn'] == fn]

    def run(self, inst, wire, trace=True, helpers=(), stop=None):
        """run one instance's reader alone on `wire` (its own bytes) -> dict(ok, used, ev, blocks, obj). Events, each
        with the stack pointer last (code inside a child reader runs below the child's entry esp):
          ['bits', header offset, pos, width, value, caller fn, esp]   header bits read through getbits
          ['read', wire offset, eip, esp]                              one wire byte read
          ['in', reader fn, obj, wire offset, esp]                     a child reader starts
          ['call', helper fn, wire offset, esp]                        a helper from `helpers` starts
          ['write', address, size, eip, esp]                           a store into the emulator's heap
          ['cur', value, eip, esp]                                     the reader moves its cursor
        stop: (header start, header end, n): stop the emulation when the reader starts its n-th field (counted the way
        pkt_schema.StructLearner.starts counts them)"""
        emu = self.emu
        u = emu.u
        snap, top = self.snaps[inst['fn']]
        u.mem_write(P.HEAP, snap)
        emu.heap = top
        emu.floor = top
        u.mem_write(WIRE, bytes(wire))
        cursor = emu.alloc(4)
        u.mem_write(cursor, struct.pack('<I', WIRE))
        ev = []
        blocks = []
        hs = []
        missing = []
        if trace:
            def esp():
                return u.reg_read(UC_X86_REG_ESP)

            fs = {'n': 0, 'cur': None, 'eip': None, 'depth': 0}

            def field_start(key):
                fs['n'] += 1
                if stop and fs['n'] >= stop[2]:
                    u.emu_stop()

            def on_bits(u, a, s, d):
                e = esp()
                ret, buf, pos, w = struct.unpack('<IIII', bytes(u.mem_read(e, 16)))
                ev.append(['bits', buf - WIRE, pos & 0xff, w & 0xff, None, PM.fn_of(ret - P.BASE), e])
                if stop and fs['depth'] == 0 and buf - WIRE == stop[0] and PM.fn_of(ret - P.BASE) == inst['fn']:
                    if fs['cur'] != ('g', pos & 0xff):
                        fs['cur'] = ('g', pos & 0xff)
                        field_start(fs['cur'])
                    fs['eip'] = None

            def on_bits_ret(u, a, s, d):
                for x in reversed(ev):
                    if x[0] == 'bits':
                        if x[4] is None:
                            x[4] = u.reg_read(UC_X86_REG_EAX) & 0xff
                        break

            def on_read(u, acc, a, s, v, d):
                eip = u.reg_read(UC_X86_REG_EIP) - P.BASE
                if eip in GETBITS_READS:
                    return
                for k in range(s):
                    ev.append(['read', a - WIRE + k, eip, esp()])
                if stop and fs['depth'] == 0:
                    off = a - WIRE
                    if PM.fn_of(eip) == inst['fn'] and stop[0] <= off < stop[1]:
                        if not (fs['eip'] is not None and abs(eip - fs['eip']) < 16 and fs['cur'] and fs['cur'][0] == 'i'):
                            fs['cur'] = ('i', eip)
                            field_start(fs['cur'])
                        fs['eip'] = eip
                    else:
                        fs['eip'] = None

            def on_entry(u, a, s, d):
                e = esp()
                ret, cur = struct.unpack('<II', bytes(u.mem_read(e, 8)))
                c = struct.unpack('<I', bytes(u.mem_read(cur, 4)))[0] if P.HEAP <= cur < P.HEAP + P.HEAP_SIZE else 0
                ev.append(['in', a - P.BASE, u.reg_read(UC_X86_REG_ECX), c - WIRE, e])
                if stop and len(stop) > 3 and stop[3] and fs['depth'] == 0 and fs['n'] >= stop[2] - 1:
                    u.emu_stop()      # stop at the first child: what came before it (a count) is all that is wanted
                fs['depth'] += 1
                fs['eip'] = None
                if ret not in self.ret_sites:
                    self.ret_sites.add(ret)
                    missing.append(ret)

            def on_out(u, a, s, d):
                ev.append(['out', a - P.BASE, esp()])
                fs['depth'] = max(0, fs['depth'] - 1)

            def on_helper(u, a, s, d):
                e = esp()
                cur = struct.unpack('<I', bytes(u.mem_read(e + 8, 4)))[0]
                c = struct.unpack('<I', bytes(u.mem_read(cur, 4)))[0] if P.HEAP <= cur < P.HEAP + P.HEAP_SIZE else 0
                ev.append(['call', a - P.BASE, c - WIRE, e])

            def on_write(u, acc, a, s, v, d):
                eip = u.reg_read(UC_X86_REG_EIP) - P.BASE
                if a == cursor:
                    ev.append(['cur', v - WIRE, eip, esp()])
                else:
                    ev.append(['write', a, s, eip, esp()])
            hs = [u.hook_add(UC_HOOK_CODE, on_bits, begin=P.BASE + GETBITS, end=P.BASE + GETBITS),
                  u.hook_add(UC_HOOK_CODE, on_bits_ret, begin=P.BASE + GETBITS_RET, end=P.BASE + GETBITS_RET),
                  u.hook_add(UC_HOOK_MEM_READ, on_read, begin=WIRE, end=WIRE + 0xe0000),
                  u.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=P.HEAP, end=P.HEAP + P.HEAP_SIZE - 1)]
            hs += [u.hook_add(UC_HOOK_CODE, on_entry, begin=P.BASE + r, end=P.BASE + r) for r in self.readers if r != inst['fn']]
            hs += [u.hook_add(UC_HOOK_CODE, on_helper, begin=P.BASE + h, end=P.BASE + h) for h in helpers]
            hs += [u.hook_add(UC_HOOK_CODE, on_out, begin=a, end=a) for a in sorted(self.ret_sites)]
            emu.on_alloc = lambda p, n: blocks.append((p, n))
        ok, err = emu.call(inst['fn'], inst['obj'], [cursor, WIRE + len(wire)], limit=50_000_000)
        emu.on_alloc = None
        for h in hs:
            u.hook_del(h)
        if missing:   # a child returns to a place not hooked yet: run again with it hooked
            return self.run(inst, wire, trace, helpers, stop)
        used = struct.unpack('<I', bytes(u.mem_read(cursor, 4)))[0] - WIRE
        return {'ok': (ok or 0) & 0xff if err is None else None, 'err': err, 'used': used, 'ev': ev, 'blocks': blocks,
                'obj': inst['obj']}


def _install_floor():
    """packet_emu.Emu.alloc wraps to the start of the heap when full; with objects that must survive between runs it
    wraps to `floor` instead"""
    old = P.Emu.alloc

    def alloc(self, n):
        floor = getattr(self, 'floor', None)
        if floor is None:
            return old(self, n)
        p = (self.heap + 15) & ~15
        if p + n > P.HEAP + P.HEAP_SIZE - 0x1000:
            p = (floor + 15) & ~15
        self.heap = p + max(n, 1)
        self.u.mem_write(p, b'\0' * max(n, 1))
        return p
    P.Emu.alloc = alloc


_install_floor()


def show_tree(pid):
    T = Tree(pid)
    print(f'readers: {", ".join(hex(r) for r in sorted(T.readers))}')

    def walk(i, depth):
        kids = i['children']
        print('  ' * depth + f'{i["fn"]:#x} obj {i["obj"]:#x} wire {i["start"]}..{i["end"]} ({i["end"] - i["start"]} B), {len(kids)} children')
        # collapse runs of children of one reader
        k = 0
        while k < len(kids):
            j = k
            while j + 1 < len(kids) and kids[j + 1]['fn'] == kids[k]['fn']:
                j += 1
            if j > k:
                print('  ' * (depth + 1) + f'{j - k + 1} x {kids[k]["fn"]:#x}, first:')
            walk(kids[k], depth + 1 + (j > k))
            k = j + 1
    for i in T.instances:
        if i['parent'] is None:
            walk(i, 0)
    return T


def show_fields(pid, fn):
    T = Tree(pid)
    inst = T.of(fn)[0]
    wire = T.wire[inst['start']:inst['end']]
    r = T.run(inst, wire)
    print(f'{fn:#x} alone on its {len(wire)} bytes: ok {r["ok"]} used {r["used"]} {r["err"] or ""}')
    last = None
    for e in r['ev']:
        if e[0] == 'bits':
            print(f'  bits hdr@{e[1]} pos {e[2]} w {e[3]} = {e[4]}' + (f'   (by {e[5]:#x})' if e[5] != fn else ''))
            last = None
        elif e[0] == 'read':
            f = PM.fn_of(e[2])
            if last and last[0] == f and e[1] == last[2] + 1:
                last[2] = e[1]
                continue
            last = [f, e[1], e[1]]
            print(f'  read {e[1]} by {f:#x}' + ('  (the reader itself: header)' if f == fn else ''))
        elif e[0] == 'in':
            print(f'  CHILD {e[1]:#x} obj {e[2]:#x} at {e[3]}')
            last = None


if __name__ == '__main__':
    if sys.argv[1] == 'tree':
        show_tree(int(sys.argv[2]))
    elif sys.argv[1] == 'fields':
        show_fields(int(sys.argv[2]), int(sys.argv[3], 16))
