"""One client's connection to a match: the real server's three-part start and the client's requests.

The real server answers the client in three parts [measured on both live recordings; live16.py]:
  0  client 1 + 64            -> 213, clock 804 + 371 (x2), game info 618
     client 197 (loading %)   -> 1095 (the loading screen's progress of every player)
  1  client second 64          -> the start state in one burst (champions, structures, shop, map objects)
  2  client third 64           -> 664 744 278, the world's first state, then the match
     client 841 (every 2 s)    -> 1007 (ping: the request's number and time, our receive and send times)

Parts 0 and 1 and the map's first state are the recorded match's own packets (data/exe1620/start16.pkl), with the
match's roster written into the champions' creation packets (222): the champion's name is all the client needs to
build the whole champion [seen in the client: Ezreal from Garen's recorded slot]. Everything after is the
simulation's (core/game.py).
"""
import json
import os
import struct
import time

from . import c2s
from . import gamedata as G
from . import packets as P
from .game import Game, DT

PONG, LOADING_ANSWER, HERO_CREATE, GAME_INFO = 1007, 1095, 222, 618
INFO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'exe1620', 'info16.json')
SUMMONER = {0x06496ea8: 'SummonerFlash', 0x06364f24: 'SummonerDot', 0x065e8695: 'SummonerSmite', 0x0364af1c: 'SummonerHeal',
            0x0ccfb982: 'SummonerBarrier', 0x004f1364: 'SummonerTeleport', 0x064acc95: 'SummonerHaste',
            0x08a8bae4: 'SummonerExhaust', 0x064d2094: 'SummonerBoost'}
GATES_OPEN = 15.084              # [m] the spawn barrier: 557 + 840 for every champion at 15.084 s
# [m: the live recording 0.238 s after, 6 replays 0 - 0.23 s (a script update)] the two spawn barriers' visuals (map
# objects the client makes itself, the same net ids in every match) are taken away (584) - without it the gate stays
# on screen though champions walk through it
GATE_FX, GATE_FX_DELAY = (0x400000f2, 0x400000f3), 0.238
PING_BASE = 9.229                # [m] the real server's clock ran this far ahead of the recording's first packet
MAX_CATCH_UP = 6                 # frames simulated in one call when the loop falls behind


class Session:
    """the handler net16.Server talks to"""
    def __init__(self, roster=None, log=None, options=None):
        self.options = options or {}
        self.log_fn = log or (lambda s: print(s, flush=True))
        self.server = None
        self.game = Game(roster, log=self.log_fn)
        self.start = self.game.start
        self.player = self.game.heroes[int(self.options.get('player_slot', 0))]
        self.game.watch.add(self.player.net)
        self.game.player_team = self.player.team
        self.t0 = None                   # server time at which game time 0 was
        self.gates_open = False
        self.timeline = list(self.start['timeline'])
        self.seen = {}
        self.hooks = []                  # fn(session, t) test aids run every frame
        # the champion each slot held in the recording (its 222's name)
        self.recorded_names = {u.net: bytes.fromhex(h['values']['+0x38']['text']).decode()
                               for h, u in zip(self.start['heroes'], self.game.heroes)}
        self.part1 = self.roster_part1()
        self.part0 = self.roster_part0()
        self.part1 = self.rune_packets(self.part1)
        self.frames = 0
        self.late = 0.0
        self.load_systems()

    def load_systems(self):
        g = self.game
        for name in ('vision', 'effects', 'templates', 'summons', 'spells', 'passives', 'statbuffs', 'pet', 'condbuffs', 'animstates', 'renewals', 'sounds', 'itembuffs', 'kits', 'tooltips', 'shop', 'jungle', 'plants', 'bbengine', 'bots'):
            try:
                mod = __import__(f'core.{name}', fromlist=['setup'])
            except ImportError:
                continue
            mod.setup(g, self)

    def log(self, text):
        t = self.server.now() if self.server else 0.0
        self.log_fn(f'[{t:8.3f}] {text}')

    # ------------------------------------------------------------------ the start state for this roster
    def roster_part1(self):
        out = list(self.start['part1'])
        sc = self.game.pk.schema(HERO_CREATE)
        for h, u in zip(self.start['heroes'], self.game.heroes):
            v = dict(h['values'])
            v['+0x38'] = P.text(u.name)
            if u.player_name:
                v['+0x58'] = P.text(u.player_name)
            v['+0x52'] = '01' if u.bot else '00'
            if u is self.player and self.options.get('skin'):
                v['+0x48'] = P.u32(int(self.options['skin']))       # the skin's number [a: the u32 after the name]
            ch, pid, net, body = out[h['index']]
            out[h['index']] = (ch, pid, net, sc.encode(v))
        return [p for p in out if not self.recorded_champions_buff(*p[-3:])]

    def rune_packets(self, part1):
        """every champion's rune page (runes.py): its 905 written again, the stat shards applied"""
        from . import runes
        g = self.game
        out = []
        for row in part1:
            ch, pid, net, body = row[-4:]
            u = g.units.get(net) if pid == 905 else None
            if u is not None and u.is_hero:
                picked = self.options.get('runes') if u is self.player else None
                if getattr(u, 'roster_perks', None):
                    picked = runes.custom_page(u.net, u.roster_perks)
                u.rune_page = picked if picked in runes.PAGES else runes.page_for(u.name)
                try:
                    row = tuple(row[:-1]) + (runes.packet(g.pk, body, u),)
                except Exception as e:                   # the recorded page stays
                    self.log(f'runes of {u.name}: {e!r}')
                runes.apply(u)
                u.recompute()
                u.hp = u.max_hp
            out.append(row)
        return out

    def recorded_champions_buff(self, pid, net, body):
        """a buff of the recorded start state that is the recorded champion's own (its passive ...) on a slot that now
        holds another champion: told by the buff's package hash, which is the champion's (gamedata.package_hash)"""
        if pid != 435:
            return False
        was = self.recorded_names.get(net)
        u = self.game.units.get(net)
        if was is None or u is None or u.name == was:
            return False
        import pkt_schema as PS
        try:
            v = PS.parse(self.game.pk.schema(435), body)
        except Exception:
            return False
        return bool(v) and v.get('+0x5c') == P.u32(G.package_hash(was))

    def roster_part0(self):
        """the game info (618) with this match's roster: the recorded packet's ten player records (champion id and
        name, position, summoner spells, team; tools/build_info16.py) written again with our champions and spliced
        into the recorded bytes - the rest of 618 (the match configuration) stays as recorded"""
        out = list(self.start['part0'])
        if not os.path.exists(INFO):
            return out
        info = json.load(open(INFO))
        body = bytearray.fromhex(info['body'])
        sc = self.game.pk.schema(GAME_INFO)
        records = info['extras']
        import pkt_schema as PS
        for rec, u in sorted(zip(records, self.game.heroes), key=lambda x: -x[0]['span'][0]):
            v = dict(rec['values'])
            u.summoners = [SUMMONER.get(P.struct.unpack('<I', bytes.fromhex(v[k]))[0], 'SummonerFlash') for k in ('+0x98', '+0x20')]
            changed = {}
            if u.name != bytes.fromhex(v['+0x48']['text']).decode():
                changed = {'+0x2c': P.u32(u.champ.champion_id), '+0x48': P.text(u.name), '+0xb0': P.text(u.name)}
                v.update(changed)
            picked = self.options.get('summoners') if u is self.player else None
            if picked:
                # the player's own two spells: the record names them by the ELF hash of their names
                picked = [s for s in picked if s in SUMMONER.values()][:2]
                if len(picked) == 2 and picked[0] != picked[1]:
                    u.summoners = picked
                    spells = {'+0x98': P.u32(P.elf(picked[0])), '+0x20': P.u32(P.elf(picked[1]))}
                    v.update(spells)
                    changed.update(spells)
            # the record's own header modes are kept (the client refuses the record in other modes [measured]); a
            # changed field whose recorded mode cannot hold the new value takes the first mode that can
            st = sc.structs[rec['key']]
            forced = {int(k): m for k, m in rec['modes'].items()}
            for fl in st['fields']:
                name = f'+{fl["off"]:#x}' if fl['off'] is not None else None
                if name in changed and not PS.fits(fl['modes'][forced[fl['bit']]], v[name], fl):
                    del forced[fl['bit']]
            forced['spare'] = rec['spare']
            a, b = rec['span']
            body[a:b] = sc.encode_struct(rec['key'], v, {rec['key']: forced}) + bytes.fromhex(rec['tail'])
        for i, (ch, pid, net, old) in enumerate(out):
            if pid == GAME_INFO:
                out[i] = (ch, pid, net, bytes(body))
        return out

    # ------------------------------------------------------------------ the client
    def on_connect(self, c):
        c.data.update(info=False, ready=0, loading=0)
        self.conn = c

    def game_time(self):
        return None if self.t0 is None else self.server.now() - self.t0

    def server_time(self):
        if self.t0 is None:
            return self.server.now() + PING_BASE
        return self.server.now() - self.t0 + self.start['gates'][2] + PING_BASE

    def on_packet(self, c, ch, pid, net, body, flags):
        st = c.data
        n = self.seen[pid] = self.seen.get(pid, 0) + 1
        if n <= 2 and pid not in (807, 1042):
            self.log(f'rcv ch {ch} id {pid} net {net:#x} len {len(body)}: {body[:32].hex()}')
        if pid == c2s.PING:
            v = c2s.ping(body)
            if v is not None:
                got = self.server_time()
                c.send(4, PONG, 0, self.game.pk.enc(PONG, {'+0x10': v[0].hex(), '+0x18': struct.pack('<d', got).hex(),
                                                           '+0x20': v[1].hex(), '+0x28': struct.pack('<d', self.server_time()).hex()}))
        elif pid == c2s.HEARTBEAT:
            answer = c2s.heartbeat_answer(body)
            if answer is not None:
                c.send(ch, c2s.HEARTBEAT_ANSWER, 0, answer)
        elif pid == c2s.HELLO and not st['info']:
            st['info'] = True
            c.send_many(self.part0)
            self.log(f'part 0 sent: {len(self.part0)} packets (clock, game info)')
        elif pid == c2s.LOADING:
            if st['loading'] < len(self.start['loading']):
                c.send(*self.start['loading'][st['loading']])
                st['loading'] += 1
        elif pid == c2s.READY:
            st['ready'] += 1
            if st['ready'] == 2:
                c.send_many(self.part1)
                self.log(f'part 1 sent: the start state, {len(self.part1)} packets')
            elif st['ready'] == 3:
                self.begin(c)
        elif self.t0 is not None:
            self.request(c, pid, net, body)

    def begin(self, c):
        """part 2: the recorded first state of the world, then our own units' state"""
        c.send_many([(ch, pid, net, body) for t, ch, pid, net, body in self.start['init']
                     if not self.recorded_champions_buff(pid, net, body)])
        self.t0 = self.server.now()
        g = self.game
        out = g.start_packets()
        v = g.vision
        for h in g.heroes[1:]:
            t_enter, pk = self.start['enter'].get(h.net, (None, []))
            early = t_enter is not None and t_enter <= 1.0            # the recorded first state brought it into sight
            if v is None or h.team == v.team:
                if pk and not early:
                    out += pk
            elif early:
                # with the fog of war the other team's champions come into sight when they are seen; one the
                # recorded first state shows is taken out again by the first look-around
                v.visible.add(h.net)
                v.known.add(h.net)
        # [m] the recorded start hides every champion's health bar (710 {0} at -0.3 s); the real server shows them at
        # 4.4 s (710 {1}, with the spawn animation) - after the part of the recording we replay
        for h in g.heroes:
            out.append((1, 710, h.net, g.pk.enc(710, {'+0x10': '01'})))
        if self.options.get('summoners'):
            for slot, name in zip((4, 5), self.player.summoners):       # the spells in the player's D and F slots
                out += g.pk.spell_in_slot(self.player.net, slot, name)
        c.send_many(out)
        self.log(f'part 2 begins: {len(self.start["init"])} packets of the world\'s first state, then ours ({len(out)})')

    def request(self, c, pid, net, body):
        g, h = self.game, self.player
        if pid == c2s.ORDER:
            o = c2s.order(body)
            if o is None:
                return
            u = g.units.get(o['target']) if o['target'] else None
            if u is not None and u.alive and u.team != h.team and u.targetable:
                h.order_attack(u.net)
            elif 0 < o['place'][0] < 16000 and 0 < o['place'][1] < 16000:
                h.order_move(o['place'])
        elif pid == c2s.SKILL_UP:
            slot = c2s.skill(body)
            if slot is not None:
                ok = h.level_spell(slot)
                self.log(f'skill-up slot {slot}: {"ok" if ok else "refused"}, levels {h.spell_levels}')
        elif pid == c2s.CAST and g.spells is not None:
            r = c2s.cast(body)
            if r is not None:
                self.log(g.spells.request(h, r))
        elif pid == c2s.BUY and getattr(g, 'shop', None) is not None:
            item = c2s.buy(body)
            if item is not None:
                self.log(g.shop.buy(h, item))
        elif getattr(g, 'shop', None) is not None and pid in (c2s.SELL, c2s.UNDO, c2s.SWAP):
            self.log(g.shop.other(h, pid, body))
        elif pid == c2s.RECALL_REQUEST and g.spells is not None:
            self.log(g.spells.recall(h))

    # ------------------------------------------------------------------ the clock
    def tick(self, c):
        if self.t0 is None:
            return
        g = self.game
        now = self.server.now() - self.t0
        out = []
        n = 0
        while g.t + DT <= now and n < MAX_CATCH_UP:
            t = g.t + DT
            while self.timeline and self.timeline[0][0] <= t:      # the map's own start script, as recorded
                tt, ch, pid, net, body = self.timeline.pop(0)
                out.append((ch, pid, net, body))
            if not self.gates_open and t >= GATES_OPEN:
                self.gates_open = True
                for h in g.heroes:
                    if h.team != self.player.team:
                        continue             # [m: the live recording] a player is told its own team's five (a replay all ten)
                    # the real server's own bytes: its empty list travels in an explicit mode [m]
                    out.append((1, 557, h.net, bytes.fromhex('63')))
                    out.append((1, 840, h.net, bytes.fromhex('5d')))
                self.log('spawn barrier lifted (557 + 840)')
            if self.gates_open and not getattr(self, 'gate_fx_gone', False) and t >= GATES_OPEN + GATE_FX_DELAY:
                self.gate_fx_gone = True
                for fx in GATE_FX:
                    out.append((1, 584, 0, g.pk.enc(584, {'+0x10': '00', '+0x14': P.u32(fx)})))
            for fn in self.hooks:
                fn(self, t)
            out += g.step(DT)
            n += 1
        if n == MAX_CATCH_UP and g.t + DT <= now:
            self.late += now - g.t
            g.t = now                              # too far behind: drop the lost time rather than spiral
        self.frames += n
        if out:
            c.send_many(out)
