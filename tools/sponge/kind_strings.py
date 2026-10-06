"""Readable strings inside each packet kind of the decoded 13.3 replay (names of units, animations, spells, sounds).

  kind_strings.py > research/exe133/kind_strings.txt
A string = a run of 4+ printable bytes in one block of a packet, zero bytes the decoder left out filled back in.
"""
import collections
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decoded

RUN = re.compile(rb'[\x20-\x7e]{4,}')
per = collections.defaultdict(collections.Counter)
for r in decoded.packets():
    blocks = collections.defaultdict(dict)
    for b, off, h, hid in r.get('f', []):
        blocks[b][off] = bytes.fromhex(h)
    for b, fs in blocks.items():
        size = max(o + len(v) for o, v in fs.items())
        if size > 1 << 16:
            continue
        buf = bytearray(size)
        for o, v in fs.items():
            buf[o:o + len(v)] = v
        for m in RUN.finditer(bytes(buf)):
            s = m.group(0).decode()
            if re.search(r'[A-Za-z]{3}', s):
                per[r['id']][s] += 1
for pid in sorted(per, key=lambda p: -sum(per[p].values())):
    c = per[pid]
    print(f'{pid:4}  {len(c)} distinct, {sum(c.values())} total: ' + ' | '.join(f'{s[:40]} x{n}' for s, n in c.most_common(25)))
