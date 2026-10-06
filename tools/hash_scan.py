"""Which packet kinds carry which named hashes: up to N packets of every kind in the replay, deserialized by Riot's
reader in the emulator (packet_emu), every 4-byte window of every field in clear looked up in name_hashes.json
(restricted by a regex on the name, e.g. particles). Prints per kind the names found.

  hash_scan.py <name regex> [per kind=25]
"""
import collections
import json
import re
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import packet_emu as P  # noqa: E402
import name_hashes as N  # noqa: E402


T0, T1 = float(os.environ.get('T0', 0)), float(os.environ.get('T1', 1e9))


def main(rx, per):
    d = json.load(open(N.OUT))
    want = {}
    r = re.compile(rx)
    for k, v in d.items():
        if r.search(v):
            want[int(k[4:], 16)] = (k[:3], v)
    print(len(want), 'names', flush=True)
    t = P.table()
    emu = P.Emu()
    seen = collections.Counter()
    found = collections.defaultdict(collections.Counter)
    for tm, ch, pid, obj, body in P.packets(P.ROFL):
        if seen[pid] >= per or pid not in t or not (T0 <= tm <= T1):
            continue
        seen[pid] += 1
        tr = {}
        try:
            emu.deserialize(t[pid], pid, obj, body, tr)
            blocks = P.decoded_blocks(emu, tr)
        except Exception:
            continue
        for name, flds in blocks:
            for off, plain, hid, k in flds:
                for i in range(len(plain) - 3):
                    v = struct.unpack_from('<I', plain, i)[0]
                    if v in want:
                        found[pid][(name.split(',')[0], off + i) + want[v]] += 1
        if sum(seen.values()) % 500 == 0:
            print(sum(seen.values()), 'packets', len(seen), 'kinds', flush=True)
    for pid in sorted(found):
        print(pid, seen[pid], 'packets')
        for k, n in found[pid].most_common(8):
            print('   ', n, k)


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 25)
