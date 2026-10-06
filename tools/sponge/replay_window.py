"""Every replay packet in a time window, decoded through Riot's reader with the learnt schemas
(research/exe133/codec/<id>.tree.json), hashes named (name_hashes.py), floats shown, texts shown.

  replay_window.py <t0> <t1> [net id hex,...] [skip ids,...]
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import pkt_schema as S  # noqa: E402
import pkt_tree as PT  # noqa: E402
import name_hashes as N  # noqa: E402

NOISE = {595, 774, 367, 43, 730, 552, 387, 507, 506, 731, 703, 68, 623, 657, 779, 490, 588, 599}
_trees, _schemas = {}, {}


def pretty(x):
    if isinstance(x, dict):
        if 'text' in x:
            try:
                return repr(bytes.fromhex(x['text']).decode())
            except UnicodeDecodeError:
                return x['text']
        return '{' + ', '.join(f'{k} {pretty(v)}' for k, v in x.items()) + '}'
    if isinstance(x, list):
        return '[' + ', '.join(pretty(v) for v in x) + ']'
    if isinstance(x, str) and len(x) == 8:
        h = int.from_bytes(bytes.fromhex(x), 'little')
        if 0x40000000 <= h < 0x40100000:
            return f'#{h:x}'
        n = N.find(h)
        if n:
            return n[0][1]
        f = struct.unpack('<f', bytes.fromhex(x))[0]
        if 1e-4 < abs(f) < 1e7:
            return f'{f:.4g}'
        return x
    return x


def decode(pid, obj, body):
    if pid not in _schemas:
        path = os.path.join(S.OUT, f'{pid}.tree.json')
        _schemas[pid] = S.Schema.load(pid) if os.path.exists(path) else None
        _trees[pid] = PT.Tree(pid) if _schemas[pid] else None
    sc = _schemas[pid]
    if not sc:
        return None
    return S.decode(_trees[pid], sc, struct.pack('<HI', pid, obj) + body)


def main():
    t0, t1 = float(sys.argv[1]), float(sys.argv[2])
    objs = {int(x, 16) for x in sys.argv[3].split(',')} if len(sys.argv) > 3 and sys.argv[3] else None
    skip = NOISE | ({int(x) for x in sys.argv[4].split(',')} if len(sys.argv) > 4 else set())
    P.KINDS, P.ENTRY = (1,), None
    for t, ch, pid, obj, body in P.packets(P.ROFL):
        if t < t0 or pid in skip:
            continue
        if t > t1:
            break
        if objs and obj not in objs:
            continue
        v = decode(pid, obj, body)
        print(f'{t:8.3f} {pid:4d} #{obj:x} ' + (pretty(v) if v is not None else f'({len(body)} B, not learnt)'), flush=True)


if __name__ == '__main__':
    main()
