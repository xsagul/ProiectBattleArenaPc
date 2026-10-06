"""The 13.3 client's generic packet listeners: functions that switch on the packet id themselves.

Besides the per-object handler map (tools/handlers.py), the net client keeps a list of listeners (+0x198);
each gets every packet no object handler took: listener->vtable[1](packet, time). Such a function starts by reading
the id (`movzx r, word ptr [packet + 4]`) and then compares it / jumps through a table. This tool finds every such
function in the image and prints the ids it handles with the code address of each case.

  listeners.py            every function that reads a u16 at +4 of an argument and switches on it
  listeners.py <rva>      the cases of one function
"""
import struct
import sys
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import exe_dis as E

T0, T1 = E.TEXT
d = E.data


def u32(r):
    return struct.unpack_from('<I', d, r)[0]


def cases(fn, limit=0x200):
    """{id: case address}: follows the compare tree / jump tables that start where the id is read"""
    out = {}
    head = list(E.md.disasm(d[fn:fn + limit], E.BASE + fn))
    reg = start = None
    for ins in head:
        mm = re.match(r'(\w+), word ptr \[(\w+) \+ 4\]$', ins.op_str)
        if ins.mnemonic == 'movzx' and mm:
            reg, start = mm.group(1), ins.address - E.BASE + ins.size
            break
    if reg is None:
        return out
    todo = [(start, 0, None, False)]
    seen = set()
    while todo:
        at, bias, last_cmp, arith = todo.pop()
        steps = 0
        while steps < 12:
            if (at, bias) in seen:
                break
            seen.add((at, bias))
            ins = next(E.md.disasm(d[at:at + 16], E.BASE + at), None)
            if ins is None:
                break
            steps += 1
            m, o = ins.mnemonic, ins.op_str
            nxt = at + ins.size
            mm = re.match(rf'{reg}, (0x[0-9a-f]+|\d+)$', o)
            if m == 'sub' and mm:
                bias += int(mm.group(1), 0); arith = True
            elif m == 'add' and mm:
                v = int(mm.group(1), 0)
                bias += (0x100000000 - v) if v > 0x7fffffff else -v
                arith = True
            elif m == 'cmp' and mm:
                last_cmp = int(mm.group(1), 0); arith = False
            elif m in ('je', 'jne'):
                val = bias if arith else (last_cmp + bias if last_cmp is not None else None)
                tgt = int(o, 0) - E.BASE
                if val is None:
                    break
                if m == 'je':
                    out.setdefault(val, tgt)
                else:
                    out.setdefault(val, nxt)
                    at = tgt
                    continue
            elif m in ('ja', 'jae', 'jb', 'jbe', 'jg', 'jge', 'jl', 'jle'):
                todo.append((int(o, 0) - E.BASE, bias, last_cmp, arith))
            elif m == 'jmp' and '*4' in o:
                jt = int(re.search(r'0x[0-9a-f]+', o).group(0), 16) - E.BASE
                for c in range((last_cmp or 0) + 1):
                    out.setdefault(c + bias, u32(jt + 4 * c) - E.BASE)
                break
            elif m == 'movzx' and re.match(r'\w+, byte ptr \[\w+ \+ (0x[0-9a-f]+)\]', o):
                idx = int(re.search(r'0x[0-9a-f]+', o).group(0), 16) - E.BASE
                j = next(E.md.disasm(d[nxt:nxt + 16], E.BASE + nxt), None)
                if j is not None and j.mnemonic == 'jmp' and '*4' in j.op_str:
                    jt = int(re.search(r'0x[0-9a-f]+', j.op_str).group(0), 16) - E.BASE
                    for c in range((last_cmp or 0) + 1):
                        out.setdefault(c + bias, u32(jt + 4 * d[idx + c]) - E.BASE)
                break
            elif m == 'jmp':
                at = int(o, 0) - E.BASE
                continue
            elif m in ('push', 'mov', 'lea', 'and', 'xor', 'test') and steps < 8 and not mm:
                pass
            else:
                break
            at = nxt
    # the default case is the address most ids share: drop it
    if out:
        cnt = {}
        for a in out.values():
            cnt[a] = cnt.get(a, 0) + 1
        dflt = max(cnt, key=cnt.get)
        if cnt[dflt] > 3:
            out = {k: v for k, v in out.items() if v != dflt}
    return out


def find_all():
    res = {}
    i = T0
    while True:
        i = d.find(b'\x0f\xb7', i, T1)
        if i < 0:
            break
        modrm = d[i + 2]
        if modrm & 0xc0 == 0x40 and d[i + 3] == 4 and (modrm & 7) != 4:
            f = E.fn_start(i)
            if i - f < 0x40 and f not in res:
                c = cases(f)
                if len(c) >= 3:
                    res[f] = c
        i += 1
    return res


if __name__ == '__main__':
    if len(sys.argv) > 1:
        f = int(sys.argv[1], 16)
        for pid, a in sorted(cases(f, 0x400).items()):
            print(f'{pid:4}  {a:#09x}')
    else:
        for f, c in sorted(find_all().items()):
            print(f'{f:#09x}  {len(c)} ids: ' + ' '.join(f'{p}@{a:#x}' for p, a in sorted(c.items())))
