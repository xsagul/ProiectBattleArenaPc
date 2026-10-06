"""The header modes (and unused bits) every struct instance of a replay packet used, for pkt_schema.Schema.encode:
re-encoding a replay packet with its own modes must give its own bytes."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'server'))
import pkt_schema as S  # noqa: E402


def replay_modes(T, sc):
    out = {}
    for k, st in sc.structs.items():
        insts = T.of(int(k, 16))
        if not insts:
            continue
        inst = insts[0]
        pre = 6 if int(k, 16) == T.info['des'] else 0
        h = int.from_bytes(T.wire[inst['start'] + pre:inst['start'] + pre + st['header']], 'little')
        d = {fl['bit']: (h >> fl['bit']) & ((1 << fl['width']) - 1) for fl in st['fields']}
        d['spare'] = sum(h & (1 << b) for b in st['spare_bits'])
        out[k] = d
    return out
