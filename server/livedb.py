"""A recorded live match in memory, for measuring what the real server does (the ground truth of the 16.20 server).

    L = livedb.Live()                      the custom 5v5 (data/live/4013831789); Live(game) for another
    L.rows                                 [(game time, way 'S' | 'C', channel, packet id, net id, body)] in order;
                                           game time = seconds since part 2 began (negative: parts 0 and 1)
    L.s2c(ids, a, b) / L.c2s(ids, a, b)    rows of a direction, optionally of some ids, in a window of game time
    L.parse(pid, body)                     the packet's values through the learnt format (None: no format / not read)
    L.inner(values)                        the packets inside a 239 container -> [(pid, net, body)]
    L.repl(body)                           a replication packet (287) -> [(net id, {name: value})]
    L.moves(body)                          a movement packet (61) -> [waypoint entry dicts with world points]
    L.frames(a, b)                         server frames: [(time, [rows])] (the packets of one datagram burst)

The first load reads packets.tsv (45 MB, ~6 s) and keeps a pickle beside it.
"""
import os
import pickle
import struct
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
sys.modules.setdefault('decoded', types.ModuleType('decoded'))

ROOT = os.path.join(HERE, '..')
DEFAULT = os.path.join(ROOT, 'data', 'live', '4013831789')
CONTAINER, REPL, MOVE = 239, 287, 61


class Live:
    def __init__(self, game=DEFAULT):
        self.game = game
        cache = os.path.join(game, 'packets.pkl')
        src = os.path.join(game, 'packets.tsv')
        if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(src):
            self.gates, self.rows = pickle.load(open(cache, 'rb'))
        else:
            import live16
            self.gates = live16.Capture(game).gates
            g = self.gates[2]
            self.rows = [(t - g, way[0], ch, pid, net, body) for t, way, ch, pid, net, body in live16.rows(src)]
            pickle.dump((self.gates, self.rows), open(cache, 'wb'), protocol=4)
        self._sc = {}
        self._repl_cls = {}

    # ------------------------------------------------------------------ rows
    def _sel(self, way, ids, a, b):
        ids = {ids} if isinstance(ids, int) else (set(ids) if ids is not None else None)
        for r in self.rows:
            if r[1] != way or (ids is not None and r[3] not in ids):
                continue
            if a is not None and r[0] < a:
                continue
            if b is not None and r[0] > b:
                break
            yield r

    def s2c(self, ids=None, a=None, b=None):
        return self._sel('S', ids, a, b)

    def c2s(self, ids=None, a=None, b=None):
        return self._sel('C', ids, a, b)

    # ------------------------------------------------------------------ values
    def schema(self, pid):
        if pid not in self._sc:
            import pkt_schema as PS
            try:
                self._sc[pid] = PS.Schema.load(pid)
            except Exception:
                self._sc[pid] = None
        return self._sc[pid]

    def parse(self, pid, body):
        import pkt_schema as PS
        sc = self.schema(pid)
        if sc is None:
            return None
        try:
            return PS.parse(sc, body)
        except Exception:
            return None

    def inner(self, values):
        import forms16
        try:
            return forms16.unpack(values)
        except Exception:
            return []

    def repl(self, body, cls_of=None):
        """[(net id, {name: value} or {'?groups': ...})]; cls_of(net) -> replication class name (default: tried in
        order AIHero, lane_minion, AITurretCommon)"""
        import replication
        import repl16
        v = self.parse(REPL, body)
        if v is None:
            return []
        out = []
        for net, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
            tried = [cls_of(net)] if cls_of else [self._repl_cls.get(net)] + ['AIHero', 'lane_minion', 'AITurretCommon', 'AIMinionCommon']
            vals = None
            for c in tried:
                if c is None:
                    continue
                try:
                    vals = repl16.read_unit(groups, c)
                    self._repl_cls.setdefault(net, c)
                    break
                except Exception:
                    continue
            out.append((net, vals if vals is not None else {'?groups': {g: (m, d.hex()) for g, (m, d) in groups.items()}}))
        return out

    def moves(self, body):
        import waypoints
        v = self.parse(MOVE, body)
        if v is None:
            return []
        out = []
        try:
            for e in waypoints.parse(bytes.fromhex(v['+0x18']['text'])):
                e = dict(e)
                e['world'] = [tuple(round(c, 1) for c in waypoints.to_world(p)) for p in e['points']]
                out.append(e)
        except Exception:
            pass
        return out

    def frames(self, a=None, b=None, way='S'):
        """rows grouped by capture time (the packets the server sent in one burst)"""
        cur_t, cur = None, []
        for r in self._sel(way, None, a, b):
            if cur_t is None or r[0] - cur_t > 0.0005:
                if cur:
                    yield cur_t, cur
                cur_t, cur = r[0], []
            cur.append(r)
        if cur:
            yield cur_t, cur


def f32(h):
    return struct.unpack('<f', bytes.fromhex(h))[0]


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little')


def vec3(h):
    return struct.unpack('<fff', bytes.fromhex(h))


if __name__ == '__main__':
    import collections
    L = Live(sys.argv[1] if len(sys.argv) > 1 else DEFAULT)
    n = collections.Counter(r[1] for r in L.rows)
    print(f'{len(L.rows)} rows, {dict(n)}, game time {L.rows[0][0]:.2f} .. {L.rows[-1][0]:.2f}, gates {L.gates}')
