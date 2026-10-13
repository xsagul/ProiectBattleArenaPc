"""Fog of war: what each team sees, and what the players are told about the rest - as the real server does it.

Measured on the live recording (a unit's time in sight = from its 684 to its 658; every packet about a champion,
a jungle monster or a lane minion of another team counted as sent in or out of sight):

  coming into sight   239 (a container) + 684 (health, 0, full health; a blob) and, the first time, every value the
                      unit replicates (62 for a lane minion); later only the values that changed meanwhile (mostly
                      none). The container holds, the first time, what creates / describes the unit (a lane minion's
                      spawn 439, a monster's level 16, a champion's summoner spells ...).
  the blob            [u8 n][n x 33: 0, slot, count, u16 charges, u32 item, f32 price, u8 1, 19 zero] = the item
                      slots that changed since the team last saw the champion (count 0 + item 0 = emptied);
                      9 zero bytes (two short lists we do not use); u32 unit looked at, u8 2, the place looked at;
                      i32 n + n x (u8 buff slot, i32 count) [ours: none]; a zero byte; then where it is -
                      3 = standing: u32 counter, a zero byte, place, facing; 2 = walking: u32 counter and the
                      unit's movement entry
  going out of sight  658 (empty). The dead stay as they were: a champion until it returns (then 658 + 158), a
                      minion until it is taken away (1090 four seconds after its 1112).
  out of sight        NOT sent: movement, attacks (390, 906, 972), missiles, casts (1215), damage (150), buffs
                      given (435), cooldowns, animations, level-ups (969: the level comes with the replicated
                      values), purchases (63, 1196: the blob's item list brings them), a minion's death and removal.
                      Sent all the same: a monster's creation (514, 568, 967) and death (1112, 1090), a champion's
                      death (166, 421) and return (158), skill ranks (810), a spell put in a slot (78), the end
                      (262) of a buff the player was told the start of.
  only the player     gold (818), the shop's count (1122), the 1050 stamp; xp (1024) only for the player's team.
  how often           sight changes fall on the server's 30 Hz frames; a unit can be back 0.1 s after it left.

Who sees: every living unit of the team within its sight range (the record's perception bubble: champions and
turrets 1350, lane minions 1200), unless a wall is in between (the navigation grid's blocked cells that are not
flagged 'see through'), and a unit standing in brush (the grid's grass flag) only from the same patch of brush
[a: or for a second after it attacks or casts]. Both teams are computed: the other team's is what its bots,
minions and turrets may aim at.
"""
import struct

import numpy as np

# sent whatever is in sight [m]
ALWAYS = frozenset({78, 158, 166, 421, 514, 568, 810, 967})
MONSTER_ALWAYS = frozenset({1112})
# never about anybody but the player's own champion [m]
PLAYER_ONLY = frozenset({818, 1050, 1122})
REVEAL = 1.0                 # s a unit in brush is shown after it attacks or casts [a]


class Vision:
    def __init__(self, game, team, emit):
        self.g, self.team, self.emit = game, team, emit
        self.visible = set()         # net ids of the other teams' units in sight now
        self.known = set()           # ... that were in sight at least once (the players' clients have them)
        self.items_seen = {}         # champion net id -> its inventory as the team last saw it
        self.first_container = {}    # champion net id -> the recorded container of its first coming into sight
        if emit:
            for net, (t0, pk) in game.start['enter'].items():
                body = next((b for ch, pid, n, b in pk if pid == 239), None)
                if body is not None:
                    self.first_container[net] = body

    # ------------------------------------------------------------------ questions
    def sees(self, net):
        """is the unit with this net id in the team's sight (its own units and all structures always are)?"""
        u = self.g.units.get(net)
        return u is None or u.team == self.team or u.is_structure or net in self.visible

    def hidden(self, u):
        return u.team != self.team and not u.is_structure and u.net not in self.visible

    def passes(self, p):
        """may this queued packet (channel, id, the net id it is about, body) go to the team's players?"""
        pid, net = p[1], p[2]
        if pid in ALWAYS or not net:
            return True
        g = self.g
        net = g.pk.owner.get(net, net)               # a missile: its owner decides
        u = g.units.get(net)
        if u is None or u.team == self.team or u.is_structure or net in self.visible:
            return True
        return pid in MONSTER_ALWAYS and u.kind == 'monster'

    # ------------------------------------------------------------------ changes
    def apply(self, now, t):
        g = self.g
        for net in now - self.visible:
            self.visible.add(net)
            if self.emit:
                self.enter(g.units[net], t)
        for net in self.visible - now:
            u = g.units.get(net)
            if u is not None and not u.alive:
                continue                             # the dead stay as they were
            self.visible.discard(net)
            if u is not None and self.emit:
                self.leave(u)

    def enter(self, u, t):
        g = self.g
        pk = g.pk
        first = u.net not in self.known
        self.known.add(u.net)
        inner, prefix, container = [], None, None
        if u.kind == 'minion':
            if first and getattr(u, 'spawn_body', None):
                if getattr(u, 'level_body', None):
                    inner.append((969, u.net, u.level_body))
                inner.append((439, u.net, u.spawn_body))
        elif u.kind == 'monster':
            lvl = getattr(u, 'camp_level', 1)
            if first and lvl > 1:
                inner.append((16, u.net, pk.enc(16, {'+0x10': '00', '+0x11': f'{lvl:02x}'})))
        elif u.is_hero:
            prefix = self.champion_blob(u)
            if first:
                container = self.first_container.get(u.net)
        elif u.kind == 'summon':
            if first and getattr(u, 'spawn_body', None):
                inner.append((626, u.net, u.spawn_body))     # [m: wards] its spawn rides in the first container
        if u.kind == 'summon' and first and getattr(u, 'spawn_pid', 626) == 1038:
            inner = [x for x in inner if x[0] != 626]
        out = pk.enter(t, u.net, u.hp, u.max_hp, u.pos, u.facing, u.path, u.speed, inner, prefix=prefix)
        if u.kind == 'summon' and first and getattr(u, 'spawn_pid', 626) == 1038:
            out.insert(0, (1, 1038, u.net, u.spawn_body))     # a pet's spawn goes before its container [replays]
        if container is not None:
            out[0] = (1, 239, u.net, container)
        for b in getattr(u, 'buff_list', {}).values():       # the buffs it was given out of sight
            if not b.get('known', True):
                b['known'] = True
                src, slot, btype, name_hash, package = b['args']
                out += pk.buff_add(u.net, src, slot, btype, name_hash, max(0.05, b['until'] - t), package=package)
        d = u.take_dirty()
        if d and u.repl_cls:
            out += pk.replication(t, [(u.net, d, u.repl_cls)])
        g.q_first += out

    def leave(self, u):
        if u.is_hero:
            self.items_seen[u.net] = self.inventory(u)
        self.g.q_first += self.g.pk.leave(u.net)

    @staticmethod
    def inventory(u):
        return [(item, u.item_stacks[slot]) if item else None for slot, item in enumerate(u.inventory)]

    def forget(self, net):
        self.visible.discard(net)

    def champion_blob(self, u):
        """the part of a champion's 684 blob before its movement"""
        g = self.g
        now = self.inventory(u)
        seen = self.items_seen.get(u.net) or [None] * len(now)
        entries = b''
        n = 0
        catalog = g.shop.db if getattr(g, 'shop', None) is not None else {}
        for slot, have in enumerate(now):
            if have == seen[slot]:
                continue
            n += 1
            item, count = have or (0, 0)
            price = float((catalog.get(item) or {}).get('total', 0)) if item else 0.0
            entries += (bytes([0, slot, min(count, 255), 0, 0]) + struct.pack('<If', item, price) + b'\x01' +
                        bytes(19))
        self.items_seen[u.net] = now
        tgt = g.units.get(u.target) if u.target else None
        if tgt is not None and self.sees(tgt.net):
            look, look_net = tgt.pos, tgt.net
        else:
            look, look_net = (u.pos[0] + u.facing[0] * 100.0, u.pos[1] + u.facing[1] * 100.0), 0
        return (bytes([n]) + entries + bytes(9) + struct.pack('<IB', look_net, 2) +
                struct.pack('<fff', look[0], g.pk.y(look), look[1]) + struct.pack('<i', 0) + b'\x00')


def look(g, t):
    """one look-around for every team with a Vision (each frame)"""
    units = [u for u in g.units.values() if u.alive]
    n = len(units)
    if not n:
        return
    nav = g.nav
    pos = np.array([u.pos for u in units], dtype=np.float64)
    cx = np.clip(((pos[:, 0] - nav.min_x) // nav.size).astype(np.int64), 0, nav.nx - 1)
    cz = np.clip(((pos[:, 1] - nav.min_z) // nav.size).astype(np.int64), 0, nav.nz - 1)
    brush = g.brush_labels[cz * nav.nx + cx]
    team = np.fromiter((u.team for u in units), dtype=np.int64, count=n)
    solid = np.fromiter((u.is_structure for u in units), dtype=bool, count=n)
    sight2 = np.fromiter((u.sight * u.sight for u in units), dtype=np.float64, count=n)
    shown = np.fromiter((u.reveal_until > t for u in units), dtype=bool, count=n)
    # [m: wards, the replays' stealth] a unit with an invisibility buff (type 6) is out of the other team's sight
    stealthy = np.fromiter((getattr(u, 'stealth_until', 0.0) > t for u in units), dtype=bool, count=n)
    clear = nav.sight_clear
    for v in g.visions.values():
        vi = np.flatnonzero(team == v.team)
        ti = np.flatnonzero((team != v.team) & ~solid)
        now = set()
        if len(vi) and len(ti):
            dx = pos[ti, 0][:, None] - pos[vi, 0][None, :]
            dz = pos[ti, 1][:, None] - pos[vi, 1][None, :]
            d2 = dx * dx + dz * dz
            ok = d2 <= sight2[vi][None, :]
            tb = brush[ti][:, None]
            ok &= (tb == 0) | (tb == brush[vi][None, :]) | shown[ti][:, None]
            ok &= ~stealthy[ti][:, None]
            for a in np.flatnonzero(ok.any(axis=1)):
                cand = np.flatnonzero(ok[a])
                if len(cand) > 1:
                    cand = cand[np.argsort(d2[a, cand])]         # the nearest looker first: most likely a clear line
                ux, uz = pos[ti[a]]
                for b in cand:
                    wx, wz = pos[vi[b]]
                    if clear(wx, wz, ux, uz):
                        now.add(units[ti[a]].net)
                        break
        v.apply(now, t)


def setup(game, session=None):
    """both teams' sight; the players' team is the one whose changes are sent"""
    if session is not None and session.options.get('no_fog'):
        if session.options.get('team_sight'):
            # a spectator's match (the golden test): both teams' sight is worked out for the game's own rules (who may
            # aim at whom, "unseen" buffs) but nothing is held back from the stream and no sight packets are sent
            game.brush_labels = np.array(game.nav.brush(), dtype=np.int32)
            for tm in (100, 200):
                game.visions[tm] = Vision(game, tm, emit=False)
        return
    team = session.player.team if session is not None else 100
    game.brush_labels = np.array(game.nav.brush(), dtype=np.int32)
    for tm in (100, 200):
        game.visions[tm] = Vision(game, tm, emit=(tm == team))
    game.vision = game.visions[team]
