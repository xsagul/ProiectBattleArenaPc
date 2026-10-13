"""Our 16.20 game server: a whole match, built as the real server's own sequence (measured on the live recording of
custom match 4013831789, data/live/<gameId>/; docs/SERVER16_ARHITECTURA.md for the whole picture).

  python server/match16.py [options] <port>

The real server talks to a player in three parts, each the answer to a client packet [measured, both live matches]:
  0  client 1 + 64            -> 213, clock 804 + 371 (x2), game info 618
     client 197 (loading %)   -> 1095 (the loading screen's progress of every player)
  1  client second 64          -> the start state in one burst (heroes, structures, shop, map objects)
  2  client third 64           -> 664 744 278, the world's first state (spell slots, buffs, units in sight), then the match
     client 841 (every 2 s)    -> 1007 (ping: the request's number and time, our receive and send times)

What comes from where (one switch each, so every system can be replaced by ours and checked alone):
  - parts 0 and 1 and the first INIT seconds of part 2: the recording (the same map and roster as recorded)
  - --pass <ids>: those packet ids of the recording's part 2 go out at their recorded time (control runs)
  - ours: ping, loading answers, the player's champion (orders -> movement 61, skill-up 544 -> 810), the world
    (--world: minion waves, world16.py)

Options: --capture <data/live/gameId> (default the custom match), --hero <net id hex> (default the recording's
player: the first 222), --init <s> (default 1.0), --pass <id,id,...>, --world, --log-c2s
"""
import collections
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
import live16    # noqa: E402
import net16     # noqa: E402

ROOT = os.path.join(HERE, '..')
DEFAULT_CAPTURE = os.path.join(ROOT, 'data', 'live', '4013831789')
PING, PONG = 841, 1007
LOADING, LOADING_ANSWER = 197, 1095
HELLO, READY = 1, 64
ORDER, SKILL_UP, CAST_REQUEST, BUY = 1032, 544, 707, 1135
HERO_CREATE, REPLICATION, MOVE = 222, 287, 61
# part 2's first seconds without these (the ping and loading answers are ours). The movement (61) of that second is
# kept: it places every allied champion at the fountain - without it the client never shows them [user, 10-11]
INIT_DROP = {PONG, LOADING_ANSWER}
# the spawn barrier: at 15.084 s the real server sends, for each champion, 557 {an empty list} + 840 {zeros}; until
# then the fountain's gates stay closed [measured live; user: "the gates never open on ours"]
GATES_OPEN = 15.084


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


class Recording:
    """What the recording gives a match of ours: its three parts and facts read from them."""
    def __init__(self, game, init):
        self.cap = live16.Capture(game)
        self.champions = {}
        g = self.cap.gates
        self.part0, self.part1, self.init, self.rest, self.loading = [], [], [], [], []
        for t, way, ch, pid, net, body in live16.rows(self.cap.path):       # one pass over the recording
            if way != 'S2C':
                continue
            if pid == LOADING_ANSWER:
                self.loading.append((ch, pid, net, body))
            if t < g[0] or pid in live16.DROP:
                continue
            if t < g[1]:
                self.part0.append((t - g[0], ch, pid, net, body))
            elif t < g[2]:
                self.part1.append((t - g[1], ch, pid, net, body))
            else:
                (self.init if t - g[2] < init else self.rest).append((t - g[2], ch, pid, net, body))

    def heroes(self):
        """[(net id, (x, z))] of the start state's champions, in creation order (222: +0x1c net id, +0x20 place)"""
        import pkt_schema as PS
        sc = PS.Schema.load(HERO_CREATE)
        out = []
        for dt, ch, pid, net, body in self.part1:
            if pid == HERO_CREATE:
                v = PS.parse(sc, body)
                x, y, z = struct.unpack('<fff', bytes.fromhex(v['+0x20']))
                out.append((struct.unpack('<I', bytes.fromhex(v['+0x1c']))[0], (x, z)))
                self.champions[out[-1][0]] = bytes.fromhex(v['+0x38']['text']).rstrip(bytes(1)).decode()
        return out

    def first_enter(self, net):
        """what the real server sent when a champion first came into the player's sight in part 2 (239{840 place,
        284, 1255 x2 summoner spells, 1224, ...} 684 635 x3 435 ... 904, all in one tick) -> [(ch, pid, net, body)];
        empty when it was already in sight in the first state of the world"""
        t0 = None
        out = []
        for dt, ch, pid, n, body in self.init + self.rest:
            if t0 is None and n == net and pid == 239:
                t0 = dt
            if t0 is not None:
                if dt > t0 + 0.0005:
                    break
                if n == net and pid in (239, 684, 635, 435, 904, 430):
                    out.append((ch, pid, n, body))
        return out if t0 is not None and t0 > 1.0 else []

    def roles(self):
        """net id -> role. The game info lists each team's players in the order the start state creates them, with
        their position (TOP JUNGLE MIDDLE BOTTOM UTILITY in this recording, read from 618 through the client's own
        reader; 618's format is not learnt yet, so the order is taken as the role)"""
        order = ['TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY']
        return {net: order[i % 5] for i, (net, place) in enumerate(self.heroes())}

    def hero_values(self, net, seconds=10.0):
        """the champion's replicated values as the real server set them in part 2's first seconds"""
        import types
        sys.modules.setdefault('decoded', types.ModuleType('decoded'))
        import pkt_schema as PS
        import repl16
        import replication
        sc = PS.Schema.load(REPLICATION)
        out = {}
        for dt, ch, pid, n, body in self.init + self.rest:
            if dt > seconds:
                break
            if pid != REPLICATION:
                continue
            v = PS.parse(sc, body)
            for unit, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
                if unit == net:
                    out.update(repl16.read_unit(groups))
        return out


class Match:
    def __init__(self, args):
        self.args = args
        self.rec = Recording(opt(args, '--capture', DEFAULT_CAPTURE), float(opt(args, '--init', 1.0)))
        self.passing = {int(x) for x in opt(args, '--pass', '').split(',') if x}
        self.log_c2s = '--log-c2s' in args
        self.t_game = None
        self.server = None
        self.c2s_seen = collections.Counter()
        heroes = self.rec.heroes()
        self.hero_net = int(opt(args, '--hero'), 16) if '--hero' in args else heroes[0][0]
        if '--champion' in args:            # test: the player's creation packet (222) names another champion
            import pkt_schema as PS
            sc = PS.Schema.load(HERO_CREATE)
            for i, (dt, ch, pid, net, body) in enumerate(self.rec.part1):
                if pid == HERO_CREATE:
                    v = PS.parse(sc, body)
                    if struct.unpack('<I', bytes.fromhex(v['+0x1c']))[0] == self.hero_net:
                        v['+0x38'] = {'text': opt(args, '--champion').encode().hex()}
                        self.rec.part1[i] = (dt, ch, pid, net, sc.encode(v))
                        self.rec.champions[self.hero_net] = opt(args, '--champion')
        place = dict(heroes)[self.hero_net]
        import hero16
        values = self.rec.hero_values(self.hero_net)
        self.hero = hero16.Hero(self.hero_net, speed=min(float(values.get('mMoveSpeed', 340.0)), 345.0), place=place, values=values)
        self.log(f'recording {self.rec.cap.name}: part 0 {len(self.rec.part0)}, part 1 {len(self.rec.part1)}, '
                 f'init {len(self.rec.init)} packets; our champion {self.hero_net:#x} at ({place[0]:.0f}, {place[1]:.0f}), '
                 f'{len(values)} values, speed {self.hero.speed:.0f}; passing {sorted(self.passing) or "nothing"}')
        self.world = None
        if '--world' in args:
            import world16
            self.world = world16.World16(live=opt(args, '--capture', DEFAULT_CAPTURE))
            self.world.heroes[self.hero.net] = self.hero
            self.world.player = self.hero
            self.bots = None
            if '--no-bots' not in args:
                import bots16
                self.bots = bots16.Bots(self.world, self.rec, self.hero_net)
                self.log('bots: ' + ', '.join(f'{b.champion} ({b.team} {b.lane})' for b in self.bots.list))
        self.spells = self.shop = None
        if self.world is not None and self.world.structs is not None:
            import spells16
            self.champion = self.rec.champions.get(self.hero_net, 'Garen')
            self.hero.set_champion(self.champion)
            self.spells = spells16.Spells(self.hero, self.champion, self.world.structs.ev)
            import shop16
            self.shop = shop16.Shop(self.hero, self.world.structs.ev)
            self.log(f'spells of {self.champion}: {self.spells.names}')
        # test aid: --hero-at "<game s>:<x>,<z>" puts our champion there at that moment (a one-point move)
        # test aids: --hero-damage <n> (attack damage), --hero-attack "<game s>:<net id hex>" (an attack order)
        if '--hero-damage' in args:
            self.hero.damage = float(opt(args, '--hero-damage'))
        self.hero_attack = []
        if '--hero-attack' in args:
            when, net = opt(args, '--hero-attack').split(':')
            self.hero_attack = [float(when), int(net, 16)]
        self.hero_at = []
        if '--hero-at' in args:
            when, where = opt(args, '--hero-at').split(':')
            self.hero_at = [float(when), tuple(float(c) for c in where.split(','))]

    def log(self, text):
        t = self.server.now() if self.server else 0.0
        print(f'{t:8.3f} {text}', flush=True)

    # ------------------------------------------------------------------ the client
    def on_connect(self, c):
        c.data.update(info=False, ready=0, loading=0, stream=None, pending=None, t_rest=None)

    def game_time(self):
        return None if self.t_game is None else self.server.now() - self.t_game

    def on_packet(self, c, ch, pid, net, body, flags):
        st = c.data
        self.c2s_seen[pid] += 1
        if self.log_c2s or self.c2s_seen[pid] <= 3:
            self.log(f'rcv ch {ch} id {pid} net {net:#x} len {len(body)}: {body[:40].hex()}')
        if pid == PING:
            self.pong(c, body)
        elif pid == HELLO and not st['info']:
            st['info'] = True
            c.send_many([(ch_, p, n, b) for dt, ch_, p, n, b in self.rec.part0])
            self.log(f'part 0 sent: {len(self.rec.part0)} packets (clock, game info)')
        elif pid == LOADING:
            if st['loading'] < len(self.rec.loading):
                c.send(*self.rec.loading[st['loading']])
                st['loading'] += 1
        elif pid == READY:
            st['ready'] += 1
            if st['ready'] == 2:
                c.send_many([(ch_, p, n, b) for dt, ch_, p, n, b in self.rec.part1])
                self.log(f'part 1 sent: the start state, {len(self.rec.part1)} packets')
            elif st['ready'] == 3:
                c.send_many([(ch_, p, n, b) for dt, ch_, p, n, b in self.rec.init if p not in INIT_DROP])
                self.t_game = self.server.now()
                st['t_rest'] = self.server.now()
                st['stream'] = iter([p for p in self.rec.rest if p[2] in self.passing])
                c.send_many(self.hero.start(0.0))
                # no fog of war yet: every champion the player did not see in the first state comes into sight now
                if getattr(self, 'bots', None) is not None:
                    for b in self.bots.list:
                        enter = self.rec.first_enter(b.net)
                        if enter:
                            c.send_many(enter)
                            self.log(f'{b.champion} comes into sight ({len(enter)} packets of the recording)')
                self.log(f'part 2 begins: {len(self.rec.init)} packets of the world\'s first state; our champion\'s values sent')
        elif pid == ORDER and self.t_game is not None:
            out, o = self.hero.on_order(netid_prefix(net) + body, self.game_time(), self.world)
            if o:
                self.log(f'order: place ({o["place"][0]:.0f}, {o["place"][1]:.0f}) target {o["target"]:#x} kind {o["kind"]:#04x} -> {len(out)} packet(s)')
            c.send_many(out)
        elif pid == CAST_REQUEST and self.t_game is not None and self.spells is not None:
            out, text = self.spells.on_request(body, self.game_time(), self.world)
            self.log(text)
            c.send_many(out)
        elif pid == BUY and self.t_game is not None and self.shop is not None:
            out, text = self.shop.on_request(body, self.game_time(), self.world)
            self.log(text)
            c.send_many(out)
        elif pid == SKILL_UP and self.t_game is not None:
            out, slot = self.hero.on_skill_up(netid_prefix(net) + body, self.game_time())
            self.log(f'skill-up: slot {slot} -> {len(out)} packet(s), levels {self.hero.levels}')
            c.send_many(out)

    def pong(self, c, body):
        import c2s16
        import codec16
        if not hasattr(self, '_ping_spec'):
            self._ping_spec = c2s16.load(PING)
        v = c2s16.decode(self._ping_spec, body)
        if v is None:
            return
        got = self.server_time()
        c.send(4, PONG, 0, codec16.encode(PONG, {'+0x10': v[0x10].hex(), '+0x18': struct.pack('<d', got).hex(),
                                                  '+0x20': v[0x18].hex(), '+0x28': struct.pack('<d', self.server_time()).hex()}))

    # the real server's clock (the times in 1007) runs on the recording's base: 9.229 s ahead of the recording's time,
    # so part 2 began at 18.496 [measured: 1007 at rec 0.113 says 9.342]; the start state's clock packets (804 / 371)
    # are in that base, and the client's game clock follows the pings: ours keep the same base
    PING_BASE = 9.229

    def server_time(self):
        if self.t_game is None:
            return self.server.now() + self.PING_BASE
        return self.server.now() - self.t_game + self.rec.cap.gates[2] + self.PING_BASE

    def tick(self, c):
        st = c.data
        if self.t_game is None:
            return
        t = self.game_time()
        out = []
        if st['stream'] is not None:
            limit = self.server.now() - st['t_rest']
            while True:
                if st['pending'] is None:
                    st['pending'] = next(st['stream'], None)
                    if st['pending'] is None:
                        st['stream'] = None
                        break
                if st['pending'][0] > limit:
                    break
                dt, ch, pid, net, body = st['pending']
                out.append((ch, pid, net, body))
                st['pending'] = None
        # the map's own start script, as recorded: 984 switches map geometry layers off (SOG_LASER = the fountain's
        # gate at 11.31 s, SOG_NEXUS at 18.09, the six SOG_<team>_<lane> at 20.09) and 302 at 20.09 [measured live]
        if not hasattr(self, 'timeline'):
            self.timeline = [p for p in self.rec.rest if p[2] in (984, 302) and p[0] < 30.0]
        while self.timeline and self.timeline[0][0] <= t:
            dt, ch, pid, net, body = self.timeline.pop(0)
            out.append((ch, pid, net, body))
            self.log(f'map script: packet {pid} of {dt:.2f} s')
        if not getattr(self, 'gates_open', False) and t >= GATES_OPEN:
            import pkt_schema as PS
            self.gates_open = True
            nets = [n for n, place in self.rec.heroes()]
            for n in nets:
                # the real server's own bytes: its empty list travels in an explicit mode (63); our encoder's constant
                # mode for the same value (01) leaves the client's barrier as it was [user: the gate stayed]
                out.append((1, 557, n, bytes.fromhex('63')))
                out.append((1, 840, n, bytes.fromhex('5d')))
            self.log(f'spawn barrier lifted for {len(nets)} champions (557 + 840)')
        if self.hero_at and t >= self.hero_at[0]:
            self.hero.a = self.hero.b = self.hero_at[1]
            self.hero.poly = None
            self.hero.t0 = t
            out.append(self.hero.move_packet(t, [self.hero_at[1]]))
            self.log(f'our champion put at {self.hero_at[1]}')
            self.hero_at = []
        if self.hero_attack and t >= self.hero_attack[0]:
            self.hero.target = self.hero_attack[1]
            self.log(f'our champion told to attack {self.hero_attack[1]:#x}')
            self.hero_attack = []
        if self.world is not None:
            out += self.world.tick(t)
            if getattr(self, 'bots', None) is not None:
                out += self.bots.tick(t, self.world)
            for ev in self.world.events:
                if ev[0] in ('hero_died', 'structure_falls', 'game_over'):
                    self.log(f'event {ev}')
            self.world.events = [e for e in self.world.events if e[0] not in ('hero_died', 'structure_falls', 'game_over')]
        out += self.hero.tick(t, self.world) if self.world is not None else []
        if self.world is not None:
            out += self.hero.take_events(t, self.world)
            out += self.hero.economy(t, self.world)
        if out:
            c.send_many(out)


def netid_prefix(net):
    import netid16
    return netid16.encode(net)


def main():
    args = sys.argv[1:]
    port = int(args[-1])
    m = Match(args)
    m.server = net16.Server(port, m, log=m.log)
    m.server.run()


if __name__ == '__main__':
    main()
