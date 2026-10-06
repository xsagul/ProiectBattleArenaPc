"""Reads the decoded 13.3 replay (data/exe133/decoded_13.3_part*.jsonl.gz, written by packet_emu.py decode).

  packets(ids=None)      -> records in stream order: {'i', 't', 'id', 'obj', 'f': [[block, offset, hex, hidden], ...]}
  fields(rec, block=0)   -> {offset: bytes} of one block
  blob(rec, block, size) -> a block's bytes, the zero bytes the decoder left out filled back in
"""
import glob
import gzip
import heapq
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = sorted(glob.glob(os.path.join(HERE, '..', 'data', 'exe133', 'decoded_13.3_part*.jsonl.gz')))


def _read(path, ids):
    with gzip.open(path, 'rt') as f:
        for line in f:
            if ids is not None:
                # cheap filter before parsing: "id":N,
                k = line.find('"id":')
                pid = int(line[k + 5:line.index(',', k)])
                if pid not in ids:
                    continue
            r = json.loads(line)
            yield r['i'], r


def packets(ids=None):
    ids = set(ids) if ids is not None else None
    for _, r in heapq.merge(*[_read(p, ids) for p in PARTS], key=lambda x: x[0]):
        yield r


def fields(rec, block=0):
    return {off: bytes.fromhex(h) for b, off, h, hid in rec.get('f', []) if b == block}


def blob(rec, block, size):
    out = bytearray(size)
    for off, raw in fields(rec, block).items():
        out[off:off + len(raw)] = raw[:max(0, size - off)]
    return bytes(out)
