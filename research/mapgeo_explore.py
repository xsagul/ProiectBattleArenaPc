"""Walks a .mapgeo up to its models and prints the bytes of the first ones after their submesh list, to compare the
layout of one version with another (research for reading patch 14.1's v15 next to the current v18).

  python research/mapgeo_explore.py <file.mapgeo> [models to show]
"""
import struct
import sys

d = open(sys.argv[1], 'rb').read()
show = int(sys.argv[2]) if len(sys.argv) > 2 else 2
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


if ver >= 17:
    for _ in range(u32()):
        u32(); s32()
else:
    print('samplers', s32(), s32())
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
print('version', ver, 'layouts', nl, 'vb', nvb, 'ib', nib, 'models', nm)
for mi in range(show):
    start = at
    vc = u32(); streams = u32(); layout = u32()
    vbs = [u32() for _ in range(streams)]
    ic = u32(); ib = u32()
    layers = d[at]; at += 1
    if ver >= 18:
        at += 4
    bucket = u32()
    nsub = u32()
    subs = []
    for _ in range(nsub):
        u32(); mat = s32(); subs.append((mat, u32(), u32(), u32(), u32()))
    print('model', mi, 'vc', vc, 'streams', streams, 'layout', layout, 'ic', ic, 'layers', layers, 'bucket %08x' % bucket, 'subs', subs[:2])
    tail = d[at:at + 200]
    print('  after submeshes:', tail.hex(' '))
    # try to find the next model by reading the v17 tail and checking it looks sane
    at_save = at
    at += 1 + 24 + 64 + 1 + 1 + 2
    print('  baked light string at +%d:' % (at - at_save), repr(d[at + 4:at + 4 + min(80, struct.unpack_from('<I', d, at)[0])]))
    at = at_save
    # stop: the caller compares by eye
    break


def walk_all():
    """Every model under the v15 hypothesis: render flags u8, then baked light, stationary light and a third channel
    (string + 16 bytes each) in place of v17's texture override list."""
    global at
    bad = 0
    names = set()
    for mi in range(nm):
        vc = u32(); streams = u32(); layout = u32()
        [u32() for _ in range(streams)]
        ic = u32(); ib = u32()
        at += 1
        if ver >= 18:
            at += 4
        u32()
        nsub = u32()
        for _ in range(nsub):
            u32(); mat = s32(); u32(); u32(); u32(); u32()
            if not mat.isprintable():
                bad += 1
        at += 1 + 24 + 64
        at += 1 + 1 + (2 if ver >= 17 else 1)
        light = s32(); at += 16
        stat = s32(); at += 16
        if ver >= 17:
            for _ in range(u32()):
                u32(); s32()
        else:
            third = s32(); at += 16
            if third:
                names.add(third[:60])
        at += 16 if ver >= 17 else 0
        if not (0 < streams <= 4 and layout < nl and ib < nib and 0 < vc < 10_000_000):
            bad += 1
            print('bad model', mi, vc, streams, layout, ib)
            break
    print('walked', mi + 1, 'models, bad', bad, 'end at', at, 'of', len(d))
    print('third channel names:', sorted(names)[:8])


at_models = None
