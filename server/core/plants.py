"""The jungle plants: Scryer's Bloom (PlantVision), Blast Cone (PlantSatchel), Honeyfruit (PlantHealth /
PlantHealthMirrored), as Riot's server runs them [m: the 16.20 replays; tools/plant_forms16.py -> plants16.json].

Their life [m: every plant of replay 4012247271, 99 of them, the same steps to a frame or two]:
  spawn    a 626 unit (team 0, 1 health), with 272 / 802 (no minimap icon), 684 and 294 - a seed, not attackable
  grow     60 s later 1088 'Grow_idle' with 904 (and 1005 for Scryer's Bloom, the idle buff 435 for Blast Cone):
           now a champion's basic attack can set it off
  trigger  the attack's hit: the attacker's 331 'Attack<plant>', a region (41) bound to the plant (2 s, the
           attacker's team), the trigger buff 435, 904 x2, 314 'Trigger' (Blast Cone: its idle buff goes, 262)
  death    30 s after the trigger: 262, 904 x2, 314 'Death'
  die      150 s after that: 150 (its own 'damage') + 1112; 4 s after that it is deleted (1090)
Where and when plants grow is Riot's random choice among the spots of LEVELS/map11/Scripts/Plants.lua (13.3): the
golden test takes them from the replay; a match of ours places them from those spots [not done yet].

Scryer's Bloom's seeds [m: 6 triggers of replay 4012247271, 193 regions each; map bin PlantHawkshot: speed 1600,
luaOnMissileUpdateDistanceInterval 100]: four missiles of the ATTACKER (its slot 0x34: PlantHawkshot +12 deg,
PlantHawkshot, PlantHawkshotAudio, PlantHawkshot -12 deg from the attacker -> plant line), 3200 away, 1600 / s, ended
(118) 2.0 s after. Every 100 units of the three seeds' flight the script puts a region at that point (whole units),
radius 320 + 0.1 x the distance, 1.5 s, the attacker's team: on the first frame the seed has flown that far; the same
region is put again 4 frames later. 31 per seed.
Blast Cone's knock-back [m: 49 triggers of 4 replays]: every champion near the plant (knocked up to 303 from it, never
from 363 on) gets the knock-back buff (435 type 31, 1.5 s, its own caster) at once and, the next frame, a jump (1140,
gravity 50) away from the plant to about 855 from it (846 - 868 mostly; the ground's nearest free cell) lasting about
0.75 s (0.72 - 0.79).
Not done: Honeyfruit's fruits (where they land is random), the seeds' hits (433).
"""
import copy
import json
import math
import os
import struct

from . import gamedata as G
from . import packets as P
from .units import Unit, NEUTRAL

FORMS = os.path.join(G.ROOT, 'data', 'exe1620', 'plants16.json')
GROW, WILT, CORPSE, GONE = 60.0, 30.0, 150.0, 4.0
SEED_SPEED, SEED_RANGE, SEED_ANGLE = 1600.0, 3200.0, math.radians(12.0)
SEED_STEP, SEED_RADIUS, SEED_GROWTH = 100.0, 320.0, 0.1
TWIN_FRAMES = 4
KNOCK_RADIUS = 330.0              # [a: between the measured 303 (knocked) and 363 (not)]
KNOCK_TO, KNOCK_TIME, KNOCK_GRAVITY, KNOCK_BUFF = 855.0, 0.75, 50.0, 1.5
SKIP = (723, 1195)                # the spectator's own sight packets
_forms = None


def forms():
    global _forms
    if _forms is None:
        try:
            _forms = json.load(open(FORMS))
        except Exception:
            _forms = {}
    return _forms


def _text(v):
    try:
        return bytes.fromhex(v['text']).rstrip(b'\0').decode(errors='replace')
    except Exception:
        return ''


class Plant(Unit):
    kind = 'plant'
    repl_cls = None
    can_move = False

    def __init__(self, game, net, name, character, pos):
        base = {'name': character, 'hp': 1.0, 'ad': 0.0, 'speed': 0.0, 'range': 0.0, 'radius': 35.0, 'sight': 0.0}
        try:
            from .summons import record
            r = record('SRU', character)
            base['radius'] = float(r.get('radius') or 35.0)
        except Exception:
            pass
        super().__init__(game, net, NEUTRAL, name, pos, base)
        self.label, self.character = name, character
        self.targetable = False           # a seed until it grows
        self.form_net = None              # the replay plant's net id the forms carry
        self.triggered = None


class Plants:
    def __init__(self, game):
        self.g = game
        self.units = []
        self.flying = []                  # [hero, dest, speed, until]: Blast Cone's jumps under way
        game.systems.append(self.tick)

    # ------------------------------------------------------------------ the forms
    def emit(self, u, step, skip=()):
        """the plant's own packets of that step, its net id / place / time written in"""
        f = forms().get(u.label, {}).get(step)
        if f is None:
            return
        for pid, v in f['own']:
            if pid in SKIP or pid in skip:
                continue
            self.g.q.append((1, pid, u.net, self.g.pk.enc(pid, self.mine(v, f['net'], u))))

    def mine(self, v, their_net, u):
        g = self.g
        s = json.dumps(v).replace(their_net, P.u32(u.net))
        return json.loads(s)

    # ------------------------------------------------------------------ life
    def spawn(self, name, pos):
        g, pk = self.g, self.g.pk
        f = forms().get(name, {}).get('spawn')
        if f is None:
            return None
        v626 = next((v for p, v in f['own'] if p == 626), {})
        character = _text(v626.get('+0x70')) or name
        u = Plant(g, g.new_net(), name, character, pos)
        g.add(u)
        self.units.append(u)
        y = pk.y(pos)
        for pid, v in f['own']:
            v = self.mine(v, f['net'], u)
            if pid == 626:
                v.update({'+0x1c': P.vec3(pos[0], y, pos[1]), '+0x4c': P.vec3(pos[0], y, pos[1] + 1.0), '+0x68': P.f32(g.t)})
                g.q.append((1, 626, u.net, pk.enc(626, v)))
            elif pid == 684:
                blob = bytes.fromhex(v['+0x20']['text'])
                g.q.append(pk.enter(g.t, u.net, 1.0, 1.0, pos, (0.0, 1.0), prefix=blob[:25])[1])
            elif pid not in SKIP:
                g.q.append((1, pid, u.net, pk.enc(pid, v)))
        if name != 'PlantHealthPack':
            g.at(g.t + GROW, lambda t, u=u: self.grow(u))
        return u

    def grow(self, u):
        if not u.alive:
            return
        self.emit(u, 'grow')
        u.targetable = True

    def hit(self, src, u):
        """a basic attack landed on the plant"""
        g = self.g
        if not u.targetable or u.triggered is not None:
            return
        u.triggered = g.t
        u.targetable = False
        g.release_attackers(u)
        f = forms().get(u.label, {}).get('trigger') or {}
        for role, pid, v in f.get('other', []):
            v = self.mine(v, f['net'], u)
            if role == 'attacker' and src is not None:
                g.q.append((1, pid, src.net, g.pk.enc(pid, v)))
            elif role == 'region':
                self.region(v, u.pos, src)
        self.emit(u, 'trigger', skip=(78, 938, 743, 223))
        if u.label == 'PlantVision' and src is not None:
            self.seeds(src, u, f)
        if u.label == 'PlantSatchel':
            self.blast(src, u, f)
        g.at(g.t + WILT, lambda t, u=u: self.wilt(u))

    def wilt(self, u):
        self.emit(u, 'death')
        self.g.at(self.g.t + CORPSE, lambda t, u=u: self.die(u))

    def die(self, u):
        g = self.g
        f = forms().get(u.label, {}).get('die')
        if f is not None:
            for pid, v in f['own']:
                v = self.mine(v, f['net'], u)
                if pid == 1112 and isinstance(v.get('+0x10'), dict):
                    v['+0x10']['+0x20'] = P.vec3(u.pos[0], g.pk.y(u.pos), u.pos[1])
                g.q.append((1, pid, u.net, g.pk.enc(pid, v)))
        u.alive = False
        g.at(g.t + GONE, lambda t, u=u: self.delete(u))

    def delete(self, u):
        self.emit(u, 'delete')
        self.g.units.pop(u.net, None)
        if u in self.units:
            self.units.remove(u)

    # ------------------------------------------------------------------ Blast Cone
    def blast(self, src, u, f):
        g, sp = self.g, self.g.spells
        form = next((v for role, pid, v in f.get('other', []) if role == 'knocked'), None)
        for h in g.heroes:
            d = math.hypot(h.pos[0] - u.pos[0], h.pos[1] - u.pos[1])
            if not h.alive or d > KNOCK_RADIUS:
                continue
            if d < 1.0:
                ref = src.pos if src is not None and src is not h else (u.pos[0] + 1.0, u.pos[1])
                dx, dz = u.pos[0] - ref[0], u.pos[1] - ref[1]
                d = math.hypot(dx, dz) or 1.0
            else:
                dx, dz = h.pos[0] - u.pos[0], h.pos[1] - u.pos[1]
            dest = (u.pos[0] + dx / d * KNOCK_TO, u.pos[1] + dz / d * KNOCK_TO)
            dest = g.nav.nearest_free(*dest) or dest
            if form is not None and sp is not None:
                if not hasattr(h, 'buff_list'):
                    h.buff_list = {}
                key = ('blastcone',)
                old = h.buff_list.get(key)
                slot = old['slot'] if old else sp.buff_slot(h)
                name_hash = int.from_bytes(bytes.fromhex(form['+0x64']), 'little')
                package = int.from_bytes(bytes.fromhex(form['+0x5c']), 'little')
                h.buff_list[key] = {'slot': slot, 'until': g.t + KNOCK_BUFF, 'hash': name_hash, 'undo': None, 'known': True,
                                    'args': (h.net, slot, 0x1f, name_hash, package)}
                g.q += g.pk.buff_add(h.net, h.net, slot, 0x1f, name_hash, KNOCK_BUFF, package=package)
                sp.buffs.append([g.t + KNOCK_BUFF, h, key])
            h.path, h.order, h.target = None, None, None
            h.cc_until = max(h.cc_until, g.t + KNOCK_TIME)
            h.dashing = True
            g.after_frames(1, lambda t, h=h, dest=dest: self.jump(h, dest))

    def jump(self, h, dest):
        g = self.g
        if not h.alive:
            return
        speed = max(1.0, math.hypot(dest[0] - h.pos[0], dest[1] - h.pos[1]) / KNOCK_TIME)
        g.q += g.pk.dash(g.t, h, [h.pos, dest], speed, KNOCK_GRAVITY)
        h.cc_until = max(h.cc_until, g.t + KNOCK_TIME)
        self.flying.append([h, dest, speed])

    def tick(self, t, dt):
        keep = []
        for f in self.flying:
            h, dest, speed = f
            left = math.hypot(dest[0] - h.pos[0], dest[1] - h.pos[1])
            if not h.alive or left <= speed * dt:
                if h.alive:
                    h.pos = dest
                h.dashing = False
                continue
            h.pos = (h.pos[0] + (dest[0] - h.pos[0]) / left * speed * dt, h.pos[1] + (dest[1] - h.pos[1]) / left * speed * dt)
            keep.append(f)
        self.flying = keep

    # ------------------------------------------------------------------ Scryer's Bloom
    def region(self, v, pos, src, radius=None):
        g = self.g
        r = v['+0x10']
        r['+0x44'] = P.u32(g.new_net())
        r['+0x25'] = '01' if src is None or src.team == 100 else '02'
        r['+0x14'] = struct.pack('<ff', pos[0], pos[1]).hex()
        if radius is not None:
            v['+0x58'] = P.f32(radius)
        g.q.append((1, 41, 0, g.pk.enc(41, v)))

    def seeds(self, src, u, f):
        g, pk = self.g, self.g.pk
        dx, dz = u.pos[0] - src.pos[0], u.pos[1] - src.pos[1]
        d = math.hypot(dx, dz) or 1.0
        base = math.atan2(dz / d, dx / d)
        ms = f.get('missiles', [])
        slots = [i for i, m in enumerate(ms) if m['pid'] == 78]
        angles = [SEED_ANGLE, 0.0, 0.0, -SEED_ANGLE]
        spells = getattr(g, 'spells', None)
        for n, i in enumerate(slots[:4]):
            name = _text(ms[i]['values'].get('+0x20'))
            m223 = next((m['values'] for m in ms[i + 1:i + 3] if m['pid'] == 223), None)
            a = base + angles[n]
            ux, uz = math.cos(a), math.sin(a)
            end = (u.pos[0] + ux * SEED_RANGE, u.pos[1] + uz * SEED_RANGE)
            mid, cast_id = g.new_net(), g.new_net()
            if spells is not None:
                spells.casts += 1
            counter = spells.casts if spells is not None else 1
            g.q += pk.spell_in_slot(src.net, 0x34, name)
            g.q += pk.missile_launch(src, mid)
            if m223 is not None:
                g.q += pk.spell_missile(g.t, mid, src.net, name, 0x34, counter, cast_id, u.pos, end, SEED_SPEED,
                                        base=copy.deepcopy(m223), owner_place=src.pos)
            g.at(g.t + SEED_RANGE / SEED_SPEED, lambda t, mid=mid: self.g.q.extend(self.g.pk.missile_end(mid)))
            if 'Audio' in name:
                continue
            for k in range(1, int(SEED_RANGE / SEED_STEP)):
                dist = SEED_STEP * k
                at = (round(u.pos[0] + ux * dist), round(u.pos[1] + uz * dist))
                g.at(g.t + dist / SEED_SPEED, lambda t, at=at, dist=dist: self.seed_region(src, at, SEED_RADIUS + SEED_GROWTH * dist, f))

    def seed_region(self, src, at, radius, f):
        regs = f.get('regions') or []
        if not regs:
            return
        self.region(copy.deepcopy(regs[0]['values']), at, src, radius)
        self.g.after_frames(TWIN_FRAMES, lambda t: self.region(copy.deepcopy(regs[0]['values']), at, src, radius))


def setup(game, session=None):
    game.plants = Plants(game)
