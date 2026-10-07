"""The score of the source reconstruction: every function of client-src/src/ compiled with Riot's compiler and compared
with the unpacked 13.3 client (match_func.py). A source file names its functions in comment lines:

  // match: <rva hex> <symbol text> [cl flags, default match_func.FLAGS]

  match_all.py            the table and the score; also writes client-src/symbols.tsv (our symbol -> client address)
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import match_func as M  # noqa: E402


def main():
    rows, objs, where = [], {}, {}
    for src in M.sources():
        for m in re.finditer(r'^// match: ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
            flags = m.group(3).split() or M.file_flags(src)
            key = (src, tuple(flags))
            if key not in objs:
                objs[key] = M.compile_obj(src, flags)
            fname, size, same, first, _ = M.compare(src, m.group(2), int(m.group(1), 16), flags, objs[key])
            if first is None:
                code = M.function_of(objs[key], m.group(2))[1]
                for sym, at in M.symbol_addresses(int(m.group(1), 16), code):
                    where.setdefault(sym, {}).setdefault(at, []).append(int(m.group(1), 16))
                where.setdefault(fname, {}).setdefault(int(m.group(1), 16), []).append(int(m.group(1), 16))
            rows.append((int(m.group(1), 16), os.path.basename(src), fname, size, same, first))
    done = 0
    for rva, src, fname, size, same, first in sorted(rows):
        done += first is None
        print(f'{rva:#9x}  {size:5d} B  {"identical" if first is None else f"{same}/{size}, differs at +{first:#x}":<28} {src}  {fname[:64]}')
    # every symbol our identical functions use must stand for one client address; the table is the link map a build
    # of these sources against the client needs
    clash = {s: a for s, a in where.items() if len(a) > 1}
    with open(os.path.join(M.ROOT, 'client-src', 'symbols.tsv'), 'w', newline=chr(10)) as f:
        f.write('# symbol in our objects' + chr(9) + 'client rva' + chr(9) + 'uses' + chr(10))
        for sym in sorted(where):
            for at, uses in sorted(where[sym].items()):
                f.write(f'{sym}{chr(9)}{at:x}{chr(9)}{len(uses)}{chr(10)}')
    for sym, a in sorted(clash.items()):
        print(f'  one symbol, several client addresses: {sym[:70]} -> ' + ', '.join(f'{at:#x} (in {uses[0]:#x})' for at, uses in sorted(a.items())))
    print(f'{len(where)} symbols placed at client addresses, {len(clash)} of them at more than one')
    print(f'{done} of {len(rows)} reconstructed functions identical; {len(M.starts())} functions in the client')
    return 0 if done == len(rows) else 1


if __name__ == '__main__':
    sys.exit(main())
