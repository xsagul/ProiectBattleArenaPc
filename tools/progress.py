"""Where the source reconstruction of the 13.3 client stands, in functions and in bytes of code:
  - rebuilt: functions of client-src/src/ that compile to the client's bytes (tools/match_all.py);
  - library: functions identical to one of the static runtime libraries (tools/match_libs.py), split into those found
    at one place only and those whose code shape occurs at several places (template code, name not certain);
  - the rest.
A function's size is the distance to the next start in client-src/functions.txt, less trailing int3 padding.

  progress.py
"""
import bisect
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
import match_func as M  # noqa: E402
import packet_emu as P  # noqa: E402

TEXT1 = 0x1000 + 0xfa96ec


def main():
    img = bytes(P.IMG)
    starts = sorted(M.starts())

    def size(rva):
        k = bisect.bisect_right(starts, rva)
        end = starts[k] if k < len(starts) else TEXT1
        while end > rva and img[end - 1] == 0xcc:
            end -= 1
        return end - rva
    total = sum(size(s) for s in starts)
    rebuilt, open_ = {}, {}
    objs = {}
    for src in M.sources():
        for m in re.finditer(r'^// match: ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
            flags = m.group(3).split() or M.file_flags(src)
            key = (src, tuple(flags))
            if key not in objs:
                objs[key] = M.compile_obj(src, flags)
            rva = int(m.group(1), 16)
            _, n, same, first, _ = M.compare(src, m.group(2), rva, flags, objs[key])
            (rebuilt if first is None else open_)[rva] = n
    unique, shaped = {}, {}
    lib = os.path.join(ROOT, 'client-src', 'lib_functions.tsv')
    for line in open(lib) if os.path.exists(lib) else ():
        p = line.rstrip('\n').split('\t')
        if line[0] != '#' and int(p[0], 16) not in rebuilt:
            (unique if p[7] == '1' else shaped)[int(p[0], 16)] = int(p[1])
    rows = [('rebuilt, identical to the client', rebuilt), ('rebuilt, not identical yet', open_),
            ('library code, found at one place', unique), ('library-shaped code, several places', shaped)]
    done = set()
    print(f'{"":<38}{"functions":>10}{"bytes":>12}{"of the code":>13}')
    for name, d in rows:
        d = {k: v for k, v in d.items() if k not in done}
        done |= set(d)
        b = sum(d.values())
        print(f'{name:<38}{len(d):>10}{b:>12}{100 * b / total:>12.2f}%')
    rest = [s for s in starts if s not in done]
    b = sum(size(s) for s in rest)
    print(f'{"not looked at":<38}{len(rest):>10}{b:>12}{100 * b / total:>12.2f}%')
    print(f'{"all":<38}{len(starts):>10}{total:>12}')


if __name__ == '__main__':
    main()
