"""The lane minions of the 13.3 replay as the server sent them: spawns, paths, attacks, deaths, in one cache.

  minion_trace.py build [seconds]     data/exe133/minion_trace.pkl from the decoded replay (default: first 400 s)
  minion_trace.py wave <n> [lane]     wave n: who targets whom, where and when (first attacks, acquisitions)
  minion_trace.py stats               distances at acquisition and at attack start, over all waves in the cache
  minion_trace.py timeline <n> <lane> <t0> <t1>   wave n's paths and attacks in a lane (0 bot, 1 mid, 2 top)
Add `--ours <f.banl>` (server.exe --simulate S --netlog f.banl) to any of them for our own server's stream.

Position of a unit at time t = along its last path (packet 552) at its speed.
"""
import collections
import math
import os
import pickle
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
CACHE = os.path.join(HERE, '..', 'data', 'exe133', 'minion_trace.pkl')
KIND = {4: 'melee', 5: 'caster', 6: 'siege', 7: 'super'}


def build(limit):
    import decoded
    import waypoints
    spawns, paths, attacks, deaths, damage = {}, collections.defaultdict(list), [], {}, []
    for r in decoded.packets({98, 552, 286, 61, 263}):
        t = r['t']
        if t > limit:
            break
        if r['id'] == 98:
            f = decoded.fields(r)
            net = struct.unpack('<I', f[0x10])[0]
            spawns[net] = {'t': struct.unpack('<f', f[0xc])[0], 'kind': f[0x14][0], 'wave': f[0x15][0],
                           'barracks': struct.unpack('<I', f[0x1c])[0]}
        elif r['id'] == 552:
            f = decoded.fields(r)
            n = struct.unpack('<I', f[0x14].ljust(4, b'\0'))[0] if 0x14 in f else 0
            if not n:
                continue
            try:
                for e in waypoints.parse(decoded.blob(r, 1, n)):
                    paths[e['net']].append((t, e['speed'], [waypoints.to_world(p) for p in e['points']]))
            except Exception:
                pass
        elif r['id'] == 286:
            f = decoded.fields(r)
            if 0x14 in f:
                attacks.append((t, r['obj'], struct.unpack('<I', f[0x14].ljust(4, b'\0'))[0]))
        elif r['id'] == 61:
            deaths.setdefault(r['obj'], t)
        elif r['id'] == 263:
            f = decoded.fields(r)
            if 0x20 in f and 0x14 in f:
                damage.append((t, struct.unpack('<I', f[0x20].ljust(4, b'\0'))[0], r['obj'], struct.unpack('<f', f[0x14].ljust(4, b'\0'))[0]))
    pickle.dump({'spawns': spawns, 'paths': dict(paths), 'attacks': attacks, 'deaths': deaths, 'damage': damage, 'limit': limit},
                open(CACHE, 'wb'))
    print(f'{len(spawns)} minions, {sum(len(v) for v in paths.values())} paths of {len(paths)} units, {len(attacks)} minion attacks, '
          f'{len(deaths)} deaths -> {CACHE}')


class Trace:
    def __init__(self):
        d = pickle.load(open(CACHE, 'rb'))
        self.spawns, self.paths, self.attacks, self.deaths, self.damage = d['spawns'], d['paths'], d['attacks'], d['deaths'], d['damage']
        # team and lane of a barracks: where its minions first stand
        self.barracks = {}
        for net, s in self.spawns.items():
            if s['barracks'] in self.barracks or net not in self.paths:
                continue
            x, z = self.paths[net][0][2][0]
            team = 0 if x + z < 14800 else 1
            # the lanes leave each base along z (top), the diagonal (mid), x (bot)
            dx, dz = (x, z) if team == 0 else (14800 - x, 14800 - z)
            lane = 2 if dz > dx * 1.5 else 0 if dx > dz * 1.5 else 1
            self.barracks[s['barracks']] = (team, lane)

    def team_lane(self, net):
        return self.barracks.get(self.spawns[net]['barracks'], (None, None))

    def pos(self, net, t):
        """where the unit is at t: along the last path sent before t"""
        ps = self.paths.get(net)
        if not ps:
            return None
        last = None
        for p in ps:
            if p[0] > t:
                break
            last = p
        if last is None:
            return None
        t0, speed, pts = last
        left = max(0.0, (t - t0) * speed)
        x, z = pts[0]
        for nx, nz in pts[1:]:
            d = math.hypot(nx - x, nz - z)
            if d >= left:
                if d > 0:
                    x, z = x + (nx - x) * left / d, z + (nz - z) * left / d
                return x, z
            left -= d
            x, z = nx, nz
        return x, z

    def dist(self, a, b, t):
        pa, pb = self.pos(a, t), self.pos(b, t)
        return math.hypot(pa[0] - pb[0], pa[1] - pb[1]) if pa and pb else None

    def moving(self, net, t):
        ps = [p for p in self.paths.get(net, []) if p[0] <= t]
        if not ps:
            return False
        t0, speed, pts = ps[-1]
        total = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))
        return (t - t0) * speed < total - 1


class OurTrace(Trace):
    """The same, from our own server's stream (server.exe --simulate S --netlog f.banl)."""

    def __init__(self, path):
        import netlog_compare as nc
        self.spawns, self.paths, self.attacks, self.deaths, self.damage = {}, collections.defaultdict(list), [], {}, []
        self.barracks = {}
        waves = []
        for tick, ch, m in nc.read_banl(path):
            t = tick * nc.TICK
            r = nc.R(m)
            if m[0] == 65:
                uid, team = r.get('I'), r.get('B')
                name = r.str()
                if 'Minion' not in name:
                    continue
                r.get('B')
                x, z = r.get('ff')
                if not waves or t - waves[-1] > 10:
                    waves.append(t)
                kind = 4 if 'Melee' in name else 5 if 'Ranged' in name else 6 if 'Siege' in name else 7
                dx, dz = (x, z) if team == 0 else (14800 - x, 14800 - z)
                lane = 2 if dz > dx * 1.5 else 0 if dx > dz * 1.5 else 1
                self.spawns[uid] = {'t': t, 'kind': kind, 'wave': len(waves), 'barracks': (team, lane)}
                self.barracks[(team, lane)] = (team, lane)
            elif m[0] == 66:
                start, n = r.get('qH')
                for _ in range(n):
                    uid, speed, k = r.get('IfH')
                    pts = [r.get('ff') for _ in range(k)]
                    if pts:
                        self.paths[uid].append((t, speed, pts))
            elif m[0] == 68:
                start, uid, target = r.get('qII')
                self.attacks.append((t, uid, target))
            elif m[0] == 70:
                start, uid = r.get('qI')
                self.deaths.setdefault(uid, t)


def open_trace(args):
    return OurTrace(args[args.index('--ours') + 1]) if '--ours' in args else Trace()


def timeline(n, lane, t0, t1, tr):
    """every path, first attack on a new target and death of wave n's minions in a lane between t0 and t1"""
    ids = sorted(k for k, s in tr.spawns.items() if s['wave'] == n and tr.team_lane(k)[1] == lane)
    per, name = collections.Counter(), {}
    for k in ids:
        key = (tr.team_lane(k)[0], tr.spawns[k]['kind'])
        per[key] += 1
        name[k] = f'{"OC"[key[0]]}{KIND.get(key[1], "?")[0]}{per[key]}'
    ev, last = [], {}
    for k in ids:
        for t, sp, pts in tr.paths.get(k, []):
            if t0 <= t <= t1:
                ev.append((t, f'{name[k]} path ' + ' '.join(f'({x:.0f},{z:.0f})' for x, z in pts)))
    for t, a, b in tr.attacks:
        if a in name and last.get(a) != b:
            last[a] = b
            if t0 <= t <= t1:
                d = tr.dist(a, b, t)
                ev.append((t, f'{name[a]} ATTACK {name.get(b, hex(b))} at {d if d is None else round(d)}'))
    for t, s in sorted(ev):
        print(f'{t:8.3f} {s}')


def wave(n, lane=None, tr=None):
    tr = tr or Trace()
    ids = sorted(k for k, s in tr.spawns.items() if s['wave'] == n and (lane is None or tr.team_lane(k)[1] == lane))
    name = {}
    per = collections.Counter()
    for k in ids:
        team, ln = tr.team_lane(k)
        key = (team, ln, KIND.get(tr.spawns[k]['kind'], '?'))
        per[key] += 1
        name[k] = f'{"OC"[team]}{"BMT"[ln]}{KIND.get(tr.spawns[k]["kind"], "?")[0]}{per[key]}'
    first = {}
    for t, a, b in tr.attacks:
        if a in name and a not in first:
            first[a] = (t, b)
    print('minion     spawn    first attack: at, on, distance, target moving | paths before it (time, points, to)')
    for k in ids:
        s = tr.spawns[k]
        if k not in first:
            print(f'{name[k]:8} {s["t"]:7.2f}   -')
            continue
        t, b = first[k]
        d = tr.dist(k, b, t)
        ps = [p for p in tr.paths.get(k, []) if p[0] <= t + 0.01]
        tail = ' '.join(f'{p[0]:.2f}:{len(p[2])}>({p[2][-1][0]:.0f},{p[2][-1][1]:.0f})' for p in ps[-4:])
        print(f'{name[k]:8} {s["t"]:7.2f}   {t:7.3f} {name.get(b, hex(b)):8} {d if d is None else round(d):>5} {tr.moving(b, t)!s:5} | {tail}')


def stats(tr=None):
    tr = tr or Trace()
    first = {}
    for t, a, b in tr.attacks:
        if a in tr.spawns and a not in first:
            first[a] = (t, b)
    by = collections.defaultdict(list)
    for a, (t, b) in first.items():
        d = tr.dist(a, b, t)
        if d is not None and b in tr.spawns:
            by[KIND.get(tr.spawns[a]['kind'], '?')].append(d)
    for k, v in sorted(by.items()):
        v.sort()
        q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
        print(f'first attack on a minion, {k:6}: n {len(v):4}  p10 {q(.1):6.0f}  median {q(.5):6.0f}  p90 {q(.9):6.0f}  max {v[-1]:6.0f}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'build':
        build(float(sys.argv[2]) if len(sys.argv) > 2 else 400.0)
    elif cmd == 'wave':
        wave(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else None, open_trace(sys.argv))
    elif cmd == 'stats':
        stats(open_trace(sys.argv))
    elif cmd == 'timeline':
        timeline(int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), open_trace(sys.argv))
