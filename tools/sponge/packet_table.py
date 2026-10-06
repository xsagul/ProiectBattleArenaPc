"""The 13.3 client's packet table, read from its in-memory image (research/exe133/exe_image_t900.bin).

The receive dispatcher (rva 0x351c60) reads a u16 packet id, asks the factory (rva 0x7fc950) for an object, then calls
the object's vtable[1](&cursor, end) to deserialize it. The factory is a switch on (id - 2) over 0x315 cases with a jump
table at rva 0x804ddc; each case is `push size; call new; mov ecx, eax; call ctor`. The ctor stores the vtable.

  packet_table.py            -> research/exe133/packet_table.txt (id, size, ctor, vtable, deserialize, readable?)
"""
import struct, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'research', 'exe133')
data = open(os.path.join(OUT, 'exe_image_t900.bin'), 'rb').read()
BASE = 0x580000
FACTORY, JT, NCASE, FIRST_ID = 0x7fc950, 0x804ddc, 0x315, 2
DEFAULT = 0x804dcb
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False


def readable(r):
    p = r & ~0xfff
    return data[p:p + 4096] != bytes(4096)


def u32(r):
    return struct.unpack_from('<I', data, r)[0]


def ins_at(r, n):
    return list(md.disasm(data[r:r + n * 15], BASE + r))[:n]


def case(r):
    """size, ctor of one factory case"""
    size = ctor = None
    for i in ins_at(r, 8):
        if i.mnemonic == 'push' and i.op_str.startswith('0x') and size is None:
            size = int(i.op_str, 16)
        if i.mnemonic == 'call' and i.op_str.startswith('0x'):
            t = int(i.op_str, 16) - BASE
            if t != 0x9bb8d0:
                ctor = t
                break
    return size, ctor


def vtable_of(ctor):
    """last `mov dword ptr [reg], imm` into offset 0 inside the ctor (derived class vtable is written last)"""
    if ctor is None or not readable(ctor):
        return None
    vt = None
    for i in ins_at(ctor, 120):
        if i.mnemonic == 'mov' and i.op_str.startswith('dword ptr [e') and ']' in i.op_str:
            dst, src = i.op_str.split(', ', 1)
            if '+' not in dst and '-' not in dst and src.startswith('0x'):
                v = int(src, 16) - BASE
                if 0xfab000 <= v < 0x1752000:
                    vt = v
        if i.mnemonic == 'ret':
            break
    return vt


rows = []
for k in range(NCASE):
    pid = k + FIRST_ID
    tgt = u32(JT + 4 * k) - BASE
    if tgt == DEFAULT:
        continue
    size, ctor = case(tgt)
    vt = vtable_of(ctor)
    des = u32(vt + 4) - BASE if vt else None
    rows.append((pid, size, ctor, vt, des))

with open(os.path.join(OUT, 'packet_table.txt'), 'w') as f:
    f.write('# id  size  ctor  vtable  deserialize(vtable[1])  code-in-dump\n')
    for pid, size, ctor, vt, des in rows:
        f.write(f'{pid:4d} {size if size is not None else -1:#6x} {ctor or 0:#09x} {vt or 0:#09x} {des or 0:#09x} '
                f'{"yes" if des and readable(des) else "NO"}\n')
n = len(rows)
print(f'{n} packet ids in the factory; ctor readable {sum(1 for r in rows if r[2] and readable(r[2]))}; '
      f'vtable found {sum(1 for r in rows if r[3])}; deserialize readable {sum(1 for r in rows if r[4] and readable(r[4]))}')
