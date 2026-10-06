"""Disassembles League's compiled DX11 shaders (the DXBC blobs inside ShaderCache.dx11.wad.client entries) with
Microsoft's own D3DDisassemble (d3dcompiler_47.dll, part of Windows), to read the exact math Riot's shaders do.

    python tools/disassemble_shaders.py <raw entry file> <out folder> [filter text]

Each DXBC blob of the entry (one per macro permutation) is written as <n>.asm; with a filter, only blobs whose
disassembly contains it are kept.
"""
import ctypes
import os
import struct
import sys


def blobs(data):
    at = 0
    while True:
        at = data.find(b'DXBC', at)
        if at < 0:
            return
        size = struct.unpack_from('<I', data, at + 24)[0]
        if size <= 32 or at + size > len(data):
            at += 4
            continue
        yield at, data[at:at + size]
        at += size


def disassemble(dll, blob):
    out = ctypes.c_void_p()
    hr = dll.D3DDisassemble(blob, len(blob), 0, None, ctypes.byref(out))
    if hr != 0 or not out.value:
        return None
    # ID3DBlob: vtable[3] = GetBufferPointer, vtable[4] = GetBufferSize, vtable[2] = Release
    vt = ctypes.cast(ctypes.cast(out, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    get_ptr = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(vt[3])
    get_size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(vt[4])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt[2])
    text = ctypes.string_at(get_ptr(out), get_size(out)).decode('latin-1').rstrip('\0')
    release(out)
    return text


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    want = sys.argv[3] if len(sys.argv) > 3 else None
    dll = ctypes.WinDLL('d3dcompiler_47.dll')
    dll.D3DDisassemble.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    data = open(src, 'rb').read()
    os.makedirs(out_dir, exist_ok=True)
    n = kept = 0
    for at, blob in blobs(data):
        text = disassemble(dll, blob)
        n += 1
        if text is None or (want and want not in text):
            continue
        open(os.path.join(out_dir, f'{n:04d}.asm'), 'w').write(text)
        kept += 1
    print(f'{n} blobs, {kept} written')


if __name__ == '__main__':
    main()
