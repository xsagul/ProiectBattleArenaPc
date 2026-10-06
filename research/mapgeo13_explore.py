"""Walks patch 12.23's base_srx.mapgeo (version 13) under a layout hypothesis and reports whether every model parses.

  python research/mapgeo13_explore.py <file.mapgeo>
"""
import struct
import sys

d = open(sys.argv[1], 'rb').read()
at = 4
ver = struct.unpack_from('<I', d, at)[0]; at += 4


def u32():
    global at
    v = struct.unpack_from('<I', d, at)[0]; at += 4
    return v


def s32():
    global at
    n = u32(); v = d[at:at + n]; at += n
    return v.decode('latin-1')


print('version', ver, 'head', d[8:80].hex(' '))
samplers = [s32(), s32()]
print('samplers', samplers)
nl = u32()
at += nl * (8 + 15 * 8)
nvb = u32()
for _ in range(nvb):
    at += 1
    size = u32()
    at += size
nib = u32()
for _ in range(nib):
    at += 1
    size = u32()
    at += size
nm = u32()
print('layouts', nl, 'vb', nvb, 'ib', nib, 'models', nm, 'at', at)

first = at
vc = u32(); streams = u32(); layout = u32()
vbs = [u32() for _ in range(streams)]
ic = u32(); ib = u32()
print('model0 vc', vc, 'streams', streams, 'layout', layout, 'vbs', vbs, 'ic', ic, 'ib', ib)
print('  next 120 bytes:', d[at:at + 120].hex(' '))


def walk(has_controller, flags_size, third_channel):
    global at
    at = first
    lights = set()
    for mi in range(nm):
        vc = u32(); streams = u32(); layout = u32()
        for _ in range(streams): u32()
        ic = u32(); ib = u32()
        if not (0 < streams <= 4 and layout < nl and ib < nib and 0 < vc < 10_000_000):
            return 'bad model %d at %d' % (mi, at)
        at += 1  # layers
        if has_controller:
            u32()
        nsub = u32()
        if nsub > 64:
            return 'bad submesh count %d at model %d' % (nsub, mi)
        for _ in range(nsub):
            u32(); mat = s32(); u32(); u32(); u32(); u32()
            if not mat.isprintable():
                return 'bad material at model %d' % mi
        at += 1 + 24 + 64 + 1 + 1 + flags_size
        lights.add(s32()[:50]); at += 16
        s32(); at += 16
        if third_channel:
            s32(); at += 16
    return 'walked %d models, end %d of %d, lights e.g. %s' % (nm, at, len(d), sorted(lights)[:3])


for hc in (False, True):
    for fs in (0, 1, 2):
        for tc in (False, True):
            try:
                print('controller', hc, 'flags', fs, 'third', tc, '->', walk(hc, fs, tc))
            except Exception as e:
                print('controller', hc, 'flags', fs, 'third', tc, '-> error', e)


def stats():
    """The chosen v13 layout: value ranges of the per-model bytes, to check they mean what the names say."""
    global at
    at = first
    from collections import Counter
    q, b, layers, cull, lights, thirds = Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    for mi in range(nm):
        vc = u32(); streams = u32(); layout = u32()
        for _ in range(streams): u32()
        u32(); u32()
        layers[d[at]] += 1; at += 1
        for _ in range(u32()):
            u32(); s32(); u32(); u32(); u32(); u32()
        cull[d[at]] += 1; at += 1 + 24 + 64
        q[d[at]] += 1; b[d[at + 1]] += 1; at += 2
        lights[s32()[:40]] += 1; at += 16
        s32(); at += 16
        thirds[s32()[:40]] += 1; at += 16
    print('layers', dict(layers)); print('backface', dict(cull)); print('quality', dict(q)); print('bush/flags', dict(b))
    print('baked lights', lights.most_common(4)); print('third', thirds.most_common(4))
    print('tail after models:', d[at:at + 64].hex(' '))


stats()
