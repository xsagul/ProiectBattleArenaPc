"""Which wire byte of a server packet ends up where, found by flipping each byte and running the client's own reader
(packet_emu) on the result. The basis for writing packets the client reads exactly as Riot's server meant them.

  wire_map.py <packet id> <body hex> [netid hex]
For each body byte: the object bytes / pointed-to block bytes it changes, or 'structure' when the packet no longer
parses to its end (a length, a flag, a count).
"""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packet_emu as P


def snapshot(emu, info, pid, netid, body):
    tr = {}
    ok, left, obj = emu.deserialize(info, pid, netid, body, tr)
    if ok is None or ok == 0 or left != 0:
        return None
    out = {('obj', i): b for i, b in enumerate(obj)}
    blocks = tr['blocks']
    for k, (p, n) in enumerate(blocks[1:], 1):
        # name a block by the object offset that points to it, so it compares across runs
        where = None
        for off in range(0, len(obj) - 3, 4):
            v = struct.unpack_from('<I', obj, off)[0]
            if p <= v < p + max(n, 1):
                where = off
                break
        if where is None:
            continue
        data = bytes(emu.u.mem_read(p, n))
        for i, b in enumerate(data):
            out[(f'block@{where:#x}', i)] = b
    return out


def wire_map(pid, body, netid=0):
    info = P.table()[pid]
    emu = P.Emu()
    base = snapshot(emu, info, pid, netid, body)
    if base is None:
        raise ValueError('the packet does not parse')
    res = []
    for i in range(len(body)):
        b = bytearray(body)
        b[i] ^= 1
        s = snapshot(emu, info, pid, netid, bytes(b))
        if s is None or set(s) != set(base):
            res.append((i, 'structure'))
            continue
        res.append((i, [k for k in base if s[k] != base[k]]))
    return res


if __name__ == '__main__':
    pid = int(sys.argv[1])
    body = bytes.fromhex(sys.argv[2])
    netid = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0
    for i, what in wire_map(pid, body, netid):
        print(f'{i:4} {body[i]:02x} {what}')
