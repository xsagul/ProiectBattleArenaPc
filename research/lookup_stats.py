"""Which life does colorLookUpType 1 follow? Counts, over every map particle emitter that has a particleColorTexture,
how many loop (no `lifetime`) with lookup type X = 1 (the class default) while their colour texture really changes
along u. If type 1 followed the emitter's life, a looping emitter would only ever show u = 0 and its gradient would be
dead weight; if it follows the particle's life, the gradient plays on every particle.

  python research/lookup_stats.py <dump of base_srx.materials.bin from bainfo bin ... hashdir> <wad> <bainfo.exe>
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

dump, wad, bainfo = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(dump, encoding='utf-8', errors='replace').read().split('\n')

emitters = []
cur = None
for line in lines:
    s = line.strip()
    if s == 'VfxEmitterDefinitionData':
        cur = {'indent': len(line) - len(line.lstrip()), 'lifetime': False, 'x': 1, 'y': 0, 'tex': None, 'name': ''}
        emitters.append(cur)
        continue
    if cur is None:
        continue
    ind = len(line) - len(line.lstrip())
    if s and ind <= cur['indent']:
        cur = None
        continue
    if ind == cur['indent'] + 2:
        if s.startswith('lifetime:'):
            cur['lifetime'] = True
        elif s.startswith('colorLookUpTypeX:'):
            cur['x'] = int(s.split(':')[1])
        elif s.startswith('colorLookUpTypeY:'):
            cur['y'] = int(s.split(':')[1])
        elif s.startswith('particleColorTexture:'):
            cur['tex'] = s.split(':', 1)[1].strip().strip('"')
        elif s.startswith('emitterName:'):
            cur['name'] = s.split(':', 1)[1].strip().strip('"')

tmp = tempfile.mkdtemp()
cache = {}


def u_variation(tex):
    """How much the texture changes along u (mean absolute difference between its first and its middle column)."""
    if tex in cache:
        return cache[tex]
    path = tex.lower()
    if path.endswith('.dds') or path.endswith('.png'):
        path = path[:-4] + '.tex'
    out = os.path.join(tmp, str(len(cache)) + '.png')
    subprocess.run([bainfo, 'tex', wad, path, out], capture_output=True)
    v = None
    if os.path.exists(out):
        im = Image.open(out).convert('RGBA')
        w, h = im.size
        px = im.load()
        y = h // 2
        a, b = px[0, y], px[w // 2, y]
        c = px[w - 1, y]
        v = max(sum(abs(a[k] - b[k]) for k in range(4)), sum(abs(a[k] - c[k]) for k in range(4))) / 4
    cache[tex] = v
    return v


with_tex = [e for e in emitters if e['tex']]
print('emitters', len(emitters), 'with particleColorTexture', len(with_tex))
from collections import Counter
print('lookup X types', Counter(e['x'] for e in with_tex), 'Y types', Counter(e['y'] for e in with_tex))
loop_x1 = [e for e in with_tex if not e['lifetime'] and e['x'] == 1]
varied = [e for e in loop_x1 if (u_variation(e['tex']) or 0) > 8]
print('looping, X = 1:', len(loop_x1), '-- of which the colour texture changes along u:', len(varied))
for e in varied[:12]:
    print('  ', e['name'], e['tex'], round(u_variation(e['tex']), 1))
timed_x1 = [e for e in with_tex if e['lifetime'] and e['x'] == 1]
print('with a lifetime, X = 1:', len(timed_x1))
