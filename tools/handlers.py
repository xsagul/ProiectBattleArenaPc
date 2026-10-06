"""Packet id -> the client's handler function, read from the 13.3 image's own registration code.

The client registers a handler per packet kind with RegisterHandler (rva 0x3710a0): arguments = the owner object, the
packet id (a constant), a std::function (0x28 bytes, by value). The std::function is built just before from
(this, member function pointer) by a small bind helper, so the member function's address is a `push <code address>`
shortly before the call. Many sites go through a per-kind thunk (the id constant sits in the thunk).

  handlers.py table            id, handler rva, registering function, strings the handler uses -> stdout
  handlers.py strings <rva>    strings a function (and what it calls, 2 levels) refers to
  handlers.py digest [depth]   every packet kind of the 13.3 replay: count, first second, handler (map entry or
                               listener case, tools/listeners.py) and the strings its code reaches
Output of `table` is kept in client-src/handler_table.txt, of `digest` in client-src/handler_digest.txt.
"""
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import exe_dis as E
from capstone import CS_OP_IMM, CS_OP_MEM

REGISTER = 0x3710a0
E.md.detail = True
T0, T1 = E.TEXT


def calls_to(target):
    t = E.data
    out = []
    i = T0
    while True:
        i = t.find(b'\xe8', i, T1 - 5)
        if i < 0:
            break
        if struct.unpack_from('<i', t, i + 1)[0] + i + 5 == target:
            out.append(i)
        i += 1
    return out


def in_text(v):
    return E.BASE + T0 <= v < E.BASE + T1


def scan_fn(start, want):
    """Walk a function linearly; at every call whose site is in `want`, report the pushes seen since the previous
    call to RegisterHandler / a thunk: (site, [small immediates pushed], [code addresses pushed or stored])."""
    out = []
    small, code = [], []
    end = max(want) + 5
    for ins in E.md.disasm(E.data[start:end], E.BASE + start):
        a = ins.address - E.BASE
        if ins.id == 0:
            continue
        if ins.mnemonic == 'push' and ins.operands[0].type == CS_OP_IMM:
            v = ins.operands[0].imm & 0xffffffff
            if in_text(v):
                code.append(v - E.BASE)
            elif v < 0x400:
                small.append(v)
        elif ins.mnemonic == 'mov' and len(ins.operands) == 2 and ins.operands[1].type == CS_OP_IMM \
                and ins.operands[0].type == CS_OP_MEM:
            v = ins.operands[1].imm & 0xffffffff
            if in_text(v):
                code.append(v - E.BASE)
        if a in want:
            out.append((a, small[:], code[:]))
            small, code = [], []
    return out


def build():
    sites = calls_to(REGISTER)
    by_fn = {}
    for s in sites:
        by_fn.setdefault(E.fn_start(s), []).append(s)
    thunks = {}   # thunk fn -> id
    direct = []   # (site, id, handler, registering fn)
    pending = {}  # registering fn -> set of sites (direct or thunk calls)
    for f, ss in by_fn.items():
        if E.fn_end(f) - f < 0x90 and len(ss) == 1:
            r = scan_fn(f, set(ss))
            if r and r[0][1]:
                thunks[f] = r[0][1][-1]
                continue
        pending.setdefault(f, set()).update(ss)
    thunk_site = {}
    for t, pid in thunks.items():
        for c in calls_to(t):
            thunk_site[c] = pid
            pending.setdefault(E.fn_start(c), set()).add(c)
    rows = []
    for f, ss in pending.items():
        for site, small, code in scan_fn(f, ss):
            if site in thunk_site:
                pid = thunk_site[site]
            else:
                pid = small[-1] if small else None
            rows.append((pid, code[-1] if code else None, f, site))
    return rows


NOISE = ('too long', 'bad function call', 'address family', 'unknown error', 'bad_weak_ptr', 'invalid string position',
         'invalid hash bucket', 'regex_error', 'CorExitProcess', 'bad allocation', 'bad cast', 'iostream',
         'invalid stoi', 'stoi argument', 'bad array', 'UTF-', 'UNICODE', 'generic', 'system', 'Unknown exception')
LISTENERS = (0x355f80, 0x3601d0, 0x562a80, 0x3554e0)


def all_handlers():
    """{packet id: [(how, code address)]} from the handler map registrations and the listeners' switches"""
    import listeners as L
    out = {}
    for pid, h, f, site in build():
        if pid is not None and h is not None:
            out.setdefault(pid, []).append((f'map (registered in {f:#x})', h))
    for f in LISTENERS:
        for pid, a in L.cases(f, 0x400).items():
            out.setdefault(pid, []).append((f'listener {f:#x}', a))
    return out


def strings_of(fn, depth=2, seen=None, limit=0x1800, case=False):
    """strings the code at fn refers to, following calls `depth` levels down. case=True: fn is one case of a
    listener's switch, which ends at its first unconditional jump (back to the shared exit)"""
    seen = set() if seen is None else seen
    if fn in seen or not (T0 <= fn < T1):
        return []
    seen.add(fn)
    out = []
    end = fn + limit if case else min(E.fn_end(fn), fn + limit)
    for ins in E.md.disasm(E.data[fn:end], E.BASE + fn):
        if ins.id == 0:
            continue
        if ins.mnemonic == 'ret' or (case and ins.mnemonic == 'jmp'):
            break
        for op in ins.operands:
            v = None
            if op.type == CS_OP_IMM:
                v = op.imm & 0xffffffff
            elif op.type == CS_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                v = op.mem.disp & 0xffffffff
            if v is None:
                continue
            if ins.mnemonic == 'call' and depth > 0 and in_text(v):
                out += strings_of(v - E.BASE, depth - 1, seen, 0x600)
            elif E.BASE + T1 <= v < E.BASE + len(E.data):
                s = E.string_at(v - E.BASE)
                if s and s not in out and not any(n in s for n in NOISE):
                    out.append(s)
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'table':
        rows = build()
        rows.sort(key=lambda r: (r[0] is None, r[0] or 0, r[2]))
        print('# id  handler  registered-in  call-site  strings the handler refers to')
        for pid, h, f, site in rows:
            ss = strings_of(h) if h else []
            print(f'{pid if pid is not None else "?":>4}  {h if h is None else hex(h):>9}  {f:#09x}  {site:#09x}  '
                  + ' | '.join(s[:60] for s in ss[:6]))
    elif sys.argv[1] == 'strings':
        for s in strings_of(E.rva(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 2):
            print(s)
    elif sys.argv[1] == 'digest':
        import re
        depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        hs = all_handlers()
        print('# id  count  first-s  objects | handler(s) | strings reached from the handler (depth %d)' % depth)
        for line in open(os.path.join(HERE, '..', 'data', 'exe133', 'rofl_summary.txt')):
            m = re.match(r'\s+(\d+)\s+(\d+)\s+(\d+)\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+(\S+),', line)
            if not m:
                continue
            pid = int(m.group(1))
            hh = hs.get(pid, [])
            ss = []
            for how, a in hh:
                for x in strings_of(a, depth, case=how.startswith('listener')):
                    if x not in ss:
                        ss.append(x)
            print(f'{pid:4} {int(m.group(2)):7} {float(m.group(4)):7.1f} {m.group(5):>6} | '
                  + '; '.join(f'{how} {a:#x}' for how, a in hh) + ' | ' + ' | '.join(x[:50] for x in ss[:14]))
