"""Reads, from outside, the memory the packer's import stubs live in (the running 13.3 client): every import slot of
the game points at a small stub that computes the real system function's address. Read-only (ReadProcessMemory).

  read_stubs.py      -> data/exe133/import_stubs.bin (+ .txt: the regions read)
"""
import ctypes, ctypes.wintypes as w, re, subprocess, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe133')
k = ctypes.WinDLL('kernel32', use_last_error=True)
out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq League of Legends.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
pid = int(out.split(',')[1].strip('"'))
k.OpenProcess.restype = w.HANDLE
h = k.OpenProcess(0x0410, False, pid)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
if not h:
    sys.exit('OpenProcess failed: %d' % ctypes.get_last_error())
stubs = sorted(int(m.group(1), 16) for m in re.finditer(r'^stub \w+ -> (\w+)', open(os.path.join(RES, 'imports.txt')).read(), re.M))


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_uint64), ('AllocationBase', ctypes.c_uint64), ('AllocationProtect', w.DWORD), ('pad1', w.DWORD),
                ('RegionSize', ctypes.c_uint64), ('State', w.DWORD), ('Protect', w.DWORD), ('Type', w.DWORD), ('pad2', w.DWORD)]


k.VirtualQueryEx.argtypes = [w.HANDLE, ctypes.c_uint64, ctypes.POINTER(MBI), ctypes.c_size_t]
k.ReadProcessMemory.argtypes = [w.HANDLE, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
regions = {}
for a in stubs:
    mbi = MBI()
    if k.VirtualQueryEx(h, a, ctypes.byref(mbi), ctypes.sizeof(mbi)):
        regions[mbi.BaseAddress] = mbi.RegionSize
with open(os.path.join(RES, 'import_stubs.bin'), 'wb') as f, open(os.path.join(RES, 'import_stubs.txt'), 'w') as t:
    for base, size in sorted(regions.items()):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        ok = k.ReadProcessMemory(h, base, buf, size, ctypes.byref(got))
        t.write(f'{base:#x} {size:#x} {f.tell():#x} {"read" if ok else "failed"}\n')
        f.write(buf.raw[:size])
        print(f'region {base:#x} size {size:#x}: {"read" if ok else "failed %d" % ctypes.get_last_error()}')
print(len(stubs), 'stubs, from', hex(stubs[0]), 'to', hex(stubs[-1]))
