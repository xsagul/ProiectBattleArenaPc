"""Where the source reconstruction of the 13.3 client stands, in functions and in bytes of code:
  - rebuilt: functions of client-src/src/ that compile to the client's bytes (tools/match_all.py);
  - library: functions identical to one of the static runtime libraries (tools/match_libs.py), split into those found
    at one place only and those whose code shape occurs at several places (template code, name not certain);
  - the rest.
The code inventory uses the distances between index entries, less trailing int3 padding. Reconstructed bytes
use compiled function ranges: an internal index entry must not count the same bytes again, and a matched short
prefix must not hide the unmatched remainder. Function counts and index-entry counts need not sum together.

  progress.py [--audit <json file>]   optionally keep the exact failures from this same complete run
"""
import bisect
import argparse
import json
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
import code_coverage as C  # noqa: E402

TEXT1 = 0x1000 + 0xfa96ec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', help='JSON report of every nonidentical source claim from this run')
    args = parser.parse_args()
    img = bytes(P.IMG)
    starts = sorted(M.starts())

    def size(rva):
        k = bisect.bisect_right(starts, rva)
        end = starts[k] if k < len(starts) else TEXT1
        while end > rva and img[end - 1] == 0xcc:
            end -= 1
        return end - rva
    index_ranges = [(s, s + size(s)) for s in starts]
    rebuilt, open_ = {}, {}
    failures = []
    # every (source, options) pair compiled once: side by side, and not at all when nothing it reads has changed
    wanted = []
    for src in M.sources():
        for m in re.finditer(r'^// match: ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
            wanted.append((src, tuple(m.group(3).split() or M.file_flags(src))))
    objs = M.compile_many(wanted)
    for src in M.sources():
        for m in re.finditer(r'^// match: ([0-9a-f]+) (\S+)(.*)$', open(src, encoding='utf-8').read(), re.M):
            flags = m.group(3).split() or M.file_flags(src)
            key = (src, tuple(flags))
            rva = int(m.group(1), 16)
            symbol, n, same, first, detail = M.compare(src, m.group(2), rva, flags, objs[key])
            (rebuilt if first is None else open_)[rva] = n
            if first is not None:
                failures.append(dict(source=os.path.abspath(src), rva=hex(rva), symbol=symbol, flags=flags,
                                     bytes=n, identical_bytes=same, first_difference=first, detail=detail))
    unique, shaped = {}, {}
    lib = os.path.join(ROOT, 'client-src', 'lib_functions.tsv')
    for line in open(lib) if os.path.exists(lib) else ():
        p = line.rstrip('\n').split('\t')
        if line[0] != '#' and int(p[0], 16) not in rebuilt:
            (unique if p[7] == '1' else shaped)[int(p[0], 16)] = int(p[1])
    rows = [('rebuilt, identical to the client', rebuilt), ('rebuilt, not identical yet', open_),
            ('library code, found at one place', unique), ('library-shaped code, several places', shaped)]
    done, data = set(), []
    for name, d in rows:
        d = {k: v for k, v in d.items() if k not in done}
        done |= set(d)
        data.append((name, d))
    code_inventory = C.inventory(index_ranges, rebuilt, (0x1000, TEXT1))
    total = C.length(code_inventory)
    parts, remaining = C.partition(code_inventory, [d for name, d in data])
    print(f'{"":<38}{"functions":>10}{"bytes":>12}{"of the code":>13}')
    for (name, d), ranges in zip(data, parts):
        b = C.length(ranges)
        print(f'{name:<38}{len(d):>10}{b:>12}{100 * b / total:>12.2f}%')
    b = C.length(remaining)
    rest = C.entries_with_uncovered_bytes(index_ranges, remaining)
    print(f'{"uncovered (function index entries)":<38}{rest:>10}{b:>12}{100 * b / total:>12.2f}%')
    print(f'{"all (index + verified code)":<38}{len(starts):>10}{total:>12}')
    if args.audit:
        with open(args.audit, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(dict(identical_functions=len(rebuilt), nonidentical_functions=len(open_),
                           code_bytes=total, failures=failures), f, ensure_ascii=False, indent=2)
            f.write('\n')


if __name__ == '__main__':
    main()
