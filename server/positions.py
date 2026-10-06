"""Where every unit is at any time of the replay: the movement packets (552) give each unit a path (its current
point first) and a speed; between packets the unit walks the path at that speed (waypoints.py, lol_packets.split_552).

  positions.py at <net id hex> <t>
"""
import bisect
import collections
import math
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import lol_packets as LP  # noqa: E402
import waypoints as W  # noqa: E402

CACHE = os.path.join(HERE, '..', 'data', 'exe133', 'paths552.pkl')


def paths():
    """{net: [(t, [(x, z) world], speed)]} from every 552 of the replay (cached)"""
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, 'rb'))
    out = collections.defaultdict(list)
    P.KINDS, P.ENTRY = (1,), None
    for t, ch, pid, obj, body in P.packets(P.ROFL, 552):
        s = LP.split_552(body)
        if not s:
            continue
        try:
            ents = W.parse(s[1])
        except Exception:
            continue
        for e in ents:
            out[e['net']].append((t, [W.to_world(p) for p in e['points']], e['speed']))
    out = dict(out)
    pickle.dump(out, open(CACHE, 'wb'))
    return out


def walk(pts, speed, dt):
    """the point reached after dt seconds along pts at speed"""
    left = speed * max(dt, 0)
    x, z = pts[0]
    for nx, nz in pts[1:]:
        d = math.hypot(nx - x, nz - z)
        if d >= left:
            f = left / d if d else 0
            return (x + (nx - x) * f, z + (nz - z) * f)
        left -= d
        x, z = nx, nz
    return (x, z)


_p = None


def at(net, t):
    global _p
    if _p is None:
        _p = paths()
    L = _p.get(net)
    if not L:
        return None
    i = bisect.bisect_right([x[0] for x in L], t) - 1
    if i < 0:
        return L[0][1][0]
    t0, pts, speed = L[i]
    return walk(pts, speed, t - t0)


if __name__ == '__main__':
    print(at(int(sys.argv[2], 16), float(sys.argv[3])))
