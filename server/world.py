"""Our server's own Summoner's Rift (the match without the replay): lane minion waves.

Everything Riot's server did that we copy is measured on the 13.3 replay (lanes_census.py -> lanes.json, the 98
packets in codec/98.all.jsonl, the minions' health in minion_hp.pkl) or read from Riot's own scripts
(data/lua133: Minion.lua -- lane minions move forward along their lane, SR_LevelScript -- waves):
  - a wave every 30 s from 65.04 s, from each of the 6 barracks (team x lane); the units of a wave 0.827 s apart:
    3 melee (98 +0x14 04), the cannon (06) on the waves the replay had one, 3 casters (05); 98 +0x16 / +0x20 per kind
    and wave as in the replay (growing every 3 waves)
  - health per kind and wave as in the replay (595 group 3: mHP, mMaxHP)
  - the client walks a new minion out of its barracks itself; the server's first move comes 3.57 s later (median)
    from the barrack's own first point, at 325 units/s, then along the lane: our minion follows its team's measured
    walk to the meeting point and then the enemy's walk backwards, to the enemy base
Not yet: fights (minions, turrets, champions), deaths, gold. [our approximation: the whole lane in one move]
"""
import bisect
import collections
import json
import math
import os
import pickle
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'data', 'exe133')
MINION_SPEED = 325.0          # every lane minion move of the replay
SEGMENT = 1200.0              # Riot's forward moves: the next 1000-1700 units of the lane, every 3-5 s (replay)
FIRST_MOVE_DELAY = 3.57       # replay median from 98 to the first 552
FIRST_WAVE = 65.039
WAVE_PERIOD = 30.0
NET_BASE = 0x40001000         # our units' net ids (the replay's keyframe uses 0x40000000..0x4000021e)


def _lane_paths(lanes):
    """{(team, lane): [(x, z)]} base to enemy base"""
    walks = lanes['lane_walks']
    out = {}
    for lane, halves in walks.items():
        for team, enemy in (('blue', 'red'), ('red', 'blue')):
            own = [tuple(p) for p in halves.get(team, [])]
            other = [tuple(p) for p in halves.get(enemy, [])]
            if not own or not other:
                continue
            enemy_base = other[0]
            reach = math.dist(own[-1], enemy_base)
            path = list(own)
            for p in reversed(other):
                if math.dist(p, enemy_base) < reach - 50:
                    path.append(p)
            out[(team, lane)] = path
    return out


def _wave_table():
    """{wave: [(offset, kind, +0x16, +0x18, +0x20)]} from the replay's first barrack"""
    rows = [json.loads(line) for line in open(os.path.join(RES, 'codec', '98.all.jsonl'))]
    rows = [r for r in rows if r['v']]
    bid = rows[0]['v']['+0x1c']
    waves = collections.defaultdict(list)
    for r in rows:
        if r['v']['+0x1c'] == bid:
            waves[int(r['v']['+0x15'], 16)].append(r)
    out = {}
    for w, rs in waves.items():
        rs.sort(key=lambda r: r['t'])
        t0 = rs[0]['t']
        out[w] = [(r['t'] - t0, r['v']['+0x14'], r['v']['+0x16'], r['v']['+0x18'], r['v']['+0x20']) for r in rs]
    return out


def _health_table():
    """{(kind byte, wave): health} from the replay"""
    m = json.load(open(os.path.join(RES, 'minions.json')))
    hp = pickle.load(open(os.path.join(RES, 'minion_hp.pkl'), 'rb'))
    kinds = {'melee': '04', 'caster': '05', 'cannon': '06'}
    out = {}
    for k, v in m.items():
        h = hp.get(int(k))
        if h:
            out.setdefault((kinds[v['kind']], v['wave']), h[0][1])
    return out


def _spawn_templates():
    """{barrack: {pid: (channel, body)}}: what Riot's server sent with the first minion of each barrack, besides the
    98: 506 x4 (the slots' cooldowns), 387 01 (visible), 518 (entering vision: the unit's net id, speed 325, its
    waypoints from the barracks), 770 (health, 0, max health)"""
    import rofl_packets as R
    rows = [json.loads(line) for line in open(os.path.join(RES, 'codec', '98.all.jsonl'))]
    first = {}
    for r in sorted((r for r in rows if r['v']), key=lambda r: r['t']):
        first.setdefault(r['v']['+0x1c'], r['obj'])
    want = {net: bid for bid, net in first.items()}
    out = collections.defaultdict(dict)
    rofl = R.Rofl(os.path.join(HERE, '..', 'data', 'rofl', 'KR-6363178603_13.3.rofl'))
    for _, (bt, ch, pid, obj, body) in R.stream(rofl, (1,)):
        if bt > 70:
            break
        if obj in want and pid in (506, 387, 518, 770):
            d = out[want[obj]]
            if pid == 506:
                d.setdefault(506, []).append((ch, body))
            else:
                d.setdefault(pid, (ch, body, obj))
    return dict(out)


def walk(path, speed, dt):
    """where a unit that started at path[0] is after dt seconds, and the rest of its path"""
    left = speed * max(dt, 0.0)
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        d = math.dist(a, b)
        if left <= d:
            f = left / d if d else 0
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            return p, [p] + path[i + 1:]
        left -= d
    return path[-1], [path[-1]]


class Minion:
    def __init__(self, net, team, lane, kind, wave, hp, spawn_t):
        self.net, self.team, self.lane, self.kind, self.wave = net, team, lane, kind, wave
        self.hp = self.max_hp = hp
        self.spawn_t = spawn_t
        self.path = None          # the path it walks and since when
        self.path_t = None

    def pos(self, t):
        if self.path is None:
            return None
        return walk(self.path, MINION_SPEED, t - self.path_t)[0]


class World:
    def __init__(self):
        self.lanes = json.load(open(os.path.join(RES, 'lanes.json')))
        self.paths = _lane_paths(self.lanes)
        self.waves = _wave_table()
        self.health = _health_table()
        self.barracks = [(bid, b['team'], b['lane'], tuple(b['first_path_point'])) for bid, b in self.lanes['barracks'].items()]
        self.next_net = NET_BASE
        self.minions = {}
        self.queue = []           # (time, what, args) sorted
        self.wave_done = 0
        import pkt_schema as PS
        import pkt_tree as PT
        self.sc98 = PS.Schema.load(98)
        self.tpl = _spawn_templates()
        self.codec = {pid: (PS.Schema.load(pid), PT.Tree(pid)) for pid in (518, 770)}

    # --------------------------------------------------------------------------------------------- waves
    def wave_units(self, w):
        if w in self.waves:
            return self.waves[w]
        last = max(self.waves)
        return self.waves[last - 2 + (w - last) % 3] if w > last else self.waves[1]

    def schedule_wave(self, w):
        t0 = FIRST_WAVE + WAVE_PERIOD * (w - 1)
        for bid, team, lane, first in self.barracks:
            for off, kind, x16, x18, x20 in self.wave_units(w):
                bisect.insort(self.queue, (t0 + off, 'spawn', (bid, team, lane, first, kind, x16, x18, x20, w)))

    def tick(self, t):
        """the world at game time t -> [(channel, packet bytes, what)]"""
        out = []
        while self.wave_done < 1 or FIRST_WAVE + WAVE_PERIOD * self.wave_done - 6 <= t:
            self.wave_done += 1
            self.schedule_wave(self.wave_done)
        moves = []
        while self.queue and self.queue[0][0] <= t:
            at, what, args = self.queue.pop(0)
            if what == 'spawn':
                out += self.spawn(at, *args)
            elif what == 'move':
                m = self.minions.get(args)
                if m and len(m.lane_path) > 1:
                    moves.append(m)
        if moves:
            out.append(self.move_packet(moves, t))
        return out

    def spawn(self, t, bid, team, lane, first, kind, x16, x18, x20, w):
        import lol_packets as LP
        import repl_codec as RC
        net = self.next_net
        self.next_net += 1
        if os.environ.get('WORLD_REPLAY_IDS') and w == 1 and self.tpl.get(bid, {}).get(518):
            # control experiment: the replay's own net id and bytes for the first minion of each barrack
            if not hasattr(self, '_used_replay'):
                self._used_replay = set()
            if bid not in self._used_replay:
                self._used_replay.add(bid)
                net = self.tpl[bid][518][2]
        hp = self.health.get((kind, min(w, 60)), 477.0)
        m = Minion(net, team, lane, kind, w, hp, t)
        path = self.paths.get((team, lane))
        if path:
            # from the barrack's own first point onto the lane, from the lane point nearest to it
            k = min(range(len(path)), key=lambda i: math.dist(path[i], first))
            m.lane_path = [first] + path[k + 1:]
        else:
            m.lane_path = [first]
        self.minions[net] = m
        bisect.insort(self.queue, (t + FIRST_MOVE_DELAY, 'move', net))
        v = {'+0xa': '0000', '+0xc': struct.pack('<f', t).hex(), '+0x10': struct.pack('<I', net).hex(), '+0x14': kind,
             '+0x15': f'{w & 0xff:02x}', '+0x16': x16, '+0x18': x18, '+0x1c': bid, '+0x20': x20}
        body = self.sc98.encode(v)
        import pkt_schema as PS
        tpl = self.tpl.get(bid, {})
        pk = [(ch, struct.pack('<HI', 506, net) + b, '506') for ch, b in tpl.get(506, [])]
        pk.append((1, struct.pack('<HI', 98, net) + body, f'98 spawn {team} {lane} wave {w} kind {kind} -> {net:#x}'))
        pk.append((1, struct.pack('<HI', 387, net) + bytes.fromhex(tpl[387][1].hex()) if 387 in tpl else b'', '387 visible'))
        if 518 in tpl:
            ch, b, old = tpl[518]
            sc, tr = self.codec[518]
            v518 = PS.decode(tr, sc, struct.pack('<HI', 518, old) + b)
            v518['+0x10']['text'] = v518['+0x10']['text'].replace(struct.pack('<I', old).hex(), struct.pack('<I', net).hex())
            pk.append((ch, struct.pack('<HI', 518, net) + sc.encode(v518), '518 enters vision'))
        if 770 in tpl:
            ch, b, old = tpl[770]
            sc, tr = self.codec[770]
            v770 = PS.decode(tr, sc, struct.pack('<HI', 770, old) + b)
            v770['+0x10']['text'] = struct.pack('<fff', hp, 0.0, hp).hex()
            pk.append((ch, struct.pack('<HI', 770, net) + sc.encode(v770), '770 health'))
        unit = RC.unit(net, {'mHP': hp, 'mMaxHP': hp}, 'lane_minion')
        pk.append((2, struct.pack('<HI', 595, 0) + LP.join_595(LP.TEMPLATE_595[0], unit, LP.TEMPLATE_595[1]),
                   f'595 minion {net:#x} health {hp:.0f}'))
        return pk

    def move_packet(self, ms, t):
        import lol_packets as LP
        import waypoints as Wp
        entries = b''
        for m in ms:
            # the next piece of the lane from where it is (SetStateAndMoveToForwardNav), the rest later
            here = m.pos(t) if m.path else m.lane_path[0]
            lane = [here] + m.lane_path[1:] if not m.path else [here] + m.lane_path
            seg, left = [here], SEGMENT
            i = 1
            while i < len(lane) and left > 0:
                d = math.dist(seg[-1], lane[i])
                if d < 1:
                    i += 1
                    continue
                if d <= left:
                    seg.append(lane[i])
                    left -= d
                    i += 1
                else:
                    f = left / d
                    seg.append((seg[-1][0] + (lane[i][0] - seg[-1][0]) * f, seg[-1][1] + (lane[i][1] - seg[-1][1]) * f))
                    left = 0
            m.lane_path = [seg[-1]] + lane[i:]
            m.path, m.path_t = seg, t
            if len(m.lane_path) > 1:
                bisect.insort(self.queue, (t + (SEGMENT - 250) / MINION_SPEED, 'move', m.net))
            cells = [(int(round((x - Wp.CENTER[0]) / Wp.CELL)), int(round((z - Wp.CENTER[1]) / Wp.CELL))) for x, z in m.path]
            entries += LP.waypoint_entry(m.net, cells, MINION_SPEED)
        return (2, struct.pack('<HI', 552, 0) + LP.encode_552(entries), f'552 {len(ms)} minions walk their lanes')


if __name__ == '__main__':
    w = World()
    for k, p in w.paths.items():
        print(k, len(p), p[0], p[-1])
    for t in (64, 65.1, 66, 70):
        for ch, data, what in w.tick(t):
            print(t, ch, len(data), what)
