"""Spells of any champion on our 16.20 server, in the live server's packet forms, from the champion's own data.

Measured on data/live/4013831789 (Garen's casts):
  client 707 = [c1][cast struct: +0x8 spell name hash (ELF, spell_info.elf), +0xc target net id (the caster itself
  for a self cast), +0x10 target place, +0x18 slot 0..3, +0x1c caster place, +0x24 flags, +0x28 cursor place]
  (c2s16 EmbeddedWriter -> codec/c2s_707.10.json)
  server answers in the same tick: 1215 (the cast: spell hash, slot, game time, caster, a cast id and a missile id,
  the target place, direction, the champion's name), 635 (cooldown: +0x10 seconds, +0x24 the slot in the client's
  in-memory form: Q ae, E a6), 1088 (the animation "Spell<slot+1>"); when the spell ends a second 635 with the cooldown
What comes from the data (spell_engine.py on game16's bins): targeting, range, radius, width, cone, missile speed, cast
time, cooldown, the damage formula; what is ours: whom a cast hits and when (spell_engine.hits / hit_delay), one hit
per cast [approximations, as on 13.3].
"""
import copy
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
import bin_tree as BT       # noqa: E402
import spell_calc as SC     # noqa: E402
import spell_engine as SE   # noqa: E402
import spell_info as SI     # noqa: E402

CAST_REQUEST, CAST, COOLDOWN, ANIMATION = 707, 1215, 635, 1088
RES = os.path.join(HERE, '..', 'data', 'exe1620')
SLOT_FORM = {0: 'ae', 1: 'aa', 2: 'a6', 3: 'a2'}     # 635 +0x24 [measured Q ae, E a6; W / R by the same step, ours]


def _spec():
    s = json.load(open(os.path.join(RES, 'codec', 'c2s_707.10.json')))
    for f in s['fields']:
        f['modes'] = {int(m): d for m, d in f['modes'].items()}
    return s


def read_request(body):
    """client 707 after its id and net id -> dict or None"""
    import c2s16
    v = c2s16.decode(_spec(), body[1:])
    if v is None:
        return None
    xz = lambda b: struct.unpack('<ff', b)
    return {'hash': struct.unpack('<I', v[0x8])[0], 'target': struct.unpack('<I', v[0xc])[0], 'target_place': xz(v[0x10]),
            'slot': v[0x18][0], 'caster_place': xz(v[0x1c]), 'flags': v[0x24][0], 'cursor': xz(v[0x28])}


class Spells:
    def __init__(self, hero, champion, events):
        self.hero, self.champion, self.ev = hero, champion, events
        rec = BT.character_record(champion) or {}
        self.names = [n.split('/')[-1] for n in rec.get('spellNames', [])][:4]
        self.all = BT.champion_spells(champion)
        self.ready_at = [0.0] * 4
        self.casts = 0
        self.cast_tpl = events.values('spell_cast', CAST)
        self.cd_tpl = events.values('spell_cast', COOLDOWN)
        self.anim_tpl = events.values('spell_cast', ANIMATION)

    def cooldown(self, slot, rank):
        sd = self.all.get(self.names[slot], {}).get('mSpell', {})
        cd = sd.get('cooldownTime') or [10.0]
        return float(cd[min(rank, len(cd) - 1)])

    def on_request(self, body, t, world):
        """-> (packets, text) for one cast request of the player"""
        r = read_request(body)
        if r is None:
            return [], 'cast request not read'
        slot = r['slot']
        h = self.hero
        if not h.alive or not 0 <= slot <= 3 or slot >= len(self.names):
            return [], f'cast slot {slot} refused (dead or no spell)'
        rank = h.levels[slot]
        if rank <= 0:
            return [], f'cast slot {slot}: not learnt'
        if t < self.ready_at[slot]:
            return [], f'cast slot {slot}: on cooldown {self.ready_at[slot] - t:.1f} s'
        name = self.names[slot]
        sh = SE.shape(self.champion, name, rank)
        windup, total = SI.cast_times(self.champion, name)
        cd = self.cooldown(slot, rank)
        self.ready_at[slot] = t + cd
        self.casts += 1
        here = h.place(t)
        aim = r['cursor'] if r['cursor'] != (0.0, 0.0) else r['target_place']
        if sh['targeting'] in ('Self', 'SelfAoe'):
            aim = here
        cast_id, missile = world.new_net(), world.new_net()
        out = [(1, CAST, h.net, self.cast_packet(t, slot, name, here, aim, r['target'], cast_id, missile, windup, cd)),
               (1, COOLDOWN, h.net, self.cooldown_packet(0.0, slot)),
               (1, ANIMATION, h.net, self.animation_packet(slot, windup))]
        world.push(t + max(total, windup), lambda t2: world.out.append((1, COOLDOWN, h.net, self.cooldown_packet(cd, slot))))
        # who it hits, how much, when
        dmg = SE.damage(self.champion, name, rank, max(1, getattr(h, 'level', 1)), SC.Stats(ad=(h.damage, 0.0), ap=(0.0, 0.0)))
        hit = []
        if dmg and dmg[0] > 0:
            units = [(u.net, u.place(), 48.0) for u in list(world.units.values()) + world.champions()
                     if u.alive and u.team != h.team]
            for net, travel in SE.hits(sh, here, aim, units):
                u = world.unit(net)
                delay = SE.hit_delay(self.champion, sh, travel)
                world.push(t + delay, lambda t2, u=u, d=dmg[0]: world.hit(t2, _Src(h.net, d), u, share=1.0))
                hit.append(net)
        return out, f'cast {name} (slot {slot}, rank {rank}) {sh["targeting"]} aim ({aim[0]:.0f}, {aim[1]:.0f}), ' \
                    f'cooldown {cd:.1f} s, damage {dmg[0] if dmg else 0:.0f} on {len(hit)} unit(s)'

    def cast_packet(self, t, slot, name, here, aim, target, cast_id, missile, windup, cd):
        v = copy.deepcopy(self.cast_tpl)
        c = v['+0x18']
        hh = struct.pack('<I', SI.elf(name)).hex()
        me = struct.pack('<I', self.hero.net).hex()
        dx, dz = aim[0] - here[0], aim[1] - here[1]
        d = math.hypot(dx, dz) or 1.0
        place = struct.pack('<fff', aim[0], 50.0, aim[1]).hex()
        c['+0x8'] = [{'+0x8': struct.pack('<I', target).hex(), '+0xc': '00'}] if target and target != self.hero.net else []
        c['+0x18'] = hh
        c['+0x28'] = struct.pack('<f', t).hex()
        c['+0x4c'] = struct.pack('<f', windup).hex()
        c['+0x60'] = f'{slot:02x}'
        c['+0x78'] = me
        c['+0x7c'] = struct.pack('<I', self.casts).hex()
        c['+0x80'] = struct.pack('<f', cd).hex()
        c['+0x88'] = me
        c['+0x8c'] = struct.pack('<I', cast_id).hex()
        c['+0x90'] = struct.pack('<fff', dx / d, 0.0, dz / d).hex()
        c['+0xac'] = place
        c['+0xbc'] = struct.pack('<I', missile).hex()
        c['+0xd0']['+0x20'] = hh
        c['+0xd0']['+0x28'] = {'text': self.champion.encode().hex()}
        c['+0xd0']['+0x38'] = struct.pack('<I', 0x300 + self.casts).hex()
        c['+0xd0']['+0x3c'] = struct.pack('<f', t + windup).hex()
        c['+0x124'] = place
        v['+0x150'] = struct.pack('<I', 0x3000 + self.casts).hex()
        return self.ev.schema(CAST).encode(v)

    def cooldown_packet(self, seconds, slot):
        v = copy.deepcopy(self.cd_tpl)
        v['+0x10'] = struct.pack('<f', seconds).hex()
        v['+0x20'] = '00000000'
        v['+0x24'] = SLOT_FORM[slot]
        return self.ev.schema(COOLDOWN).encode(v)

    def animation_packet(self, slot, windup):
        v = copy.deepcopy(self.anim_tpl)
        v['+0x10'] = {'text': f'Spell{slot + 1}'.encode().hex()}
        return self.ev.schema(ANIMATION).encode(v)


class _Src:
    def __init__(self, net, damage):
        self.net, self.damage = net, damage
