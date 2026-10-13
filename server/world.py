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
Lane minions fight each other (2026-10-10; the packet forms are the replay's, the rules are ours and simple):
  - a minion with an enemy minion nearer than ACQUIRE stops walking its lane; out of reach it walks to the enemy,
    in reach it stands (552 with one point) and attacks: 286 (basic attack: target, attack slot 0x40, target
    position, own position), the damage lands after the windup (and the missile's flight for ranged ones) as 263
    plus the target's health in 595; at zero health 61 (death, killer = the minion) and the unit is gone
  - damage 12 / 24 / 41 (melee / caster / cannon: the amounts the replay's 263 carry between minions); attack
    periods, ranges and missile speeds are the usual values of these units [approximation, not measured]
  - with no enemy left it walks on along its lane from where it stands
A new unit's state (2026-10-11): Riot's server sends EVERY replicated value of a new lane minion twice -- in the tick
of its creation (what it may do: ActionState 0x200000f, health, "can be targeted" 1 / team flags 4) and 0.132 s later
(the kind's attack damage and range, move speed 325). We sent health alone: the client had a unit that may not move
(it stood on its spawn point until our first path snapped it forward, one inside the other) and cannot be targeted (the
cursor never became the attack cursor on a minion). Our two blocks are byte for byte the replay's (minion_values).
Turrets (2026-10-11; data/exe133/world_data.json from tools/world_data.py):
  - they are in the client from the start state, not targetable; Riot's server opens them at 10.094 s (mIsTargetable 1,
    team flags 4 = enemies may attack: the outer ones; 2 = protected: the others, 4 once the turret before fell) --
    in a start-only match nobody sent that, so no turret could be attacked
  - a turret attacks the nearest enemy lane minion within 775 of its edge, else an enemy champion: the replay's own
    packets with our ids (740 target, 66, 592 first attack / 26 next, 516, 779 when the missile leaves 0.265 s later,
    490 + 66 + 740 cleared when it stops), 1.322 s between attacks (replay median); the damage lands when the missile
    (1200 units/s) arrives: 45 / 70 / 14 % of a melee / caster / cannon minion's full health [the usual shares]
  - lane minions with no enemy minion near attack an enemy turret in reach, else an enemy champion very near
  - a turret at zero health: 310 (death, killer), 65 + 71 (the destroyed animation), not targetable any more; the next
    turret of the lane opens (inhibitor turret -> the two nexus turrets)
The jungle (2026-10-11): every monster of the replay is created again at its replay time with the replay's own
packets (506 x4, 359 with its place / name / skin, 518, 770, 387 and its first replication blocks, raw): 12 camps from
88 s, the crabs at 209 s, the dragon at 293 s, the herald at 477 s. Like the replay's they cannot be targeted at first;
1.75 s later they can (StatusFlags 0, mIsTargetable 1, team flags 4). A monster a champion hits fights back with its
camp (286 like a lane minion, its replicated attack damage), follows up to MONSTER_LEASH from its place, then walks
home and heals. Dead: 61, gold and experience to the killer [the usual amounts]; the camp comes back later with new
net ids (the 359 re-encoded with the new id).
The other nine champions (2026-10-11) are bots of ours [rules ours, simple]: each has a lane, stands behind its
lane's front minion, attacks enemy minions, an enemy champion that comes near and, with minions around, a turret;
under 30 % health it walks to its fountain and heals; dead, it returns there later. Their packets are the replay's:
the attack of a unit without cast data (592 / 26 / 516, the turret's templates), the champion's death and return
(780 / 417 / 440 / 568, 128).
The player's champions are the server's (lnp_server.py): it tells us where they are (set_hero) and takes what happens
to them from `events` (hero_hit, xp, gold, turret_dead).
"""
import bisect
import collections
import copy
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
# Header bits no field of our schema reads, which Riot's server sets in EVERY packet of the kind (measured on the
# 13.3 replay, per-bit check: 100 % of 2.3-4 thousand packets each) and our encoder left 0: {packet id: (header bytes,
# bits)}. The unit's spawn (518) and health (770) carried bit 7 clear. Not 286 (attack): there bit 7 is read as a mode
# of the attacker position and the learnt codec cannot yet write every real packet.
SPARE = {518: (1, 1 << 7), 770: (1, 1 << 7), 263: (3, 1 << 22),
         61: (2, (1 << 9) | (1 << 10) | (1 << 11) | (1 << 13)), 98: (4, 1 << 29)}


def seal(pid, body):
    """the packet body with the header bits Riot's server always sets"""
    if pid not in SPARE:
        return body
    n, bits = SPARE[pid]
    return (int.from_bytes(body[:n], 'little') | bits).to_bytes(n, 'little') + body[n:]
ACQUIRE = 550.0               # an enemy this near makes a minion leave its lane walk [approximation]
THINK = 0.1                   # the fights are looked at this often
KIND_FLAG = {'05': '0100'}     # 98 +0xa by kind (replay: 0000 melee, 0100 caster; cannon filled in when measured)
APPEAR_DELAY = 0.034          # creation -> visible / enters vision / health: the next server tick (replay: 33 ms)
RADIUS = 48.0                 # a lane minion's body [approximation]
HEIGHT = 54.0                 # ground height the lanes are near (286 carries the target's x, y, z)
# per kind (98 +0x14): damage as in the replay's 263 between minions; reach, time between attacks, windup and
# missile speed (0 = melee) [approximations]
KINDS = {'04': dict(damage=12.0, reach=110.0, period=0.8, windup=0.3, missile=0.0),
         '05': dict(damage=24.0, reach=550.0, period=1.5, windup=0.4, missile=650.0),
         '06': dict(damage=41.0, reach=300.0, period=1.0, windup=0.35, missile=1200.0)}
STATS = {'04': (12.0, 110.0), '05': (24.0, 550.0), '06': (43.0, 300.0)}   # replicated attack damage, range (replay)
STATS_DELAY = 0.132           # creation -> the second replication block with the kind's stats (replay)
TURRETS_OPEN = 10.094         # game time Riot's server makes the turrets targetable (replay)
TURRET_STATS = 0.371          # ... and gives them their armor and attack damage (replay)
TURRET_REACH = 775.0          # attack range, from the turret's edge
TURRET_BODY = 88.4            # a turret's gameplay radius
TURRET_PERIOD = 1.322         # between two attacks of a turret (replay median of 279)
TURRET_AIM = 0.266            # target chosen (740) -> first attack (replay: 65.204 -> 65.470)
TURRET_WINDUP = 0.265         # attack -> the missile leaves (779) (replay: 65.470 -> 65.735)
TURRET_MISSILE = 1200.0       # [approximation]
TURRET_SHARE = {'04': 0.45, '05': 0.70, '06': 0.14}   # of the minion's full health per shot [the usual shares]
HERO_NEAR = 400.0             # a champion this near is attacked by minions that have nothing else [approximation]
HERO_LEASH = 750.0            # ... and let go once it is this far
XP_RANGE = 1400.0             # champions this near a dying minion share its experience
MINION_XP = {'04': 61.75, '05': 30.4, '06': 95.0}     # [the usual values]
TURRET_GOLD = 250.0           # to the enemy champions for a fallen turret [approximation]
MONSTER_OPEN = 1.75           # creation -> can be targeted (replay: 88.37 -> 90.12 for the first camps)
MONSTER_LEASH = 800.0         # how far from its place a monster follows
MONSTER_PERIOD = 1.5          # between its attacks [approximation]
MONSTER_WINDUP = 0.3
MONSTER_BODY = 80.0           # [approximation]
# per skin: gold, experience [the usual amounts, approximations]; a camp returns after CAMP_BACK seconds
JUNGLE = {'SRU_Red': (90, 110), 'SRU_Blue': (90, 110), 'SRU_Gromp': (80, 120), 'SRU_Murkwolf': (55, 65),
          'SRU_MurkwolfMini': (15, 25), 'SRU_Razorbeak': (35, 20), 'SRU_RazorbeakMini': (8, 20), 'SRU_Krug': (15, 37),
          'SRU_KrugMini': (10, 18), 'Sru_Crab': (55, 100), 'SRU_Dragon_Hextech': (100, 150), 'SRU_RiftHerald': (100, 200)}
CAMP_BACK = {'SRU_Red': 300.0, 'SRU_Blue': 300.0, 'Sru_Crab': 150.0, 'SRU_Dragon_Hextech': 300.0, 'SRU_RiftHerald': 360.0}
BOTS_START = 1.0              # game time the bots get their state (what they may do, health)
BOTS_LEAVE = 25.0             # ... and leave the fountain for their lanes
BOT_LANES = {'blue': ['top', 'mid', 'bot', 'bot', 'mid'], 'red': ['top', 'mid', 'mid', 'bot', 'bot']}
BOT_SIGHT = 650.0             # an enemy champion this near is attacked [approximation]
CHAMPION_GOLD = 300.0
CHAMPION_XP = 140.0


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
        self.target = None        # net id of the enemy it fights
        self.standing = False     # it stopped to attack
        self.chasing = False      # it left its lane walk to reach an enemy
        self.next_attack = 0.0
        self.goal = None          # where it stands (or walks) to attack, and where its enemy was then
        self.goal_ref = None
        self.attacks = 0

    def pos(self, t):
        if self.path is None:
            return None
        return walk(self.path, MINION_SPEED, t - self.path_t)[0]


class Turret:
    def __init__(self, d):
        self.net, self.name, self.team, self.lane, self.tier = d['net'], d['name'], d['team'], d['lane'], d['tier']
        self.pos = tuple(d['pos'])
        self.hp = self.max_hp = float(d['hp'])
        self.armor, self.damage = float(d['armor']), float(d['damage'])
        self.alive = True
        self.open = False         # enemies may attack it
        self.target = None
        self.first = True         # the next attack is the first one on this target
        self.next_attack = 0.0
        self.respawn_at = 0.0


def read_values(groups, cls='lane_minion'):
    """{name: number} of one unit's raw replication groups {group: (mask, bytes)}"""
    import replication as RP
    import repl_codec as RC
    table = {(g, b): (n, k) for n, (g, b, k) in RC.names(cls).items()}
    out = {}
    for g, (mask, data) in groups.items():
        at = 0
        for b in range(32):
            if not mask >> b & 1:
                continue
            name, kind = table.get((g, b), (f'g{g}b{b}', 'i'))
            end = RP.take(data, at, kind)
            raw, at = data[at:end], end
            if kind == 'f':
                out[name] = 0.0 if raw == b'\xff' else struct.unpack('<f', raw[-4:])[0]
            else:
                v, sh = 0, 0
                for c in raw:
                    v |= (c & 0x7f) << sh
                    sh += 7
                out[name] = v
    return out


def raw_unit(net, groups):
    """one unit of a replication buffer from raw groups {group: (mask, bytes)}"""
    out = bytes([sum(1 << g for g in groups)]) + struct.pack('<I', net)
    for g in sorted(groups):
        mask, data = groups[g]
        out += struct.pack('<IB', mask, len(data)) + data
    return out


def camp_of(name):
    """a monster's camp: the number before its two last name parts ('SRU_RazorbeakMini3.1.2' -> '3'), else its name"""
    import re
    m = re.search(r'(\d+)\.\d+\.\d+$', name)
    return m.group(1) if m else name


class Monster:
    def __init__(self, index, d, net, t, values):
        self.index, self.net, self.name, self.skin = index, net, d['name'], d['skin']
        self.camp = camp_of(self.name)
        self.home = tuple(d['pos'])
        self.hp = self.max_hp = float(d['hp'])
        self.damage = float(values.get('mBaseAttackDamage', 20.0))
        self.reach = float(values.get('mAttackRange', 150.0)) or 150.0
        self.speed = float(values.get('mMoveSpeed', 300.0)) or 300.0
        self.armor = float(values.get('mArmor', 0.0))
        self.path, self.path_t = [self.home], t
        self.open = False
        self.target = None
        self.next_attack = self.next_path = 0.0
        self.attacks = 0

    def pos(self, t):
        return walk(self.path, self.speed, t - self.path_t)[0]

    def moving(self, t):
        return len(self.path) > 1 and math.dist(self.pos(t), self.path[-1]) > 5


class Bot:
    """one of the nine champions the player does not play"""
    def __init__(self, d, lane, home):
        import spell_info as SI
        rec = SI.char_record(d['champion'])
        self.net, self.champion, self.team, self.lane, self.home = d['net'], d['champion'], d['team'], lane, tuple(home)
        self.hp = self.max_hp = float(rec.get('baseHP', 600.0))
        self.damage = float(rec.get('baseDamage', 60.0))
        self.armor = float(rec.get('baseArmor', 30.0))
        self.reach = float(rec.get('attackRange', 125.0))
        self.speed = float(rec.get('baseMoveSpeed', 335.0))
        self.radius = float(rec.get('overrideGameplayCollisionRadius', 65.0))
        try:
            self.period, self.windup = SI.attack_times(d['champion'])
        except Exception:
            self.period, self.windup = 1.6, 0.3
        self.ranged = self.reach > 300
        self.path, self.path_t = [self.home], 0.0
        self.alive, self.back_at = True, 0.0
        self.target, self.first = None, True
        self.next_attack = self.next_path = self.next_health = 0.0
        self.retreat = False
        self.sent_hp = self.hp

    def pos(self, t):
        return walk(self.path, self.speed, t - self.path_t)[0]

    def moving(self, t):
        return len(self.path) > 1 and math.dist(self.pos(t), self.path[-1]) > 5


class Real:
    """A real packet body our world sends again with its own ids: decoded once (tools/world_data.py), encoded here
    with the changed fields. Our encoder leaves header bits clear that Riot's server sets (in the packet's own
    header and in the headers of the structs inside); they are put back from the real body, so an unchanged value
    comes out as the real bytes."""
    def __init__(self, d):
        import pkt_schema as PS
        self.pid, self.ch, self.body, self.value = d['pid'], d['ch'], bytes.fromhex(d['body']), d['value']
        if self.value is None:                    # a packet we only send as it is (no reader learnt for it)
            self.same_shape = self.exact = True
            return
        self.sc = PS.Schema.load(self.pid)
        plain = self.sc.encode(self.value)
        self.plain_len = len(plain)
        self.same_shape = len(plain) == len(self.body)
        self.diff = bytes(a ^ b for a, b in zip(plain, self.body)) if self.same_shape else b''
        self.exact = self.same_shape and self.build() == self.body

    def build(self, change=None):
        import copy
        v = copy.deepcopy(self.value)
        if change is not None:
            change(v)
        out = self.sc.encode(v)
        if self.same_shape and len(out) == self.plain_len:
            out = bytes(a ^ b for a, b in zip(out, self.diff))
        return out

    def packet(self, net, change=None, what=''):
        return (self.ch, struct.pack('<HI', self.pid, net) + self.build(change), what or str(self.pid))

    def as_sent(self, net, what=''):
        """the real bytes, unchanged (a body with no id inside)"""
        return (self.ch, struct.pack('<HI', self.pid, net) + self.body, what or str(self.pid))


def minion_values(hp, kind=None, is_super=False):
    """every replicated value of a lane minion as Riot's server sends them: kind None = in the tick of its creation,
    else 0.132 s later, with the kind's stats (checked: the bytes of the replay's first minion, both blocks)"""
    import repl_codec as RC
    v = {name: 0 for name in RC.names('lane_minion')}
    v.update(ActionState=0x200000f, ActionState2=4, mBaseAttackDamage=25.0, mAttackSpeedMod=1.0, mHP=hp, mMaxHP=hp,
             mPAREnabled=1, mSAREnabled=1, mPercentMultiplicativeAttackSpeedMod=1.0, mScaleSkinCoef=1.0,
             mIsTargetable=1, mIsTargetableToTeamFlags=4)
    if kind is not None:
        damage, reach = STATS.get(kind, STATS['04'])
        if is_super:
            damage = 180.0
        v.update(mBaseAttackDamage=damage, mSAR=100.0, mMaxSAR=100.0, mAttackRange=reach,
                 mCritDamageMultiplier=1.75, mMoveSpeed=MINION_SPEED)
    return v


class World:
    def __init__(self):
        self.lanes = json.load(open(os.path.join(RES, 'lanes.json')))
        self.paths = _lane_paths(self.lanes)
        import navgrid
        self.nav = navgrid.grid()                # the map's walkable ground (server/navgrid.py)
        self.paths = {k: self.routed(p) for k, p in self.paths.items()}
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
        self.fight = {pid: PS.Schema.load(pid) for pid in (286, 263, 61)}
        self.next_think = 0.0
        self.deaths = 0
        self.died = None          # a list when somebody wants every death: (time, net id, killer)
        self.spots = {}           # net id -> the place a fighting minion stands on or walks to
        self._initial = {}        # barrack -> the way out of it that the spawn packet gives the client
        self.later = []           # (time, order, packets) of new units: what follows their creation, sorted
        self.later_n = 0
        self.counter = [2000000]  # the replication packets' counter; the server shares its own with us
        data = json.load(open(os.path.join(RES, 'world_data.json')))
        self.turrets = {d['net']: Turret(d) for d in data['turrets']}
        self.real = {key: [Real(x) for x in items] for key, items in data['templates'].items()}
        self.structures = data['structures']
        self.turrets_stats = self.turrets_open = False
        # the two nexuses stand among the turrets as structures that never attack (tier 'hq'): 5500 health, no armor;
        # open once both nexus turrets of their team fell; the match is over when one falls
        for team, net in data.get('nexus', {}).items():
            self.turrets[net] = Turret(dict(net=net, name='HQ_T1' if team == 'blue' else 'HQ_T2', team=team, lane='nexus',
                                            tier='hq', pos=self.structures['nexus']['HQ_T1' if team == 'blue' else 'HQ_T2'],
                                            hp=5500.0, armor=0.0, damage=0.0))
        # the 6 inhibitor dampeners (tier 'dampener'): 4000 health, 20 armor; open when their lane's inhibitor turret falls
        self.super_minions = {'blue': {'top': False, 'mid': False, 'bot': False},
                              'red': {'top': False, 'mid': False, 'bot': False}}
        self.inhibitor_info = [
            ('Barracks_T1_L1', 'blue', 'top', 0xff9303e1, tuple(self.structures['inhibitors']['Barracks_T1_L1'])),
            ('Barracks_T1_C1', 'blue', 'mid', 0xff4a20f1, tuple(self.structures['inhibitors']['Barracks_T1_C1'])),
            ('Barracks_T1_R1', 'blue', 'bot', 0xffd23c3e, tuple(self.structures['inhibitors']['Barracks_T1_R1'])),
            ('Barracks_T2_L1', 'red', 'top', 0xff6793d0, tuple(self.structures['inhibitors']['Barracks_T2_L1'])),
            ('Barracks_T2_C1', 'red', 'mid', 0xffff8f1f, tuple(self.structures['inhibitors']['Barracks_T2_C1'])),
            ('Barracks_T2_R1', 'red', 'bot', 0xff26ac0f, tuple(self.structures['inhibitors']['Barracks_T2_R1'])),
        ]
        for name, team, lane, net, pos in self.inhibitor_info:
            self.turrets[net] = Turret(dict(net=net, name=name, team=team, lane=lane,
                                            tier='dampener', pos=pos, hp=4000.0, armor=20.0, damage=0.0))
        self.over = None          # the team that lost, once a nexus fell
        self.heroes = {}          # net id -> dict(team, pos, alive, radius): the champions, kept by the server
        self._champs = (None, [])
        self._ways = {}           # routes found on the grid, by the cells of their ends
        self._decoded = {}        # (barrack, packet id) -> the spawn template read once
        PS.KEEP_INVERSES = True
        self.events = []          # what happened to champions; the server takes them after every tick
        self.attack_count = 0x1000
        self.attack_nets = {}     # attacker's net id -> the net id of its attacks' missile (attack_net)
        self.turret_deaths = 0
        # the jungle: every monster at its replay time
        self.monster_data = data.get('monsters', [])
        self.monster_real = {}
        self.monsters = {}
        for i, d in enumerate(self.monster_data):
            bisect.insort(self.queue, (float(d['t']), 'monster', (i, d['net'])))
        # the other champions
        self.bots = {}
        self.bots_started = False
        fountain = self.structures['fountain']
        seats = {'blue': 0, 'red': 0}
        for d in sorted(data.get('champions', []), key=lambda c: c['slot']):
            lanes = BOT_LANES[d['team']]
            lane = lanes[seats[d['team']] % len(lanes)]
            seats[d['team']] += 1
            try:
                self.bots[d['net']] = Bot(d, lane, fountain[d['team']])
            except Exception as ex:
                print('no bot for', d['champion'], ex, flush=True)
        self.lane_len = {k: self.lengths(p) for k, p in self.paths.items()}

    # --------------------------------------------------------------------------------------------- units in general
    def set_hero(self, net, team, pos, alive=True, radius=65.0):
        """a champion a player plays (not a bot of ours): where it is now"""
        self.bots.pop(net, None)
        self._champs = (None, [])
        self.heroes[net] = dict(team=team, pos=tuple(pos), alive=alive, radius=radius)

    def champions(self, t):
        """[(net, team, place)] of every champion that can be attacked now"""
        if self._champs[0] == t:
            return self._champs[1]
        out = [(n, h['team'], h['pos']) for n, h in self.heroes.items() if h['alive']]
        if self.bots_started:
            out += [(n, b.team, b.pos(t)) for n, b in self.bots.items() if b.alive]
        self._champs = (t, out)
        return out

    def targets_for(self, team, t):
        """[(net, place, radius)] of what a champion of `team` can hit with a spell: enemy lane minions, the jungle's
        monsters that can be targeted, enemy champions"""
        out = [(n, m.pos(t), RADIUS) for n, m in self.minions.items() if m.team != team and m.path]
        out += [(n, mo.pos(t), MONSTER_BODY) for n, mo in self.monsters.items() if mo.open]
        out += [(n, p, self.body(n)) for n, tm, p in self.champions(t) if tm != team]
        return out

    def knows(self, net):
        return net in self.minions or net in self.turrets or net in self.monsters or net in self.bots

    @staticmethod
    def lengths(path):
        out = [0.0]
        for a, b in zip(path, path[1:]):
            out.append(out[-1] + math.dist(a, b))
        return out

    def along(self, key, p):
        """how far along a lane (base -> enemy base) a point is: the arc length of its nearest place on the path"""
        path, ln = self.paths[key], self.lane_len[key]
        best = (1e18, 0.0)
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            d = ln[i + 1] - ln[i]
            f = 0.0 if d <= 0 else max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (d * d)))
            q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            e = math.dist(p, q)
            if e < best[0]:
                best = (e, ln[i] + d * f)
        return best[1]

    def point_at(self, key, s):
        path, ln = self.paths[key], self.lane_len[key]
        s = max(0.0, min(s, ln[-1]))
        for i in range(len(path) - 1):
            if s <= ln[i + 1]:
                d = ln[i + 1] - ln[i]
                f = (s - ln[i]) / d if d > 0 else 0.0
                return (path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f)
        return path[-1]

    def new_net(self):
        self.next_net += 1
        return self.next_net - 1

    def attack_net(self, net):
        """the net id a unit's basic attack names for its missile (286 +0xc+0x20). The client makes the missile of a
        ranged attacker an object of its own under this id (Riot's server then sends 387 / 623 to it), so it must
        never be the attacker's id: we wrote the attacker's, and from its first attack on a caster or cannon minion
        was no longer the unit behind its net id in the client (measured with the census, match_census1: every
        ranged minion left the client's table 20-35 s after its creation while it lived on here, melee ones never)
        -- it stood where it was for good, took no path, no health, no death. One id per attacker, kept for all
        its attacks, as in the replay (72 ids for the 426 caster attacks of its first 200 s)."""
        a = self.attack_nets.get(net)
        if a is None:
            a = self.attack_nets[net] = self.new_net()
        return a

    def team_of(self, net):
        if net in self.minions:
            return self.minions[net].team
        if net in self.turrets:
            return self.turrets[net].team
        if net in self.heroes:
            return self.heroes[net]['team']
        if net in self.bots:
            return self.bots[net].team
        return 'jungle' if net in self.monsters else None

    def place(self, net, t, where=None):
        """where a unit that can be attacked is now; None when it is gone"""
        if net in self.minions:
            if where is not None:
                return where.get(net)
            return self.minions[net].pos(t)
        tu = self.turrets.get(net)
        if tu is not None:
            return tu.pos if tu.alive else None
        h = self.heroes.get(net)
        if h is not None:
            return h['pos'] if h['alive'] else None
        b = self.bots.get(net)
        if b is not None:
            return b.pos(t) if b.alive and self.bots_started else None
        mo = self.monsters.get(net)
        if mo is not None:
            return mo.pos(t) if mo.open else None
        return None

    def body(self, net):
        if net in self.turrets:
            tu = self.turrets[net]
            if tu.tier == 'hq':
                return 300.0
            if tu.tier == 'dampener':
                return 150.0
            return TURRET_BODY
        if net in self.heroes:
            return self.heroes[net]['radius']
        if net in self.bots:
            return self.bots[net].radius
        if net in self.monsters:
            return MONSTER_BODY
        return RADIUS

    def replication_raw(self, t, units, what):
        """595 from units already in buffer form (raw_unit)"""
        import repl_codec as RC
        if RC._sc is None:
            import pkt_schema as PS
            RC._sc = PS.Schema.load(595)
        self.counter[0] += 1
        value = {'+0xc': {'text': b''.join(units).hex()}, '+0x18': f'{len(units):02x}',
                 '+0x1c': struct.pack('<f', t).hex(), '+0x20': struct.pack('<I', self.counter[0]).hex()}
        return (2, struct.pack('<HI', 595, 0) + RC._sc.encode(value), what)

    @staticmethod
    def cells(points):
        import waypoints as Wp
        return [(int(round((x - Wp.CENTER[0]) / Wp.CELL)), int(round((z - Wp.CENTER[1]) / Wp.CELL))) for x, z in points]

    def path_packets(self, entries, what):
        """552 for every unit of the buffer (several packets when there are more units than one packet takes)"""
        import lol_packets as LP
        return [(2, struct.pack('<HI', 552, 0) + body, what) for body in LP.bodies_552(entries)]

    def replication(self, t, units, what):
        import repl_codec as RC
        self.counter[0] += 1
        return (2, struct.pack('<HI', 595, 0) + RC.packet(units, t, self.counter[0]), what)

    def damage_number(self, target, source, damage):
        """263: the damage a unit takes, shown as a number over it"""
        v = {'+0xa': '00', '+0xc': struct.pack('<I', target).hex(), '+0x10': '00',
             '+0x14': struct.pack('<f', damage).hex(), '+0x18': '00000000', '+0x1c': '04', '+0x1d': '01',
             '+0x20': struct.pack('<I', source).hex()}
        return (1, struct.pack('<HI', 263, target) + seal(263, self.fight[263].encode(v)), f'263 {damage:.0f} damage on {target:#x}')

    def push_later(self, at, packets):
        self.later_n += 1
        bisect.insort(self.later, (at, self.later_n, packets))

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
        if self.over is not None:
            while self.later and self.later[0][0] <= t:
                out += [x for x in self.later.pop(0)[2] if x[0] != 'open']
            return out
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
                if m and len(m.lane_path) > 1 and m.target is None and m not in moves:
                    moves.append(m)
            elif what == 'hit':
                out += self.hit(at, *args)
            elif what == 'missile':
                out += self.turret_missile(at, *args)
            elif what == 'monster':
                # the replay's own net id while it cannot meet one of ours (ours start at NET_BASE; the replay's later
                # monsters - crabs, dragon, herald - have ids above it)
                out += self.monster_appears(at, args[0], args[1] if args[1] < NET_BASE else self.new_net())
            elif what == 'camp':
                for i in args[1]:
                    out += self.monster_appears(at, i, self.new_net())
        while self.later and self.later[0][0] <= t:
            at, _, items = self.later.pop(0)
            for item in items:
                if item[0] == 'open':
                    out += self.monster_opens(at, item[1])
                else:
                    out.append(item)
        out += self.structures_start(t)
        # inhibitor respawns (measured: packet 108 with 0xf0, resets super minions)
        for tu in self.turrets.values():
            if tu.tier == 'dampener' and not tu.alive and tu.respawn_at and t >= tu.respawn_at:
                tu.alive = tu.open = True
                tu.hp = tu.max_hp
                tu.respawn_at = 0.0
                enemy = 'red' if tu.team == 'blue' else 'blue'
                self.super_minions[enemy][tu.lane] = False
                out.append((1, struct.pack('<HI', 108, tu.net) + bytes.fromhex('f0'), f'108 inhibitor {tu.name} respawned'))
                units = [(tu.net, {'mHP': tu.hp, 'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4, 'StatusFlags': 256}, 'turret')]
                out.append(self.replication(t, units, f'595 inhibitor {tu.name} respawned'))
                self.events.append(('inhibitor_respawn', t, tu.net, tu.team, tu.lane))
        if t >= getattr(self, 'next_fountain_heal', 0.0):
            self.next_fountain_heal = t + 1.0
            fountain = self.structures.get('fountain', {})
            for net, h in self.heroes.items():
                if h['alive']:
                    fpos = fountain.get(h['team'])
                    if fpos and math.dist(h['pos'], fpos) <= 1000.0:
                        self.events.append(('fountain_heal', t, net))
        if os.environ.get('WORLD_NO_MOVES'):
            return out                      # control experiments: creation only, somebody else moves the units
        if t >= self.next_think:
            self.next_think = t + THINK
            out += self.think(t, moves)
        if moves:
            out += self.move_packet(moves, t)
        return out

    # --------------------------------------------------------------------------------------------- fights
    def think(self, t, moves):
        """targets, approach and attacks of every lane minion at time t; minions that walk their lane again are
        put into `moves`"""
        import lol_packets as LP
        import waypoints as Wp
        out, entries = [], b''
        self.now = t
        where = {net: m.pos(t) for net, m in self.minions.items() if m.path}
        by_lane = collections.defaultdict(list)
        for net in where:
            by_lane[self.minions[net].lane].append(net)

        def cells(points):
            return [(int(round((x - Wp.CENTER[0]) / Wp.CELL)), int(round((z - Wp.CENTER[1]) / Wp.CELL)))
                    for x, z in points]
        for net, here in where.items():
            m = self.minions[net]
            k = KINDS.get(m.kind, KINDS['04'])
            there = self.place(m.target, t, where) if m.target is not None else None
            if there is None or ((m.target in self.heroes or m.target in self.bots) and math.dist(here, there) > HERO_LEASH):
                m.target = there = None
            if m.target is None or m.target not in self.minions:
                # enemy minions first; a minion busy with a turret or a champion turns to one that comes near
                near = [(math.dist(here, where[o]), o) for o in by_lane[m.lane] if self.minions[o].team != m.team]
                near = [x for x in near if x[0] <= ACQUIRE]
                if near:
                    m.target = min(near)[1]
                    m.goal = None
                elif m.target is None:
                    m.target = self.other_target(m, here)
                    m.goal = None
                if m.target is None:
                    if m.standing or m.chasing:       # nothing left to fight: on along the lane
                        m.standing = m.chasing = False
                        m.goal = None
                        self.spots.pop(net, None)
                        if m not in moves:
                            moves.append(m)
                    continue
                there = self.place(m.target, t, where)
            d = math.dist(here, there)
            size = self.body(m.target)
            limit = k['reach'] + RADIUS + size
            if not (m.standing and d <= limit + 25):
                # A place of its own to attack from: several minions on one enemy used to stop on the very same
                # point, inside each other. The place is kept while the enemy stays near where it was.
                if m.goal is None or math.dist(m.goal_ref, there) > 120 or math.dist(m.goal, there) > limit:
                    m.goal = self.spot(net, here, there, min(d, k['reach'] + size))
                    m.goal_ref = there
                    m.standing = False
                    if math.dist(here, m.goal) > 12:
                        m.chasing = True
                        m.path, m.path_t = self.way(here, m.goal), t
                        entries += LP.waypoint_entry(net, cells(m.path), MINION_SPEED)
                        continue
                if math.dist(here, m.goal) > 12:
                    continue                          # on its way there
                m.standing, m.chasing = True, False
                m.path, m.path_t = [m.goal], t
                here = m.goal
                entries += LP.waypoint_entry(net, cells([here]), MINION_SPEED)
                m.next_attack = max(m.next_attack, t)
            if t >= m.next_attack:
                if m.attacks:
                    # Riot's server repeats the one-point path with every attack of a standing minion (replay:
                    # one-point 552 entries 0.8 s apart for a melee minion in a fight)
                    entries += LP.waypoint_entry(net, cells([here]), MINION_SPEED)
                m.next_attack = t + k['period']
                m.attacks += 1
                v = {'+0xc': {'+0x4': '01000000', '+0x8': struct.pack('<I', m.target).hex(),
                              '+0xc': '40' if m.attacks % 2 else '41', '+0x14': '00000000',
                              '+0x1c': '80', '+0x20': struct.pack('<I', self.attack_net(net)).hex(),
                              '+0x24': struct.pack('<fff', there[0], HEIGHT, there[1]).hex()},
                     '+0x3c': struct.pack('<ff', here[0], here[1]).hex()}
                out.append((1, struct.pack('<HI', 286, net) + seal(286, self.fight[286].encode(v)),
                            f'286 {net:#x} attacks {m.target:#x}'))
                flight = (d / k['missile']) if k['missile'] else 0.0
                dmg = (180.0 + 10.0 * max(0, m.wave - 1)) if getattr(m, 'is_super', False) else k['damage']
                bisect.insort(self.queue, (t + k['windup'] + flight, 'hit', (net, m.target, dmg)))
        if entries:
            out += self.path_packets(entries, '552 minions stop or close in')
        out += self.think_turrets(t, where)
        out += self.think_monsters(t, where)
        out += self.think_bots(t, where)
        return out

    def other_target(self, m, here):
        """what a lane minion with no enemy minion near attacks: an enemy turret in reach that may be attacked, else
        an enemy champion very near"""
        best = None
        end = len(getattr(m, 'lane_path', [])) <= 1       # it walked its whole lane: the enemy base is all around
        for tu in self.turrets.values():
            if tu.alive and tu.open and tu.team != m.team:
                d = math.dist(here, tu.pos)
                if (d <= ACQUIRE + TURRET_BODY or (end and d <= 3500.0)) and (best is None or d < best[0]):
                    best = (d, tu.net)
        if best is None:
            for net, team, p in self.champions(self.now):
                if team != m.team:
                    d = math.dist(here, p)
                    if d <= HERO_NEAR and (best is None or d < best[0]):
                        best = (d, net)
        return best[1] if best else None

    # --------------------------------------------------------------------------------------------- turrets
    def structures_start(self, t):
        """what Riot's server tells about the turrets after the start state: their armor and attack damage (0.371 s)
        and, at 10.094 s, that they can be targeted (the outer ones by the enemy: team flags 4, status flags 256; the
        others not yet: 2)"""
        out = []
        if not self.turrets_stats and t >= TURRET_STATS:
            self.turrets_stats = True
            units = [(tu.net, {'mArmor': tu.armor, 'mBaseAttackDamage': tu.damage}, 'turret')
                     for tu in self.turrets.values() if tu.tier not in ('fountain', 'hq', 'dampener')]
            out.append(self.replication(t, units, f'595 {len(units)} turrets: armor, attack damage'))
        if not self.turrets_open and t >= TURRETS_OPEN:
            self.turrets_open = True
            units = []
            for tu in self.turrets.values():
                if tu.tier in ('fountain', 'hq', 'dampener'):
                    continue
                tu.open = tu.tier == 'outer'
                v = {'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4 if tu.open else 2}
                if tu.open:
                    v['StatusFlags'] = 256
                units.append((tu.net, v, 'turret'))
            out.append(self.replication(t, units, f'595 {len(units)} turrets can be targeted'))
        return out

    def think_turrets(self, t, where):
        out = []
        if not self.turrets_open:
            return out
        for tu in self.turrets.values():
            if not tu.alive or tu.tier in ('dampener', 'hq'):
                continue
            if tu.tier == 'fountain':
                # Fountain Laser defense: True damage beam against hostile champions in 1200 range
                reach = 1200.0
                hostiles = [(math.dist(tu.pos, p), net) for net, tm, p in self.champions(t) if tm != tu.team and math.dist(tu.pos, p) <= reach]
                if not hostiles:
                    tu.target = None
                    continue
                target_net = min(hostiles)[1]
                if t >= tu.next_attack:
                    tu.next_attack = t + 0.5
                    damage = 500.0
                    out.append(self.damage_number(target_net, tu.net, damage))
                    if target_net in self.heroes:
                        self.events.append(('hero_hit', t, tu.net, target_net, damage))
                    elif target_net in self.bots:
                        out += self.hit_bot(t, tu.net, target_net, damage, show=False)
                continue
            reach = TURRET_REACH + TURRET_BODY
            there = self.place(tu.target, t, where) if tu.target is not None else None
            if tu.target is not None and (there is None or math.dist(tu.pos, there) > reach + 30):
                out += self.turret_stops(tu)
                there = None
            if tu.target is None:
                best = None
                for net, p in where.items():
                    if self.minions[net].team != tu.team:
                        d = math.dist(tu.pos, p)
                        if d <= reach and (best is None or d < best[0]):
                            best = (d, net)
                if best is None:
                    for net, team, p in self.champions(t):
                        if team != tu.team:
                            d = math.dist(tu.pos, p)
                            if d <= reach and (best is None or d < best[0]):
                                best = (d, net)
                if best is None:
                    continue
                tu.target, tu.first = best[1], True
                tu.next_attack = max(tu.next_attack, t + TURRET_AIM)
                tgt = struct.pack('<I', tu.target).hex()
                out.append(self.real['attack_740'][0].packet(tu.net, lambda v: v.update({'+0xc': tgt}),
                                                             f'740 turret {tu.name} targets {tu.target:#x}'))
                continue
            if t >= tu.next_attack:
                out += self.turret_attacks(tu, t, there)
        return out

    def turret_attacks(self, tu, t, there):
        """one attack of a turret, as the replay's: the first on a target is 66 + 592 (with the turret's place), the
        next ones 26; 516 with each; the missile leaves 0.265 s later (779)"""
        self.attack_count += 4
        missile = self.new_net()
        tgt = struct.pack('<I', tu.target).hex()
        pos = struct.pack('<fff', there[0], HEIGHT, there[1]).hex()
        count = struct.pack('<I', self.attack_count).hex()

        def attack(v):
            a = v['+0xc']
            a['+0x4'], a['+0x8'], a['+0x20'], a['+0x24'] = count, tgt, struct.pack('<I', missile).hex(), pos
            if '+0x3c' in v:
                v['+0x3c'] = struct.pack('<ff', float(int(tu.pos[0])), float(int(tu.pos[1]))).hex()
        out = []
        if tu.first:
            out.append(self.real['attack_66'][0].packet(tu.net, lambda v: v.update({'+0xc': tgt}), '66 turret target'))
            out.append(self.real['attack_592'][0].packet(tu.net, attack, f'592 turret {tu.name} attacks {tu.target:#x}'))
        else:
            out.append(self.real['attack_26'][0].packet(tu.net, attack, f'26 turret {tu.name} attacks {tu.target:#x}'))
        out.append(self.real['attack_516'][0].packet(tu.net, lambda v: v.update({'+0xc': pos, '+0x18': tgt}), '516 turret aims'))
        tu.first = False
        # from the moment the attack was due, not from the tick that noticed it (the period would grow by a tick)
        tu.next_attack = (tu.next_attack if t - tu.next_attack < 2 * THINK else t) + TURRET_PERIOD
        bisect.insort(self.queue, (t + TURRET_WINDUP, 'missile', (tu.net, tu.target, missile)))
        return out

    def turret_missile(self, t, source, target, missile):
        """the turret's missile leaves (779); it lands after its flight"""
        tu = self.turrets.get(source)
        there = self.place(target, t)
        if tu is None or not tu.alive or there is None:
            return []
        mid = struct.pack('<I', missile).hex()
        m = self.minions.get(target)
        damage = TURRET_SHARE.get(m.kind, 0.45) * m.max_hp if m is not None else tu.damage
        flight = max(0.0, math.dist(tu.pos, there) - TURRET_BODY) / TURRET_MISSILE
        bisect.insort(self.queue, (t + flight, 'hit', (source, target, damage)))
        return [self.real['attack_779'][0].packet(source, lambda v: v.update({'+0xc': mid}), '779 turret missile')]

    def turret_stops(self, tu):
        """the turret has nothing to attack any more: 490, then target cleared (66, 740), the replay's own bytes"""
        tu.target, tu.first = None, True
        return [self.real['attack_490'][0].as_sent(tu.net, f'490 turret {tu.name} stops'),
                self.real['attack_66'][1].as_sent(tu.net, '66 turret target cleared'),
                self.real['attack_740'][1].as_sent(tu.net, '740 turret target cleared')]

    def hit_turret(self, t, source, target, damage, show=True):
        """an attack lands on a turret: the damage goes through its armor; 263, the new health (595) and, at zero,
        its fall"""
        tu = self.turrets[target]
        if not tu.alive or not tu.open:
            return []
        damage = damage * 100.0 / (100.0 + tu.armor)
        tu.hp = max(0.0, tu.hp - damage)
        out = [self.damage_number(target, source, damage)] if show else []
        if tu.tier == 'hq':
            out.append(self.structure_values(t, tu, {0: struct.pack('<f', tu.hp) if tu.hp else b'\xff'}, {}))
            if tu.hp <= 0:
                out += self.nexus_falls(t, tu, source)
            return out
        out.append(self.replication(t, [(target, {'mHP': tu.hp}, 'turret')], f'595 turret {tu.name} health {tu.hp:.0f}'))
        if tu.hp <= 0:
            if tu.tier == 'dampener':
                out += self.inhibitor_falls(t, tu, source)
            else:
                out += self.turret_falls(t, tu, source)
        return out

    def inhibitor_falls(self, t, tu, source):
        """an inhibitor's death as the replay's (e.g. red top inhibitor at 1331.34 s): packet 634 on the inhibitor,
        310 with killer, 65 destroyed animation, 71 pose, packet 108 (state switch: 300s duration), untargetable 595;
        enables super minions and opens nexus turrets"""
        tu.alive = tu.open = False
        tu.respawn_at = t + 300.0
        killer = struct.pack('<I', source).hex()
        out = []
        if 'end_634' in self.real:
            out.append(self.real['end_634'][0].packet(tu.net, lambda v: v.update({'+0xc': killer}),
                                                      f'634 inhibitor {tu.name} falls (killer {source:#x})'))
        out += [self.real['death_310'][0].packet(tu.net, lambda v: v.update({'+0x2c': killer}),
                                                f'310 inhibitor {tu.name} falls'),
                self.real['death_65'][0].as_sent(tu.net, '65 inhibitor destroyed animation'),
                self.real['death_71'][0].as_sent(tu.net, '71 inhibitor destroyed pose')]
        # Packet 108: PKT_DampenerSwitchStates_s duration = 300s (measured on 13.3 replay: f94ef8)
        out.append((1, struct.pack('<HI', 108, tu.net) + bytes.fromhex('f94ef8'), f'108 inhibitor {tu.name} 300s timer'))
        units = [(tu.net, {'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3, 'StatusFlags': 257}, 'turret')]
        # open nexus turrets of this team
        nxt = [x for x in self.turrets.values() if x.team == tu.team and x.tier == 'nexus']
        for x in nxt:
            if x.alive and not x.open:
                x.open = True
                units.append((x.net, {'mIsTargetableToTeamFlags': 4, 'StatusFlags': 256}, 'turret'))
        out.append(self.replication(t, units, f'595 inhibitor {tu.name} down, {len(units) - 1} nexus turrets open'))
        enemy = 'red' if tu.team == 'blue' else 'blue'
        self.super_minions[enemy][tu.lane] = True
        for net, h in self.heroes.items():
            if h['team'] == enemy:
                self.events.append(('gold', t, net, 50.0))
        self.events.append(('inhibitor_dead', t, tu.net, tu.team, tu.lane, source))
        # if nexus turrets are already gone, opening the inhibitor opens the nexus
        if not any(x.alive for x in self.turrets.values() if x.team == tu.team and x.tier == 'nexus'):
            for hq in self.turrets.values():
                if hq.tier == 'hq' and hq.team == tu.team and hq.alive and not hq.open:
                    hq.open = True
                    out.append(self.structure_values(t, hq, {}, {0: b'\x01', 1: b'\x04'}))
            self.events.append(('nexus_open', t, tu.team))
        return out

    def structure_values(self, t, tu, health, target):
        """595 for a nexus: its class keeps the health in group 2 (bit 0 mHP, bit 1 mMaxHP: floats) and "can be
        targeted" in group 7 (bit 0 flag, bit 1 team flags) -- the start state's own layout (masks 0x7ff and 0x3)"""
        groups = {}
        if health:
            groups[2] = (sum(1 << b for b in health), b''.join(health[b] for b in sorted(health)))
        if target:
            groups[7] = (sum(1 << b for b in target), b''.join(target[b] for b in sorted(target)))
        return self.replication_raw(t, [raw_unit(tu.net, groups)], f'595 nexus {tu.name} health {tu.hp:.0f}')

    def nexus_falls(self, t, tu, source):
        """the end of the match as the replay's (the red nexus at 1863.668 s): 589 (SOG_NEXUS), 634 on the nexus with
        the killer, 785, 716; four seconds later 766, then 137 and 213 -- the replay's own bytes (its blue team
        won; what they say when red wins is not known yet)"""
        tu.alive = tu.open = False
        self.over = tu.team
        killer = struct.pack('<I', source).hex()
        out = []
        if 'end_589' in self.real:
            out.append(self.real['end_589'][0].as_sent(0, '589 the nexus fell'))
        if 'end_634' in self.real:
            out.append(self.real['end_634'][0].packet(tu.net, lambda v: v.update({'+0xc': killer}),
                                                      f'634 nexus {tu.name} falls (killer {source:#x})'))
        for key in ('end_785', 'end_716'):
            if key in self.real:
                out.append(self.real[key][0].as_sent(0, key[4:] + ' end of the match'))
        # 766 +0x14 = the team whose nexus fell (0xc8 = 200 = red in the replay), 137 +0xc = the team that won (0x64 =
        # 100 = blue there): the two fields that name a team, set for our match
        lost = 'c8' if tu.team == 'red' else '64'
        won = '64000000' if tu.team == 'red' else 'c8000000'
        if 'end_766' in self.real:
            self.push_later(t + 4.0, [self.real['end_766'][0].packet(0, lambda v: v.update({'+0x14': lost}), '766 end of the match')])
        last = []
        if 'end_137' in self.real:
            last.append(self.real['end_137'][0].packet(0, lambda v: v.update({'+0xc': won}), f'137 end of the match, winner {won[:2]}'))
        if 'end_213' in self.real:
            last.append(self.real['end_213'][0].as_sent(0, '213 end of the match'))
        if last:
            self.push_later(t + 5.2, last)
        self.events.append(('game_over', t, tu.team, source))
        return out

    def turret_falls(self, t, tu, source):
        """a turret's death as the replay's (the red bot outer turret at 654.64 s): 310 with the killer, 65 + 71 (the
        destroyed animation; real bytes), not targetable any more; the next turret of the lane opens"""
        tu.alive = tu.open = False
        self.turret_deaths += 1
        killer = struct.pack('<I', source).hex()
        out = [self.real['death_310'][0].packet(tu.net, lambda v: v.update({'+0x2c': killer}),
                                                f'310 turret {tu.name} falls (killer {source:#x})'),
                self.real['death_65'][0].as_sent(tu.net, '65 turret destroyed animation'),
                self.real['death_71'][0].as_sent(tu.net, '71 turret destroyed pose')]
        units = [(tu.net, {'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3, 'StatusFlags': 257}, 'turret')]
        order = ['outer', 'inner', 'inhibitor']
        nxt = []
        if tu.tier in order[:2]:
            want = order[order.index(tu.tier) + 1]
            nxt = [x for x in self.turrets.values() if x.team == tu.team and x.lane == tu.lane and x.tier == want]
        elif tu.tier == 'inhibitor':
            nxt = [x for x in self.turrets.values() if x.team == tu.team and x.lane == tu.lane and x.tier == 'dampener']
        for x in nxt:
            if x.alive and not x.open:
                x.open = True
                units.append((x.net, {'mIsTargetableToTeamFlags': 4, 'StatusFlags': 256}, 'turret'))
        out.append(self.replication(t, units, f'595 turret {tu.name} gone, {len(units) - 1} more can be attacked'))
        for other in self.turrets.values():
            if other.target == tu.net:
                other.target = None
        enemy = 'red' if tu.team == 'blue' else 'blue'
        for net, h in self.heroes.items():
            if h['team'] == enemy:
                self.events.append(('gold', t, net, TURRET_GOLD))
        self.events.append(('turret_dead', t, tu.net, tu.team, source))
        if tu.tier == 'nexus' and not any(x.alive for x in self.turrets.values() if x.team == tu.team and x.tier == 'nexus'):
            # both nexus turrets are gone: the nexus itself can be attacked if at least one inhibitor is down
            any_inh_down = any(not x.alive for x in self.turrets.values() if x.team == tu.team and x.tier == 'dampener')
            if any_inh_down:
                for hq in self.turrets.values():
                    if hq.tier == 'hq' and hq.team == tu.team and hq.alive and not hq.open:
                        hq.open = True
                        out.append(self.structure_values(t, hq, {}, {0: b'\x01', 1: b'\x04'}))
                self.events.append(('nexus_open', t, tu.team))
        return out

    def spot(self, net, here, there, want):
        """where a minion goes to attack the enemy at `there`: `want` away from it, on the side it comes from, or
        the nearest place around the enemy that no other minion has taken (two bodies apart)"""
        base = math.atan2(here[1] - there[1], here[0] - there[0])
        step = min(0.9, 2.2 * RADIUS / max(want, 1.0))
        others = [p for n, p in self.spots.items() if n != net]
        first = None
        for i in range(13):
            for sign in ((1,) if i == 0 else (1, -1)):
                a = base + sign * i * step
                c = (there[0] + want * math.cos(a), there[1] + want * math.sin(a))
                if self.nav.is_blocked(*c):
                    continue                      # inside a wall or a turret's footprint
                first = first or c
                if all(math.dist(c, p) >= 1.9 * RADIUS for p in others):
                    self.spots[net] = c
                    return c
        first = first or self.nav.nearest_free(*there) or there
        self.spots[net] = first
        return first

    def hit(self, t, source, target, damage, show=True, kind=0, is_basic=True):
        """an attack lands: 263 (show=False: the caller sends the damage number itself), the new health (595)
        and, at zero, the death (61)"""
        import lol_packets as LP
        import repl_codec as RC
        if target in self.turrets:
            return self.hit_turret(t, source, target, damage, show)
        if target in self.heroes:
            # a champion's health is the server's: it gets the raw damage and sends what follows itself
            if self.heroes[target]['alive']:
                self.events.append(('hero_hit', t, source, target, damage))
            return []
        if target in self.monsters:
            return self.hit_monster(t, source, target, damage, show)
        if target in self.bots:
            return self.hit_bot(t, source, target, damage, show)
        m = self.minions.get(target)
        if m is None:
            return []
        m.hp = max(0.0, m.hp - damage)
        v = {'+0xa': '00', '+0xc': struct.pack('<I', target).hex(), '+0x10': f'{kind:02x}',
             '+0x14': struct.pack('<f', damage).hex(), '+0x18': '00000000', '+0x1c': '04',
             '+0x1d': '01' if is_basic else '00',
             '+0x20': struct.pack('<I', source).hex()}
        out = [(1, struct.pack('<HI', 263, target) + seal(263, self.fight[263].encode(v)), f'263 {damage:.1f} damage on minion {target:#x} (HP: {m.hp:.1f})')] if show else []
        # the client takes a replication packet only when its counter is newer than the last one it saw: every
        # health update needs its own (the fixed head and trailer of a replay packet are applied once only)
        self.counter[0] += 1
        out.append((2, struct.pack('<HI', 595, 0) + RC.packet([(target, {'mHP': m.hp}, 'lane_minion')], t, self.counter[0]),
                    f'595 minion {target:#x} health {m.hp:.1f}'))
        if m.hp <= 0:
            where = m.pos(t)
            del self.minions[target]
            self.spots.pop(target, None)
            self.attack_nets.pop(target, None)
            self.deaths += 1
            if self.died is not None:
                self.died.append((t, target, source))
            # the enemy champions near a dying minion share its experience
            near = [n for n, h in self.heroes.items() if h['alive'] and h['team'] != m.team and where is not None
                    and math.dist(h['pos'], where) <= XP_RANGE]
            for n in near:
                self.events.append(('xp', t, n, MINION_XP.get(m.kind, 60.0) / len(near)))
            if source in self.heroes:
                gold_amt = {'04': 21.0, '05': 14.0, '06': 57.0}.get(m.kind, 21.0)
                self.events.append(('gold', t, source, gold_amt, target))
            v = {'+0xc': '00000000', '+0x10': {'+0x4': '00000000', '+0x8': '00000000', '+0xc': '20010000',
                                                 '+0x10': '00000000', '+0x14': '02'},
                 '+0x28': '00', '+0x2c': struct.pack('<I', source).hex(), '+0x30': '00000000'}
            out.append((1, struct.pack('<HI', 61, target) + seal(61, self.fight[61].encode(v)),
                        f'61 minion {target:#x} dies ({self.deaths} so far)'))
        return out

    # --------------------------------------------------------------------------------------------- the jungle
    def monster_appears(self, t, index, net):
        """a monster is created as in the replay: its own packets, in their order and spacing; a returning camp's
        monster gets a new net id (the 359 holds it at +0x6c)"""
        d = self.monster_data[index]
        if index not in self.monster_real:
            self.monster_real[index] = Real(d['create'])
        create = self.monster_real[index]
        same = net == d['net']
        nid = struct.pack('<I', net).hex()
        now = [(ch, struct.pack('<HI', pid, net) + bytes.fromhex(hx), f'{pid} monster') for dt, ch, pid, hx in d['packets'] if pid == 506]
        now.append(create.as_sent(net, f'359 monster {d["name"]} -> {net:#x}') if same else
                   create.packet(net, lambda v: v.update({'+0x6c': nid}), f'359 monster {d["name"]} -> {net:#x}'))
        for dt, ch, pid, hx in d['packets']:
            if pid != 506:
                self.push_later(t + dt, [(ch, struct.pack('<HI', pid, net) + bytes.fromhex(hx), f'{pid} monster')])
        # its first replication blocks (every value: what it may do, health, stats), as sent, before anyone hit it
        values, last = {}, None
        for dt, groups in d['blocks']:
            if dt > 0.6:
                break
            g = {int(k): (m, bytes.fromhex(hx)) for k, (m, hx) in groups.items()}
            if g == last:
                continue
            last = g
            values.update(read_values(g))
            self.push_later(t + dt, [self.replication_raw(t + dt, [raw_unit(net, g)], f'595 monster {d["name"]}')])
        mo = Monster(index, d, net, t, values)
        self.monsters[net] = mo
        self.push_later(t + MONSTER_OPEN, [('open', net)])
        return now

    def monster_opens(self, t, net):
        mo = self.monsters.get(net)
        if mo is None:
            return []
        mo.open = True
        return [self.replication(t, [(net, {'StatusFlags': 0, 'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4,
                                           'mHP': mo.hp, 'mMaxHP': mo.max_hp}, 'lane_minion')],
                                 f'595 monster {mo.name} can be targeted')]

    def think_monsters(self, t, where):
        import lol_packets as LP
        out, entries = [], b''
        for net, mo in list(self.monsters.items()):
            if mo.target is None:
                continue
            here = mo.pos(t)
            there = self.place(mo.target, t, where)
            if there is None or math.dist(mo.home, there) > MONSTER_LEASH:
                # the one it fought is gone or too far: home, and whole again
                mo.target = None
                mo.path, mo.path_t = self.way(here, mo.home), t
                entries += LP.waypoint_entry(net, self.cells(mo.path), mo.speed)
                if mo.hp < mo.max_hp:
                    mo.hp = mo.max_hp
                    out.append(self.replication(t, [(net, {'mHP': mo.hp}, 'lane_minion')], f'595 monster {mo.name} heals'))
                continue
            d = math.dist(here, there)
            reach = mo.reach + self.body(mo.target) + MONSTER_BODY * 0.5
            if d > reach:
                if t >= mo.next_path:
                    mo.next_path = t + 0.35
                    mo.path, mo.path_t = self.way(here, there), t
                    entries += LP.waypoint_entry(net, self.cells(mo.path), mo.speed)
                continue
            if mo.moving(t):
                mo.path, mo.path_t = [here], t
                entries += LP.waypoint_entry(net, self.cells([here]), mo.speed)
            if t >= mo.next_attack:
                mo.next_attack = t + MONSTER_PERIOD
                mo.attacks += 1
                out.append(self.basic_attack(net, mo.target, here, there, mo.attacks))
                bisect.insort(self.queue, (t + MONSTER_WINDUP, 'hit', (net, mo.target, self.through_armor(mo.target, mo.damage))))
        if entries:
            out += self.path_packets(entries, '552 monsters')
        return out

    def basic_attack(self, net, target, here, there, count=1):
        """286: the basic attack of a unit without cast data (lane minions, monsters)"""
        v = {'+0xc': {'+0x4': '01000000', '+0x8': struct.pack('<I', target).hex(),
                      '+0xc': '40' if count % 2 else '41', '+0x14': '00000000',
                      '+0x1c': '80', '+0x20': struct.pack('<I', self.attack_net(net)).hex(),
                      '+0x24': struct.pack('<fff', there[0], HEIGHT, there[1]).hex()},
             '+0x3c': struct.pack('<ff', here[0], here[1]).hex()}
        return (1, struct.pack('<HI', 286, net) + seal(286, self.fight[286].encode(v)), f'286 {net:#x} attacks {target:#x}')

    def through_armor(self, target, damage):
        """physical damage on a bot goes through its armor here; a player's champion gets the raw number (the server
        knows its armor); turrets take theirs in hit_turret; minions and monsters: as it is"""
        b = self.bots.get(target)
        if b is not None:
            return damage * 100.0 / (100.0 + b.armor)
        mo = self.monsters.get(target)
        if mo is not None:
            return damage * 100.0 / (100.0 + mo.armor)
        return damage

    def death_packet(self, target, source, what):
        v = {'+0xc': '00000000', '+0x10': {'+0x4': '00000000', '+0x8': '00000000', '+0xc': '20010000',
                                             '+0x10': '00000000', '+0x14': '02'},
             '+0x28': '00', '+0x2c': struct.pack('<I', source).hex(), '+0x30': '00000000'}
        return (1, struct.pack('<HI', 61, target) + seal(61, self.fight[61].encode(v)), what)

    def hit_monster(self, t, source, target, damage, show=True):
        mo = self.monsters[target]
        if not mo.open:
            return []
        if source in self.heroes:
            damage = damage * 100.0 / (100.0 + mo.armor)      # a player's attack comes without the monster's armor
        mo.hp = max(0.0, mo.hp - damage)
        out = [self.damage_number(target, source, damage)] if show else []
        out.append(self.replication(t, [(target, {'mHP': mo.hp}, 'lane_minion')], f'595 monster {mo.name} health {mo.hp:.0f}'))
        if source in self.heroes or source in self.bots:
            for other in self.monsters.values():      # the whole camp turns on the one who hit it
                if other.camp == mo.camp and other.target is None and other.open:
                    other.target = source
        if mo.hp <= 0:
            del self.monsters[target]
            self.attack_nets.pop(target, None)
            out.append(self.death_packet(target, source, f'61 monster {mo.name} dies'))
            gold, xp = JUNGLE.get(mo.skin, (30, 40))
            if source in self.heroes:
                self.events.append(('gold', t, source, float(gold)))
                self.events.append(('xp', t, source, float(xp)))
            if not any(o.camp == mo.camp for o in self.monsters.values()):
                back = CAMP_BACK.get(mo.skin.replace('Mini', ''), 135.0)
                idx = tuple(i for i, d in enumerate(self.monster_data) if camp_of(d['name']) == mo.camp)
                bisect.insort(self.queue, (t + back, 'camp', (mo.index, idx)))
        return out

    # --------------------------------------------------------------------------------------------- the bots
    def bots_start(self, t):
        """the nine champions nobody plays get what Riot's server gives a champion in the first seconds: what it may
        do (ActionState 0x200000f, ActionState2 4), that it can be targeted, and our health / stats for it"""
        self.bots_started = True
        units = []
        for b in self.bots.values():
            units.append((b.net, {'ActionState': 0x200000f, 'ActionState2': 4, 'mIsTargetable': 1,
                                  'mIsTargetableToTeamFlags': 4, 'mHP': b.hp, 'mMaxHP': b.max_hp,
                                  'mBaseAttackDamage': b.damage, 'mArmor': b.armor, 'mAttackRange': b.reach,
                                  'mMoveSpeed': b.speed}, 'hero'))
        out = []
        for i in range(0, len(units), 3):                 # a few units a packet: the buffer's size field is a byte
            out.append(self.replication(t, units[i:i + 3], f'595 bots {[hex(u[0]) for u in units[i:i + 3]]} start state'))
        return out

    def bot_post(self, b, t, where):
        """where a bot with nothing to attack stands: behind its lane's front minion; with no minion of its own
        there, behind its lane's first turret still standing; never inside an enemy turret's range without two of
        its own minions in it"""
        key = (b.team, b.lane)
        if key not in self.paths:
            return b.home
        mine = [self.along(key, p) for n, p in where.items() if self.minions[n].team == b.team and self.minions[n].lane == b.lane]
        back = 420.0 if b.ranged else 140.0
        if mine:
            s = max(mine) - back
        else:
            tiers = {'outer': 0, 'inner': 1, 'inhibitor': 2}
            own = sorted((tiers[tu.tier], tu.pos) for tu in self.turrets.values()
                         if tu.alive and tu.team == b.team and tu.lane == b.lane and tu.tier in tiers)
            s = (self.along(key, own[0][1]) - 250.0) if own else 2500.0
        for _ in range(12):
            q = self.point_at(key, s)
            danger = False
            for tu in self.turrets.values():
                if tu.alive and tu.team != b.team and tu.tier != 'fountain' and math.dist(q, tu.pos) < TURRET_REACH + TURRET_BODY + 150:
                    cover = sum(1 for n, p in where.items() if self.minions[n].team == b.team
                                and math.dist(p, tu.pos) < TURRET_REACH + TURRET_BODY)
                    if cover < 2:
                        danger = True
            if not danger:
                break
            s -= 200.0
        return self.point_at(key, max(s, 600.0))

    def bot_target(self, b, here, t, where):
        """an enemy champion that came near (when the bot is healthy and the place is safe), else the weakest enemy
        lane minion in reach, else an enemy turret with two of its own minions under it"""
        def safe(p):
            for tu in self.turrets.values():
                if tu.alive and tu.team != b.team and tu.tier != 'fountain' and math.dist(p, tu.pos) < TURRET_REACH + TURRET_BODY + 60:
                    cover = sum(1 for n, q in where.items() if self.minions[n].team == b.team
                                and math.dist(q, tu.pos) < TURRET_REACH + TURRET_BODY)
                    if cover < 2:
                        return False
            return True
        if b.hp > 0.45 * b.max_hp:
            near = [(math.dist(here, p), n) for n, team, p in self.champions(t) if team != b.team and n != b.net]
            near = [x for x in near if x[0] <= BOT_SIGHT]
            if near:
                d, n = min(near)
                if safe(self.place(n, t, where)):
                    return n
        best = None
        for n, p in where.items():
            m = self.minions[n]
            if m.team != b.team and math.dist(here, p) <= b.reach + 350:
                if best is None or m.hp < best[0]:
                    best = (m.hp, n)
        if best is not None and safe(where[best[1]]):
            return best[1]
        for tu in self.turrets.values():
            if tu.alive and tu.open and tu.team != b.team and math.dist(here, tu.pos) <= b.reach + TURRET_BODY + 500:
                cover = sum(1 for n, q in where.items() if self.minions[n].team == b.team
                            and math.dist(q, tu.pos) < TURRET_REACH + TURRET_BODY)
                if cover >= 2:
                    return tu.net
        return None

    def think_bots(self, t, where):
        import lol_packets as LP
        out, entries = [], b''
        if not self.bots_started:
            if t < BOTS_START:
                return out
            out += self.bots_start(t)
        for net, b in self.bots.items():
            if not b.alive:
                if t >= b.back_at:
                    out += self.bot_returns(t, b)
                continue
            here = b.pos(t)
            if math.dist(here, b.home) < 1000.0 and b.hp < b.max_hp:
                b.hp = min(b.max_hp, b.hp + 0.085 * b.max_hp * THINK)
            if abs(b.hp - b.sent_hp) >= 1.0 and t >= b.next_health:
                b.next_health, b.sent_hp = t + 1.0, b.hp
                out.append(self.replication(t, [(net, {'mHP': b.hp}, 'hero')], f'595 bot {b.champion} health {b.hp:.0f}'))
            if t < BOTS_LEAVE:
                continue
            if b.retreat and b.hp >= 0.9 * b.max_hp:
                b.retreat = False
            if not b.retreat and b.hp < 0.3 * b.max_hp:
                b.retreat, b.target = True, None
            goal = None
            if b.retreat:
                goal = b.home
            else:
                there = self.place(b.target, t, where) if b.target is not None else None
                if there is None or math.dist(here, there) > BOT_SIGHT + 400 or t >= getattr(b, 'retarget', 0.0):
                    b.retarget = t + 0.5
                    new = self.bot_target(b, here, t, where)
                    if new != b.target:
                        b.target, b.first = new, True
                    there = self.place(b.target, t, where) if b.target is not None else None
                if b.target is None or there is None:
                    b.target = None
                    goal = self.bot_post(b, t, where)
                else:
                    d = math.dist(here, there)
                    reach = b.reach + b.radius + self.body(b.target)
                    if d > reach:
                        goal = there
                    else:
                        if b.moving(t):
                            b.path, b.path_t = [here], t
                            entries += LP.waypoint_entry(net, self.cells([here]), b.speed)
                        if t >= b.next_attack:
                            out += self.bot_attacks(b, t, here, there, d)
            if goal is not None:
                far = math.dist(here, goal)
                moved = math.dist(b.path[-1], goal)
                if far > 60 and (moved > 100 or not b.moving(t)) and t >= b.next_path:
                    b.next_path = t + 0.4
                    b.path, b.path_t = self.bot_way(b, here, goal), t
                    entries += LP.waypoint_entry(net, self.cells(b.path), b.speed)
        if entries:
            out += self.path_packets(entries, '552 bots')
        return out

    def bot_attacks(self, b, t, here, there, d):
        """a champion's basic attack: the replay's attack of a unit without cast data (592 first on a target, 26
        next, 516), our ids; the damage lands after the windup (and a missile's flight for a ranged champion)"""
        self.attack_count += 4
        missile = self.new_net()
        tgt = struct.pack('<I', b.target).hex()
        pos = struct.pack('<fff', there[0], HEIGHT, there[1]).hex()
        count = struct.pack('<I', self.attack_count).hex()

        def attack(v):
            a = v['+0xc']
            a['+0x4'], a['+0x8'], a['+0x20'], a['+0x24'] = count, tgt, struct.pack('<I', missile).hex(), pos
            if '+0x3c' in v:
                v['+0x3c'] = struct.pack('<ff', here[0], here[1]).hex()
        key = 'attack_592' if b.first else 'attack_26'
        out = [self.real[key][0].packet(b.net, attack, f'{key[7:]} bot {b.champion} attacks {b.target:#x}'),
               self.real['attack_516'][0].packet(b.net, lambda v: v.update({'+0xc': pos, '+0x18': tgt}), '516 bot aims')]
        b.first = False
        b.next_attack = t + b.period
        flight = d / 2000.0 if b.ranged else 0.0
        bisect.insort(self.queue, (t + b.windup + flight, 'hit', (b.net, b.target, self.through_armor(b.target, b.damage))))
        return out

    def hit_bot(self, t, source, target, damage, show=True):
        b = self.bots[target]
        if not b.alive:
            return []
        b.hp = max(0.0, b.hp - damage)
        b.sent_hp = b.hp
        out = [self.damage_number(target, source, damage)] if show else []
        out.append(self.replication(t, [(target, {'mHP': b.hp}, 'hero')], f'595 bot {b.champion} health {b.hp:.0f}'))
        if b.hp <= 0:
            out += self.bot_dies(t, b, source)
        return out

    def bot_dies(self, t, b, source):
        """a champion's death as the replay's (Jax at 308.379 s): target cleared, 568, the death time (780, 417 with
        the killer), 440; it stops where it is"""
        import lol_packets as LP
        here = b.pos(t)
        wait = min(52.5, 8.0 + t / 60.0)
        b.alive, b.back_at, b.target, b.retreat = False, t + wait, None, False
        b.path, b.path_t = [here], t
        f32 = struct.pack('<f', wait).hex()
        killer = struct.pack('<I', source).hex()
        own = struct.pack('<I', b.net).hex()
        out = [self.real['attack_740'][1].as_sent(b.net, '740 bot target cleared'),
               self.real['herodeath_568'][0].as_sent(b.net, '568 bot dies'),
               self.real['herodeath_780'][0].packet(b.net, lambda v: v.update({'+0xc': f32}), '780 bot death time'),
               self.real['herodeath_417'][0].packet(b.net, lambda v: v.update({'+0xc': f32, '+0x2c': killer}),
                                                    f'417 bot {b.champion} dies (killer {source:#x}, back in {wait:.0f} s)'),
               self.real['herodeath_440'][0].packet(b.net, lambda v: v.update({'+0xc': own}), '440 bot dies'),
               *self.path_packets(LP.waypoint_entry(b.net, self.cells([here]), b.speed), '552 bot stops (dead)')]
        if source in self.heroes:
            self.events.append(('gold', t, source, CHAMPION_GOLD))
            self.events.append(('xp', t, source, CHAMPION_XP))
        self.events.append(('champion_dead', t, b.net, b.team, source))
        return out

    def bot_returns(self, t, b):
        """alive again at its fountain (the replay's 128 with the place, a one-point 552 there, full health)"""
        import lol_packets as LP
        b.alive, b.hp, b.sent_hp, b.first = True, b.max_hp, b.max_hp, True
        b.path, b.path_t = [b.home], t
        place = struct.pack('<ff', *b.home).hex()
        return [self.real['respawn_128'][0].packet(b.net, lambda v: v.update({'+0xc': place}), f'128 bot {b.champion} alive again'),
                *self.path_packets(LP.waypoint_entry(b.net, self.cells([b.home]), b.speed), '552 bot at its fountain'),
                self.replication(t, [(b.net, {'mHP': b.hp}, 'hero')], f'595 bot {b.champion} health {b.hp:.0f}')]

    def routed(self, points):
        """a polyline whose every straight piece stays on walkable ground: a piece that crosses a wall is replaced by
        the path around it (the top lane's long piece along the north edge cut through terrain)"""
        out = [points[0]]
        for a, b in zip(points, points[1:]):
            if not self.nav.line_clear(a, b):
                way = self.nav.path(a, b)
                if way and len(way) > 1:
                    out += way[1:-1]
            out.append(b)
        return out

    def way(self, a, b):
        """points from a to b on walkable ground (a straight line when it is clear)"""
        if self.nav.line_clear(a, b):
            return [a, b]
        key = (int(a[0] // 100), int(a[1] // 100), int(b[0] // 100), int(b[1] // 100))
        way = self._ways.get(key)
        if way is None:
            way = self.nav.path(a, b) or [a, b]
            if len(self._ways) > 4000:
                self._ways.clear()
            self._ways[key] = way
        return [a] + list(way[1:-1]) + [b] if len(way) > 1 else [a, b]

    def bot_way(self, b, here, goal):
        """a champion's way: straight when it can, along its lane when both ends are near it (the lane's own
        points, no search), else over the grid"""
        if self.nav.line_clear(here, goal):
            return [here, goal]
        key = (b.team, b.lane)
        if key in self.paths and math.dist(here, goal) > 1500.0:
            sa, sb = self.along(key, here), self.along(key, goal)
            pa, pb = self.point_at(key, sa), self.point_at(key, sb)
            if math.dist(here, pa) < 4500.0 and math.dist(goal, pb) < 4500.0:
                path, ln = self.paths[key], self.lane_len[key]
                lo, hi = min(sa, sb), max(sa, sb)
                mid = [path[i] for i in range(len(path)) if lo < ln[i] < hi]
                if sa > sb:
                    mid.reverse()
                pts = self.way(here, pa) + mid + self.way(pb, goal)
                out = [pts[0]]
                for q in pts[1:]:
                    if math.dist(q, out[-1]) > 5:
                        out.append(q)
                return out if len(out) > 1 else [here, goal]
        return self.way(here, goal)

    def initial_path(self, bid):
        """the path a barrack's new minion gets inside its 518 (the replay's own, same for every minion of the
        barrack): world points, or None when the template has none we can read"""
        if bid not in self._initial:
            self._initial[bid] = None
            tpl = self.tpl.get(bid, {})
            if 518 in tpl:
                import pkt_schema as PS
                import waypoints as Wp
                ch, b, old = tpl[518]
                sc, tr = self.codec[518]
                v = PS.decode(tr, sc, struct.pack('<HI', 518, old) + b)
                blob = bytes.fromhex(v['+0x10']['text']) if v else b''
                i = blob.find(struct.pack('<I', old))
                if i >= 2:
                    n = blob[i - 2] // 2
                    mask = (2 * (n - 1) + 7) // 8 if n > 1 else 0
                    # every coordinate a full i16 (mask bits clear), as the replay's spawn paths are
                    if n > 1 and not any(blob[i + 8:i + 8 + mask]) and len(blob) >= i + 8 + mask + 4 * n:
                        cells = [struct.unpack_from('<hh', blob, i + 8 + mask + 4 * k) for k in range(n)]
                        self._initial[bid] = [(x * Wp.CELL + Wp.CENTER[0], z * Wp.CELL + Wp.CENTER[1])
                                              for x, z in cells]
        return self._initial[bid]

    def spawn(self, t, bid, team, lane, first, kind, x16, x18, x20, w):
        import lol_packets as LP
        import repl_codec as RC
        net = self.next_net
        self.next_net += 1
        if os.environ.get('WORLD_REPLAY_NETS'):
            # control experiments: our n-th minion of a barrack takes the net id of the replay's n-th minion of that
            # barrack, so the replay's own packets of a kind (lnp_server --pass-kinds) can stand in for ours
            if not hasattr(self, '_replay_nets'):
                self._replay_nets, self._replay_count = collections.defaultdict(list), collections.Counter()
                for line in open(os.path.join(RES, 'codec', '98.all.jsonl')):
                    r_ = json.loads(line)
                    if r_['v']:
                        self._replay_nets[r_['v']['+0x1c']].append(r_['obj'])
            if self._replay_count[bid] < len(self._replay_nets[bid]):
                net = self._replay_nets[bid][self._replay_count[bid]]
                self._replay_count[bid] += 1
        if os.environ.get('WORLD_REPLAY_IDS') and w == 1 and self.tpl.get(bid, {}).get(518):
            # control experiment: the replay's own net id and bytes for the first minion of each barrack
            if not hasattr(self, '_used_replay'):
                self._used_replay = set()
            if bid not in self._used_replay:
                self._used_replay.add(bid)
                net = self.tpl[bid][518][2]
        hp = self.health.get((kind, min(w, 60)), 477.0)
        is_super = self.super_minions.get(team, {}).get(lane, False) and kind == '06'
        if is_super:
            hp = 1800.0 + 100.0 * max(0, w - 1)
        m = Minion(net, team, lane, kind, w, hp, t)
        if is_super:
            m.is_super = True
        path = self.paths.get((team, lane))
        start = self.initial_path(bid)
        if start:
            # The spawn's "enters vision" packet (518) already gives the client a path out of the barracks
            # (about 1500 units, 4.6-5.2 s). The unit is on it from now on: the first move we send must start
            # where the client has it, not at a fixed point (that was a jump of 150-400 units for every minion).
            m.path, m.path_t = start, t
            first = start[-1]
        if path:
            # onto the lane from the lane point nearest to where the way out of the barracks ends
            k = min(range(len(path)), key=lambda i: math.dist(path[i], first))
            m.lane_path = [first] + path[k + 1:]
        else:
            m.lane_path = [first]
        self.minions[net] = m
        bisect.insort(self.queue, (t + FIRST_MOVE_DELAY, 'move', net))
        v = {'+0xa': KIND_FLAG.get(kind, '0000'), '+0xc': struct.pack('<f', t).hex(), '+0x10': struct.pack('<I', net).hex(), '+0x14': kind,
             '+0x15': f'{w & 0xff:02x}', '+0x16': x16, '+0x18': x18, '+0x1c': bid, '+0x20': x20}
        body = seal(98, self.sc98.encode(v))
        import pkt_schema as PS
        tpl = self.tpl.get(bid, {})
        pk = [(ch, struct.pack('<HI', 506, net) + b, '506') for ch, b in tpl.get(506, [])]
        pk.append((1, struct.pack('<HI', 98, net) + body, f'98 spawn {team} {lane} wave {w} kind {kind} -> {net:#x}'))
        # Riot's server sends the unit's creation (506 x4, 98) in one tick and what happens to the unit - visible (387),
        # enters vision with its way out of the barracks (518), health (770) - in the NEXT tick, 33 ms later (replay:
        # 98 at 125.031, 387 / 518 / 770 at 125.064). Sent together with the 98 they reach the client before the unit
        # exists: the way out was lost and the minion stood on the spawn point until our first move.
        now, pk = pk, []
        pk.append((1, struct.pack('<HI', 387, net) + bytes.fromhex(tpl[387][1].hex()) if 387 in tpl else b'', '387 visible'))
        if 518 in tpl:
            ch, b, old = tpl[518]
            sc, tr = self.codec[518]
            if (bid, 518) not in self._decoded:
                self._decoded[(bid, 518)] = PS.decode(tr, sc, struct.pack('<HI', 518, old) + b)
            v518 = copy.deepcopy(self._decoded[(bid, 518)])
            blob = bytearray.fromhex(v518['+0x10']['text'])
            i = blob.find(struct.pack('<I', old))
            if i >= 7 and blob[i - 7] == 2:
                # The movement data inside carries the server's movement counter (replay: 69,246 for the first
                # minion at 65.07 s, 70,285 for the next 0.83 s later, 110,155 in wave 2 ...). The template's old
                # value on every minion made the client drop the way out of the barracks: they stood on the spawn
                # point, one inside the other, until our first 552. It must be the newest value we have sent.
                import lol_packets as LP_
                import sync552
                struct.pack_into('<I', blob, i - 6, sync552.last_value(LP_.SYNC_FLOOR))
            v518['+0x10']['text'] = bytes(blob).hex().replace(struct.pack('<I', old).hex(), struct.pack('<I', net).hex())
            pk.append((ch, struct.pack('<HI', 518, net) + seal(518, sc.encode(v518)), '518 enters vision'))
        if 770 in tpl:
            ch, b, old = tpl[770]
            sc, tr = self.codec[770]
            if (bid, 770) not in self._decoded:
                self._decoded[(bid, 770)] = PS.decode(tr, sc, struct.pack('<HI', 770, old) + b)
            v770 = copy.deepcopy(self._decoded[(bid, 770)])
            v770['+0x10']['text'] = struct.pack('<fff', hp, 0.0, hp).hex()
            pk.append((ch, struct.pack('<HI', 770, net) + seal(770, sc.encode(v770)), '770 health'))
        # Every replicated value of the new unit, in the tick of its creation: what it may do (it moves, it attacks),
        # its health, that it can be targeted. 0.132 s later the kind's stats (attack damage, range, move speed 325).
        # Both blocks are the replay's, byte for byte, for the first minion (minion_values).
        now.append(self.replication(t, [(net, minion_values(hp), 'lane_minion')], f'595 minion {net:#x} created, health {hp:.0f}'))
        self.push_later(t + STATS_DELAY, [self.replication(t + STATS_DELAY, [(net, minion_values(hp, kind, is_super), 'lane_minion')],
                                                           f'595 minion {net:#x} stats')])
        real = os.environ.get('WORLD_REAL_KINDS')
        if real:
            # control experiments (with WORLD_REPLAY_NETS): for the listed packet ids the replay's own bytes about
            # this very unit go out instead of ours, one kind at a time, to find the kind we write wrongly
            want = {int(x) for x in real.split(',')}
            table, used = self._real_packets(), collections.Counter()

            def swap(items):
                out_ = []
                for ch_, data_, what_ in items:
                    pid_ = struct.unpack_from('<H', data_)[0]
                    bodies = table.get((pid_, net), []) if pid_ in want else []
                    if pid_ in want and used[pid_] < len(bodies):
                        out_.append((ch_, data_[:6] + bodies[used[pid_]], what_ + ' (replay bytes)'))
                        used[pid_] += 1
                    elif pid_ in want:
                        continue                      # the replay has no such packet for this unit
                    else:
                        out_.append((ch_, data_, what_))
                return out_
            now, pk = swap(now), swap(pk)
        self.push_later(t + APPEAR_DELAY, pk)
        return now

    def _real_packets(self):
        """(packet id, net id) -> bodies in replay order, for the first 140 s (control experiments only)"""
        if not hasattr(self, '_real'):
            import rofl_packets as R
            self._real = collections.defaultdict(list)
            r = R.Rofl(os.path.join(HERE, '..', 'data', 'rofl', 'KR-6363178603_13.3.rofl'))
            for e, (tt, ch, pid, obj, body) in R.stream(r):
                if tt > 140:
                    break
                if pid in (506, 98, 387, 518, 770):
                    self._real[(pid, obj)].append(bytes(body))
        return self._real

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
        return self.path_packets(entries, f'552 {len(ms)} minions walk their lanes')


if __name__ == '__main__':
    w = World()
    for k, p in w.paths.items():
        print(k, len(p), p[0], p[-1])
    for t in (64, 65.1, 66, 70):
        for ch, data, what in w.tick(t):
            print(t, ch, len(data), what)
