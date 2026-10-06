"""Disassemble the 13.3 client's in-memory image (research/exe133/exe_image_unpacked.bin, base 0x580000).

  exe_dis.py fn <rva|va>        whole function around the address (start found by CC/C3 padding before a prologue)
  exe_dis.py at <rva|va> [n]    n instructions from the address
  exe_dis.py xref <rva|va>      code places that use the address as an immediate/displacement or call/jump to it
exe_image_unpacked.bin has every code page the packer unlocks during a replay (all 4010 .text pages touched; see
run_replay.sh touch). Only the 38-page block at rva 0x1c000..0x4a000 stays encrypted (it decrypts into scratch, never
in place): the tool says so instead of disassembling it. Override the image with BA_EXE_IMG=<path>.
"""
import struct, sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.environ.get('BA_EXE_IMG') or os.path.join(HERE, '..', '..', 'research', 'exe133', 'exe_image_unpacked.bin')
BASE = 0x580000
TEXT = (0x1000, 0x1000 + 0xfa96ec)
data = open(IMG, 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True


def rva(x):
    x = int(x, 16) if isinstance(x, str) else x
    return x - BASE if x >= BASE else x


def page_zero(r):
    p = r & ~0xfff
    return data[p:p + 4096] == bytes(4096)


def string_at(r):
    if not (0 < r < len(data)):
        return None
    end = data.find(b'\0', r, r + 200)
    s = data[r:end] if end > r else b''
    if len(s) >= 4 and all(32 <= c < 127 for c in s):
        return s.decode()
    return None


def annotate(ins):
    notes = []
    for tok in ins.op_str.replace('[', ' ').replace(']', ' ').replace(',', ' ').split():
        if tok.startswith('0x'):
            v = int(tok, 16)
            if BASE <= v < BASE + len(data):
                s = string_at(v - BASE)
                notes.append(f'rva {v - BASE:#x}' + (f' "{s[:70]}"' if s else ''))
    return ('   ; ' + '; '.join(notes)) if notes else ''


def dis(start, end):
    if page_zero(start):
        print(f'{start:#x}: page not in the dump (still encrypted when dumped)')
        return
    for ins in md.disasm(data[start:end], BASE + start):
        print(f'{ins.address - BASE:#09x}  {ins.mnemonic:7} {ins.op_str}{annotate(ins)}')
        if page_zero(ins.address - BASE):
            print('   ...page not in the dump'); break


def fn_start(r):
    i = r
    while i > TEXT[0] and r - i < 0x20000:
        if data[i - 1] in (0xCC, 0xC3) and data[i] in (0x55, 0x53, 0x56, 0x57, 0x83, 0x81, 0x8B, 0x6A, 0x51, 0x64, 0xA1, 0x68):
            if data[i - 1] == 0xCC or data[i - 2] == 0xCC:
                return i
        i -= 1
    return r


def fn_end(s):
    for ins in md.disasm(data[s:s + 0x20000], BASE + s):
        a = ins.address - BASE
        if ins.mnemonic in ('ret', 'jmp') and data[a + ins.size] == 0xCC and a >= s:
            # stop at the first ret followed by padding that is past every jump target seen; good enough
            return a + ins.size
    return s + 0x400


def xref(r):
    va = BASE + r
    pat = struct.pack('<I', va)
    i = TEXT[0]
    while True:
        i = data.find(pat, i, TEXT[1])
        if i < 0: break
        print(f'imm at {i:#x}  fn {fn_start(i):#x}')
        i += 1
    # rel32 calls / jumps
    for op in (0xE8, 0xE9):
        j = TEXT[0]
        t = data[TEXT[0]:TEXT[1]]
        # brute force: slow but fine for one target
        for k in range(len(t) - 5):
            if t[k] == op and struct.unpack_from('<i', t, k + 1)[0] == r - (TEXT[0] + k + 5):
                print(f'{"call" if op == 0xE8 else "jmp"} at {TEXT[0] + k:#x}  fn {fn_start(TEXT[0] + k):#x}')


if __name__ == '__main__':
    cmd, x = sys.argv[1], rva(sys.argv[2])
    if cmd == 'fn':
        s = fn_start(x); print(f'function {s:#x}'); dis(s, fn_end(s) if len(sys.argv) < 4 else s + int(sys.argv[3], 16))
    elif cmd == 'at':
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
        cnt = 0
        for ins in md.disasm(data[x:x + n * 16], BASE + x):
            print(f'{ins.address - BASE:#09x}  {ins.mnemonic:7} {ins.op_str}{annotate(ins)}'); cnt += 1
            if cnt >= n: break
    elif cmd == 'xref':
        xref(x)
