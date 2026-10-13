"""The header bits of a 13.3 packet that the client's reader never takes a field from ("spare"): what the real server
writes there, and what our encoder writes there. Our schema encoder leaves them 0; Riot's server sets them (518 and
770: always bit 7, 286: always 0x85 ...). A client may well look at them after the reader is done.

  spare_bits.py <pid> [<pid> ...]     per packet id: header size, used bits, the spare values of the real stream
  spare_bits.py write                 data/exe133/spare_bits.json for the ids our world writes (modal value per id)
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
import pkt_schema as PS  # noqa: E402
import rofl_packets as R  # noqa: E402

OUT = os.path.join(ROOT, 'data', 'exe133', 'spare_bits.json')
WORLD_IDS = [98, 506, 387, 518, 770, 286, 263, 61, 740, 606]


def layout(pid):
    """(header bytes, mask of the bits an inline field uses, over all header bytes) of a packet id's root struct"""
    sc = PS.Schema.load(pid)
    root = sc.structs[sc.root]
    hdr = root.get('header', 1)
    mask = 0
    for f in root['fields']:
        if f.get('inline'):
            for b in range(f['bit'], f['bit'] + f['width']):
                mask |= 1 << b
    return hdr, mask


def real_values(pids):
    r = R.Rofl(os.path.join(ROOT, 'data', 'rofl', 'KR-6363178603_13.3.rofl'))
    lay = {p: layout(p) for p in pids}
    hist = {p: collections.Counter() for p in pids}
    for e, (t, ch, pid, obj, body) in R.stream(r):
        if pid in hist and len(body) >= lay[pid][0]:
            hdr, mask = lay[pid]
            v = int.from_bytes(body[:hdr], 'little')
            hist[pid][v & ~mask & ((1 << (8 * hdr)) - 1)] += 1
    return lay, hist


def main():
    a = sys.argv[1:]
    if a[:1] == ['write']:
        lay, hist = real_values(WORLD_IDS)
        out = {}
        for p in WORLD_IDS:
            hdr, mask = lay[p]
            top = hist[p].most_common(3)
            out[str(p)] = dict(header=hdr, used=mask, spare=top[0][0] if top else 0,
                               share=round(top[0][1] / max(sum(hist[p].values()), 1), 4) if top else 0)
            print(p, out[str(p)], top)
        json.dump(out, open(OUT, 'w'), indent=1)
        return
    pids = [int(x) for x in a] or WORLD_IDS
    lay, hist = real_values(pids)
    for p in pids:
        hdr, mask = lay[p]
        print(p, 'header', hdr, 'bytes; used mask', format(mask, 'b'), '; real spare values:',
              [(hex(k), v) for k, v in hist[p].most_common(4)])


if __name__ == '__main__':
    main()
