"""Disassemble one function of an object file made by match_func.py (client-src/obj/<name>.obj).

  dis_obj.py <object> <symbol text> [from offset hex]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import match_func as M  # noqa: E402
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

name, code, rel = M.function_of(sys.argv[1], sys.argv[2])
start = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, 0):
    if i.address >= start:
        print(f'{i.address:#6x} {i.mnemonic} {i.op_str}' + ('   ; reloc' if any(i.address + k in rel for k in range(i.size)) else ''))
