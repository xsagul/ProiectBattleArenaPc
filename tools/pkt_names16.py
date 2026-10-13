"""Packet id -> the name Riot gave the packet (PKT_<name>), read from the 16.20 client's own handler registrations.

The client registers one handler per server packet kind: RegisterHandler(rva 0x697440, rcx = the dispatcher,
r8d = the packet id, r9 = a std::function). The std::function wraps a lambda made by Riot::MakeFunction<Owner,
PKT_<name>>; the lambda's RTTI type descriptor survives in .data and names the packet struct. Chain:
  type descriptor  <- `lea rax, [descriptor]; ret` = the std::function's _Target_type (vtable slot 3, a leaf
                      function without .pdata)
  that function    <- a pointer in .rdata = slot 3 of the _Func_impl vtable
  the vtable       <- `lea rax, [vtable]` where the registering code builds the std::function, followed by
                      `mov r8d, <id>` and the call to RegisterHandler.
Only packets the client handles through such a lambda are named (320 names; the rest go through other paths).

    python tools/pkt_names16.py            -> data/exe1620/packet_names16.json  {id: name}, prints the table
    python tools/pkt_names16.py <word>     the ids whose name contains <word>
"""
import bisect
import collections
import json
import os
import re
import struct
import sys

import capstone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'data', 'exe1620', 'exe_image_live.bin')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'packet_names16.json')
REGISTER = 0x697440
TEXT = (0x1000, 0x19fd000)
RDATA = (0x19fd000, 0x19fd000 + 0x44a000)


def build():
    img = open(IMG, 'rb').read()
    base = int(open(IMG[:-4] + '_pages.txt').readline().split()[1], 16)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    names = {}
    for m in re.finditer(rb'\.\?AV<lambda_\d+>@[\x21-\x7e]*?VPKT_([A-Za-z0-9_]+?)@@', img):
        names[m.start() - 16] = m.group(1).decode()
    t0, t1 = TEXT
    text = img[t0:t1]
    leas = collections.defaultdict(list)
    for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', text):
        i = m.start()
        leas[t0 + i + 7 + struct.unpack_from('<i', text, i + 3)[0]].append(t0 + i)
    r0, r1 = RDATA
    rdata = img[r0:r1]
    funcs = _pdata(img)
    starts = [f[0] for f in funcs]
    calls = None

    def registered_after(site, thunks=True):
        """the packet id registered by the code from `site` on: `mov r8d, <id>` + call RegisterHandler, either
        inline or inside a per-kind thunk the code calls (the thunk holds the id)"""
        pid = None
        for k, ins in enumerate(md.disasm(img[site:site + 0x200], base + site)):
            if k > 60:
                return None
            if ins.mnemonic == 'mov' and ins.op_str.startswith('r8d, 0x'):
                pid = int(ins.op_str.split(', ')[1], 16)
            elif ins.mnemonic == 'call':
                tgt = int(ins.op_str, 16) - base if ins.op_str.startswith('0x') else None
                if tgt == REGISTER and pid is not None:
                    return pid
                if thunks and tgt is not None and k > 0:
                    inner = registered_after(tgt, thunks=False)
                    if inner is not None:
                        return inner
        return None
    out = {}
    for td, name in names.items():
        for f in leas.get(td, []):
            if img[f + 7] != 0xc3:                     # not `lea rax, [td]; ret`
                continue
            key = struct.pack('<Q', base + f)
            i = rdata.find(key)
            while i >= 0:
                vt = r0 + i - 24
                for site in leas.get(vt, []):
                    pid = registered_after(site)
                    if pid is not None:
                        out.setdefault(pid, set()).add(name)
                        continue
                    # the std::function is built by a small out-of-line helper: the registration follows its calls
                    k = bisect.bisect_right(starts, site) - 1
                    if k < 0 or not funcs[k][0] <= site < funcs[k][1] or funcs[k][1] - funcs[k][0] > 0x80:
                        continue
                    if calls is None:
                        calls = _calls(img, base)
                    for c in calls.get(funcs[k][0], []):
                        pid = registered_after(c)
                        if pid is not None:
                            out.setdefault(pid, set()).add(name)
                i = rdata.find(key, i + 8)
    table = {str(k): sorted(v)[0] if len(v) == 1 else '|'.join(sorted(v)) for k, v in sorted(out.items())}
    json.dump(table, open(OUT, 'w'), indent=0)
    return table


def _pdata(img):
    pe = struct.unpack_from('<I', img, 0x3c)[0]
    nsec, opt = struct.unpack_from('<H', img, pe + 6)[0], struct.unpack_from('<H', img, pe + 20)[0]
    for i in range(nsec):
        name, vs, va = struct.unpack_from('<8sII', img, pe + 24 + opt + i * 40)
        if name.rstrip(b'\x00') == b'.pdata':
            out = []
            for o in range(va, va + vs, 12):
                b, e, _ = struct.unpack_from('<III', img, o)
                if not b:
                    break
                out.append((b, e))
            return sorted(out)
    return []


def _calls(img, base):
    """call target rva -> [rvas of the calls] (direct `call rel32` in .text)"""
    t0, t1 = TEXT
    out = collections.defaultdict(list)
    for m in re.finditer(rb'\xe8', img[t0:t1]):
        i = t0 + m.start()
        out[i + 5 + struct.unpack_from('<i', img, i + 1)[0]].append(i)
    return out


def load():
    if not os.path.exists(OUT):
        return build()
    return json.load(open(OUT))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        t = load()
        w = sys.argv[1].lower()
        for k, v in t.items():
            if w in v.lower() or w == k:
                print(k, v)
        sys.exit()
    t = build()
    for k, v in t.items():
        print(f'{int(k):5d} {v}')
    print(len(t), 'ids named ->', OUT)
