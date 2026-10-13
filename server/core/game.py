"""The match: one simulation of Summoner's Rift, stepped 30 times a second as the real server is (its packets to
a player leave in bursts 33-34 ms apart [measured on the live recording, 8650 bursts]).

A frame, in the order the real server's packets show (movement first, then what happened in the order it
happened, the changed replicated values near the end, removals last):
    1  what was scheduled for this moment (missiles landing, units removed, respawns)
    2  the map's own script: minion waves (BarracksConfig), jungle camps
    3  who sees whom (vision.py): units come into / go out of each team's sight
    4  champions: orders, basic attacks, regeneration, gold; bots think
    5  minions, monsters, turrets: look around, attack
    6  spells in flight, areas, buffs
    7  every unit walks
    8  the frame's packets: sight changes, 61 (paths changed), the events, 287 (values changed), removals -
       without what the players may not know (vision.py's rules)

The simulation writes no bytes: units call packets.py through self.pk and put the result in self.q.
"""
import heapq
import math
import struct
import os
import pickle
import random
import sys

from . import gamedata as G
from . import packets as P
from . import ai
from . import pet
from . import vision
from .units import Unit, Minion, Monster, Turret, Inhibitor, Nexus, dist, ORDER, CHAOS, NEUTRAL
from .heroes import Hero, KILL_GOLD, ASSIST_POOL, ASSIST_WINDOW

HELPING_HAND = {1056, 1054, 1120, 3070}
GENERIC_DAMAGE = 0x6a4229fc       # [m] the 150 name of item / rune damage without a name of its own ('fc29426a')
MONSTER_CURRENT_HP = {'SRU_Blue': 0.05, 'SRU_Red': 0.05, 'SRU_Gromp': 0.05, 'SRU_Krug': 0.03, 'SRU_Murkwolf': 0.03,
                      'SRU_Razorbeak': 0.03}
SCRIPT_UPDATE = 0.26729          # [m] a script's update period: 8 of the real server's frames (~33.4 ms each)
# [m: the replays' frame stamps 33-34 ms apart, the script updates 8 frames; 10-13: the waves' drift] the real server's
# frame is 33.41 ms, not 1/30 s: its timers fire on the first frame at or past their due time, so a timer re-armed from
# its own firing drifts by about half a frame each time (the waves: 30.04, 60.12, 90.13, 120.15 ...)
DT = SCRIPT_UPDATE / 8.0
# [m: 6 replays, 330 waves] the wave timer is re-armed on the frame it fired, a frame that comes late by a random part of
# a (jittered) frame: each wave comes 0.0191 s later than the last one's time + the interval on average (0 - 0.10), the
# first one 0.036 - 0.060 s after its 30 s; our frames are regular, so the mean is added to the due times
WAVE_SLIP, WAVE_START = 0.0191, 0.03
UPDATE_FRAMES = 8                # [m] a script update every 8 frames
FIRST_FRAMES = 4                 # [m] a new script's first update 0 - 8 frames after it was made: the middle
SCRIPT_FIRST = 0.134             # [m] a new script's first update: 0 - 0.27 s after it was made (the middle)
NET_BASE = 0x40002000            # our own units' net ids (the recorded start state uses up to about 0x400002b3)
CORPSE = 4.0                     # [m] a dead minion is removed four seconds after its death
INHIBITOR_RESPAWN = 300          # [m] s: the chaos mid inhibitor fell at 1443.29 and was back at 1743.26
INHIBITOR_GOLD = 50.0            # [wiki] to the champion that destroys it
# turret numbers the real server sets in the first second [m: live replication]: health, attack damage, armor = mr
TURRET = {'outer': (9000.0, 182.0, 60.0), 'inner': (5000.0, 187.0, 60.0), 'inhibitor': (4750.0, 187.0, 60.0),
          'nexus': (3500.0, 165.0, 60.0), 'fountain': (9999.0, 999.0, 0.0)}
TURRET_TIER = {0: 'outer', 2: 'inner', 1: 'inhibitor', 4: 'nexus', 5: 'nexus'}
# what a turret shot takes from a minion, as a share of its full health [a: LoL's usual rule]
TURRET_VS_MINION = {4: 0.45, 5: 0.70, 6: 0.14, 7: 0.05}
TURRET_GOLD_LOCAL, TURRET_GOLD_GLOBAL = 250.0, 50.0
# the six barracks' net ids in the start state [m: the replay, where every spawn is seen with its place]
BARRACKS_NET = {(ORDER, 'bot'): 0x40000089, (ORDER, 'top'): 0x40000090, (ORDER, 'mid'): 0x40000099,
                (CHAOS, 'mid'): 0x40000095, (CHAOS, 'top'): 0x400000aa, (CHAOS, 'bot'): 0x400000ad}
START = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'exe1620', 'start16.pkl')


class Game:
    def __init__(self, roster=None, log=None, seed=1620):
        import navgrid
        self.data = G.map11()
        self.pk = P.Packets()
        self.nav = navgrid.grid()
        self.pk.height = self.nav.height
        self.start = pickle.load(open(START, 'rb'))
        self.rng = random.Random(int(os.environ.get('BA_SEED', seed)))      # BA_SEED: the golden test's noise check
        self.t = 0.0
        self.frame = 0
        self.frame_heap = []              # (frame, seq, fn): after_frames
        self.units = {}
        self.heroes, self.minions, self.monsters, self.turrets, self.structures = [], [], [], [], []
        self.heap, self.seq = [], 0
        self.q_moves, self.q, self.q_late = [], [], []
        self.q_first = []                # a unit coming into / going out of the players' sight: before the frame's rest
        self.q_all = []                  # packets for everyone whatever is in sight (a monster's creation)
        self.visions = {}                # team -> vision.Vision: what the team sees (empty = no fog of war)
        self.vision = None               # ... the players' team's: its changes are sent
        self.player_team = ORDER
        self.towers_down = 0
        self.next_net = NET_BASE
        self._log = log or (lambda s: print(s, flush=True))
        self.watch = set()               # net ids of champions played by clients (floating numbers go to them)
        self.over = None                 # the team that lost
        self.wave = 0
        self.next_wave = None             # the next wave's due time (each re-armed from the last one's real frame)
        self.real_frames = False          # stepped on a real match's frame moments (tools/replay_golden16.py)
        self.spells = None               # spells.Spells, set by the session when available
        self.fx = None                   # effects.Effects: the scripts' visual effects
        self.jungle = None
        self.systems = []                # extra per-frame systems: fn(t, dt)
        self.setup_structures()
        self.setup_barracks()
        self.setup_heroes(roster)

    # ------------------------------------------------------------------ small things
    def log(self, text):
        self._log(f'{self.t:8.2f} {text}')

    def new_net(self):
        self.next_net += 1
        return self.next_net

    def at(self, when, fn):
        self.seq += 1
        heapq.heappush(self.heap, (when, self.seq, fn))

    def after_frames(self, n, fn):
        """fn(t) n frames from now [m: Riot's scripts are updated every 8 frames, whatever a frame lasted]"""
        self.seq += 1
        heapq.heappush(self.frame_heap, (self.frame + max(1, int(n)), self.seq, fn))

    def script_timer(self, period, fn, count=None, first=True, alive=None):
        """a script's periodic timer as Riot's server runs it [m: Ignite, Burning, the role quests, static heartbeats in
        the replays]: the script is updated every SCRIPT_UPDATE s (0.25 s on 30 Hz frames = 8 frames), its first
        update SCRIPT_FIRST after it was made (the real ones: 0 - 0.27 s, the middle taken); a timer of `period` adds
        each update's time and fires when it reaches the period, keeping the rest (1 s: 1.069, 1.069, 1.069, 0.802 ...).
        fn(t) is called `count` times (None: until alive() is false); first: it fires on the first update too"""
        state = {'acc': 0.0, 'left': count, 'first': first, 'last': None}

        def update(t):
            if alive is not None and not alive():
                return
            fire = False
            step = t - state['last'] if state['last'] is not None else SCRIPT_UPDATE
            state['last'] = t
            if state['first']:
                state['first'] = False
                fire = True
            else:
                state['acc'] += step
                if state['acc'] >= period - 1e-6:
                    state['acc'] -= period
                    fire = True
            if fire:
                fn(t)
                if state['left'] is not None:
                    state['left'] -= 1
                    if state['left'] <= 0:
                        return
            self.after_frames(UPDATE_FRAMES, update)
        self.after_frames(FIRST_FRAMES, update)

    def add(self, u):
        self.units[u.net] = u
        return u

    def stat_outputs(self, u, zero_first=False, queue='q'):
        """294 [m: replays] a new minion's / monster's / 626 unit's stat formula outputs: on its first script update
        (0 - 0.27 s after it was made: SCRIPT_FIRST), a 626 unit also gets the zero values at once"""
        if zero_first:
            getattr(self, queue).append(self.pk.stat_outputs(u.net, False))
        self.after_frames(FIRST_FRAMES, lambda t, u=u: getattr(self, queue).append(self.pk.stat_outputs(u.net))
                          if u.net in self.units else None)

    def seen_by(self, team, u):
        """may the team's units act on u (aim at it)? - its own units, structures and what is in its sight"""
        v = self.visions.get(team)
        return v is None or u.team == team or u.is_structure or u.net in v.visible

    def tell_all(self, packets):
        """queue packets that go out whatever is in sight (marked: the frame's output does not hold them back)"""
        self.q += [p + (True,) for p in packets]

    def enemies_near(self, u, radius, kinds=None):
        """[(distance, unit)] of the living, targetable units of another team within radius of u"""
        out = []
        px, pz = u.pos
        for o in self.units.values():
            if o.team == u.team or not o.alive or not o.targetable or o.kind == 'plant':
                continue
            if kinds is not None and o.kind not in kinds:
                continue
            d = math.hypot(o.pos[0] - px, o.pos[1] - pz)
            if d <= radius:
                out.append((d, o))
        return out

    def units_in(self, center, radius, team_not=None, kinds=None):
        out = []
        for o in self.units.values():
            if not o.alive or (team_not is not None and o.team == team_not) or o.kind == 'plant':
                continue
            if kinds is not None and o.kind not in kinds:
                continue
            if math.hypot(o.pos[0] - center[0], o.pos[1] - center[1]) <= radius + o.radius:
                out.append(o)
        return out

    # ------------------------------------------------------------------ the map's units
    def setup_structures(self):
        forms = self.pk.forms
        live = [(d['net'], tuple(d['pos'])) for d in forms['turrets']]
        live += [(int(n, 16), tuple(d['pos'])) for n, d in forms['others'].items()]
        base_turret = G.unit('Turret')
        for s in self.data['structures']:
            net = min(live, key=lambda x: dist(x[1], s['pos']))
            if dist(net[1], s['pos']) > 400:
                continue
            net = net[0]
            ch = s['character']
            if ch == 'Turret' or ch.startswith('SRUAP_'):
                tier = TURRET_TIER.get(s['position'], 'outer') if ch == 'Turret' else 'fountain'
                hp, ad, armor = TURRET[tier]
                base = dict(G.unit(ch) or base_turret, hp=hp, ad=ad, armor=armor, mr=armor)
                if tier == 'fountain':
                    base.update(range=1250.0, **{'as': 2.5})
                u = Turret(self, net, s['team'], ch, s['pos'], base, s['lane'], tier)
                u.targetable = tier == 'outer'
                self.turrets.append(u)
            elif ch == 'Inhibitor':
                u = Inhibitor(self, net, s['team'], ch, s['pos'], dict(G.unit(ch)), s['lane'], 'dampener')
            elif ch == 'Nexus':
                u = Nexus(self, net, s['team'], ch, s['pos'], dict(G.unit(ch)), 'base', 'hq')
            else:
                continue
            u.sent = {'mHP': u.hp, 'mMaxHP': u.max_hp}
            self.structures.append(self.add(u))

    def setup_barracks(self):
        self.barracks = []
        for b in self.data['barracks']:
            net = BARRACKS_NET[(b['team'], b['lane'])]
            lane = [tuple(p) for p in self.data['lanes'][b['lane']]]
            if b['team'] == CHAOS:
                lane = lane[::-1]
            cfg = self.data['waves'][b['config']]
            self.barracks.append({'net': net, 'team': b['team'], 'lane': b['lane'], 'pos': tuple(b['pos']), 'points': lane, 'cfg': cfg})
        cfg = self.barracks[0]['cfg']
        self.wave_first, self.wave_period = float(cfg.get('InitialSpawnTimeSecs', 30)), float(cfg.get('WaveSpawnIntervalSecs', 30))
        self.wave_gap = float(cfg.get('MinionSpawnIntervalSecs', 0.8))

    def setup_heroes(self, roster):
        rec = self.start['heroes']
        roster = roster or [{} for _ in rec]
        for i, h in enumerate(rec):
            r = roster[i] if i < len(roster) else {}
            champ = r.get('champion') or h['champion']
            tpl = self.start['hero_values'].get(h['net']) or self.start['hero_values'][rec[0]['net']]
            u = Hero(self, h['net'], h['team'], champ, h['pos'], tpl, r.get('name') or h['name'], bot=r.get('bot', i > 0), slot=i)
            u.role = r.get('role') or ('TOP', 'JUNGLE', 'MIDDLE', 'BOTTOM', 'UTILITY')[i % 5]
            u.roster_perks = r.get('perks')                # a page given whole (the replay's players' own)
            self.heroes.append(self.add(u))

    def start_packets(self):
        """the first values of our own units' state, sent when part 2 begins: every champion's full replicated
        state, the structures that can be attacked"""
        units = [(h.net, h.start_values(), 'AIHero') for h in self.heroes]
        for h in self.heroes:
            h.sent.update(units[self.heroes.index(h)][1])
        return self.pk.replication(self.t, units)

    # ------------------------------------------------------------------ waves (the map's BarracksConfig)
    def wave_counts(self, cfg, n, t, team):
        """how many of each minion type wave n holds: [(type, character, upgrade data, count)] in spawn order"""
        out = []
        supers = 0
        for u in cfg['units']:
            c = self.behavior_count(u.get('behavior'), n, t, team, cfg)
            if u['type'] == 7:
                supers = c
            out.append([u['type'], u['character'], u.get('upgrade') or {}, c])
        if supers:
            for o in out:
                if o[0] == 6:
                    o[3] = 0                     # a lane with super minions sends no siege minion
        return [o for o in out if o[3] > 0]

    def behavior_count(self, b, n, t, team, cfg):
        if not isinstance(b, dict):
            return 0
        kind = b.get('_type')
        if kind == 'ConstantWaveBehavior':
            return int(b.get('SpawnCount', 0))
        if kind == 'RotatingWaveBehavior':
            lst = b.get('SpawnCountsByWave') or [0]
            return int(lst[(n - 1) % len(lst)])
        if kind == 'TimedVariableWaveBehavior':
            cur = None
            for info in b.get('behaviors', []):
                if t >= float(info.get('StartTimeSecs', 0)):
                    cur = info.get('Behavior')
            return self.behavior_count(cur, n, t, team, cfg)
        if kind == 'InhibitorWaveBehavior':
            return 0                              # set per lane in spawn_wave (the enemy inhibitors that are down)
        return 0

    def wave_interval(self, t):
        """[m: three replays' 55 waves each] 30 s, then 25 s once the next wave would come at 14:00 or later, 20 s once
        it would come at 30:00 or later (the waves at 810.5 / 840.5 / 865.5 and 1766.1 / 1791.1 / 1811.1)"""
        if t + 20.0 >= 1800.0:
            return 20.0
        if t + 25.0 >= 840.0:
            return 25.0
        return self.wave_period

    def spawn_wave(self, n):
        """a wave now [m]: each barracks' minions one after the other, every MinionSpawnIntervalSecs from the last one's
        real spawn (0.80 - 0.81 s apart in the replays: the timer re-armed on its frame)"""
        t0 = self.t
        for b in self.barracks:
            if b['net'] is None:
                continue
            counts = self.wave_counts(b['cfg'], n, t0, b['team'])
            down = [s for s in self.structures if s.kind == 'inhibitor' and s.team != b['team'] and not s.alive]
            if any(s.lane == b['lane'] for s in down):
                per = next((u for u in b['cfg']['units'] if u['type'] == 7), None)
                lst = ((per or {}).get('behavior') or {}).get('SpawnCountPerInhibitorDown') or [1, 1, 2]
                k = lst[min(len(down), len(lst)) - 1]
                name = (per or {}).get('character') or ('SRU_OrderMinionSuper' if b['team'] == ORDER else 'SRU_ChaosMinionSuper')
                counts = [[7, name, (per or {}).get('upgrade') or {}, k]] + [c for c in counts if c[0] not in (6, 7)]
            order = []
            for mtype, name, up, count in counts:
                if not name:
                    name = {4: 'Melee', 5: 'Ranged', 6: 'Siege', 7: 'Super'}[mtype]
                    name = f"SRU_{'Order' if b['team'] == ORDER else 'Chaos'}Minion{name}"
                order += [(mtype, name, up)] * count

            self.spawn_next(b, order, n)

    def spawn_next(self, b, order, n):
        """the barracks' next minion of this wave now, the one after it MinionSpawnIntervalSecs later"""
        if not order:
            return
        mtype, name, up = order.pop(0)
        self.spawn_minion(self.t, b, mtype, name, up, n)
        if order:
            self.at(self.t + self.wave_gap, lambda t: self.spawn_next(b, order, n))

    def spawn_minion(self, t, b, mtype, name, up, wave):
        if self.over:
            return
        cfg = b['cfg']
        base = dict(G.unit(name) or G.unit('SRU_OrderMinionMelee'))
        # upgrades [m: live values of every wave follow these rules exactly]: one at the first wave, one more every
        # UpgradeIntervalSecs; health += HPUpgrade each; damage += floor(DamageUpgrade x n) for the first five, then
        # DamageUpgrade + DamageUpgradeLate each; armor grows by ArmorUpgradeGrowth x (1 + 2 + ...) from the seventh
        u = 1 + int(max(0.0, t - self.wave_first) // float(cfg.get('UpgradeIntervalSecs', 90)))
        early = int(cfg.get('UpgradesBeforeLateGameScaling', 5))
        base['hp'] += min(float(up.get('HpMaxBonus', 1e9)), float(up.get('HPUpgrade', 0.0)) * u)
        dmg = math.floor(float(up.get('DamageUpgrade', 0.0)) * min(u, early)) + \
            (float(up.get('DamageUpgrade', 0.0)) + float(up.get('DamageUpgradeLate', 0.0))) * max(0, u - early)
        base['ad'] = min(float(up.get('DamageMax', 1e9)), base['ad'] + dmg) if up.get('DamageMax') else base['ad'] + dmg
        k = max(0, u - early - 1)
        base['armor'] += min(float(up.get('ArmorMax', 0.0)), float(up.get('ArmorUpgradeGrowth', 0.0)) * k * (k + 1) / 2)
        base['gold'] = min(float(up.get('GoldMax', 1e9)), base['gold'] + float(up.get('GoldUpgrade', 0.0)) * (u - 1))
        steps = 0
        if t >= float(cfg.get('MoveSpeedIncreaseInitialDelaySecs', 1e9)):
            steps = min(int(cfg.get('MoveSpeedIncreaseMaxTimes', 0)),
                        1 + int((t - float(cfg['MoveSpeedIncreaseInitialDelaySecs'])) // float(cfg.get('MoveSpeedIncreaseIntervalSecs', 300))))
        base['speed'] += steps * float(cfg.get('MoveSpeedIncreaseIncrement', 0))
        m = Minion(self, self.new_net(), b['team'], name, b['pos'], base, mtype, wave, b['lane'], b['net'])
        m.lane_points = b['points']
        m.lane_i = 0
        m.path = [b['points'][0]]                        # the way out of the barracks: the client walks it from 684
        m.xp_radius = float(base.get('xp_radius') or cfg.get('ExpRadius', 1400.0))
        self.minions.append(self.add(m))
        # [m: 3,200 minions of two replays, 99.8 %] its level = its team's champions' average level, rounded down
        own = [h.level for h in self.heroes if h.team == b['team']]
        m.level = int(sum(own) / len(own) + 1e-6) if own else 1
        spawn = self.pk.minion_spawn(t, m.net, b['net'], mtype, wave, m.hp, m.max_hp, m.speed, [m.pos, b['points'][0]], m.level)
        m.dirty = ai.minion_values(self, m)
        if self.vision is not None and m.team != self.vision.team:
            # the other team's minion: the player learns of it when it first comes into sight (its spawn rides in
            # that moment's container)
            m.spawn_body = self.pk.inner_body(spawn[0])
            m.level_body = self.pk.minion_level(m.level) if m.level > 1 else None
        else:
            self.q += spawn
        self.stat_outputs(m)

    def entered(self, u):
        """the unit comes into the players' sight at once (without the fog of war: every unit does when it appears)"""
        if self.vision is not None:
            return                               # the vision system brings it into sight when it is seen
        inner = []
        lvl = getattr(u, 'camp_level', 1)
        if u.kind == 'monster' and lvl > 1:
            inner.append((16, u.net, self.pk.enc(16, {'+0x10': '00', '+0x11': f'{lvl:02x}'})))
        self.q += self.pk.enter(self.t, u.net, u.hp, u.max_hp, u.pos, u.facing, u.path, u.speed, inner)

    # ------------------------------------------------------------------ damage and death
    def mitigate(self, src, tgt, amount, dtype):
        if dtype == P.TRUE:
            return amount
        res = tgt.armor if dtype == P.PHYSICAL else tgt.mr
        if src is not None and src.is_hero:
            if dtype == P.PHYSICAL:
                res = res * (1.0 - src.bonus.get('armor_pen', 0.0)) - src.bonus.get('lethality', 0.0)
            else:
                res = res * (1.0 - src.bonus.get('magic_pen_pct', 0.0)) - src.bonus.get('magic_pen', 0.0)
            res = max(res, min(0.0, tgt.armor if dtype == P.PHYSICAL else tgt.mr))
        return amount * (100.0 / (100.0 + res) if res >= 0 else 2.0 - 100.0 / (100.0 - res))

    def basic_hit(self, src, tgt):
        """a basic attack lands"""
        if tgt.kind == 'plant':
            if getattr(self, 'plants', None) is not None:
                self.plants.hit(src, tgt)                # a plant is set off, not damaged (core/plants.py)
            return
        bb = getattr(self, 'bb', None)
        if bb is not None and src.is_hero and bb.handles(src):
            if bb.attack_hit(src, tgt):
                return                                   # the attack was a script's (an overridden attack)
        amount, crit = src.ad, False
        if src.kind == 'turret':
            if tgt.kind == 'minion':
                self.deal(src, tgt, TURRET_VS_MINION.get(tgt.mtype, 0.45) * tgt.max_hp, P.TRUE, basic=True,
                          spell_hash=P.elf(src.attack_name) if src.attack_name else 0)
                return
            if tgt.is_hero:                         # the shots at one champion grow: +40 % each, up to +120 % [a]
                amount *= 1.0 + 0.4 * min(3, src.heat)
                src.heat += 1
        elif src.is_hero and src.attack_crit:
            amount, crit = amount * 1.75, True
        if tgt.is_structure and src.kind == 'minion':
            amount *= 0.6 if src.mtype in (4, 5) else 1.0          # [a] lane minions hit structures for less
        dtype = P.PHYSICAL
        if src.kind == 'monster':
            # [wiki: the camps' notes; m: 4 replays' first clears, residual 0.1] large monsters' attacks add a share of
            # the target's current health; Gromp's are magic damage. A jungler takes half (core/pet.py: Pets.modify)
            stem = src.name.split('.')[0]
            amount += MONSTER_CURRENT_HP.get(stem, 0.0) * tgt.hp
            if stem == 'SRU_Gromp':
                dtype = P.MAGIC
        kits = getattr(self, 'kits', None)
        if kits is not None and src.is_hero:
            k = kits.of(src)
            if k is not None and hasattr(k, 'attack_hit'):
                amount = k.attack_hit(src, tgt, amount)
        if src.is_hero and tgt.kind == 'minion' and HELPING_HAND & set(getattr(src, 'inventory', None) or ()):
            # [wiki: Doran's Ring / Shield / Helm, Tear of the Goddess - Helping Hand; m: its own 150 'fc29426a', 5.0
            # physical, in the attack's frame before the attack's damage]
            self.deal(src, tgt, 5.0, P.PHYSICAL, basic=False, source=P.SRC_DIRECT, spell_hash=GENERIC_DAMAGE)
            if not tgt.alive:
                return
        tips = getattr(self, 'tooltips', None)
        if src.is_hero and tgt.kind == 'minion' and tips is not None and src.net in tips.support:
            # World Atlas's execute comes before the attack's own damage (core/tooltips.py: Shared Riches)
            if tips.sup_execute(src, tgt, self.mitigate(src, tgt, amount, dtype), src.base.get('range', 500.0) > 300.0):
                return
        over = getattr(src, 'hit_override', None)
        if over is not None:                             # a unit a spell made: its hits are the spell's (templates.spawn)
            dealt = self.deal(src, tgt, over[0], over[1], basic=False, source=P.SRC_PERIODIC)
        else:
            name = src.attack_name
            if name and P.damage_rule(P.elf(name)) is None:
                first = src.attack_variants()[0][0]
                name = first if P.damage_rule(P.elf(first)) is not None else name
            dealt = self.deal(src, tgt, amount, dtype, basic=True, crit=crit, spell_hash=P.elf(name) if name else 0)
        if self.fx is not None and src.is_hero:
            self.fx.on_attack_hit(src, tgt)
        if getattr(self, 'pets', None) is not None and src.is_hero:
            self.pets.on_attack_hit(src, tgt)          # Crest of Cinders
        if kits is not None and src.is_hero:
            kits.call(src, 'after_attack', src, tgt, dealt)
        if src.is_hero and dealt > 0:
            if src.bonus.get('lifesteal'):
                src.set_hp(src.hp + dealt * src.bonus['lifesteal'])
            if self.spells is not None:
                self.spells.on_basic_hit(src, tgt, dealt)

    def deal(self, src, tgt, amount, dtype=P.PHYSICAL, basic=False, source=P.SRC_ATTACK, crit=False, spell_hash=0):
        """damage from src (a unit or None) to tgt -> the amount taken"""
        if not tgt.alive or amount <= 0 or self.over:
            return 0.0
        if tgt.is_structure and not tgt.targetable:
            return 0.0
        kits = getattr(self, 'kits', None)
        if kits is not None and tgt.is_hero:
            k = kits.of(tgt)
            if k is not None and hasattr(k, 'incoming'):
                amount = k.incoming(tgt, src, amount, dtype, basic)      # before mitigation (Amumu's Tantrum)
        curse = getattr(tgt, 'curse', None)
        if curse is not None and dtype == P.MAGIC and spell_hash != P.elf('AmumuP') and amount > 0:
            if self.t < curse[1] and curse[0].alive:
                # [wiki: Cursed Touch] 10 % of incoming pre-mitigation magic damage as true damage, Amumu's
                self.at(self.t, lambda t, c=curse[0], a=0.1 * amount: tgt.alive and self.deal(
                    c, tgt, a, P.TRUE, basic=False, source=P.SRC_DIRECT, spell_hash=P.elf('AmumuP')))
            else:
                tgt.curse = None
        refl = getattr(tgt, 'reflect', None)
        if refl is not None and src is not None and src.team != tgt.team and not src.is_structure and amount > 0:
            if self.t < refl['until'] and src.net not in refl['hit']:
                # a shield that burns who damages it (Annie's Molten Shield): once per enemy per cast
                refl['hit'].add(src.net)
                self.at(self.t, lambda t, r=refl, s=src: s.alive and self.deal(r['owner'], s, r['amount'], P.MAGIC, basic=False,
                                                                                 source=P.SRC_DIRECT, spell_hash=r['name']))
            elif self.t >= refl['until']:
                tgt.reflect = None
        dealt = self.mitigate(src, tgt, amount, dtype)
        if getattr(self, 'pets', None) is not None:
            dealt = self.pets.modify(src, tgt, dealt, dtype)
        red = getattr(tgt, 'damage_reduction', None)
        if red is not None and dtype != P.TRUE:
            if self.t < red[0]:
                dealt *= 1.0 - red[1]                    # a kit's "reduces incoming damage" (Alistar's R)
            else:
                tgt.damage_reduction = None
        if getattr(self, 'renewals', None) is not None:
            self.renewals.on_damage(src, tgt, basic)
        if getattr(self, 'itembuffs', None) is not None:
            self.itembuffs.on_damage(src, tgt, basic)
        if getattr(self, 'statbuffs', None) is not None:
            self.statbuffs.on_damage(src, tgt, dealt, basic, source, spell_hash)
        if getattr(self, 'kits', None) is not None and src is not None and src.is_hero:
            self.kits.call(src, 'dealt', src, tgt, dealt, basic, spell_hash, source)
        if src is not None and src.is_hero and (tgt.is_hero or tgt.is_structure) and tgt.team != src.team:
            tips = getattr(self, 'tooltips', None)
            if tips is not None and src.net in tips.support:
                tips.sup_hit(src, tgt, ('attack', src.attacks) if basic else (spell_hash, round(self.t, 1)))
        if src is not None and src.is_hero:
            tgt.last_hit_by[src.net] = self.t
            src.in_combat_until = self.t + 5.0
            src.last_damage = self.t
            if tgt.is_hero:
                src.last_hero_damage = tgt.last_hero_damage = self.t
        if tgt.is_hero:
            tgt.last_damage = self.t
        if src is not None and src.is_hero and tgt.kind == 'minion':
            ai.minion_hit(self, src, tgt)
        if src is not None and src.is_hero and tgt.kind == 'monster' and getattr(self, 'pets', None) is not None:
            self.pets.on_hit(src, tgt, spell_hash)
        if tgt.is_hero:
            tgt.in_combat_until = self.t + 5.0
            if tgt.recalling is not None:
                tgt.recall_cancel()
            if src is not None and src.is_hero:
                ai.call_for_help(self, tgt, src)
        src_net = src.net if src is not None else 0
        if src_net in self.watch or tgt.net in self.watch:
            rule = P.damage_rule(spell_hash)
            flag, kind = (rule[0], rule[1]) if rule else (basic, source)
            self.q += self.pk.damage(tgt, src_net, dealt, dtype, flag, kind, crit, spell_hash)
            # what the player's death recap is made of: the damage it took and dealt lately
            who = tgt if tgt.net in self.watch else src
            who.recap.append((self.t, tgt.net in self.watch, src_net, getattr(src, 'name', ''), spell_hash, basic, dtype, dealt))
            if len(who.recap) > 400:
                del who.recap[:200]
        sh = getattr(tgt, 'shield', None)
        if sh and dealt > 0:                             # a shield takes the damage first (templates.py sets them)
            for k in ('mPhysicalShield' if dtype == P.PHYSICAL else 'mMagicalShield' if dtype == P.MAGIC else None, 'mAllShield'):
                if k and sh.get(k, 0.0) > 0.0 and dealt > 0:
                    take = min(sh[k], dealt)
                    sh[k] -= take
                    dealt -= take
                    tgt.set(k, sh[k])
        tgt.set_hp(tgt.hp - dealt)
        if tgt.kind == 'monster' and src is not None:
            ai.monster_hit(self, tgt, src)
        if tgt.hp <= 0.0 and getattr(self, 'kits', None) is not None and tgt.is_hero and                 self.kits.call(tgt, 'fatal', tgt, src):
            pass                                         # the kit kept it alive (Anivia's Rebirth)
        elif tgt.hp <= 0.0:
            self.kill(tgt, src)
        return dealt

    def kill(self, u, killer):
        if not u.alive:
            return
        t = self.t
        if getattr(self, 'statbuffs', None) is not None:
            self.statbuffs.takedown(u)
        killer_net = killer.net if killer is not None else 0
        if getattr(u, 'told_target', None) is not None:
            u.end_engagement()
        if u.is_hero:
            self.hero_killed(u, killer)
            return
        u.alive = False
        u.path = None
        u.windup_end = None
        if u.kind in ('minion', 'monster', 'summon'):
            if getattr(self, 'kits', None) is not None:
                if killer is not None and killer.is_hero:
                    self.kits.call(killer, 'killed', killer, u)
                for x in self.heroes:
                    self.kits.call(x, 'any_unit_death', x, u, killer)
            self.q += self.pk.death(u, killer_net)
            self.release_attackers(u)
            self.at(t + CORPSE, lambda t2, u=u: self.remove(u))
            self.minion_rewards(u, killer)
            if u.kind == 'monster' and self.jungle is not None:
                self.jungle.on_death(u, killer)
            if u.kind == 'monster' and getattr(self, 'pets', None) is not None:
                self.pets.on_kill(killer, u)
        elif u.kind == 'turret':
            self.turret_falls(u, killer)
        elif u.kind == 'inhibitor':
            self.inhibitor_falls(u, killer)
        elif u.kind == 'nexus':
            self.nexus_falls(u, killer)

    def release_attackers(self, u):
        for o in self.units.values():
            if o.target == u.net:
                o.target = None
                o.target_lost = True
                if o.kind == 'minion':
                    o.spot = None
                    o.next_think = 0.0

    def remove(self, u):
        self.units.pop(u.net, None)
        if u in self.minions:
            self.minions.remove(u)
        if u in self.monsters:
            self.monsters.remove(u)
        v = self.vision
        # [m] a unit of another team is taken away for the players only if it is in their sight (the dead stay in
        # sight), a jungle monster always (it was created for everyone)
        if v is None or u.team == v.team or u.net in v.visible or u.kind == 'monster':
            self.q_late += self.pk.delete(u.net)
        for w in self.visions.values():
            w.forget(u.net)

    def minion_rewards(self, u, killer):
        """gold to the champion that made the kill; experience to the enemy champions near, shared by the map's
        table [data: mPlayerMinionSplitXp, experienceRadius]"""
        gold = u.base.get('gold', 0.0)
        tips = getattr(self, 'tooltips', None)
        if (killer is not None and killer.is_hero and u.kind == 'minion' and tips is not None and
                killer.net in tips.support and tips.sup_minion_kill(killer, u, gold)):
            killer.cs += 1
        elif killer is not None and killer.is_hero:
            killer.add_gold(gold, u.net)
            killer.cs += 1
            killer.farmed(gold)
        radius = getattr(u, 'xp_radius', 0.0) or u.base.get('xp_radius') or 1400.0
        near = [h for h in self.heroes if h.alive and h.team != u.team and dist(h.pos, u.pos) <= radius]
        if u.team == NEUTRAL:
            near = [killer] if killer is not None and killer.is_hero else []
        tips = getattr(self, 'tooltips', None)
        if tips is not None:
            if killer is not None and killer.is_hero and u.team != NEUTRAL:
                tips.minion_killed(killer)
            tips.unit_killed(u, killer)
            for h in near:
                tips.minion_died_near(h)
        if near:
            split = self.data.get('xp_minion_split') or [1.0]
            share = split[min(len(near), len(split)) - 1]
            xp = u.base.get('xp', 0.0) * share
            if u.team == NEUTRAL:
                from .jungle import xp_growth                  # the camp's level (the jungle item's bonus: core/pet.py)
                xp *= xp_growth(getattr(u, 'camp_level', 1))
            for h in near:
                h.add_xp(xp)

    def hero_killed(self, h, killer):
        t = self.t
        if getattr(self, 'pets', None) is not None:
            self.pets.holder_killed(h, killer)
        credit = killer if killer is not None and killer.is_hero else None
        helpers = [self.units[n] for n, when in h.last_hit_by.items()
                   if t - when <= ASSIST_WINDOW and n in self.units and self.units[n].is_hero and self.units[n].team != h.team]
        if credit is None and helpers:
            credit = max(helpers, key=lambda x: h.last_hit_by[x.net])
        others = [x for x in helpers if x is not credit]
        gold = h.kill_gold()                       # its worth before the death changes it
        if credit is not None:
            credit.kills += 1
            for x in others:
                x.assists += 1
        h.die(t, credit or killer, others if credit is not None else ())
        if credit is not None and getattr(self, 'tooltips', None) is not None:
            self.tooltips.unit_killed(h, credit, [credit] + others)
        if credit is not None and getattr(self, 'kits', None) is not None:
            for x in [credit] + others:
                self.kits.call(x, 'takedown', x, h)
        if getattr(self, 'kits', None) is not None:
            self.kits.call(h, 'died', h)
            for x in self.heroes:
                self.kits.call(x, 'any_death', x, h, credit)    # every kit hears of every champion's death
        h.last_hit_by = {}
        self.release_attackers(h)
        if credit is not None:
            credit.add_gold(gold, h.net)
            xp = self.data['xp_for_kill'][min(h.level, len(self.data['xp_for_kill'])) - 1]
            for x in others:
                x.add_gold(ASSIST_POOL * gold / KILL_GOLD / len(others), h.net)
            sharers = [credit] + others
            for x in sharers:
                x.add_xp(xp / len(sharers))

    # ------------------------------------------------------------------ structures fall
    def open_structure(self, s):
        if s.alive and not s.targetable:
            s.targetable = True
            s.set_many({'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4})

    def close_structure(self, s):
        if s.alive and s.targetable:
            s.targetable = False
            s.set_many({'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3})
            self.release_attackers(s)

    def turret_falls(self, s, killer):
        killer_net = killer.net if killer is not None else 0
        s.targetable = False
        # the recorded fall was the match's first: its chat line (210, ch 3) is the first turret's only [m: the one
        # 210 of this kind in the recording]; "_Friendly" / "_Enemy" by who reads it [the client's string table]
        skip = (938, 904, 584, 635, 683, 827, 262, 515, 88, 78, 818, 1024) + ((210,) if self.towers_down else ())
        self.towers_down += 1
        side = 'Friendly' if s.team != self.player_team else 'Enemy'
        for dt, ch, pid, net, body in self.pk.recipe('turret_falls', {'T': s.net, 'K': killer_net},
                                                     change={232: lambda v: v.update({'+0x50': P.u32(killer_net)}) or v,
                                                             210: {'+0x38': P.text('game_announcement_OnFirstTowerKill_' + side)}},
                                                     skip=skip):
            if dt <= 0.002:
                self.q.append((ch, pid, net, body))
            else:
                self.at(self.t + dt, lambda t2, it=(ch, pid, net, body): self.q.append(it))
        s.set_many({'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3})
        self.release_attackers(s)
        enemies = [h for h in self.heroes if h.team != s.team]
        near = [h for h in enemies if h.alive and dist(h.pos, s.pos) <= 2000.0] or ([killer] if killer is not None and killer.is_hero else [])
        for h in near:
            h.add_gold(TURRET_GOLD_LOCAL / len(near), s.net)
        for h in enemies:
            h.add_gold(TURRET_GOLD_GLOBAL)
        order = ['outer', 'inner', 'inhibitor']
        if s.tier in order:
            nxt = order[order.index(s.tier) + 1] if s.tier != 'inhibitor' else None
            for o in self.structures:
                if o.team != s.team or o.lane != s.lane:
                    continue
                if (nxt and o.kind == 'turret' and o.tier == nxt) or (nxt is None and o.kind == 'inhibitor'):
                    self.open_structure(o)
        elif s.tier == 'nexus':
            if not any(o.alive for o in self.turrets if o.team == s.team and o.tier == 'nexus'):
                for o in self.structures:
                    if o.team == s.team and o.kind == 'nexus':
                        self.open_structure(o)
        self.log(f'turret {s.net:#x} ({s.team} {s.lane} {s.tier}) falls to {getattr(killer, "name", "?")}')

    def inhibitor_rubble(self, s):
        """the map's own effect for this inhibitor lying in ruins: the VfxEntityTemplate placed on it"""
        best = None
        for key, p in self.data.get('placeables', {}).items():
            if p['type'] == 'VfxEntityTemplate':
                d = dist(p['pos'], s.pos)
                if d < 80.0 and (best is None or d < best[0]):
                    best = (d, int(key, 16), p)
        return best

    def inhibitor_falls(self, s, killer):
        """[m: the chaos mid inhibitor's two falls in the live recording] 693 (down), 716 (who did it), the map's
        particles of the living inhibitor off (984 SOG_<team>_<lane>) and of its ruin on (984 RUNETIMER_...), the
        ruin's effect created (502 + 1170 with the map's own key, transform and net id), 904 (its animation)"""
        pk = self.pk
        killer_net = killer.net if killer is not None else 0
        tag = f'{"ORDER" if s.team == ORDER else "CHAOS"}_{s.lane.upper()}'
        s.targetable = False
        self.q += pk.inhibitor_state(s.net, False, INHIBITOR_RESPAWN if s.falls else 0)
        s.falls += 1
        self.q += pk.building_died(s.net, killer_net)
        self.q += pk.map_effect('SOG_' + tag, 1, 1)
        self.q += pk.map_effect('RUNETIMER_' + tag, 1, 0)
        if s.team != self.player_team:
            self.q.append((1, 1061, 0, pk.enc(1061, {'+0x10': P.u32(0), '+0x14': '00', '+0x18': 'c8e35577', '+0x1c': 'b5f4c2ba'})))
        rubble = self.inhibitor_rubble(s)
        if rubble is not None:
            self.q += pk.placeable(rubble[2]['net'], rubble[1], rubble[2]['matrix'])
        self.q += pk.anim_states(s.net, [(0x9dd9dc06, 0x54de7ae2)])
        s.set_many({'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3})
        self.release_attackers(s)
        for o in self.turrets:
            if o.team == s.team and o.tier == 'nexus':
                self.open_structure(o)
        if killer is not None and killer.is_hero:
            killer.add_gold(INHIBITOR_GOLD, s.net)
        s.respawn_at = self.t + INHIBITOR_RESPAWN
        self.at(s.respawn_at - 11.66, lambda t2, s=s: None if self.over else self.q.extend(pk.animation(s.net, 'Respawn')))
        self.at(s.respawn_at, lambda t2, s=s: self.inhibitor_returns(s))
        self.log(f'inhibitor {s.net:#x} ({s.team} {s.lane}) falls to {getattr(killer, "name", "?")}')

    def inhibitor_returns(self, s):
        """[m] 300 s later: the map's particles switched back (984), 693 (up, 300), the ruin's effect removed (543)"""
        if self.over:
            return
        pk = self.pk
        tag = f'{"ORDER" if s.team == ORDER else "CHAOS"}_{s.lane.upper()}'
        s.alive, s.targetable = True, True
        s.hp = s.max_hp
        self.q += pk.map_effect('SOG_' + tag, 1, 0)
        self.q += pk.map_effect('RUNETIMER_' + tag, 1, 1)
        self.q += pk.map_effect('RUNETIMER_' + tag, 2, 0)
        if s.team != self.player_team:
            self.q.append((1, 1061, 0, pk.enc(1061, {'+0x10': P.u32(0), '+0x14': '00', '+0x18': 'db235643', '+0x1c': 'b5f4c2ba'})))
        self.q += pk.inhibitor_state(s.net, True, INHIBITOR_RESPAWN)
        rubble = self.inhibitor_rubble(s)
        if rubble is not None:
            self.q += pk.placeable_gone(rubble[2]['net'])
        s.set_many({'mHP': s.hp, 'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4})
        # the nexus and its turrets can be attacked only while an inhibitor of the team is down [wiki]
        if all(o.alive for o in self.structures if o.kind == 'inhibitor' and o.team == s.team):
            for o in self.structures:
                if o.team == s.team and (o.kind == 'nexus' or (o.kind == 'turret' and o.tier == 'nexus')):
                    self.close_structure(o)
        self.log(f'inhibitor {s.net:#x} ({s.team} {s.lane}) is back')

    def nexus_falls(self, s, killer):
        self.over = s.team
        killer_net = killer.net if killer is not None else 0
        player = next(iter(self.watch), 0)
        cam, tm = P.vec3(s.pos[0], 91.0, s.pos[1]), P.f32(self.t)
        for dt, ch, pid, net, body in self.pk.recipe('nexus_falls', {'N': s.net, 'K': killer_net, 'P': player},
                                                     change={258: {'+0x18': cam}, 1050: {'+0x14': tm, '+0x18': tm}}):
            self.q.append((ch, pid, net, body))
        lost = 'c8' if s.team == CHAOS else '64'
        # [m] 3.5 s after the nexus: 365 (the game's end: the team that lost, 2.0), 0.24 s later 673
        self.at(self.t + 3.5, lambda t2: self.q.extend((ch, pid, net, body) for dt, ch, pid, net, body in
                                                       self.pk.recipe('match_ends', {}, change={365: {'+0x10': lost}})))
        self.at(self.t + 3.74, lambda t2: self.q.append((1, 673, 0, self.pk.enc(673, {
            '+0x10': '01', '+0x11': '00', '+0x12': '00', '+0x14': P.u32(2), '+0x18': '00'}))))
        self.log(f'the {"chaos" if s.team == CHAOS else "order"} nexus falls: the match is over')

    # ------------------------------------------------------------------ the frame
    def step(self, dt=DT):
        """one frame -> the packets to send, in the real server's order"""
        self.t += dt
        self.frame += 1
        t = self.t
        while self.heap and self.heap[0][0] <= t:
            when, _, fn = heapq.heappop(self.heap)
            fn(when)
        while self.frame_heap and self.frame_heap[0][0] <= self.frame:
            _, _, fn = heapq.heappop(self.frame_heap)
            fn(t)
        if not self.over:
            if self.next_wave is None:
                self.next_wave = self.wave_first + WAVE_START
            if t >= self.next_wave - 1e-9:
                self.wave += 1
                self.spawn_wave(self.wave)
                # the slip is the real frames' lateness: stepped on the real frames (golden test), they make it
                self.next_wave = (t if self.real_frames else self.next_wave + WAVE_SLIP) + self.wave_interval(self.next_wave)
        if self.visions:
            vision.look(self, t)             # who sees whom: fixed for the rest of the frame
        if not self.over:
            for h in self.heroes:
                h.tick(t, dt)
            ai.tick(self, t)
            for fn in self.systems:
                fn(t, dt)
            for u in self.heroes:
                if u.path and u.alive:
                    u.advance(dt)
            for u in self.minions:
                if u.path and u.alive and u.advance(dt):
                    ai.minion_arrived(self, u)
            for u in self.monsters:
                if u.path and u.alive:
                    u.advance(dt)
        v = self.vision
        watch = self.watch
        events = [p[:4] for p in self.q if p[1] not in vision.PLAYER_ONLY or p[2] in watch]
        if v is not None:
            # the fog of war: nothing about a unit out of the players' sight but what the real server sends anyway;
            # the values it replicates wait until it is seen
            moves = [e for e in self.q_moves if v.sees(struct.unpack_from('<I', e, 2)[0])]
            events = [p[:4] for p in self.q if (p[1] not in vision.PLAYER_ONLY or p[2] in watch) and (len(p) > 4 or v.passes(p))]
            repl = [(u.net, u.take_dirty(), u.repl_cls) for u in self.units.values()
                    if u.dirty and u.repl_cls and not v.hidden(u)]
        else:
            moves = self.q_moves
            repl = [(u.net, u.take_dirty(), u.repl_cls) for u in self.units.values() if u.dirty and u.repl_cls]
        out = self.q_first
        if moves:
            out += self.pk.moves(t, moves)
        out += self.q_all
        out += events
        if repl:
            out += self.pk.replication(t, repl)
        out += self.q_late
        for i, p in enumerate(out):
            if p[1] == 1140:                         # a dash: numbered after this frame's movement packets
                out[i] = (p[0], p[1], p[2], self.pk.restamp_dash(p[3], t))
        out = self.pk.merge_effects(out)
        self.q_first, self.q_moves, self.q, self.q_late, self.q_all = [], [], [], [], []
        owner = self.pk.owner
        if len(owner) > 4000:                        # missiles long gone
            for k in list(owner)[:2000]:
                del owner[k]
        return out
