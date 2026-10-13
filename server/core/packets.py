"""Every server packet our simulation writes, in the live 16.20 server's forms. The one place bytes are made: the
simulation calls these by meaning (an attack, a death, a cast) and never touches a packet's fields itself.

A writer starts from a decoded sample of the real server's own packet of that kind (data/exe1620/forms16.json,
tools/build_forms16.py), sets the fields whose meaning is measured and keeps the rest as the real server sent it.
Field meanings: docs/SERVER16_ARHITECTURA.md; [m] measured on the live recording, [a] our reading.

Every writer returns a list of (channel, packet id, net id, body).
"""
import copy
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)
os.environ.setdefault('BA_PATCH', '1620')
import types                                             # noqa: E402
sys.modules.setdefault('decoded', types.ModuleType('decoded'))
import forms16          # noqa: E402
import lol_packets      # noqa: E402
import pkt_schema as PS  # noqa: E402
import repl16           # noqa: E402
import waypoints        # noqa: E402

RES = os.path.join(SERVER, '..', 'data', 'exe1620')
MOVE, REPL = 61, 287
MOVE_COUNTER_RATE = 913.0        # [m] the movement packet's counter grows about this much a second
# damage packet 150 [m]: +0x18 type, +0x19 basic attack, +0x1a source kind, +0x20 05 normal / 03 critical
PHYSICAL, MAGIC, TRUE = 0, 1, 2
# the damage packet's source kind [m: tools/damage_rules16.py] - 0 a direct hit (attack or spell), 6 over time, 5 a pulsing
# area, 9 / 10 a missile out / back; per spell name the real values come from damage_rules16.json
SRC_ATTACK, SRC_DIRECT, SRC_SPELL, SRC_AOE, SRC_PERSIST, SRC_PERIODIC = 0x00, 0x00, 0x00, 0x09, 0x0a, 0x06


def u32(n):
    return struct.pack('<I', int(n) & 0xffffffff).hex()


def f32(x):
    return struct.pack('<f', float(x)).hex()


def vec3(x, y, z):
    return struct.pack('<fff', x, y, z).hex()


def cell(p):
    return (int(round((p[0] - waypoints.CENTER[0]) / waypoints.CELL)), int(round((p[1] - waypoints.CENTER[1]) / waypoints.CELL)))


def text(s):
    return {'text': (s if isinstance(s, bytes) else s.encode()).hex()}


_damage_rules = None


def damage_rule(name_hash):
    """(flag +0x19, source +0x1a) the real server gives a damage packet of that spell / attack [m: tools/damage_rules16.py,
    the majority over 30 replays] or None"""
    global _damage_rules
    if _damage_rules is None:
        try:
            _damage_rules = {int(k, 16): v for k, v in json.load(open(os.path.join(RES, 'damage_rules16.json'))).items()}
        except Exception:
            _damage_rules = {}
    r = _damage_rules.get(name_hash) if name_hash else None
    return (bool(r[0]), r[1]) if r else None


_damage_names = None


def damage_hash(spell_name):
    """the name hash a spell's damage carries [m: tools/damage_names16.py - KindredQ's damage is KindredQMissile's]"""
    global _damage_names
    if _damage_names is None:
        try:
            _damage_names = json.load(open(os.path.join(RES, 'damage_names16.json')))
        except Exception:
            _damage_names = {}
    nm = _damage_names.get(spell_name, spell_name)
    return int(nm[1:], 16) if nm.startswith('#') else elf(nm)


def elf(name):
    """the 32-bit ELF hash of a lower-cased name: how packets name spells and buffs"""
    h = 0
    for c in name.lower().encode():
        h = (h << 4) + c
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


# [m: replay 4012367010, Aatrox's Deathbringer attack at 69.547 s] the cast struct an attack-spell's 906 carries: its
# fixed fields (modes) as the real server wrote them; cast_struct() writes this attack's own values over them
ATTACK_SPELL = {'+0x8': [], '+0x18': '00000000', '+0x1c': '00008000', '+0x20': '0000', '+0x24': '0000803f', '+0x28': '00000000',
                '+0x30': '20200000006000000000000008000000', '+0x40': '000000000000000000000000', '+0x4c': '00000000',
                '+0x50': {'text': ''}, '+0x60': '2e', '+0x64': '00000000', '+0x68': '000080bf', '+0x6c': '0c0c0c0c', '+0x70': '00',
                '+0x74': '00000000', '+0x78': '00000000', '+0x7c': '00000000', '+0x80': '00000000', '+0x84': '00',
                '+0x88': '00000000', '+0x8c': '00000000', '+0x90': '000000000000000000000000', '+0x9c': '00', '+0xa0': '00000000',
                '+0xa4': 'ff', '+0xa8': '00000000', '+0xac': '000000000000000000000000', '+0xb8': '01', '+0xbc': '00000000',
                '+0xc0': '00000000', '+0xc4': 'f1f1f1f1', '+0xc8': '0000',
                '+0xd0': {'+0x8': '00000000', '+0xc': '0000', '+0x10': {'text': ''}, '+0x20': '00000000', '+0x24': '00000000',
                          '+0x28': {'text': ''}, '+0x38': '00000000', '+0x3c': '00000000', '+0x40': '0000', '+0x42': '0000',
                          '+0x44': '00000000'},
                '+0x118': '0000', '+0x11c': '00000000', '+0x120': 'ffff', '+0x124': '000000000000000000000000', '+0x130': '00000000'}


FX_FORMATS = {294}                 # ids written with the replays' reading format (data/exe1620/codec_fx)


class Packets:
    def __init__(self):
        self.forms = json.load(open(os.path.join(RES, 'forms16.json')))
        self.recipes = json.load(open(os.path.join(RES, 'recipes16.json')))
        self.sc = {}
        self.move_counter = 0
        self.repl_counter = 3_000_000
        self.height = None                 # fn (x, z) -> ground height, set by the game (the navigation grid)
        self.owner = {}                    # a missile's net id -> the unit it belongs to (for the fog of war)
        self.buff_hooks = []               # told of every buff given / taken away / counted (effects, renewals)

    # ------------------------------------------------------------------ plumbing
    def schema(self, pid):
        if pid not in self.sc:
            if pid in FX_FORMATS:
                # [10-13] learnt on the replays only (codec_fx: the server's own learning left the element format out)
                out, PS.OUT = PS.OUT, os.path.join(os.path.dirname(PS.OUT), 'codec_fx')
                try:
                    self.sc[pid] = PS.Schema.load(pid, borrow=False)
                finally:
                    PS.OUT = out
            else:
                self.sc[pid] = PS.Schema.load(pid)
        return self.sc[pid]

    def enc(self, pid, values):
        return self.schema(pid).encode(values)

    def form(self, name):
        f = self.forms[name]
        return f['pid'], copy.deepcopy(f['values'])

    def y(self, p):
        return self.height(p[0], p[1]) if self.height else 50.0

    def at3(self, p):
        return vec3(p[0], self.y(p), p[1])

    # ------------------------------------------------------------------ the frame's two streams
    def move_entry(self, net, points, speed, flags=0):
        return lol_packets.waypoint_entry(net, [cell(p) for p in points], speed, flags=flags)

    def moves(self, t, entries):
        """movement entries -> packets 61 [m: +0x10 units, +0x18 the entries, +0x28 a counter that only grows]"""
        out = []
        for i in range(0, len(entries), 16):
            group = entries[i:i + 16]
            self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
            out.append((2, MOVE, 0, self.enc(MOVE, {'+0x10': struct.pack('<H', len(group)).hex(),
                                                    '+0x18': {'text': b''.join(group).hex()},
                                                    '+0x28': u32(self.move_counter)})))
        return out

    def replication(self, t, units):
        """[(net, {name: value}, class)] -> packets 287"""
        out = []
        for i in range(0, len(units), 10):
            self.repl_counter += 1
            out.append((2, REPL, 0, repl16.packet(units[i:i + 10], game_time=t, counter=self.repl_counter)))
        return out

    # ------------------------------------------------------------------ units appear and vanish
    def minion_spawn(self, t, net, barracks_net, kind, wave, hp, max_hp, speed, way_out, level=1):
        """a new lane minion [m]: the container 239 holding its level (969 {0, level}, only above 1) and its spawn 439
        (barracks, kind, own id, wave, time), then 684: health and the way out of its barracks, which the client walks
        by itself"""
        m = self.forms['minion']
        f = dict(m['spawn'].get(str(kind)) or m['spawn']['4'])
        f.update({'+0x14': u32(barracks_net), '+0x18': f'{kind:02x}', '+0x1c': u32(net), '+0x20': f'{wave & 0xff:02x}', '+0x24': f32(t)})
        body = self.enc(439, f)
        en = m['enter'].get(f'{barracks_net:x}') or next(iter(m['enter'].values()))
        self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
        blob = bytes.fromhex(en['prefix']) + bytes([en['mark']]) + struct.pack('<I', self.move_counter) + \
            self.move_entry(net, way_out, speed, en.get('flags', 0))
        inner = ([(969, net, self.minion_level(level))] if level > 1 else []) + [(439, net, body)]
        return [(1, forms16.CONTAINER, net, self.enc(forms16.CONTAINER, forms16.pack(inner))),
                (1, 684, net, self.enc(684, {'+0x10': {'text': struct.pack('<fff', hp, 0.0, max_hp).hex()}, '+0x20': {'text': blob.hex()}}))]

    def enter(self, t, net, hp, max_hp, pos, facing=(1.0, 0.0), path=None, speed=0.0, inner=(), prefix=None):
        """a unit comes into the player's sight [m]: the container 239 (packets that describe it: its level, its
        spells ...; often empty) and 684: health, 0, full health, then where it is - standing (mark 3: a counter, its
        place, its facing) or walking (mark 2: a counter and its movement entry)"""
        m = self.forms['minion']
        en = next(iter(m['enter'].values()))
        self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
        blob = bytes.fromhex(en['prefix']) if prefix is None else prefix
        if path:
            blob += bytes([2]) + struct.pack('<I', self.move_counter) + self.move_entry(net, [pos] + list(path), speed)
        else:
            blob += bytes([3]) + struct.pack('<IB', self.move_counter, 0) + struct.pack('<ffff', pos[0], pos[1], facing[0], facing[1])
        return [(1, forms16.CONTAINER, net, self.enc(forms16.CONTAINER, forms16.pack(list(inner)))),
                (1, 684, net, self.enc(684, {'+0x10': {'text': struct.pack('<fff', hp, 0.0, max_hp).hex()}, '+0x20': {'text': blob.hex()}}))]

    def leave(self, net):
        """658 [m]: the unit is out of the player's sight (an empty packet)"""
        return [(1, 658, net, b'')]

    def inner_body(self, packet):
        """the body of the main packet inside a container we wrote"""
        ch, pid, net, body = packet
        v = PS.parse(self.schema(pid), body)
        return forms16.unpack(v)[-1][2]               # the last one (a minion: its 439 after its level)

    def delete(self, net):
        pid, v = self.form('delete')
        v['+0x10'] = u32(net)
        return [(1, pid, net, self.enc(pid, v))]

    # ------------------------------------------------------------------ basic attacks
    def attack(self, u, tgt, attack_id, counter, slot=0x40, spell=None):
        """the attack begins. A minion: 390; a champion, turret or monster: 906 + 972 [m: the struct holds a
        counter, the attack's spell slot (0x40 + variant), the target's place, the attack's own net id (its missile's
        when it has one, the same for all attacks of the unit), the target; then the attacker's place]"""
        there = tgt.pos
        if u.kind in ('minion', 'monster', 'summon'):         # [replays] a pet attacks with the minions' 390
            pid, v = self.form('attack_minion')
            v['+0x10'].update({'+0x8': u32(1), '+0xd': f'{slot:02x}', '+0x10': self.at3(there), '+0x1c': u32(attack_id), '+0x20': u32(tgt.net),
                               '+0x28': []})
            v['+0x50'] = bytes(16).hex() + struct.pack('<ff', u.pos[0], u.pos[1]).hex()
            out = [(1, pid, u.net, self.enc(pid, v))]
            if u.kind == 'monster':
                out += self.attack_aim(u, tgt)          # [m: every monster attack has its 972] (units.start_attack)
            return out
        pid, v = self.form('attack_hero')
        cast = []
        if spell is not None:
            # [m: Aatrox's Deathbringer attack, slot 0x2e] an attack that is a spell carries its cast struct (name, slot,
            # windup and total time, the attack's id, the target); a plain attack an empty list
            st = copy.deepcopy(ATTACK_SPELL)
            d = math.hypot(there[0] - u.pos[0], there[1] - u.pos[1]) or 1.0
            self.cast_struct(st, spell['t'], u.net, spell['name'], slot, counter, attack_id, attack_id, there, there, u.pos,
                             ((there[0] - u.pos[0]) / d, (there[1] - u.pos[1]) / d), spell['cast_time'], spell['total_time'],
                             0.0, 0.0, tgt.net, spell.get('package', 0), spell.get('champion', ''))
            cast = [st]
        v['+0x10'].update({'+0x8': u32(counter), '+0xd': f'{slot:02x}', '+0x10': self.at3(there), '+0x1c': u32(attack_id),
                           '+0x20': u32(tgt.net), '+0x28': cast})
        v['+0x48'] = struct.pack('<ff', u.pos[0], u.pos[1]).hex()
        return [(1, pid, u.net, self.enc(pid, v))] + self.attack_aim(u, tgt)

    def attack_aim(self, u, tgt):
        """972 {the target, its place, 2}: with a champion's / turret's 906, with every attack of a monster"""
        pid2, v2 = self.form('attack_aim')
        v2.update({'+0x10': u32(tgt.net), '+0x14': self.at3(tgt.pos), '+0x20': '02'})
        return [(1, pid2, u.net, self.enc(pid2, v2))]

    def missile_launch(self, u, missile):
        """the windup is over and the attack has a missile [m]: 938 about the attacker, 743 about the missile"""
        self.owner[missile] = u.net
        return [(1, 938, u.net, self.enc(938, {'+0x10': u32(missile)})),
                (1, 743, missile, self.enc(743, {'+0x10': u32(missile), '+0x14': '00'}))]

    def missile_end(self, missile):
        return [(1, 118, missile, self.enc(118, {'+0x10': '01'}))]

    def attack_stop(self, u):
        pid, v = self.form('attack_stop')
        v['+0x1c'] = u32(getattr(u, 'attacks', 1) or 1)      # [m] the unit's own attack counter
        return [(1, pid, u.net, self.enc(pid, v))]

    def target(self, u, tgt_net):
        return [(1, 447, u.net, self.enc(447, {'+0x10': u32(tgt_net)}))]

    def face(self, u, direction):
        pid, v = self.form('face')
        d = math.hypot(*direction) or 1.0
        v['+0x14'] = vec3(direction[0] / d, 0.0, direction[1] / d)
        return [(1, pid, u.net, self.enc(pid, v))]

    # ------------------------------------------------------------------ damage, death, rewards
    def damage(self, tgt, src_net, amount, dtype=PHYSICAL, basic=True, source=SRC_ATTACK, crit=False, spell_hash=0):
        """the floating number over a unit (150) [m]"""
        pid, v = self.form('damage')
        v.update({'+0x10': f32(amount), '+0x14': u32(tgt.net), '+0x18': f'{dtype:02x}', '+0x19': '01' if basic else '00',
                  '+0x1a': f'{source:02x}', '+0x1c': u32(src_net), '+0x20': '03' if crit else '05', '+0x24': '00000000',
                  '+0x28': '00000000', '+0x2c': u32(spell_hash)})
        return [(1, pid, tgt.net, self.enc(pid, v))]

    def death(self, u, killer_net):
        """a unit dies (1112) [m: +0x10+0x20 its place, +0x50 the killer]"""
        pid, v = self.form('death')
        v['+0x10']['+0x20'] = self.at3(u.pos)
        v['+0x50'] = u32(killer_net)
        return [(1, pid, u.net, self.enc(pid, v))]

    def gold(self, hero_net, amount, from_net):
        """818 a gold gain with its source (to its own player) - with a 121 in the same frame (gold_mark) [m: replay
        4012247271, 579 of 621 champion gold frames have it; the other 121s come every ~5 s, cause not known]"""
        pid, v = self.form('gold')
        v.update({'+0x14': f32(amount), '+0x18': u32(hero_net), '+0x1c': u32(from_net)})
        return [(1, pid, hero_net, self.enc(pid, v))]

    def gold_mark(self, hero_net):
        """121 {0, the champion}: with a champion's gold gain, told to everyone [m: live, all ten champions]"""
        return [(1, 121, 0, self.enc(121, {'+0x10': f32(0.0), '+0x14': u32(hero_net)}))]

    def xp(self, hero_net, amount):
        pid, v = self.form('xp')
        v.update({'+0x10': u32(hero_net), '+0x14': f32(amount)})
        return [(1, pid, 0, self.enc(pid, v))]

    def leash_state(self, net, state):
        """586 S2C_NeutralCampLeashStateChanged {state} [m: replays - 1 at the camp's spawn, 5 when it is drawn into a
        fight (twice in that frame), on a reset 8, 2, 9, 3 and 1 again]"""
        return [(1, 586, net, self.enc(586, {'+0x10': u32(state)}))]

    def merge_effects(self, out):
        """[m: replay 4012290107 - 1,702 effect packets (10), never two in one frame: 944 one group of one instance,
        284 two groups, 92 one group of two instances ...] the frame's effects go out as ONE 10 at the first one's place:
        its groups in order, the instances of a group equal in all else put together"""
        idx = [i for i, p in enumerate(out) if p[1] == 10]
        if len(idx) < 2:
            return out
        sc = self.schema(10)
        groups, keys = [], {}
        for i in idx:
            try:
                v = PS.parse(sc, out[i][3])
            except Exception:
                return out                               # a body we cannot read: left as it is
            for grp in v.get('+0x10') or []:
                key = json.dumps({k: x for k, x in grp.items() if k != '+0x10'}, sort_keys=True)
                if key in keys:
                    keys[key]['+0x10'] = (keys[key].get('+0x10') or []) + (grp.get('+0x10') or [])
                else:
                    g2 = dict(grp)
                    keys[key] = g2
                    groups.append(g2)
        try:
            body = self.enc(10, {'+0x10': groups})
        except Exception:
            return out
        first = out[idx[0]]
        drop = set(idx[1:])
        merged = [p for i, p in enumerate(out) if i not in drop]
        merged[idx[0]] = (first[0], 10, 0, body)
        return merged

    def stat_outputs(self, net, on=True):
        """294 S2C_StatFormulaOutputs [m: every lane minion, monster and 626 unit of the replays, 11,294 of 11,294 about
        the packet's own unit]: one entry, index 3, values [1, 0, 1, 0] ([0, 0, 0, 0] the moment a 626 unit is made)"""
        one = f32(1.0 if on else 0.0)
        return (1, 294, net, self.enc(294, {'+0x10': [{'+0x8': [one, f32(0.0), one, f32(0.0)], '+0x18': '03'}],
                                            '+0x20': u32(net)}))

    def minion_level(self, level):
        return self.enc(969, {'+0x10': '00', '+0x11': f'{level:02x}'})

    def level_up(self, hero_net, level):
        return [(1, 969, hero_net, self.enc(969, {'+0x10': '01', '+0x11': f'{level:02x}'}))]

    def skill_level(self, hero_net, slot, level, points_left):
        """810 [m: +0x10 1, +0x11 the new level, +0x12 the slot, +0x13 points left]"""
        return [(1, 810, hero_net, self.enc(810, {'+0x10': '01', '+0x11': f'{level:02x}', '+0x12': f'{slot:02x}',
                                                  '+0x13': f'{points_left:02x}'}))]

    # ------------------------------------------------------------------ recipes (several packets of one real event)
    def recipe(self, name, roles, change=None, skip=()):
        """[(delay, ch, pid, net, body)] of a recorded event with our units in its roles (events16.py)"""
        import events16
        nets = {r: u32(n) for r, n in roles.items()}
        out = []
        for s in self.recipes[name]:
            if s['pid'] in skip:
                continue
            about = s['about']
            net = roles.get(about, 0) if isinstance(about, str) and len(about) <= 2 else (int(about, 16) if about else 0)
            if s['values'] is None:
                body = bytes.fromhex(s['raw'])
            else:
                v = events16._from_roles(copy.deepcopy(s['values']), nets)
                c = (change or {}).get(s['pid'])
                if callable(c):
                    v = c(v) or v
                elif c:
                    v.update(c)
                body = self.enc(s['pid'], v)
            out.append((s['dt'], s['ch'], s['pid'], net, body))
        return out

    # ------------------------------------------------------------------ spells
    def cast_struct(self, c, t, caster, name, slot, counter, cast_id, missile_id, aim, end, launch, direction,
                    cast_time, total_time, cooldown, mana, target=0, package=0, champion=''):
        """the cast info a 1215 and a 223 carry [m: spell hash (ELF of the name), start time, aimed place, cast and
        total time, slot, caster (twice), cooldown, the cast's net id, direction, package hash, end place, missile
        net id; an inner struct with the slot, the hash, the champion's name and the time the cast time ends; mana
        cost; the launch place]"""
        h = u32(name if isinstance(name, int) else elf(name))     # a name, or its hash (a template's spell)
        me = u32(caster)
        d = math.hypot(direction[0], direction[1]) or 1.0
        c['+0x8'] = [{'+0x8': u32(target), '+0xc': '00'}] if target else []
        c.update({'+0x18': h, '+0x28': f32(t), '+0x40': self.at3(aim), '+0x4c': f32(cast_time), '+0x60': f'{slot:02x}',
                  '+0x78': me, '+0x7c': u32(counter), '+0x80': f32(cooldown), '+0x88': me, '+0x8c': u32(cast_id),
                  '+0x90': vec3(direction[0] / d, 0.0, direction[1] / d), '+0xa0': u32(package), '+0xa8': f32(total_time),
                  '+0xac': self.at3(end), '+0xb8': '00', '+0xbc': u32(missile_id), '+0x118': '0100', '+0x11c': f32(mana),
                  '+0x124': self.at3(launch)})
        c['+0xd0'].update({'+0xc': struct.pack('<H', slot).hex(), '+0x20': h, '+0x28': text(champion),
                           '+0x38': u32(0x300 + counter), '+0x3c': f32(t + cast_time)})
        return c

    def cast(self, t, caster, name, slot, counter, cast_id, missile_id, aim, end, launch, direction, cast_time, total_time,
             cooldown, mana, target=0, package=0, champion='', flag=None):
        pid, v = self.form('cast')
        self.cast_struct(v['+0x18'], t, caster, name, slot, counter, cast_id, missile_id, aim, end, launch, direction,
                         cast_time, total_time, cooldown, mana, target, package, champion)
        if flag is not None:
            v['+0x18']['+0xb8'] = f'{flag:02x}'          # [m] a byte that differs by spell (recall: 4); not understood
        self.event_counter = getattr(self, 'event_counter', 0x3000) + 1
        v['+0x150'] = u32(self.event_counter)
        return [(1, pid, caster, self.enc(pid, v))]

    def cooldown(self, hero_net, slot, seconds):
        """635 [m: +0x10 the cooldown left, +0x24 the slot in the client's in-memory form (Q ae, E a6: 0xae - 4 x slot)]"""
        pid, v = self.form('cooldown')
        v.update({'+0x10': f32(seconds), '+0x14': '00', '+0x18': '00000000', '+0x1c': '00000000', '+0x20': '00000000',
                  '+0x24': f'{(0xae - 4 * slot) & 0xff:02x}'})
        return [(1, pid, hero_net, self.enc(pid, v))]

    def animation(self, net, name, speed=1.0):
        pid, v = self.form('animation')
        v.update({'+0x10': text(name), '+0x20': f32(speed)})
        return [(1, pid, net, self.enc(pid, v))]

    def spell_missile(self, t, missile_id, caster, name, slot, counter, cast_id, start, end, speed, package=0, champion='', target=0,
                      base=None, owner_place=None):
        """223 [m]: a missile that is a spell of its own: where it starts (100 above the ground), its owner's place,
        where it goes, its speed, velocity and direction, and the missile spell's cast struct.
        base: the real server's own 223 of this missile spell (a template's, its fixed fields: first speed +0x98,
        acceleration +0xf0, least / greatest speed +0x40 / +0x234, the cast struct's times and flags) - only this
        cast's places, units, ids and times are written into it"""
        self.owner[missile_id] = caster
        dx, dz = end[0] - start[0], end[1] - start[1]
        d = math.hypot(dx, dz) or 1.0
        ux, uz = dx / d, dz / d
        y0, y1 = self.y(start) + 100.0, self.y(end) + 100.0
        if base is None:
            pid, v = self.form('spell_missile')
            v.update({'+0x98': f32(speed)})
            self.cast_struct(v['+0xf8'], t, caster, name, slot, counter, cast_id, missile_id, end, end, start, (ux, uz), 0.0, 1.0, 0.0, 0.0,
                             target, package, champion)
        else:
            pid, v = 223, base
            c = v['+0xf8']
            me = u32(caster)
            c['+0x8'] = [{'+0x8': u32(target), '+0xc': '00'}] if target else []
            c.update({'+0x28': f32(t), '+0x40': self.at3(end), '+0x78': me, '+0x7c': u32(counter), '+0x88': me, '+0x8c': u32(cast_id),
                      '+0x90': vec3(ux, 0.0, uz), '+0xa0': u32(package), '+0xac': self.at3(end), '+0xbc': u32(missile_id)})
            if isinstance(c.get('+0xd0'), dict):
                c['+0xd0'].update({'+0x38': u32(0x300 + counter), '+0x3c': f32(t)})
        v.update({'+0x14': vec3(start[0], y0, start[1]), '+0x48': self.at3(owner_place or start), '+0x54': vec3(end[0], y1, end[1]),
                  '+0x244': vec3(ux * speed, 0.0, uz * speed), '+0x250': vec3(start[0], y0, start[1]), '+0x268': vec3(ux, 0.0, uz)})
        v['+0xf8']['+0x124'] = vec3(start[0], y0, start[1])
        return [(1, pid, missile_id, self.enc(pid, v))]

    def missile_hit(self, missile_id, target_net, place):
        """433 [m]: a missile has hit a unit there"""
        return [(1, 433, missile_id, self.enc(433, {'+0x10': {'+0x8': [{'+0x8': u32(target_net), '+0xc': self.at3(place)}]}}))]

    def spell_in_slot(self, net, slot, name):
        """78 [m]: the spell a slot holds now (+0x10+0xf the slot, the name with its zero)"""
        pid, v = self.form('spell_slot')
        v['+0x10']['+0xf'] = f'{slot:02x}'
        v['+0x20'] = text(name.encode() + b'\0')
        return [(1, pid, net, self.enc(pid, v))]

    def heal_event(self, src_net, tgt_net, amount, cause=0, name=0x6a4229fc, flag=0, mid=b'', tail=b''):
        """699 e14f047c [m: replays, every heal - the jungle pet's ticks, Smite's, life steal / omnivamp]: a 52-byte
        event: 0x1d9, the healer, the cause (the damage name the heal came with, the pet's attack), flag (0 a heal,
        6 one from damage dealt) in the low byte of the heal's name, healer, healed, the amount, 12 bytes of the
        heal kind's own (mid), the heal's name, 8 more (tail)"""
        b = struct.pack('<IIII', 0x1d9, src_net, cause, (name & 0xffffff00) | flag) + struct.pack('<IIf', src_net, tgt_net, amount)
        b += (mid + bytes(12))[:12] + struct.pack('<I', name) + (tail + bytes(8))[:8]
        return [(1, 699, src_net, self.enc(699, {'+0x10': 'e14f047c', '+0x18': {'text': b.hex()}, '+0x28': '4b00'}))]

    def buff_add(self, tgt_net, caster_net, slot, btype, name_hash, duration, package=0, count=1):
        """435 [m: +0x1c caster, +0x38 buff type (LoL's BuffType: 5 stun, 7 silence, 11 slow, 12 snare, 30 knock-up, 31 knockback [replays] ...),
        +0x3c duration, +0x40 count, +0x5c package hash, +0x60 the unit's buff slot, +0x64 name hash]"""
        pid, v = self.form('buff_add')
        v.update({'+0x10': '00000000', '+0x14': '00000000', '+0x18': '00000000', '+0x1c': u32(caster_net), '+0x38': f'{btype:02x}',
                  '+0x39': '03', '+0x3c': f32(duration), '+0x40': f'{count:02x}', '+0x5c': u32(package), '+0x60': f'{slot:02x}',
                  '+0x64': u32(name_hash), '+0x68': '01'})
        self.buff_added(tgt_net, caster_net, slot, name_hash, count)
        return [(1, pid, tgt_net, self.enc(pid, v))]

    def buff_added(self, tgt_net, caster_net, slot, name_hash, count=1):
        for h in self.buff_hooks:
            h.on_buff_add(tgt_net, caster_net, slot, name_hash)
            if hasattr(h, 'on_buff_counter'):
                h.on_buff_counter(tgt_net, slot, count)

    def buff_count(self, tgt_net, slot, caster_net, duration, count):
        """282 NPC_BuffUpdateCount [m: replays - +0x10 the duration set, +0x14 0, +0x18 the slot, +0x1c the caster,
        +0x20 the count]: a buff renewed"""
        return [(1, 282, tgt_net, self.enc(282, {'+0x10': f32(duration), '+0x14': f32(0.0), '+0x18': f'{slot:02x}',
                                                 '+0x1c': u32(caster_net), '+0x20': f'{count & 0xff:02x}'}))]

    def buff_counter(self, tgt_net, slot, name_hash, count):
        """430 NPC_BuffUpdateNumCounter [m: replays - +0x10 the counter (u32), +0x14 1, +0x18 the buff's name hash,
        +0x1c its slot]: a number a buff shows on its icon"""
        for h in self.buff_hooks:
            if hasattr(h, 'on_buff_counter'):
                h.on_buff_counter(tgt_net, slot, count)
        return [(1, 430, tgt_net, self.enc(430, {'+0x10': u32(count), '+0x14': '01', '+0x18': u32(name_hash), '+0x1c': f'{slot:02x}'}))]

    def buff_remove(self, tgt_net, slot, name_hash):
        for h in self.buff_hooks:
            h.on_buff_remove(tgt_net, slot)
        return [(1, 262, tgt_net, self.enc(262, {'+0x10': f'{slot:02x}', '+0x14': u32(name_hash), '+0x18': '00000000'}))]

    def dash(self, t, u, points, dash_speed, gravity=0.0):
        """1140 [m]: a movement with its own speed (a dash, a jump). An entry: [2 x points][03][net id][the unit's
        speed][the path's speed][the jump's gravity][8 zero bytes][start x, z][24 zero bytes][01][7 zero bytes], then
        the path as in a movement entry (one bit per coordinate after the first point: 0 = an i16 of its own)"""
        cells = [cell(p) for p in points]
        n = len(cells)
        e = bytes([2 * n, 0x03]) + struct.pack('<Ifff', u.net, u.speed, dash_speed, gravity) + bytes(8) + \
            struct.pack('<ff', points[0][0], points[0][1]) + bytes(24) + b'\x01' + bytes(7)
        e += bytes((2 * (n - 1) + 7) // 8 if n > 1 else 0)
        for x, z in cells:
            e += struct.pack('<hh', x, z)
        # [m: 2012 live dashes] +0x28 is the movement packets' own counter (61's +0x28), one more than the last 61's:
        # a smaller one is an old movement to the client, which then leaves the unit where it stood
        self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
        return [(1, 1140, 0, self.enc(1140, {'+0x10': struct.pack('<H', 1).hex(), '+0x18': {'text': e.hex()}, '+0x28': u32(self.move_counter)}))]

    def restamp_dash(self, body, t):
        """a 1140 as it leaves, after the frame's 61s: its counter is the next of the movement packets' [m: 2012 live
        dashes, each one more than the last 61's] - with a smaller one the client takes it for an old movement"""
        v = PS.parse(self.schema(1140), body)
        self.move_counter = max(self.move_counter + 1, 2000 + int(t * MOVE_COUNTER_RATE))
        v['+0x28'] = u32(self.move_counter)
        return self.enc(1140, v)

    def death_recap(self, player, player_name, killer, sources, own):
        """1166 [m: the six of the live recording], to the player that died: who damaged it and with what
        (sources: [(net id, name, entries)]), and what it did itself (own: entries).
        An entry = (basic attack?, true, magic, physical damage, the spell's name hash, slot)"""
        def entries(lst):
            return [{'+0x8': '01' if basic else '00', '+0xc': f32(true), '+0x10': f32(magic), '+0x14': f32(phys),
                     '+0x18': u32(h), '+0x1c': '00' if basic else '01', '+0x20': u32(slot)}
                    for basic, true, magic, phys, h, slot in lst]
        v = {'+0x10': [{'+0x8': entries(e), '+0x18': u32(net), '+0x20': text(name)} for net, name, e in sources],
             '+0x20': u32(killer), '+0x24': f32(0.0), '+0x28': f32(0.0),
             '+0x30': {'+0x8': entries(own), '+0x18': u32(player), '+0x20': text(player_name)},
             '+0x60': f32(0.0), '+0x64': f32(0.0)}
        return [(1, 1166, 0, self.enc(1166, v))]

    # ------------------------------------------------------------------ the map's own things
    def map_effect(self, name, a, b):
        """984 [m]: a named group of the map's particles (the map bin's MapParticle group names) switched:
        (1, 1) hides it, (1, 0) shows it, (2, 0) follows a (1, 1) when an inhibitor returns"""
        return [(1, 984, 0, self.enc(984, {'+0x10': text(name), '+0x20': u32(a), '+0x24': u32(b)}))]

    def placeable(self, net, key, matrix):
        """502 [m] + 1170: an effect the map places (a VfxEntityTemplate: its key, its transform) is created"""
        v = {'+0x10': {'+0x8': '01', '+0x18': (bytes(56) + struct.pack('<16f', *matrix)).hex(),
                       '+0x20': u32(key) + u32(1), '+0x28': {'default': True}}}
        return [(1, 502, net, self.enc(502, v)),
                (1, 1170, net, self.enc(1170, {'+0x10': {'+0x8': '01', '+0xc': u32(0), '+0x10': u32(0)}}))]

    def placeable_gone(self, net):
        return [(1, 543, net, b'')]

    def inhibitor_state(self, net, up, seconds):
        """693 [m]: 0 = down, 1 = up; the u16 is 0 the first time it falls and the respawn time (300) from its
        first return on"""
        return [(1, 693, net, self.enc(693, {'+0x10': '01' if up else '00', '+0x12': struct.pack('<H', seconds).hex(), '+0x14': '00'}))]

    def building_died(self, net, killer):
        """716 [m]: an inhibitor's (killer, killer) or the nexus' (0, killer) end"""
        return [(1, 716, net, self.enc(716, {'+0x10': u32(killer), '+0x14': u32(killer)}))]

    def anim_states(self, net, pairs):
        """904 [m]: the unit's animation overrides: [(from hash, to hash)]"""
        return [(1, 904, net, self.enc(904, {'+0x10': [{'+0x8': u32(a), '+0xc': u32(b), '+0x10': '01'} for a, b in pairs]}))]
