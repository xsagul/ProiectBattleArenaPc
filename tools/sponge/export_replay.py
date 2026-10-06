"""The decoded 13.3 replay as one binary file our client plays: client.exe --replay <file.barp>.

Stage 1 of "our exe runs the replay": Riot's own deserializers (run in the emulator, tools/sponge/packet_emu.py) have
already turned every packet into its fields in clear; this writes them in stream order for the client, whose packet
handlers (client/src/Replay.cpp) then do what Riot's handlers do. Stage 2 replaces this file with the .rofl itself,
once the client reads the wire format natively.

  export_replay.py [out.barp]      default research/exe133/replay_13.3.barp

File: "BARP", u32 version (1), u32 number of packets, then per packet:
    f32 seconds, u16 packet id, u32 net id, u8 number of blocks, per block: u32 size, the bytes
Block 0 is the packet object as the deserializer left it (fields at Riot's own offsets, zero where the decoder kept
nothing), the others are what it points at (strings, buffers, vectors), in the decoder's order.
First the packets of the first keyframe (the state the match starts from: heroes, turrets, camps), then the chunks.
"""
import collections
import gzip
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decoded

RES = os.path.join(HERE, '..', '..', 'research', 'exe133')


def record(r):
    bl = collections.defaultdict(dict)
    for b, off, h, hid in r.get('f', []):
        bl[b][off] = bytes.fromhex(h)
    out = [struct.pack('<fHIB', r['t'], r['id'], r['obj'], (max(bl) + 1) if bl else 0)]
    for b in range((max(bl) + 1) if bl else 0):
        fs = bl.get(b, {})
        size = max((o + len(v) for o, v in fs.items()), default=0)
        buf = bytearray(size)
        for o, v in fs.items():
            buf[o:o + len(v)] = v
        out.append(struct.pack('<I', size))
        out.append(bytes(buf))
    return b''.join(out)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RES, 'replay_13.3.barp')
    n = 0
    with open(out, 'wb') as f:
        f.write(b'BARP' + struct.pack('<II', 1, 0))
        for line in gzip.open(os.path.join(RES, 'decoded_13.3_key1.jsonl.gz'), 'rt'):
            r = json.loads(line)
            if 'error' in r:
                continue
            r['t'] = 0.0
            f.write(record(r))
            n += 1
        for r in decoded.packets():
            if 'error' in r:
                continue
            f.write(record(r))
            n += 1
        f.seek(8)
        f.write(struct.pack('<I', n))
    print(n, 'packets ->', out, os.path.getsize(out), 'bytes')


if __name__ == '__main__':
    main()
