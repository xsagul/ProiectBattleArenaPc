"""A third-party library inside the client, found from its public source: every C / C++ file of the library is
compiled with one of our compilers and each resulting function is compared, byte by byte, with the client's functions
(as tools/match_libs.py does for the runtime libraries: bytes under relocations left out, the function must start at
a function start of the client and end where that function ends).

  match_objs.py [--msvc <toolchain dir name>] <label> <source files glob | @list file> [cl flags ...]   default flags: -O2
      -> also client-src/lib_<label>.src: object name -> its source file
      --msvc: another compiler than Riot's own, for libraries the client got prebuilt (e.g. msvc-14.16.27048)
      -> client-src/obj/<label>/*.obj and client-src/lib_<label>.tsv (rva, bytes, object, symbol, client addresses
         with this match)

Example:  match_objs.py lua515 "data/libsrc/lua-5.1.5/src/*.c" -O2
"""
import collections
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import match_libs as L  # noqa: E402


def place(objects, min_fixed=8):
    """objects: (object name, COFF bytes). -> {client rva: [(size, object, symbol)]}, functions tried."""
    import packet_emu as P
    img = bytes(P.IMG)
    starts = sorted(M.starts())
    startset = set(starts)
    indexes = {}

    def index(k):
        if k not in indexes:
            indexes[k] = collections.defaultdict(list)
            for s in starts:
                indexes[k][img[s + k:s + k + 4]].append(s)
        return indexes[k]
    found, tried = {}, 0
    for name, body in objects:
        for sym, code, rel in L.functions(body):
            keep = [i for i in range(len(code)) if i not in rel]
            k = next((i for i in range(len(code) - 3) if not rel & {i, i + 1, i + 2, i + 3}), None)
            if len(keep) < min_fixed or k is None or k > 64:
                continue
            tried += 1
            for s in index(k).get(code[k:k + 4], ()):
                e = s + len(code)
                if all(img[s + i] == code[i] for i in keep) and (e in startset or img[e] == 0xcc):
                    found.setdefault(s, []).append((len(code), name, sym))
    return found, tried


def main():
    args = sys.argv[1:]
    cl, vc_include = M.CL, os.path.join(M.MSVC, 'include')
    if args[0] == '--msvc':
        base = glob.glob(os.path.join(ROOT, 'toolchain', args[1], 'VC', 'Tools', 'MSVC', '*'))[0]
        cl = glob.glob(os.path.join(base, 'bin', 'Host*', 'x86', 'cl.exe'))[0]
        vc_include = os.path.join(base, 'include')
        args = args[2:]
    label, pattern = args[0], args[1]
    flags = args[2:] or ['-O2']
    out = os.path.join(ROOT, 'client-src', 'obj', label)
    os.makedirs(out, exist_ok=True)
    include = [vc_include] + [os.path.join(M.SDK, d) for d in ('ucrt', 'shared', 'um')]
    env = dict(os.environ, INCLUDE=';'.join(os.path.abspath(d) for d in include if os.path.isdir(d)))
    objects, failed = [], []
    if pattern.startswith('@'):              # a file listing the sources, one path per line (relative to ROOT)
        srcs = [os.path.join(ROOT, x.strip()) for x in open(os.path.join(ROOT, pattern[1:])) if x.strip()]
    else:
        srcs = sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True))
    names = collections.Counter(os.path.basename(x) for x in srcs)
    where = {}
    for src in srcs:
        b = os.path.basename(src)
        if names[b] > 1:                    # the same file name in several directories: the object takes the path
            b = os.path.relpath(src, os.path.commonpath(srcs)).replace(os.sep, '_').replace('/', '_')
        obj = os.path.join(out, os.path.splitext(b)[0] + '.obj')
        where[os.path.basename(obj)] = os.path.relpath(src, ROOT).replace(os.sep, '/')
        r = subprocess.run([cl, '/nologo', '/c', *flags, '/Fo' + obj, src], capture_output=True, text=True, env=env)
        if r.returncode:
            failed.append(os.path.basename(src) + ': ' + (r.stdout.strip().splitlines() or ['?'])[-1][:100])
            continue
        objects.append((os.path.basename(obj), open(obj, 'rb').read()))
    found, tried = place(objects)
    places = collections.Counter(max(v)[2] for v in found.values())
    path = os.path.join(ROOT, 'client-src', f'lib_{label}.tsv')
    with open(os.path.join(ROOT, 'client-src', f'lib_{label}.src'), 'w', newline=chr(10)) as f:
        f.write(''.join(f'{o}{chr(9)}{w}{chr(10)}' for o, w in sorted(where.items())))
    with open(path, 'w', newline='\n') as f:
        f.write('# rva\tbytes\tobject\tsymbol\tclient addresses with this match\n')
        for s in sorted(found):
            size, name, sym = max(found[s])
            f.write(f'{s:x}\t{size}\t{name}\t{sym}\t{places[sym]}\n')
    for line in failed[:8]:
        print('  not compiled:', line)
    total = sum(max(v)[0] for v in found.values())
    sure = sum(1 for v in found.values() if places[max(v)[2]] == 1)
    print(f'{label} {" ".join(flags)}: {len(objects)} objects ({len(failed)} did not compile), {tried} functions tried, '
          f'{len(found)} client functions matched ({sure} at one place only), {total} bytes -> {path}')


if __name__ == '__main__':
    main()
