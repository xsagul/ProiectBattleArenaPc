"""The 13.3 packet readers start with a block of header bits: for every field a small number (its "mode") says whether
the field takes a constant or is read off the wire, and by which helper. This tool finds that structure for one packet
kind by running Riot's own reader in the emulator (packet_emu.Emu):

  pkt_modes.py fields <id> [k]        the replay's k-th packet of that id: every header-bit read (bit position, width,
                                      value) with the wire bytes and object bytes that follow it
  pkt_modes.py modes <id> [k]         every mode of every field: what the field becomes (constant / which helper reads
                                      how many wire bytes)

The header is read through rva 0x91cae0 (bits, bit position, width): little-endian bit order over the header bytes.
"""
import os
import struct
import sys
import bisect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from emu_backend import P  # noqa: E402
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_CODE, UC_HOOK_MEM_WRITE  # noqa: E402

PAD = 32   # bytes added after the body while trying modes, so a mode that reads more than the replay's still reads
_fs = []


fn_of = P.fn_of


def packets(pid):
    """the packets of one id: keyframe 1 first (creation packets live there), then the chunks"""
    out = []
    P.KINDS, P.ENTRY = (2,), 1
    out += [b for t, ch, p, obj, b in P.packets(P.ROFL, pid)]
    P.KINDS, P.ENTRY = (1,), None
    if not out:
        for t, ch, p, obj, b in P.packets(P.ROFL, pid):
            out.append(b)
            if len(out) > 50:
                break
    if os.environ.get('PKT_LONGEST'):
        # learn on the longest sample: a first packet with empty lists teaches nothing about their elements
        allb = out + [b for t, ch, p, obj, b in P.packets(P.ROFL, pid)][:3000]
        out = sorted(allb, key=len, reverse=True)[:1] + out
    return out


def run(emu, info, pid, body, hdr_len=None):
    """deserialize with a trace of events in order: ('bits', pos, width, value, ret eip), ('read', wire offset in the
    body, eip), ('write', object offset, size, eip). Returns (ok, left, events, object block)"""
    ev = []
    pend = {}
    obj_box = {}

    def on_code(u, addr, size, data):
        pos, width, ret = P.getbits_call(u)
        pend['bits'] = (pos, width, ret)
        ev.append(['bits', pos, width, None, ret])

    def on_ret(u, addr, size, data):
        if ev and ev[-1][0] == 'bits' and ev[-1][3] is None:
            ev[-1][3] = P.retval(u) & 0xff
        else:  # reads happened in between (none expected inside getbits besides the header)
            for e in reversed(ev):
                if e[0] == 'bits' and e[3] is None:
                    e[3] = P.retval(u) & 0xff
                    break

    def on_read(u, access, addr, size, value, data):
        off = addr - P.BUF - P.WIRE_SKIP
        eip = P.ip(u)
        if eip in P.GETBITS_READS:
            return
        for k in range(size):
            ev.append(['read', off + k, eip])

    u = emu.u
    h1 = u.hook_add(UC_HOOK_CODE, on_code, begin=P.BASE + P.GETBITS, end=P.BASE + P.GETBITS)
    # getbits returns at 0x91cb44 (ret)
    h2 = u.hook_add(UC_HOOK_CODE, on_ret, begin=P.BASE + P.GETBITS_RET, end=P.BASE + P.GETBITS_RET)
    h3 = u.hook_add(UC_HOOK_MEM_READ, on_read, begin=P.BUF, end=P.BUF + 0x10000)
    tr = {}
    try:
        ok, left, o = emu.deserialize(info, pid, 0, body, tr)
    finally:
        for h in (h1, h2, h3):
            u.hook_del(h)
    obj = tr['blocks'][0][0] if tr.get('blocks') else None
    return ok, left, ev, tr, obj


def header_bits(body, pos, width):
    v = int.from_bytes(body[:8].ljust(8, b'\0'), 'little')
    return (v >> pos) & ((1 << width) - 1)


def set_bits(body, pos, width, val):
    b = bytearray(body)
    v = int.from_bytes(bytes(b[:8]).ljust(8, b'\0'), 'little')
    mask = ((1 << width) - 1) << pos
    v = (v & ~mask) | (val << pos)
    nb = v.to_bytes(8, 'little')
    for i in range(min(8, len(b))):
        b[i] = nb[i]
    return bytes(b)


def segments(ev, tr, obj, size):
    """split the trace at every header-bit read of a NEW bit position -> [(pos, width, value, [wire offsets],
    {object offset: (eip, size)})]"""
    out = []
    cur = None
    writes = iter(tr.get('writes', []))
    for e in ev:
        if e[0] == 'bits':
            if cur is None or cur[0] != e[1]:
                cur = [e[1], e[2], e[3], [], []]
                out.append(cur)
        elif e[0] == 'read' and cur is not None and e[1] >= 0:
            cur[3].append((e[1], e[2]))
    return out


def fields(pid, k):
    t = P.table()
    emu = P.Emu()
    body = packets(pid)[k]
    ok, left, ev, tr, obj = run(emu, t[pid], pid, body)
    print(f'ok {ok} left {left} body {len(body)} B')
    # interleave bit reads, wire reads and object stores in time: the write trace has no timestamps, so use order of
    # write events relative to the read events through a combined hook instead
    for e in ev:
        if e[0] == 'bits':
            print(f'bits pos {e[1]:2d} width {e[2]} = {e[3]}   (caller {e[4]:#x})')
        else:
            print(f'   wire {e[1]:3d} {body[e[1]]:02x} by {e[2]:#x} ({fn_of(e[2]):#x})' if e[1] >= 0 else f'   wire {e[1]}')


def timeline(emu, info, pid, body):
    """one run, every event in order including object stores: [('bits', pos, w, val, caller) | ('read', off, eip) |
    ('write', objoff, size, eip)]"""
    ev = []
    u = emu.u
    box = {}

    def on_alloc_first(p, n):
        box.setdefault('obj', p)

    def on_code(u, addr, size, data):
        pos, width, ret = P.getbits_call(u)
        ev.append(['bits', pos, width, None, ret])

    def on_ret(u, addr, size, data):
        for e in reversed(ev):
            if e[0] == 'bits':
                if e[3] is None:
                    e[3] = P.retval(u) & 0xff
                break

    def on_read(u, access, addr, size, value, data):
        eip = P.ip(u)
        if eip in P.GETBITS_READS:
            return
        off = addr - P.BUF - P.WIRE_SKIP
        for k in range(size):
            ev.append(['read', off + k, eip])

    def on_write(u, access, addr, size, value, data):
        eip = P.ip(u)
        ev.append(['write', addr, size, eip])

    hs = [u.hook_add(UC_HOOK_CODE, on_code, begin=P.BASE + P.GETBITS, end=P.BASE + P.GETBITS),
          u.hook_add(UC_HOOK_CODE, on_ret, begin=P.BASE + P.GETBITS_RET, end=P.BASE + P.GETBITS_RET),
          u.hook_add(UC_HOOK_MEM_READ, on_read, begin=P.BUF, end=P.BUF + 0x10000),
          u.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=P.HEAP, end=P.HEAP + P.HEAP_SIZE - 1)]
    heap0 = emu.heap
    tr = {}
    try:
        res = emu.deserialize(info, pid, 0, body, tr)
    finally:
        for h in hs:
            u.hook_del(h)
    objp = tr['blocks'][0][0] if tr.get('blocks') else None
    # object-relative offsets
    for e in ev:
        if e[0] == 'write' and objp is not None:
            e[1] = e[1] - objp
    return res, ev, tr


def modes(pid, k):
    t = P.table()
    emu = P.Emu()
    body = packets(pid)[k]
    info = t[pid]
    (ok, left, _), ev, tr = timeline(emu, info, pid, body)
    order = []
    for e in ev:
        if e[0] == 'bits' and (not order or order[-1][0] != e[1]):
            order.append((e[1], e[2], e[3]))
    print(f'{len(order)} header fields, in reading order: ' + ' '.join(f'{p}:{w}={v}' for p, w, v in order))
    for idx, (pos, width, val) in enumerate(order):
        print(f'-- bits {pos}..{pos + width - 1} (replay value {val})')
        for m in range(1 << width):
            b2 = set_bits(body, pos, width, m) + bytes(PAD)
            (ok2, left2, _), ev2, tr2 = timeline(emu, info, pid, b2)
            plain = {}
            if tr2.get('writes'):
                for off, raw, hid, w in P.plain_fields([(w, a - tr2['blocks'][0][0], s, v) for w, a, s, v in tr2['writes']], info['size']):
                    plain[off] = raw
            # events between this field's first header read and the next field's
            start = next((i for i, e in enumerate(ev2) if e[0] == 'bits' and e[1] == pos), None)
            if start is None:
                print(f'   mode {m}: field not reached')
                continue
            end = len(ev2)
            for i in range(start + 1, len(ev2)):
                e = ev2[i]
                if e[0] == 'bits' and e[1] != pos:
                    end = i
                    break
            seg = ev2[start:end]
            reads = [e for e in seg if e[0] == 'read' and e[1] >= 0]
            helpers = sorted({fn_of(e[2]) for e in reads})
            wr = sorted({(e[1], e[2]) for e in seg if e[0] == 'write' and 0 <= e[1] < info['size']})
            offs = sorted({e[1] + j for e in seg if e[0] == 'write' and 0 <= e[1] < info['size'] for j in range(e[2])})
            span = f'{offs[0]:#x}..{offs[-1]:#x}' if offs else '-'
            fail = '' if ok2 else f' (ok {ok2} left {left2})'
            val = ' '.join(f'+{o:#x}={plain[o].hex()}' for o in sorted(plain) if offs and offs[0] <= o <= offs[-1])
            print(f'   mode {m}: {len(reads)} wire bytes by {",".join(hex(h) for h in helpers) or "-"}; object {span} {val}{fail}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    pid = int(sys.argv[2])
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    if cmd == 'fields':
        fields(pid, k)
    elif cmd == 'modes':
        modes(pid, k)
