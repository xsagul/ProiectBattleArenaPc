"""Writes the bone palette of one skinned draw of a capture as text, for the client's --match-pose.

  python tools/sponge/palette.py <tag dir> <draw index> <out.txt> [bones]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import read_sponge as rs  # noqa: E402

tag, want, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
bones = int(sys.argv[4]) if len(sys.argv) > 4 else 64
frame = sorted(f for f in os.listdir(tag) if f.startswith('frame_') and f.endswith('.bin'))[0]
for i, head, d, cbs in rs.draws(os.path.join(tag, frame)):
    if i != want:
        continue
    vs = cbs.get(d['vs_cb'][0])
    n = min(bones, len(vs) // 48)
    with open(out, 'w') as f:
        for b in range(n):
            f.write(' '.join('%.6f' % x for x in struct.unpack_from('<12f', vs, 48 * b)) + '\n')
    print('wrote', n, 'bones; first bone:', ' '.join('%.3f' % x for x in struct.unpack_from('<12f', vs, 0)))
    break
