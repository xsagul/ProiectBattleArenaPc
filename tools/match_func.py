"""Compile one reconstructed source file with Riot's compiler (toolchain/msvc-14.32.31328, see get_msvc.py) and compare
one function of the object file, byte by byte, with the same function in the unpacked 13.3 client.

Bytes covered by a relocation in our object (absolute addresses, call targets) are left out of the byte comparison;
everything else has to be identical. Where the client's target has a name in client-src/names.tsv (library code,
imports, functions named by hand), the symbol ours names there has to be the same one, and a constant of
ours (string literal, floating-point value) has to have the client's bytes. The result is the number of identical bytes and, where they differ, the two
disassemblies side by side from the first difference.

  match_func.py <source.cpp> <symbol text> <rva hex> [cl flags ...]     default flags: -O2 -std:c++17 (in Git Bash write flags with -, /O2 becomes a path)
"""
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
MSVC = os.path.join(ROOT, 'toolchain', 'msvc-14.32.31328', 'VC', 'Tools', 'MSVC', '14.32.31326')
CL = os.path.join(MSVC, 'bin', 'Hostx64', 'x86', 'cl.exe')
# the options measured so far on rebuilt functions (docs/MIGRARE_12.23.md): speed optimisation, frame pointer omitted,
# SSE2, no exception handling, C++17 (the transport's queue needs its aligned operator new)
FLAGS = ['-O2', '-std:c++17']
# the Windows SDK whose static C runtime is in the client (ucrt objects of compiler build 27412; tools/get_winsdk.py)
SDK = os.path.join(ROOT, 'toolchain', 'winsdk-10.0.19041', 'Windows Kits', '10', 'Include', '10.0.19041.0')
OUT = os.path.join(ROOT, 'client-src', 'obj')


def file_flags(src):
    """The cl options of a source: a line `// flags: ...` (libraries with their own build options), else FLAGS."""
    import re
    m = re.search(r'^// flags: (.*)$', open(src, encoding='utf-8', errors='replace').read(4000), re.M)
    return m[1].split() if m else FLAGS


def compiler_of(src):
    """(cl.exe, its include dir) for a source: Riot's own compiler, or the toolset a line
    `// compiler: <toolchain dir name>` names (libraries the client got prebuilt with another MSVC build)."""
    import re
    head = open(src, encoding='utf-8', errors='replace').read(4000)
    m = re.search(r'^// compiler: (\S+)', head, re.M)
    if not m:
        return CL, os.path.join(MSVC, 'include')
    import glob
    base = glob.glob(os.path.join(ROOT, 'toolchain', m[1], 'VC', 'Tools', 'MSVC', '*'))[0]
    return glob.glob(os.path.join(base, 'bin', 'Host*', 'x86', 'cl.exe'))[0], os.path.join(base, 'include')


def compile_obj(src, flags):
    import hashlib
    os.makedirs(OUT, exist_ok=True)
    tag = hashlib.sha1((os.path.abspath(src) + ' '.join(flags)).encode()).hexdigest()[:8]
    obj = os.path.join(OUT, os.path.splitext(os.path.basename(src))[0] + '_' + tag + '.obj')
    cl, vc_include = compiler_of(src)
    include = [vc_include] + [os.path.join(SDK, d) for d in ('ucrt', 'shared', 'um')]
    env = dict(os.environ, INCLUDE=';'.join(os.path.abspath(d) for d in include if os.path.isdir(d)))
    r = subprocess.run([cl, '/nologo', '/c', *flags, '/Fo' + obj, src], capture_output=True, text=True, env=env,
                       cwd=ROOT)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return obj


def function_of(obj, text):
    """(code bytes, set of relocated byte offsets) of the function whose symbol contains text."""
    d = open(obj, 'rb').read()
    nsec, symptr, nsym = struct.unpack_from('<H', d, 2)[0], *struct.unpack_from('<II', d, 8)
    strtab = symptr + 18 * nsym

    def name(s):
        if s[:4] == b'\0\0\0\0':
            o = strtab + struct.unpack_from('<I', s, 4)[0]
            return d[o:d.index(b'\0', o)].decode()
        return s[:8].rstrip(b'\0').decode()
    syms, k = [], 0
    while k < nsym:
        s = d[symptr + 18 * k:symptr + 18 * k + 18]
        value, sec, typ, cls, aux = struct.unpack_from('<IhHBB', s, 8)
        syms.append((name(s), value, sec, typ, cls))
        k += 1 + aux
    hits = [s for s in syms if text in s[0] and s[3] == 0x20 and s[2] > 0
            and not (s[0].startswith('__') and '$' in s[0])]       # not EH funclets (__unwindfunclet$..., __ehhandler$...)
    exact = [s for s in hits if s[0] == text]
    hits = exact or hits
    if len(hits) != 1:
        raise SystemExit(f'{len(hits)} functions contain "{text}": {[h[0] for h in hits]}')
    fname, value, sec, _, _ = hits[0]
    h = 20 + struct.unpack_from('<H', d, 16)[0] + 40 * (sec - 1)
    size, raw, relptr = struct.unpack_from('<III', d, h + 16)
    nrel = struct.unpack_from('<H', d, h + 32)[0]
    end = min([s[1] for s in syms if s[2] == sec and s[3] == 0x20 and s[1] > value] + [size])
    rel = set()
    TARGETS.clear()
    CONSTANTS.clear()
    for i in range(nrel):
        off, symidx, typ = struct.unpack_from('<IIH', d, relptr + 10 * i)
        if value <= off < end:
            rel.update(range(off - value, off - value + 4))
            sym = d[symptr + 18 * symidx:symptr + 18 * symidx + 18]
            TARGETS[off - value] = (typ, name(sym))
            # a constant of ours (string literal, floating-point value): its bytes, to compare with the client's
            ssec = struct.unpack_from('<h', sym, 12)[0]
            if ssec > 0 and struct.unpack_from('<I', sym, 8)[0] == 0:
                sh = 20 + struct.unpack_from('<H', d, 16)[0] + 40 * (ssec - 1)
                ssize, sraw = struct.unpack_from('<II', d, sh + 16)
                snrel, sflags = struct.unpack_from('<H', d, sh + 32)[0], struct.unpack_from('<I', d, sh + 36)[0]
                if sflags & 0x1040 == 0x1040 and not sflags & 0x80000020 and not snrel and 0 < ssize <= 4096:
                    CONSTANTS[off - value] = d[sraw:sraw + ssize]
    return fname, d[raw + value:raw + end], rel


CONSTANTS = {}  # offset in the last function read -> bytes of the read-only constant addressed there
TARGETS = {}    # offset in the last function read -> (relocation type, symbol): what our code calls or addresses


def known_names():
    """rva -> the names a thing at that address may go by (client-src/names.tsv; for library code every library
    symbol with those bytes, client-src/lib_functions.tsv)."""
    if not hasattr(known_names, 'v'):
        known_names.v = {}
        for line in open(os.path.join(ROOT, 'client-src', 'names.tsv')):
            p = line.rstrip(chr(10)).split(chr(9))
            if len(p) == 3 and p[2] and p[1] != 'unfunc' and '__x' not in p[2]:
                known_names.v.setdefault(int(p[0], 16), set()).add(p[2])
        lib = os.path.join(ROOT, 'client-src', 'lib_functions.tsv')
        for line in open(lib) if os.path.exists(lib) else ():
            p = line.rstrip(chr(10)).split(chr(9))
            if line[0] != '#' and len(p) > 7 and p[7] == '1':
                known_names.v.setdefault(int(p[0], 16), set()).update(p[6].split(' '))
    return known_names.v


def rebuilt_symbols():
    """rva -> symbol texts of the "// match:" lines in client-src/src: the functions rebuilt so far."""
    if not hasattr(rebuilt_symbols, 'v'):
        import glob
        import re
        rebuilt_symbols.v = {}
        for src in sources():
            # "// same: <rva> <symbol>": another name of a rebuilt function (identical code folding gave several
            # functions of the source one address)
            for m in re.finditer(r'^// (?:match|same): ([0-9a-f]+) (\S+)', open(src, encoding='utf-8').read(), re.M):
                rebuilt_symbols.v.setdefault(int(m.group(1), 16), []).append(m.group(2))
    return rebuilt_symbols.v


def plain(name):
    """A symbol without the decorations that differ between an object file and the names table."""
    if name.startswith('__imp_'):
        name = name[6:]
    if '__1of' in name:
        name = name[:name.index('__1of')]
    if not name.startswith('?') and '@' in name:
        name = name[:name.index('@')]               # stdcall byte count
    return name.lstrip('_')


def same_thing(ours, theirs):
    core = plain(ours)
    for t in theirs:
        if plain(t) == core:
            return True
        # an import slot is named imp_<module>_<function>; kernel32's critical section calls are ntdll's Rtl ones
        if t.startswith('imp_') and (t.endswith('_' + core) or t.endswith('_Rtl' + core)):
            return True
    return False


def wrong_targets(rva, ours):
    """Relocated places where the client's code points at a named thing other than the one ours names."""
    import packet_emu as P
    out = []
    for off, (typ, sym) in sorted(TARGETS.items()):
        if off + 4 > len(ours):
            continue
        v = struct.unpack_from('<i', P.IMG, rva + off)[0]
        target = rva + off + 4 + v if typ == 0x14 else (v & 0xffffffff) - P.BASE if typ == 6 else None
        rebuilt = rebuilt_symbols().get(target)
        if rebuilt:                                 # a function we have rebuilt: ours must call that very symbol
            if not any(text in sym for text in rebuilt):
                out.append((off, sym, 'the rebuilt ' + rebuilt[0]))
            theirs = None
        else:
            theirs = known_names().get(target)
        if theirs and not same_thing(sym, theirs):
            out.append((off, sym, sorted(theirs)[0]))
        const = CONSTANTS.get(off)
        if const is not None and typ == 6:          # our code addresses the constant plus an offset (the addend)
            const = const[max(0, struct.unpack_from('<i', ours, off)[0]):]
        if const is not None and target is not None and bytes(P.IMG[target:target + len(const)]) != const:
            out.append((off, f'{sym[:40]} = {const[:24]!r}', f'{bytes(P.IMG[target:target + min(len(const), 24)])!r}'))
    return out


def symbol_addresses(rva, ours):
    """(symbol, client rva it stands for) for every relocation of the last function read: what the linker would have
    to put there for our code to be the client's. One symbol must come out at one address everywhere."""
    import packet_emu as P
    out = []
    for off, (typ, sym) in sorted(TARGETS.items()):
        if off + 4 > len(ours) or typ not in (6, 0x14):
            continue
        addend = struct.unpack_from('<i', ours, off)[0]
        v = struct.unpack_from('<i', P.IMG, rva + off)[0]
        target = rva + off + 4 + v if typ == 0x14 else (v & 0xffffffff) - P.BASE
        out.append((sym, target - addend))
    return out


def compare(src, text, rva, flags, obj=None):
    """(symbol, size, identical bytes, first difference or None, side-by-side text) for one function."""
    import packet_emu as P
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    fname, ours, rel = function_of(obj or compile_obj(src, flags), text)
    while ours and ours[-1] in (0xcc, 0x90) and len(ours) - 1 not in rel:   # padding after the function
        ours = ours[:-1]
    theirs = bytes(P.IMG[rva:rva + len(ours) + 64])
    same = sum(1 for i in range(len(ours)) if i in rel or ours[i] == theirs[i])
    first = next((i for i in range(len(ours)) if i not in rel and ours[i] != theirs[i]), None)
    if first is None and theirs[len(ours)] not in (0xcc, 0x90) and rva + len(ours) not in starts():
        first = len(ours)                                   # ours ends before Riot's function does
    if first is None:
        bad = wrong_targets(rva, ours)
        if bad:                                             # same bytes, but a call or address of something else
            lines = [f'  +{off:#x}: ours names {sym}, the client has {theirs} there' for off, sym, theirs in bad]
            return fname, len(ours), same, bad[0][0], 'same bytes, different targets:' + chr(10) + chr(10).join(lines)
        return fname, len(ours), same, None, ''
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def dis(code):
        return [(i.address, f'{i.mnemonic} {i.op_str}') for i in md.disasm(code, 0)]
    a, b = dis(ours), dis(theirs[:len(ours) + 32])
    show = max(first, int(os.environ.get('MATCH_FROM', '0'), 16))     # MATCH_FROM=<hex>: start the listing later
    k = max(0, max([n for n, x in enumerate(a) if x[0] <= show] or [0]) - 3)
    out = [f'{"ours":<48}Riot']
    for x, y in zip(a[k:k + 60], b[k:k + 60]):
        skip = x == y or any(x[0] + j in rel for j in range(1, 7))
        out.append(f'{x[0]:#6x} {x[1]:<40} {y[0]:#6x} {y[1]}' + ('' if skip else '   <<'))
    return fname, len(ours), same, first, chr(10).join(out)


def sources():
    """The reconstructed source files: C++ and C (libraries Riot compiled as C are included from .c files)."""
    import glob
    return sorted(glob.glob(os.path.join(ROOT, 'client-src', 'src', '**', '*.cpp'), recursive=True) +
                  glob.glob(os.path.join(ROOT, 'client-src', 'src', '**', '*.c'), recursive=True))


def starts():
    if not hasattr(starts, 'v'):
        starts.v = {int(x, 16) for x in open(os.path.join(ROOT, 'client-src', 'functions.txt')).read().split()}
    return starts.v


def main():
    src, text, rva = sys.argv[1], sys.argv[2], int(sys.argv[3], 16)
    flags = sys.argv[4:] or FLAGS
    fname, size, same, first, report = compare(src, text, rva, flags)
    print(f'{fname}  {" ".join(flags)}: {size} bytes, {same} identical'
          + ('  -> IDENTICAL' if first is None else f', first difference at +{first:#x}'))
    if report:
        print(report)
    return 0 if first is None else 1


if __name__ == '__main__':
    sys.exit(main())
