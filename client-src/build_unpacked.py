"""Builds the 13.3 client without its packer: an executable assembled from the decrypted code, that our own library
starts instead of stub.dll.

  build_unpacked.py [out.exe]     default C:\\Users\\Sorin\\Desktop\\ProiectBattleArenaPc\\game\\League of Legends.unpacked.exe
                                  also writes client-src/ba_host_imports.h (the import table for ba_host.dll)

What goes in:
  headers, .rdata, .data, .rodata, _RDATA, .rsrc   the file on disk (they are stored in clear)
  .text      the decrypted code from the memory image (client-src/exe_image_unpacked.bin). The packer relocated
             it to the base the game ran at (0x580000) and keeps the list of those fix-ups to itself, so the new file
             is fixed at that base: its data is relocated here once, with the file's own relocation table (which
             covers the data only), and the table is then switched off
  imports    the packer removed the import list; the file now imports one function, ba_host.dll!ba_start, which fills
             the game's 430 import slots (client-src/import_table.txt, read from the live process)
  entry      a 11-byte thunk in the old .stub section: call ba_start, then jump to the program's real entry point
             (rva 0xf40d33: `call __security_init_cookie; jmp __scrt_common_main_seh`, the only code of that shape
             nothing refers to)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe133')
GAME = r'C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game'
BASE_OLD, BASE_NEW = 0x400000, 0x580000
OEP = 0xf40d33

disk = bytearray(open(os.path.join(GAME, 'League of Legends.exe'), 'rb').read())
mem = open(os.path.join(RES, '..', '..', 'client-src', 'exe_image_unpacked.bin'), 'rb').read()
pe = struct.unpack_from('<I', disk, 0x3c)[0]
nsec = struct.unpack_from('<H', disk, pe + 6)[0]
opt = pe + 24
secs = []
for i in range(nsec):
    o = opt + struct.unpack_from('<H', disk, pe + 20)[0] + 40 * i
    name = bytes(disk[o:o + 8]).rstrip(b'\0').decode()
    vs, va, rs, ro = struct.unpack_from('<IIII', disk, o + 8)
    secs.append((name, va, vs, ro, rs, o))


def raw(rva):
    for name, va, vs, ro, rs, o in secs:
        if va <= rva < va + rs:
            return ro + rva - va
    return None


assert struct.unpack_from('<I', disk, opt + 28)[0] == BASE_OLD
# 1. the decrypted code
name, va, vs, ro, rs, _ = secs[0]
assert name == '.text'
disk[ro:ro + rs] = mem[va:va + rs]
# on disk the section is marked as code only (the packer sets the pages' access itself): readable and executable now
struct.pack_into('<I', disk, secs[0][5] + 36, 0x60000020)
# 2. the data, relocated once to the new base
delta = BASE_NEW - BASE_OLD
rdir, rsize = struct.unpack_from('<II', disk, opt + 96 + 8 * 5)
at, end, n, skipped = raw(rdir), raw(rdir) + rsize, 0, 0
while at < end:
    page, size = struct.unpack_from('<II', disk, at)
    if size == 0:
        break
    for i in range((size - 8) // 2):
        e = struct.unpack_from('<H', disk, at + 8 + 2 * i)[0]
        if e >> 12 != 3:
            continue
        rva = page + (e & 0xfff)
        assert not (va <= rva < va + rs), 'a relocation inside .text'
        f = raw(rva)
        if f is None:
            skipped += 1
            continue
        struct.pack_into('<I', disk, f, (struct.unpack_from('<I', disk, f)[0] + delta) & 0xffffffff)
        n += 1
    at += size
print(f'{n} data relocations applied (+{delta:#x}), {skipped} outside the file')
# how well that reproduces the running image: every page of .rdata must now equal the memory's, but for the import slots
name, va, vs, ro, rs, _ = secs[1]
diff = [p for p in range(0, min(vs, rs), 4096) if disk[ro + p:ro + p + 4096] != mem[va + p:va + p + 4096]]
print(f'.rdata pages that differ from the running image: {len(diff)} of {(min(vs, rs) + 4095) // 4096}', [hex(va + p) for p in diff[:8]])
# 3. the base is fixed
struct.pack_into('<I', disk, opt + 28, BASE_NEW)
ch = struct.unpack_from('<H', disk, pe + 22)[0]
struct.pack_into('<H', disk, pe + 22, ch | 0x0001)                       # IMAGE_FILE_RELOCS_STRIPPED
dll = struct.unpack_from('<H', disk, opt + 70)[0]
struct.pack_into('<H', disk, opt + 70, dll & ~0x0040)                    # no IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE
struct.pack_into('<II', disk, opt + 96 + 8 * 5, 0, 0)                    # no relocation directory
struct.pack_into('<II', disk, opt + 96 + 8 * 4, 0, 0)                    # the signature no longer holds: none
struct.pack_into('<I', disk, opt + 64, 0)                                # checksum
# 4. the old .stub section: the entry thunk and the one import
name, sva, svs, sro, srs, so = secs[-1]
assert name == '.stub'
stub = bytearray(srs)
T_CODE, T_DESC, T_ILT, T_IAT, T_DLL, T_HINT = 0x000, 0x040, 0x080, 0x090, 0x0a0, 0x0c0
slot_va = BASE_NEW + sva + T_IAT
code = b'\xff\x15' + struct.pack('<I', slot_va)                          # call dword ptr [ba_start]
code += b'\xe9' + struct.pack('<i', OEP - (sva + T_CODE + len(code) + 5))  # jmp the real entry point
stub[T_CODE:T_CODE + len(code)] = code
struct.pack_into('<IIIII', stub, T_DESC, sva + T_ILT, 0, 0, sva + T_DLL, sva + T_IAT)
struct.pack_into('<II', stub, T_ILT, sva + T_HINT, 0)
struct.pack_into('<II', stub, T_IAT, sva + T_HINT, 0)
stub[T_DLL:T_DLL + 12] = b'ba_host.dll\0'
stub[T_HINT:T_HINT + 11] = b'\0\0ba_start\0'
disk[sro:sro + srs] = stub
struct.pack_into('<I', disk, so + 8, 0x1000)                             # the section's virtual size
struct.pack_into('<II', disk, opt + 96 + 8 * 1, sva + T_DESC, 40)        # import directory
struct.pack_into('<II', disk, opt + 96 + 8 * 12, sva + T_IAT, 8)         # IAT directory
struct.pack_into('<I', disk, opt + 16, sva + T_CODE)                     # AddressOfEntryPoint
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME, 'League of Legends.unpacked.exe')
# the certificate table sat at the file's end: cut it off
cert = raw(sva) + srs
open(out, 'wb').write(disk[:cert])
print('written', out, cert, 'bytes; entry thunk at rva', hex(sva), '-> real entry', hex(OEP))
# the import table for ba_host.dll
rows = [l.split() for l in open(os.path.join(RES, '..', '..', 'client-src', 'import_table.txt')) if not l.startswith('#')]
with open(os.path.join(HERE, 'ba_host_imports.h'), 'w') as f:
    f.write('// generated by build_unpacked.py from client-src/import_table.txt: the game\'s import slots\n')
    f.write('static const struct { unsigned rva; const char* dll; const char* name; } kImports[] = {\n')
    for slot, dllname, fn in rows:
        f.write(f'  {{0x{slot}, "{dllname}", "{fn}"}},\n')
    f.write('};\n')
print(len(rows), 'imports -> ba_host_imports.h')
