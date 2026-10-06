"""Patch 14.1's Summoner's Rift terrain shaders (srx_blend_*): disassembles each one's pixel shader permutations from the
14.1 ShaderCache and picks, for each, the colour permutation with environment transitions and no fog of war, shadows or
stationary light (the plain look), so its math can be read. Writes research/shaders141/<name>/main.asm.

  python research/srx141_shaders.py <14.1 ShaderCache.dx11.wad.client> <bainfo.exe>
"""
import glob
import os
import re
import subprocess
import sys

cache, bainfo = sys.argv[1], sys.argv[2]
root = os.path.join(os.path.dirname(__file__), 'shaders141')
here = os.path.dirname(os.path.abspath(__file__))
disasm = os.path.join(here, '..', 'tools', 'disasm_shaders.py')
names = [l.strip().split('/')[-1] for l in open(os.path.join(here, 'm141', 'staticmesh_shaders.txt'))]
names = [n for n in names if n.startswith('srx_blend') or n in ('defaultenv', 'defaultenv_flat', 'defaultenv_flat_alphatest',
                                                                 'defaultenv_flat_alphatest_doublesided', 'vertexdeform')]
listing = subprocess.run([bainfo, 'wad', cache, os.path.join(here, '..', '..', 'BattleArena', 'art', 'lol-data', 'hashes.game.txt')],
                         capture_output=True, text=True).stdout
for name in names:
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=True)
    entries = sorted(set(re.findall(r'(assets/shaders/generated/shaders/staticmesh/%s\.ps\.dx11_\d+)' % re.escape(name), listing)))
    for e in entries:
        out = os.path.join(d, os.path.basename(e).replace('.', '_'))
        if not os.path.isdir(out):
            subprocess.run([bainfo, 'raw', cache, e, out + '.bin'], capture_output=True)
            subprocess.run([sys.executable, disasm, out + '.bin', out], capture_output=True)
    best = None
    for f in glob.glob(os.path.join(d, '*ps_dx11_*', '*.asm')):
        t = open(f).read()
        tex = set(re.findall(r'^// (\w+)\s+texture', t, re.M))
        if 'FOW_MAP' in tex or any('SHADOW' in x for x in tex) or 'STATIONARY_LIGHT' in tex:
            continue
        if 'mov o0.xyzw, l(1.000000,1.000000,1.000000,1.000000)' in t:
            continue  # depth / shadow-caster permutations write plain white
        if name.startswith('srx_blend') and 'EnvironmentTransitionPixelCB' not in t:
            continue
        m = re.search(r'Approximately (\d+)', t)
        slots = int(m.group(1)) if m else 0
        if best is None or slots < best[0]:
            best = (slots, f)
    if best:
        open(os.path.join(d, 'main.asm'), 'w').write(open(best[1]).read())
    print(name, len(entries), 'bundles; main:', best and os.path.relpath(best[1], root), best and best[0], 'slots')
