"""Every replay packet of one id decoded through Riot's reader (pkt_schema decode), one JSON line each:
{"t": game time, "obj": net id, "v": values}. Output: data/exe133/codec/<id>.all.jsonl

  pkt_dump_all.py <id> [max]
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
import packet_emu as P  # noqa: E402
import pkt_schema as S  # noqa: E402
import pkt_tree as PT  # noqa: E402


def main(pid, most=None):
    sc = S.Schema.load(pid)
    T = PT.Tree(pid)
    allp = []
    P.KINDS, P.ENTRY = (2,), 1
    allp += [(t, obj, b) for t, ch, p_, obj, b in P.packets(P.ROFL, pid)]
    P.KINDS, P.ENTRY = (1,), None
    allp += [(t, obj, b) for t, ch, p_, obj, b in P.packets(P.ROFL, pid)]
    if most:
        allp = allp[:most]
    out = os.path.join(S.OUT, f'{pid}.all.jsonl')
    with open(out, 'w') as f:
        for i, (t, obj, body) in enumerate(allp):
            v = S.decode(T, sc, struct.pack('<HI', pid, obj) + body)
            f.write(json.dumps({'t': t, 'obj': obj, 'v': v}) + '\n')
            if i % 1000 == 0:
                print(i, len(allp), flush=True)
    print('written', out, len(allp))


if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else None)
