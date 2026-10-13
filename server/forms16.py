"""Packet forms of the LIVE 16.20 server that are more than one packet's fields [measured on data/live/4013831789].

Container 239: +0x10 = the lengths of the packets inside (u16 each), +0x20 = those packets one after the other, each
written as on the wire (id, net id, body). The outer packet's net id is the unit it is about. A new lane minion is
239{439 spawn} + 684 + replication; a unit coming into sight is 239{...} + 684. Inner ids seen in the live match:
439 (2911), 626 (2460), 16, 894, 584, 794, 881, 1149, 515, 88, 1224, 291, 272, 1112, 683, 1005, 1134, 840, ...
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lnp16     # noqa: E402
import netid16   # noqa: E402

CONTAINER = 239


def inner(pid, net, body):
    return lnp16.var_id(pid) + netid16.encode(net) + body


def pack(items):
    """[(pid, net, body)] -> the values of a 239 container holding them"""
    blobs = [inner(*it) for it in items]
    return {'+0x10': [len(b).to_bytes(2, 'little').hex() for b in blobs], '+0x20': {'text': b''.join(blobs).hex()}}


def unpack(values):
    """the values of a 239 container -> [(pid, net, body)]"""
    lens = values.get('+0x10')
    blob = bytes.fromhex(values['+0x20']['text']) if isinstance(values.get('+0x20'), dict) else b''
    if not isinstance(lens, list):
        lens = [len(blob).to_bytes(2, 'little').hex()] if blob else []
    out, at = [], 0
    for h in lens:
        n = int.from_bytes(bytes.fromhex(h), 'little')
        d = blob[at:at + n]
        at += n
        pid, used = lnp16.read_id(d)
        net, k = netid16.decode(d[used:])
        out.append((pid, net, d[used + k:]))
    return out
