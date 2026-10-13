"""Server packets of the 16.20 client by value: the learnt formats (data/exe1620/codec/<id>.tree.json, pkt_schema.py)
read and written with one call each.

  decode(pid, net, body)  -> {'+0x10': ..., ...} as the client's own reader reads it (None if it does not)
  encode(pid, values)     -> body bytes (after the packet id and the net id)
  edit(pid, net, body, changes) -> body with some fields changed (a recorded packet as the template)

Reading runs the client's reader in the emulator (slow: tens of ms); writing is plain Python. A server builds its
packets with encode() from values, and uses decode() only once per template.
"""
import functools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
import pkt_schema as PS    # noqa: E402
import pkt_tree as PT      # noqa: E402
from emu_backend import P  # noqa: E402


@functools.lru_cache(maxsize=None)
def schema(pid):
    return PS.Schema.load(pid)


def has(pid):
    return os.path.exists(os.path.join(PS.OUT, f'{pid}.tree.json'))


@functools.lru_cache(maxsize=None)
def tree(pid):
    return PT.Tree(pid)


def decode(pid, net, body):
    return PS.decode(tree(pid), schema(pid), P.wire(pid, net, body))


def encode(pid, values, modes=None):
    return schema(pid).encode(values, modes)


def edit(pid, net, body, changes):
    v = decode(pid, net, body)
    if v is None:
        raise ValueError(f'packet {pid} is not read by the client reader')
    v.update(changes)
    return encode(pid, v)
