"""Name the packer's import stubs of the 16.20 exe from a memory image.

    python tools/resolve_imports64.py <image.bin> <out.txt> [pid]

Each stub (64 bytes, in .riot1) loads two numbers and asks the packer's resolver for an
address, then jumps to it. The stub is run in Unicorn on the image; the address it would
jump to is looked up in the image's own import table (names + filled address table).
With a pid, pages outside the image are read from the live process on demand (read-only).
"""
import ctypes, ctypes.wintypes as wt, struct, sys
import unicorn
from unicorn import x86_const as X

img = bytearray(open(sys.argv[1], "rb").read())
out_path = sys.argv[2]
pid = int(sys.argv[3]) if len(sys.argv) > 3 else 0
BASE = int(open(sys.argv[1][:-4] + "_pages.txt").readline().split()[1], 16)
PAGE = 0x1000


def u32(r): return struct.unpack_from("<I", img, r)[0]
def u64(r): return struct.unpack_from("<Q", img, r)[0]
def cstr(r): return bytes(img[r:img.index(b"\0", r)]).decode("latin1")


def sections():
    pe = u32(0x3c)
    n, opt = struct.unpack_from("<H", img, pe + 6)[0], struct.unpack_from("<H", img, pe + 20)[0]
    res = {}
    for i in range(n):
        name, vs, va = struct.unpack_from("<8sII", img, pe + 24 + opt + i * 40)
        res[name.rstrip(b"\0").decode()] = (va, vs)
    return res, pe


SECS, PE = sections()


def import_table():
    """address -> (dll, name), and slot rva -> (dll, name)"""
    rva = u32(PE + 24 + 112 + 8)
    by_addr, by_slot = {}, {}
    while True:
        ilt, _, _, name, iat = struct.unpack_from("<IIIII", img, rva)
        if not name and not iat:
            break
        dll, k = cstr(name), 0
        while u64(ilt + k * 8):
            v = u64(ilt + k * 8)
            fn = f"#{v & 0xffff}" if v >> 63 else cstr(v + 2)
            by_addr.setdefault(u64(iat + k * 8), (dll, fn))
            by_slot[iat + k * 8] = (dll, fn)
            k += 1
        rva += 20
    return by_addr, by_slot


def stubs():
    """(slot rva in .rdata, stub rva) for every .rdata pointer into .riot1"""
    r0, rs = SECS[".rdata"]
    a, s = SECS[".riot1"]
    res = []
    for o in range(r0, r0 + rs - 7, 8):
        p = u64(o) - BASE
        if a <= p < a + s:
            res.append((o, p))
    return res


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_ulonglong, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
HPROC = k32.OpenProcess(0x0410, False, pid) if pid else None


def live_page(addr):
    if not HPROC:
        return None
    buf, got = ctypes.create_string_buffer(PAGE), ctypes.c_size_t()
    return buf.raw if k32.ReadProcessMemory(HPROC, addr, buf, PAGE, ctypes.byref(got)) else None


STACK = 0x0000_7000_0000_0000
EXIT = 0x0000_7100_0000_0000


def run_stub(rva):
    mu = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_64)
    size = (len(img) + PAGE - 1) & ~(PAGE - 1)
    mu.mem_map(BASE, size)
    mu.mem_write(BASE, bytes(img))
    mu.mem_map(STACK, 0x40000)
    mu.mem_map(EXIT, PAGE)
    sp = STACK + 0x30000
    mu.mem_write(sp, struct.pack("<Q", EXIT))
    mu.reg_write(X.UC_X86_REG_RSP, sp)
    note = []

    def unmapped(uc, access, addr, sz, value, _):
        page = addr & ~(PAGE - 1)
        data = live_page(page)
        if data is None:
            note.append(f"unmapped {addr:#x}")
            return False
        uc.mem_map(page, PAGE)
        uc.mem_write(page, data)
        return True

    def code(uc, addr, sz, _):
        if not BASE <= addr < BASE + len(img):
            note.append(f"left image to {addr:#x}")
            uc.emu_stop()

    mu.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED, unmapped)
    mu.hook_add(unicorn.UC_HOOK_CODE, code)
    try:
        mu.emu_start(BASE + rva, 0, count=2_000_000)
    except unicorn.UcError as e:
        note.append(str(e))
    return mu.reg_read(X.UC_X86_REG_RIP), mu.reg_read(X.UC_X86_REG_RAX), note


def main():
    by_addr, by_slot = import_table()
    rows, named = [], 0
    for slot, stub in stubs():
        rip, rax, note = run_stub(stub)
        hit = by_addr.get(rip) or by_addr.get(rax)
        if hit:
            named += 1
            rows.append(f"{slot:08x} {stub:08x} {hit[0]}!{hit[1]}")
        elif BASE <= rip < BASE + len(img):
            rows.append(f"{slot:08x} {stub:08x} ?  stopped at rva {rip - BASE:#x} rax {rax:#x} {'; '.join(note)}")
        else:
            rows.append(f"{slot:08x} {stub:08x} ?  target {rip:#x} {'; '.join(note)}")
    open(out_path, "w").write("\n".join(rows) + "\n")
    print(f"stubs {len(rows)}, named {named}, direct imports in table {len(by_slot)}")


if __name__ == "__main__":
    main()
