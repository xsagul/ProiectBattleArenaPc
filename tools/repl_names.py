"""Names of the replicated values in packet 595: (group, bit) -> variable name, per kind of unit.

Each unit class registers its replicated variables at construction (hero: rva 0x17a490): rva 0x1a2ff0 builds the
replication manager over 8 group tables (static objects 0x108 bytes apart), then every variable goes in with
`mov ecx, <group table>; push <name>; push <variable>; push <owner>; call rva 0x189df0 / 0x19ccc0`. The register
function appends to the table: +0 count, +8 + 4*i the variable's offset in the object, +0x88 + 4*i its name. The bit of
a value in 595 is its index i in the group's table. The tables are filled at run time; the image we dumped from a
running replay holds them filled, so they are read straight from it.

  BA_EXE_IMG=client-src/exe_image_match78.bin repl_names.py
                              every unit class's groups with their names -> data/exe133/repl_names.json
  (the tables fill when the first unit of a class is built: exe_image_match78.bin was dumped from our unpacked
  client at game second ~78, minions out; its .text is the same code)
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import exe_dis as E

BASE = E.BASE
D = E.data
MANAGER = 0x1a2ff0      # builds a replication manager over 8 group tables
RES = os.path.join(HERE, '..', 'data', 'exe133')


def u32(r):
    return struct.unpack_from('<I', D, r)[0]


def cstr(va):
    r = va - BASE
    if not 0 < r < len(D):
        return None
    e = D.find(b'\0', r, r + 200)
    return D[r:e].decode('latin1')


def groups_of(fn):
    """the 8 group tables a class's registration passes to the manager: the 8 pushes of immediates before the call"""
    import capstone
    ins = list(E.md.disasm(D[fn:fn + 0x400], BASE + fn))
    for i, x in enumerate(ins):
        if x.mnemonic == 'call' and x.op_str.startswith('0x') and int(x.op_str, 16) - BASE == MANAGER:
            pushes = [int(y.op_str, 16) for y in ins[max(0, i - 16):i]
                      if y.mnemonic == 'push' and y.op_str.startswith('0x') and int(y.op_str, 16) > BASE]
            return sorted(pushes)[:8]
    return None


def table(g):
    """[(variable offset, name)] of one group table (its address as a VA)"""
    r = g - BASE
    n = u32(r)
    if n > 32:
        return None
    return [(u32(r + 8 + 4 * i), cstr(u32(r + 0x88 + 4 * i))) for i in range(n)]


# the classes, by the function that registers them (the manager's 8 group tables are its arguments); the lane
# minion picks its tables by a flag (rva 0x1cdd46: [vtable+0xe4 result + 0x3c] bit 3): flag 0 is the lane minion
# (its tables match the replay's minion updates), flag 1 another AI minion whose tables were empty in our dumps
MINION_FLAG0 = [0x316d6c8, 0x316d7d0, 0x316d8d8, 0x316dae8, 0x316dcf8, 0x316de00, 0x316e010, 0x316e118]
MINION_FLAG1 = [0x316d6c8, 0x316d7d0, 0x316d9e0, 0x316dbf0, 0x316dcf8, 0x316df08, 0x316e010, 0x316e118]
CLASSES = {
    'hero': ('fn', 0x17a490),
    'turret': ('fn', 0x1ce2a0),
    'lane_minion': ('groups', MINION_FLAG0),
    'ai_minion_flag1': ('groups', MINION_FLAG1),
    'object_0x770d60': ('fn', 0x770d60),
    'object_0x770f40': ('fn', 0x770f40),
    'object_0x7710a0': ('fn', 0x7710a0),
    'object_0x1ce4c0': ('fn', 0x1ce4c0),
}


def main():
    out = {}
    for key, (how, x) in CLASSES.items():
        gs = groups_of(x) if how == 'fn' else [BASE + g for g in x]
        cls = {}
        for k, g in enumerate(gs):
            t = table(g)
            cls[k] = [{'bit': i, 'offset': off, 'name': name} for i, (off, name) in enumerate(t or [])]
        flags = [u32(g - BASE + 4) for g in gs]
        out[key] = {'groups': [f'{g:#x}' for g in gs], 'flags': flags, 'values': cls}
        print(f'{key}: groups {[f"{g - BASE:#x}" for g in gs]}')
        for k, vals in cls.items():
            if vals:
                print(f'  group {k}: ' + ', '.join(f'{v["bit"]}={v["name"]}' for v in vals))
    with open(os.path.join(RES, 'repl_names.json'), 'w') as f:
        json.dump(out, f, indent=1)


def main_old():
    out = {}
    for line in os.popen(f'python "{os.path.join(HERE, "exe_dis.py")}" xref {BASE + MANAGER:#x}'):
        p = line.split()
        if len(p) < 5 or p[0] != 'call':
            continue
        fn = int(p[4], 16)
        gs = groups_of(fn)
        if not gs:
            continue
        cls = {}
        for k, g in enumerate(gs):
            t = table(g)
            cls[k] = [{'bit': i, 'offset': off, 'name': name} for i, (off, name) in enumerate(t or [])]
        key = f'{fn:#x}'
        if key in out:
            continue
        out[key] = {'groups': [f'{g:#x}' for g in gs], 'values': cls}
        print(f'class registered in {fn:#x}: groups {[f"{g - BASE:#x}" for g in gs]}')
        for k, vals in cls.items():
            print(f'  group {k}: ' + ', '.join(f'{v["bit"]}={v["name"]}' for v in vals))
    with open(os.path.join(RES, 'repl_names.json'), 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
