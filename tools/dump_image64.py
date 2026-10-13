"""Dump the main module image of a running 64-bit game process, read-only.

    python tools/dump_image64.py <pid> <out-prefix>

Writes <out-prefix>.bin (SizeOfImage bytes, unreadable pages zero filled) and
<out-prefix>_pages.txt (one line per region: rva, size, state, protection, readable).
Refuses to run while the Vanguard driver (vgk) is loaded.
"""
import ctypes, ctypes.wintypes as wt, struct, subprocess, sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_INFORMATION, PROCESS_VM_READ = 0x0400, 0x0010
MEM_COMMIT = 0x1000
PAGE_NOACCESS, PAGE_GUARD = 0x01, 0x100
PROT = {0x01: "---", 0x02: "r--", 0x04: "rw-", 0x08: "rwc", 0x10: "--x", 0x20: "r-x", 0x40: "rwx", 0x80: "rwcx"}


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_ulonglong), ("AllocationBase", ctypes.c_ulonglong),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.WORD), ("_pad", wt.WORD),
                ("RegionSize", ctypes.c_ulonglong), ("State", wt.DWORD), ("Protect", wt.DWORD),
                ("Type", wt.DWORD), ("_pad2", wt.DWORD)]


class MODINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p), ("SizeOfImage", wt.DWORD), ("EntryPoint", ctypes.c_void_p)]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_ulonglong, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
psapi.EnumProcessModules.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p), wt.DWORD, ctypes.POINTER(wt.DWORD)]
psapi.GetModuleInformation.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MODINFO), wt.DWORD]


def vanguard_loaded():
    out = subprocess.run(["sc", "query", "vgk"], capture_output=True, text=True).stdout
    return "RUNNING" in out


def read(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, addr, buf, size, ctypes.byref(got))
    return buf.raw[:got.value] if ok else None


def main():
    pid, prefix = int(sys.argv[1]), sys.argv[2]
    if vanguard_loaded():
        sys.exit("vgk is loaded: not touching the game process")
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        sys.exit(f"OpenProcess failed: {ctypes.get_last_error()}")
    mod = ctypes.c_void_p()
    need = wt.DWORD()
    if not psapi.EnumProcessModules(h, ctypes.byref(mod), ctypes.sizeof(mod), ctypes.byref(need)):
        sys.exit(f"EnumProcessModules failed: {ctypes.get_last_error()}")
    mi = MODINFO()
    psapi.GetModuleInformation(h, mod, ctypes.byref(mi), ctypes.sizeof(mi))
    base, size = mi.lpBaseOfDll, mi.SizeOfImage
    print(f"base {base:#x} size {size:#x} entry rva {mi.EntryPoint - base:#x}")
    image = bytearray(size)
    lines = [f"base {base:#x} size {size:#x}"]
    addr, readable, locked = base, 0, 0
    mbi = MBI()
    while addr < base + size:
        if not k32.VirtualQueryEx(h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        end = min(mbi.BaseAddress + mbi.RegionSize, base + size)
        n = end - addr
        ok = 0
        if mbi.State == MEM_COMMIT and not mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD):
            for off in range(0, n, 0x1000):
                page = read(h, addr + off, 0x1000)
                if page and len(page) == 0x1000:
                    image[addr - base + off:addr - base + off + 0x1000] = page
                    ok += 1
        readable += ok
        locked += n // 0x1000 - ok
        lines.append(f"{addr - base:08x} {n:08x} state {mbi.State:#x} prot {PROT.get(mbi.Protect & 0xff, hex(mbi.Protect))} read {ok}/{n // 0x1000}")
        addr = end
    open(prefix + ".bin", "wb").write(image)
    open(prefix + "_pages.txt", "w").write("\n".join(lines) + "\n")
    print(f"pages readable {readable}, not readable {locked}, regions {len(lines) - 1}")


if __name__ == "__main__":
    main()
