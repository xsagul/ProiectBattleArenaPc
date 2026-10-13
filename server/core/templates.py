"""Spells as Riot's server sends them: every champion's spell templates (data/exe1620/spells16/<Champion>.json, made
by tools/spell_templates16.py from real 16.20 matches' replays) played back at each cast - the same packets, in the
recorded order, at their recorded times after the cast, with this match's units, places and times put in.

A template's events by role (whose packet it is):
  caster   the champion's own: buffs on itself (435 / 262 / 139), spells put in its slots (78: recast forms and
           sub-spells), animations (1088 / 280 / 904), sub-casts (1215 of extra slots), stealth flags (291), fades
           (947 / 596 / 29), alpha (236), character data (982 / 468 / 813), ammo (835), spell modifiers, events
           (699 ...), its replicated state (ActionState, shields, StatusFlags ...)
  missile  missile spells it launches (223, with the 78 that names them) - the cast's own missile is spells.py's
  spawn    a unit it creates (626 ...: summons.py) and that unit's own packets
  other    what it does to the units it hits: their buffs (435: the crowd control type and its duration), effects
Played: the 'core' events (seen in at least half of the casts), at their median time, in the recorded order.
Left to the simulation (it makes them itself): the cast (1215 of the spell's own slot), basic attacks and damage
(906 / 972 / 515 / 390 / 150), the flight of missiles (938 / 743 / 118 / 548 / 433), movement (61 / 1140), the
spectator's sight packets (723 / 1195), effect removal (584).
Fields: as recorded unless computed ({'$': 'net' | 'time' | 'place' | 'vary'}: tools/spell_templates16.py).
"""
import json
import os
import struct

from . import gamedata as G
from . import packets as P
from .units import dist

TEMPLATES = os.path.join(G.ROOT, 'data', 'exe1620', 'spells16')
SIMULATED = frozenset({906, 972, 515, 390, 150, 938, 743, 118, 548, 433, 61, 1140, 723, 1195, 1201, 584, 362, 755, 1052, 660,
                       282, 430, 294, 1126, 121, 264, 1143, 211, 536, 1183,
                       # [m: in the replays, never in the live recordings] the spectator's own: team sight, camera, the
                       # followed unit, banners
                       756, 347, 488, 281, 322, 741, 1217})
SPAWN_SIDE = frozenset({626, 684, 239})       # made by summons.spawn
MAX_DT = 12.0
STEALTH_BIT = 0x20
# packets whose differing fields are the match's situation (a cooldown cut by a pickup, gold, the unit aimed at, an
# event naming units): played only when every field was the same in all the casts seen
SITUATIONAL = frozenset({635, 818, 1143, 447, 972, 699, 1210, 838, 139, 1248, 912, 639})
# LoL's buff types [m: 5 stun, 7 silence, 11 slow, 12 snare in the live recording; the rest by the enum's order]
CC = {5: 'stun', 7: 'silence', 8: 'taunt', 11: 'slow', 12: 'snare', 22: 'fear', 23: 'charm', 25: 'suppress',
      29: 'flee', 30: 'knockup', 31: 'knockback', 32: 'disarm', 33: 'grounded', 34: 'drowsy', 35: 'asleep'}


def _u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and len(h) == 8 else 0


def _f32(h):
    return struct.unpack('<f', bytes.fromhex(h))[0] if isinstance(h, str) and len(h) == 8 else 0.0


def _text(v):
    try:
        return bytes.fromhex(v['text']).decode('latin-1').rstrip('\0') if isinstance(v, dict) else ''
    except Exception:
        return ''


def load(champ):
    """a champion's templates, with what is not the spell's own marked ('amb'): a buff on the units hit (435, role
    'other') that also shows after the champion's other casts - in a cast that is no spell of its (a ward, a summoner
    spell, an item, the recall) or in three or more of its spells - at no steady time after the cast (more than 2 s
    between the earliest and the latest) is what the champion's attacks, items or runes do (a red buff's slow, an
    item's, Ashe's frost on every arrow), not this spell [the replays: Ashe's Volley slows 0.3 - 0.9 s after the
    cast, its Q's window holds the same slow at any time]"""
    p = os.path.join(TEMPLATES, f'{champ}.json')
    d = json.load(open(p)) if os.path.exists(p) else {}
    for t in d.values():
        # played ('core'): in at least half of the casts still watched at its time, and in enough of them to be no
        # accident [a: 8 % of the casts sampled, at least 2 - Zed's shadow is watched in 15 of 120, his next spell
        # comes that fast]
        need = max(2, 0.08 * t.get('samples', 0))
        for e in t.get('events', []) + t.get('trigger', []):
            if 'seen' in e:
                e['core'] = bool(e.get('cond')) or (e['share'] >= float(os.environ.get('BA_CORE_SHARE', 0.5)) and e['seen'] >= need)
            n = e.get('net')
            if e['role'] == 'other' and isinstance(n, dict) and n.get('$') == 'net' and str(n.get('of', '')).startswith('spawn'):
                # a packet about the unit the cast made that came before its creation in the frame (Shaco's box gets
                # its 40 s "JackInTheBox" buff first): the unit's own
                e['role'] = 'spawn'
        # at one time the unit's creation goes first: the rest of that frame is about it
        t['events'].sort(key=lambda e: (round(e['dt'], 2), 0 if e['role'] == 'spawn' and e['pid'] in (626, 1038) else 1))
    seen = {}
    for name, t in d.items():
        for e in t.get('events', []):
            if e['pid'] == 435 and e['role'] == 'other' and e['share'] >= 0.15 and isinstance(e.get('values'), dict):
                h = e['values'].get('+0x64')
                if isinstance(h, str):
                    seen.setdefault(h, []).append((name, t.get('qwer')))
    for name, t in d.items():
        for e in t.get('events', []):
            if e['pid'] == 435 and e['role'] == 'other' and isinstance(e.get('values'), dict):
                where = seen.get(e['values'].get('+0x64'), [])
                wide = e['dt_hi'] - e['dt_lo'] > 2.0
                if wide and (len(where) >= 3 or any(q is None and not n.startswith(champ) for n, q in where)):
                    e['amb'] = True
    return d


class Cast:
    """one cast being played: the units, places and times its template's computed fields stand for"""
    def __init__(self, hero, tpl, t0, aim, end, launch, target, cast_id, missile_id, sctx=None):
        self.hero, self.tpl, self.t0, self.sctx = hero, tpl, t0, sctx
        self.places = {'aim': aim, 'end': end, 'launch': launch}
        self.nets = {'caster': hero.net, 'target': target.net if target is not None else 0, 'cast': cast_id,
                     'missile0': missile_id}
        self.target = target
        self.fades = []


class Templates:
    def __init__(self, game):
        self.g = game
        self.by_champ = {}
        self.fade_id = 0x100

    # ------------------------------------------------------------------ the templates
    def of(self, champ, spell):
        d = self.by_champ.get(champ)
        if d is None:
            d = self.by_champ[champ] = load(champ)
        t = d.get(spell)
        if t is None:
            low = spell.lower()
            t = next((v for k, v in d.items() if k.lower() == low), None)
        return t

    def has(self, champ, spell):
        return self.of(champ, spell) is not None

    @staticmethod
    def core(tpl, roles=('caster', 'missile', 'spawn')):
        return [e for e in tpl['events'] if e['core'] and e['role'] in roles and e['dt'] <= MAX_DT]

    def hit_buffs(self, champ, spell):
        """[(type, name hash, duration)] the spell gives the units it hits [the template's 'other' 435 events]"""
        tpl = self.of(champ, spell)
        out = []
        for e in (tpl or {}).get('events', []):
            if e['role'] == 'other' and e['pid'] == 435 and e['share'] >= 0.25 and isinstance(e.get('values'), dict) \
                    and not e.get('amb'):
                v = e['values']
                if v.get('+0x5c') in (P.u32(G.PACKAGE_GLOBAL), P.u32(G.PACKAGE_MAP)) and                         not (isinstance(v.get('+0x38'), str) and int(v['+0x38'], 16) in CC):
                    continue                             # an item's or a rune's (the shared package), not the spell's;
                    #                                      the shared "Stun" / "Slow" buffs a spell gives are kept
                if isinstance(v.get('+0x38'), str) and isinstance(v.get('+0x64'), str):
                    out.append((int(v['+0x38'], 16), _u32(v['+0x64']), _f32(v.get('+0x3c')) if isinstance(v.get('+0x3c'), str) else 1.0))
        return out

    def movement(self, champ, spell):
        """('teleport' | 'dash', s after the cast) when the real server moved the champion so in most casts"""
        tpl = self.of(champ, spell)
        for e in (tpl or {}).get('events', []):
            if e['role'] == 'caster' and e['share'] >= 0.5 and e['dt'] <= 2.0:
                v = e.get('values') or {}
                if e['pid'] == 61 and isinstance(v, dict) and v.get('teleport') is not None:
                    return 'teleport', e['dt']
                if e['pid'] == 1140:
                    gm = tpl.get('geom')
                    if gm is not None and not gm.get('dash'):
                        continue                         # a dash of another unit (Zed's shadow flying out), not the caster's
                    return 'dash', e['dt']
        return None

    def cast_times(self, champ, spell):
        """(cast time, total time) the real server wrote in this spell's 1215 [the template's cast struct: +0x4c,
        +0xa8]; None for one that differed between casts (attack-speed scaled, a channel cut short)"""
        tpl = self.of(champ, spell)
        c = ((tpl or {}).get('cast') or {}).get('+0x18') or {}
        ct, tt = c.get('+0x4c'), c.get('+0xa8')
        return (_f32(ct) if isinstance(ct, str) else None, _f32(tt) if isinstance(tt, str) else None)

    def hit_effects(self, champ, spell):
        """the effects (10) the real server put on the units this spell hit [the template's 'other' 10 events]"""
        tpl = self.of(champ, spell)
        return [e for e in (tpl or {}).get('events', []) if e['role'] == 'other' and e['pid'] == 10 and e['share'] >= 0.25
                and isinstance(e.get('values'), dict)]

    def show_hit(self, hero, spell, tgt):
        """the spell hit tgt: its recorded hit effects on it -> True when the template had any"""
        fx = self.g.fx
        evs = self.hit_effects(hero.name, spell)
        if fx is None or not evs:
            return bool(evs)
        for e in evs:
            for grp in e['values'].get('+0x10') or []:
                if not isinstance(grp, dict):
                    continue
                key = _u32(grp.get('+0x20')) if isinstance(grp.get('+0x20'), str) else 0
                if not key:
                    continue
                fid = fx.create(key, hero, bound=tgt, target=tgt, flags=int.from_bytes(bytes.fromhex(grp.get('+0x50', '2000')), 'little')
                                if isinstance(grp.get('+0x50'), str) else 0x20,
                                bone=_u32(grp.get('+0xc')) if isinstance(grp.get('+0xc'), str) else 0,
                                target_bone=_u32(grp.get('+0x38')) if isinstance(grp.get('+0x38'), str) else 0)
                fx.until.append((self.g.t + 4.0, fid))
        return True

    def self_buff_types(self, champ, spell):
        """the buff types the real server gave the caster at this spell (15 = haste ...): its own packets are the
        template's, the simulation applies only their effect"""
        tpl = self.of(champ, spell)
        return {int(e['values']['+0x38'], 16) for e in (tpl or {}).get('events', [])
                if e['core'] and e['role'] == 'caster' and e['pid'] == 435 and isinstance(e.get('values'), dict)
                and isinstance(e['values'].get('+0x38'), str)}

    def direct_damage(self, champ, spell):
        """the real server's damage (150) under this spell's own name in most casts: it hits at the cast (Annie's R
        landing), not only through the unit it creates"""
        tpl = self.of(champ, spell)
        h = P.u32(P.elf(spell))
        return any(e['pid'] == 150 and e['role'] == 'other' and e['share'] >= 0.4 and isinstance(e.get('values'), dict)
                   and e['values'].get('+0x2c') == h for e in (tpl or {}).get('events', []))

    def makes_units(self, champ, spell):
        """the spell creates a unit in most casts (a trap, a pet): its effect is that unit's, not a hit at the cast"""
        tpl = self.of(champ, spell)
        return any(e['pid'] == 626 and e['role'] == 'spawn' and e['core'] for e in (tpl or {}).get('events', []))

    def missiles(self, champ, spell):
        tpl = self.of(champ, spell)
        return [e for e in self.core(tpl, ('missile',)) if e['pid'] == 223] if tpl else []

    def real_damage(self, champ, spell):
        """(amount, type) of the damage the real server dealt under this spell's own name [the template's 150s on the
        units hit: +0x10 the amount (the middle one of the casts seen), +0x18 the type]; None when it dealt none"""
        key = (champ, spell)
        cache = self.__dict__.setdefault('_real_damage', {})
        if key not in cache:
            tpl = self.of(champ, spell)
            h = P.u32(P.elf(spell))
            best = None
            for e in (tpl or {}).get('events', []):
                v = e.get('values')
                if e['pid'] == 150 and e['role'] == 'other' and e['share'] >= 0.25 and isinstance(v, dict) and v.get('+0x2c') == h:
                    a = v.get('+0x10')
                    ex = a.get('ex') if isinstance(a, dict) else [a]
                    amounts = sorted(x for x in (_f32(y) for y in ex or [] if isinstance(y, str)) if 0.0 < x < 5000.0)
                    t = v.get('+0x18')
                    if amounts and (best is None or e['share'] > best[2]):
                        best = (amounts[len(amounts) // 2], int(t, 16) if isinstance(t, str) and len(t) == 2 else None, e['share'])
            cache[key] = best[:2] if best else None
        return cache[key]

    def hit_time(self, champ, spell):
        """s after the cast at which the real server's damage under this spell's own name fell, when that was a
        steady time over the casts (at most 0.8 s between the earliest and the latest: not a missile's flight, not
        a player's later attack); None otherwise"""
        key = (champ, spell)
        cache = self.__dict__.setdefault('_hit_time', {})
        if key not in cache:
            tpl = self.of(champ, spell)
            h = P.u32(P.elf(spell))
            best = None
            for e in (tpl or {}).get('events', []):
                v = e.get('values')
                if e['pid'] == 150 and e['role'] == 'other' and e['share'] >= 0.4 and isinstance(v, dict) and \
                        v.get('+0x2c') == h and e['dt_hi'] - e['dt_lo'] <= 0.8:
                    if best is None or e['dt'] < best:
                        best = e['dt']
            cache[key] = best
        return cache[key]

    def geom(self, champ, spell):
        """the spell's measured geometry (tools/spell_geom16.py): reach, missiles, dash"""
        return (self.of(champ, spell) or {}).get('geom')

    def own_missile(self, champ, spell):
        """s after the cast at which the cast's own missile left in most real casts (a 938 naming the missile id the
        1215 carried); None: this spell has none"""
        tpl = self.of(champ, spell)
        for e in (self.core(tpl, ('caster',)) if tpl else []):
            if e['pid'] == 938 and isinstance(e.get('values'), dict) and e['values'].get('+0x10') == {'$': 'net', 'of': 'missile0'}:
                return e['dt']
        return None

    def primary_missiles(self, champ, spell):
        """the missile spells the cast itself launches from the champion [the replays: in most casts, within 1.5 s,
        starting at the caster's place]: their hits are the spell's hits"""
        tpl = self.of(champ, spell)
        if not tpl:
            return []
        gm = (tpl.get('geom') or {}).get('missiles') or {}
        out = []
        for e in self.missiles(champ, spell):
            hx = ((e.get('values') or {}).get('+0xf8') or {}).get('+0x18')
            m = gm.get(hx) if isinstance(hx, str) else None
            if e['dt'] <= 1.5 and (m is None or (m['from_caster'] >= 0.5 and m['to_caster'] < 0.5)):
                out.append(e)
        return out

    def spell_by_hash(self, hero, h):
        """the name of the champion's spell with this ELF hash (a missile spell named by a 223)"""
        m = getattr(hero.champ, '_by_hash', None)
        if m is None:
            m = hero.champ._by_hash = {P.elf(n): n for n in hero.champ.objects}
        return m.get(h)

    # ------------------------------------------------------------------ playing a cast
    def find_hash(self, champ, h):
        """(champion, spell key) of a template whose spell's ELF hash is h: the champion's own first, then any
        champion's (an item's or a trinket's active is the same for everyone) through an index kept on disk"""
        def match(key):
            return key == f'#{h:08x}' or P.elf(key) == h
        own = self.by_champ.get(champ)
        if own is None:
            own = self.by_champ[champ] = load(champ)
        for key in own:
            if match(key):
                return champ, key
        idx = getattr(self, '_hash_index', None)
        if idx is None:
            path = os.path.join(TEMPLATES, '_hash_index.json')
            try:
                idx = json.load(open(path))
            except Exception:
                idx = {}
                for f in sorted(os.listdir(TEMPLATES)):
                    if not f.endswith('.json') or f.startswith('_') or not f[0].isupper():
                        continue
                    try:
                        d = json.load(open(os.path.join(TEMPLATES, f), encoding='utf-8'))
                    except Exception:
                        continue
                    for key, tpl in d.items():
                        if isinstance(tpl, dict):
                            hh = int(key[1:], 16) if key.startswith('#') else P.elf(key)
                            idx.setdefault(f'{hh:08x}', [f[:-5], key])
                json.dump(idx, open(path, 'w'))
            self._hash_index = idx
        hit = idx.get(f'{h:08x}')
        return tuple(hit) if hit else None

    def play(self, hero, spell, aim, end, launch, target, cast_id, missile_id, sctx=None, champ=None, only=None):
        """schedule the template's events of this cast -> the Cast (None: no template); sctx = spells.py's cast
        (its missiles' hits are the spell engine's); champ: whose template (an item's active: any champion's)"""
        tpl = self.of(champ or hero.name, spell)
        if tpl is None:
            return None
        g = self.g
        c = Cast(hero, tpl, g.t, aim, end, launch, target, cast_id, missile_id, sctx)
        core = self.core(tpl)
        c.ends = self.end_groups(core)
        ending = {id(x) for grp in c.ends.values() for x in grp}
        c.conds = [e for e in core if e.get('cond')]
        c.fired = set()
        for e in core:
            if only is not None and e['pid'] not in only:
                continue                                 # the rest is the champion's scripts' (core/bbengine.py)
            if id(e) in ending or e.get('cond'):
                continue                                 # sent when its buff ends (buff_add's undo) / when the cast hits
            if e['pid'] in SIMULATED or (e['pid'] == 1215 and _slot_of(e) == tpl['slot']):
                continue
            if e['pid'] in SITUATIONAL and _varies(e.get('values')) and not _own_cooldown(e) and e['pid'] != 699:
                continue
            if e['role'] == 'spawn' and e['pid'] in SPAWN_SIDE and e['pid'] != 626:
                continue
            if e['dt'] <= 0.001:
                self.emit(c, e)                          # [the replays] in the cast's own frame, right after its 1215
            else:
                g.at(g.t + e['dt'], lambda t2, e=e, c=c: self.emit(c, e))
        # the area's renewed buffs on other units (zone_aura): from the 'other' events, which are otherwise not played
        from .spells import buff_refresh
        for e in self.core(tpl, roles=('other',)):
            if e['pid'] == 435 and isinstance(e.get('values'), dict) and e['values'].get('+0x64') in buff_refresh():
                g.at(g.t + e['dt'], lambda t2, e=e, c=c: self.emit(c, e))
        return c

    @staticmethod
    def end_groups(core):
        """{buff name hash: [events]}: a buff the cast gives the champion and what the real server sent at the moment
        it was taken away (its 262 and, within 50 ms, the champion's other packets: the fade undone, the stealth flags
        cleared, the cooldown started, the action state back) - played when the buff really ends: its time runs out
        or something breaks it (an attack ends an invisibility)"""
        added = {}
        for e in core:
            if e['pid'] == 435 and e['role'] == 'caster' and isinstance(e.get('values'), dict) and                     isinstance(e['values'].get('+0x64'), str):
                added.setdefault(e['values']['+0x64'], e['dt'])
        out = {}
        for r in core:
            if r['pid'] != 262 or r['role'] != 'caster' or not isinstance(r.get('values'), dict):
                continue
            h = r['values'].get('+0x14')
            if h not in added or r['dt'] <= added[h] + 0.05:
                continue                                 # taken away before the cast gives it: the last cast's buff
            out[h] = [r] + [x for x in core if x is not r and x['role'] == 'caster' and abs(x['dt'] - r['dt']) <= 0.05
                            and x['pid'] in (29, 291, 635, 287, 236, 947, 1088, 280, 904, 78) and not _extra_slot(x)]
        return out

    def end_of(self, c, h):
        """the buff with this name hash (hex) ended: its end group, without its 262 (the buff's end sends that)"""
        for e in c.ends.get(h, []):
            if e['pid'] != 262:
                self.emit(c, e)

    def emit(self, c, e, hit=None):
        if hit is not None:
            c.hit_net = hit                              # an 'other' event of a hit is about the unit hit
            try:
                return self.emit(c, e)
            finally:
                c.hit_net = None
        g, pk = self.g, self.g.pk
        hero = c.hero
        if not hero.alive and e['role'] == 'caster' and e['pid'] not in (262, 29):
            return
        kits = getattr(g, 'kits', None)
        if kits is not None and kits.call(hero, 'skip_template', e):
            return                                       # the champion's kit plays this one itself (core/kits)
        pid = e['pid']
        try:
            if pid == 287:
                return self.replicated(c, e)
            if pid in (626, 1038) and e['role'] == 'spawn':
                return self.spawn(c, e)
            if e['role'] == 'spawn' and pid in (1112, 1090):
                return self.spawn_end(c, e)
            if pid == 223 and e['role'] == 'missile':
                # a missile is a unit of its own: its net id is this match's (the template's is never used)
                v = self.fill(c, e.get('values'))
                return self.missile(c, e, v) if isinstance(v, dict) else None
            if pid == 435 and e['role'] == 'other' and isinstance(e.get('values'), dict):
                from .spells import buff_refresh
                r = buff_refresh().get(e['values'].get('+0x64'))
                if r is not None:
                    return self.zone_aura(c, e, r)
            if pid == 41:
                return self.region(c, e)
            net = self.net_of(c, e)
            if net is None:
                return
            v = self.fill(c, e.get('values'))
            if v is None:
                return
            if pid == 435:
                return self.buff_add(c, e, net, v)
            if pid == 262:
                return self.buff_remove(c, net, v)
            if pid == 223:
                return self.missile(c, e, v)
            if pid == 1215:
                return self.subcast(c, v)
            if pid == 699:
                return self.event(c, e, net)
            if pid == 10:
                return self.effect(c, e, v)
            if pid in (947, 596):
                self.fade_id += 1
                v['+0x10']['+0x10'] = struct.pack('<H', self.fade_id & 0xffff).hex()
                c.fades.append((net, self.fade_id))
                u = g.units.get(net)
                if u is not None:
                    u.fades = getattr(u, 'fades', []) + [self.fade_id & 0xffff]
            elif pid == 635 and isinstance((e.get('values') or {}).get('+0x10'), dict):
                slot = (0xae - int(v.get('+0x24', 'ae'), 16)) // 4
                if not 0 <= slot < 4 or g.spells is None:
                    return
                from .spells import info
                inf = info(hero.champ, hero.spell_name(slot))
                seen = sorted(x for x in (_f32(y) for y in e['values']['+0x10'].get('ex') or [] if isinstance(y, str)) if x >= 0)
                if seen and seen[len(seen) // 2] < 2.0:
                    v['+0x10'] = P.f32(seen[len(seen) // 2])     # a short lock, the same for every rank
                else:
                    v['+0x10'] = P.f32(inf.cooldown(max(1, hero.spell_levels[slot])) * 100.0 / (100.0 + hero.bonus.get('haste', 0.0)))
                for k in ('+0x18', '+0x1c', '+0x20'):
                    if not isinstance(v.get(k), str):
                        v[k] = '00000000'
            elif pid == 29:
                fid = next((f for n, f in reversed(c.fades) if n == net), None)
                u = g.units.get(net)
                if fid is None or u is None or (fid & 0xffff) not in getattr(u, 'fades', []):
                    return                                   # already undone (the unit showed itself)
                u.fades.remove(fid & 0xffff)
                v['+0x10'] = struct.pack('<H', fid & 0xffff).hex()
            g.q.append((e.get('ch') or 1, pid, net, pk.enc(pid, v)))
            if pid == 78 and net == hero.net:
                self.slot_spell(hero, v)
            elif pid == 635 and net == hero.net:
                self.cooldown(hero, v)
        except Exception as x:                           # a template field we cannot write: that packet is left out
            g.log(f'template {hero.name} {pid}: {x!r}')

    def region(self, c, e):
        """41 [m 10-13: the replays' regions after casts]: a perception bubble of the cast - bound to the caster / its
        target or standing at one of the cast's places; its own new net id (+0x44), the caster's team (+0x25)"""
        g = self.g
        v = self.fill(c, e.get('values'))
        if not isinstance(v, dict) or not isinstance(v.get('+0x10'), dict):
            return
        r = v['+0x10']
        r['+0x44'] = P.u32(g.new_net())
        r['+0x25'] = '01' if c.hero.team == 100 else '02'
        for k in ('+0x8', '+0x1c'):
            if isinstance(r.get(k), dict) or not isinstance(r.get(k), str):
                r[k] = P.u32(0)
        if not isinstance(r.get('+0x14'), str) or len(r['+0x14']) != 16:
            r['+0x14'] = struct.pack('<ff', c.hero.pos[0], c.hero.pos[1]).hex()
        try:
            g.q.append((1, 41, 0, g.pk.enc(41, v)))
        except Exception as x:
            g.log(f'41 of {c.hero.name}: {x!r}')

    def slot_spell(self, hero, v):
        """78 put another spell in one of the champion's four slots (a recast form): its next cast is that one"""
        slot = int((v.get('+0x10') or {}).get('+0xf', 'ff'), 16)
        name = _text(v.get('+0x20'))
        if 0 <= slot < 4 and name:
            base = hero.champ.spells[slot]
            was = hero.slot_names[slot]
            hero.slot_names[slot] = name
            held = hero.__dict__.setdefault('held_cooldowns', {})
            if name != base and was == base:
                # a recast form took the slot: it can be cast at once (Zed's swap, Garen's cancel); the spell's own
                # cooldown waits until the slot is the spell's again [a: counted from the first cast]
                held[slot] = hero.cooldowns[slot]
                hero.cooldowns[slot] = self.g.t + 0.25
                hero.refresh_bits()
            elif name == base and slot in held:
                hero.cooldowns[slot] = max(self.g.t, held.pop(slot))
                hero.refresh_bits()

    def cooldown(self, hero, v):
        """635 set a slot's cooldown [m: +0x10 seconds left, +0x24 the slot in the client's in-memory form, 0xae - 4 x
        slot]: the real server's own cooldown of a recast"""
        code = int(v.get('+0x24', 'ae'), 16)
        slot = (0xae - code) // 4
        if 0 <= slot < 4 and (0xae - code) % 4 == 0:     # [m: Ahri's R sends a7 - no slot of that form]
            hero.cooldowns[slot] = self.g.t + max(0.0, _f32(v.get('+0x10')))
            hero.refresh_bits()

    # ------------------------------------------------------------------ fields
    def on_cast_hit(self, c, tgt):
        """the cast hit a unit: its events that the real server sent only when the cast hit (anything / a champion)
        [m: spell_templates16.conditions], dt_cond after the hit, an 'other' one about the unit hit"""
        g = self.g
        for e in getattr(c, 'conds', ()):
            if e['cond'] == 'hit_hero' and not tgt.is_hero:
                continue
            k = (id(e), tgt.net if e['role'] == 'other' else 0)
            if k in c.fired:
                continue
            c.fired.add(k)
            g.at(g.t + e.get('dt_cond', 0.0), lambda t2, e=e, n=tgt.net: self.emit(c, e, hit=n))

    def net_of(self, c, e):
        if e['role'] == 'other' and getattr(c, 'hit_net', None):
            return c.hit_net
        n = e.get('net')
        if isinstance(n, dict) and n.get('$') == 'net':
            return c.nets.get(n['of'])
        if e['role'] == 'spawn':
            return c.nets.get('spawn0')
        if isinstance(n, str) and len(n) == 8:
            if e['role'] == 'caster':
                return c.hero.net
            if e['role'] == 'spawn':
                return c.nets.get('spawn0')
            return None
        return c.hero.net if e['role'] == 'caster' else None

    def fill(self, c, v):
        """a template value with this cast's units, places and times"""
        if isinstance(v, dict):
            k = v.get('$')
            if k == 'net':
                return P.u32(c.nets.get(v['of']) or 0)
            if k == 'time':
                return P.f32(c.t0 + v['off'])
            if k == 'place':
                p = c.places.get(v['of']) or c.hero.pos
                return P.vec3(p[0], self.g.pk.y(p) + v.get('dy', 0.0), p[1])
            if k == 'place2':
                p = c.hero.pos if v['of'] == 'caster' else (c.places.get(v['of']) or c.hero.pos)
                return struct.pack('<ff', p[0], p[1]).hex()
            if k == 'vary':
                ex = v['ex'][0] if v.get('ex') else None
                if isinstance(ex, str) and len(ex) == 8 and ex[4:8] == '0040' and ex[0:4] != '0000':
                    return P.u32(0)                     # a unit of that match (0x4000xxxx; 2.0 - 4.0 s are floats)
                return ex
            return {kk: self.fill(c, x) for kk, x in v.items()}
        if isinstance(v, list):
            return [self.fill(c, x) for x in v]
        return v

    # ------------------------------------------------------------------ the kinds made by the simulation's systems
    def buff_add(self, c, e, net, v):
        g = self.g
        u = g.units.get(net)
        if u is None:
            return
        btype = int(v['+0x38'], 16)
        h = _u32(v['+0x64'])
        dur = _f32(v['+0x3c'])
        sp = g.spells
        if not hasattr(u, 'buff_list'):
            u.buff_list = {}
        key = ('tpl', h)
        old = u.buff_list.get(key)
        slot = old['slot'] if old else sp.buff_slot(u)
        until = g.t + (dur if 0 < dur < 1000 else 3600.0)
        hh = v['+0x64']
        undo = (lambda c=c, hh=hh: self.end_of(c, hh)) if hh in getattr(c, 'ends', {}) else None
        u.buff_list[key] = {'slot': slot, 'until': until, 'hash': h, 'undo': undo, 'known': g.vision is None or not g.vision.hidden(u),
                            'args': (_u32(v.get('+0x1c')) or c.hero.net, slot, btype, h, _u32(v.get('+0x5c')))}
        v['+0x60'] = f'{slot:02x}'
        g.q.append((1, 435, net, g.pk.enc(435, v)))
        g.pk.buff_added(net, _u32(v.get('+0x1c')) or c.hero.net, slot, h, int(v.get('+0x40') or '01', 16))
        sp.buffs.append([until, u, key])
        sp.renew_on_updates(u, key)
        if btype == 6:                                  # [m: wards] invisibility: hidden from the other team
            u.stealth_until = until
        if btype in (17, 18):
            u.untargetable_until = until

    def event(self, c, e, net):
        """699 OnEvent [m: the client registers each event type with its size; the body is the event's raw struct,
        +0x4 its source unit]: the real server's event of this cast with this match's units - the recorded source
        becomes the caster, any other unit of that match the cast's target (or the caster)"""
        g = self.g
        v = e.get('values') or {}
        body = v.get('+0x18')
        if isinstance(body, dict) and body.get('$') == 'vary':
            body = (body.get('ex') or [None])[0]
        if not isinstance(body, dict) or not isinstance(body.get('text'), str) or not isinstance(v.get('+0x10'), str):
            return
        raw = bytearray(bytes.fromhex(body['text']))
        src = bytes(raw[4:8]) if len(raw) >= 8 else b''
        me = struct.pack('<I', c.hero.net)
        other = struct.pack('<I', c.nets.get('target') or c.hero.net)
        for i in range(0, len(raw) - 3):
            w = bytes(raw[i:i + 4])
            if w == src:
                raw[i:i + 4] = me
            elif w[3] == 0x40 and w[2] == 0 and w[1] < 0x20 and w != src:
                raw[i:i + 4] = other                    # a unit of the recorded match (0x400000xx - 0x40001fxx)
        out = {'+0x10': v['+0x10'], '+0x18': {'text': raw.hex()}}
        if isinstance(v.get('+0x28'), str):
            out['+0x28'] = v['+0x28']
        try:
            g.q.append((1, 699, net, g.pk.enc(699, out)))
        except Exception as x:
            g.log(f'699 of {c.hero.name}: {x!r}')

    def zone_aura(self, c, e, r):
        """[m: tools/buff_refresh16.py + the cast evidence] a buff the cast puts on the units in its area and renews on
        every script update while they stand there (Singed's poison, Hwei's lava, Anivia's storm): each update the
        enemies in the area get it (435 the first time, 282 after), one that leaves keeps it for its duration (262 when
        it ends). Area: the spell's radius around where it was aimed; it lasts the spell's data duration"""
        g, sp = self.g, self.g.spells
        sc = c.sctx or {}
        inf, rank = sc.get('inf'), sc.get('rank', 1)
        if inf is None or sp is None:
            return
        v = e['values']
        h, btype = _u32(v['+0x64']), int(v.get('+0x38', '01'), 16)
        key = ('aura', h, id(c))
        if getattr(c, 'auras', None) is None:
            c.auras = set()
        if h in c.auras:
            return
        c.auras.add(h)
        center = c.places.get('aim') or c.places.get('end') or c.hero.pos
        radius = inf.radius(rank) or 250.0
        life = inf.data_value(('Duration', 'ZoneDuration', 'TotalDuration', 'BuffDuration', 'PoolDuration'), rank) or 3.0
        until = g.t + life
        package = _u32(v.get('+0x5c'))
        from .game import SCRIPT_UPDATE

        def update(t):
            if t > until:
                return
            for u in list(g.units.values()):
                if not u.alive or u.team == c.hero.team or not u.targetable or u.is_structure:
                    continue
                if dist(u.pos, center) > radius + u.radius:
                    continue
                if not hasattr(u, 'buff_list'):
                    u.buff_list = {}
                b = u.buff_list.get(key)
                known = g.vision is None or not g.vision.hidden(u)
                if b is None:
                    slot = sp.buff_slot(u)
                    b = u.buff_list[key] = {'slot': slot, 'until': t + r['dur'], 'hash': h, 'undo': None, 'known': known,
                                            'args': (c.hero.net, slot, btype, h, package)}
                    if known:
                        g.q += g.pk.buff_add(u.net, c.hero.net, slot, btype, h, r['dur'], package=package)
                else:
                    b['until'] = t + r['dur']
                    if b.get('known', True):
                        g.q += g.pk.buff_count(u.net, b['slot'], c.hero.net, r['dur'], r['count'])
                sp.buffs.append([b['until'], u, key])
            g.after_frames(8, update)
        update(g.t)                                      # the event is played at its own moment already

    def buff_remove(self, c, net, v):
        g = self.g
        u = g.units.get(net)
        if u is None:
            return
        h = _u32(v.get('+0x14'))
        key = ('tpl', h)
        b = getattr(u, 'buff_list', {}).pop(key, None)
        if b is None:
            return
        g.q += g.pk.buff_remove(net, b['slot'], h)
        if getattr(u, 'stealth_until', 0) and b.get('args', (0, 0, 0))[2] == 6:
            u.stealth_until = 0.0

    def replicated(self, c, e):
        field = e.get('field')
        vals = e.get('values') or {}
        before, after = (vals.get(field) or [None, None])[:2]
        u = c.hero if e['role'] == 'caster' else self.g.units.get(c.nets.get('spawn0'))
        if u is None or after is None:
            return
        if field == 'ActionState':
            # [m: Shaco's Deceive and boxes, the replays] bit 0x20 = invisible to the other team
            if after & STEALTH_BIT and not before & STEALTH_BIT:
                u.stealth_until = max(getattr(u, 'stealth_until', 0.0), self.g.t + 3600.0)
            elif before & STEALTH_BIT and not after & STEALTH_BIT:
                u.stealth_until = 0.0
            if not u.is_hero:
                u.set('ActionState', after)
                return
            on, off = after & ~before, before & ~after
            u.tpl_bits = ((getattr(u, 'tpl_bits', (0, 0))[0] | on) & ~off, (getattr(u, 'tpl_bits', (0, 0))[1] | off) & ~on)
            if self.g.spells is not None:
                self.g.spells.action_state(u)
            return
        if field in ('mAllShield', 'mPhysicalShield', 'mMagicalShield'):
            u.shield = getattr(u, 'shield', {})
            u.shield[field] = float(after)
        if field == 'mIsTargetable':
            u.targetable = bool(after)                   # [the replays] Yi's Alpha Strike, Fizz's E ...: no one may aim at it
            if not u.targetable:
                self.g.release_attackers(u)
        if field == 'mAttackRange' and isinstance(after, (int, float)):
            # a form or a buff changes the attack range (Jayce's cannon, Jinx's rockets): the simulation's own reach too
            u.remove_mods(('tpl', 'range'))
            u.add_mods(('tpl', 'range'), {'range': float(after) - u.range})
        u.set(field, after)

    def spawn(self, c, e):
        g = self.g
        if getattr(g, 'summons', None) is None:
            return
        v = self.fill(c, e.get('values') or {})
        p = e.get('values', {}).get('+0x1c' if e['pid'] == 626 else '+0x24')
        place = c.places.get(p['of']) if isinstance(p, dict) and p.get('$') == 'place' else None
        if place is None:
            place = c.places.get('end') or c.places.get('aim') or c.hero.pos
        life = None
        if e['pid'] == 1038:
            # a pet whose 1038 says "until killed" (25000) lives as long as the buff the cast gave its owner
            # [m: Shaco's clone and HallucinateGuide's 18 s]
            durs = [_f32(x['values'].get('+0x3c')) for x in self.core(c.tpl, ('caster',)) if x['pid'] == 435
                    and isinstance(x.get('values'), dict) and isinstance(x['values'].get('+0x3c'), str)]
            durs = [d for d in durs if 1.0 < d < 1000.0]
            life = max(durs) if durs else None
        u = g.summons.spawn(c.hero, v, place, pid=e['pid'], life=life)
        if not u.trap and c.tpl.get('samples', 0) >= 6 and not any(
                x['role'] == 'spawn' and x['pid'] in (390, 906, 51, 134) and x['share'] >= 0.2
                for x in c.tpl['events'] + c.tpl.get('trigger', [])):
            # [the replays] the real unit never attacked after this spell (Zed's shadow only copies his spells):
            # it stands where it was put
            u.marker = True
        k = sum(1 for n in c.nets if n.startswith('spawn'))
        c.nets[f'spawn{k}'] = u.net
        if e['pid'] == 626 and u.expires is None:
            # [the replays] it lives as long as the buff the real server gives it when it is made (Shaco's box: 40 s)
            durs = []
            for x in c.tpl['events']:
                xv = x.get('values')
                if x['role'] == 'spawn' and x['pid'] == 435 and abs(x['dt'] - e['dt']) <= 0.05 and isinstance(xv, dict):
                    dv = xv.get('+0x3c')
                    dv = dv['ex'][0] if isinstance(dv, dict) and dv.get('ex') else dv
                    if isinstance(dv, str) and 1.0 < _f32(dv) < 1000.0:
                        durs.append(_f32(dv))
            if durs:
                u.expires = g.t + max(durs)
        if u.base_ad > 0 and g.spells is not None:
            # its attacks deal the spell's damage (the spell's numbers, not the unit record's attack damage)
            from .spells import info
            inf = info(c.hero.champ, self.spell_of(c))
            slot = c.tpl.get('slot', 9)
            if inf is not None and slot < 4:
                amount, dtype = g.spells.damage_of(c.hero, inf, max(1, c.hero.spell_levels[slot]))
                if amount > 0:
                    u.hit_override = (amount, dtype)
        if u.trap:
            # armed when the real server hides it (its invisibility buff), else after the spell's arm time [data]
            hide = [x['dt'] for x in c.tpl['events'] if x['role'] == 'spawn' and (
                    (x['pid'] == 435 and isinstance(x.get('values'), dict) and x['values'].get('+0x38') == '06') or
                    (x['pid'] == 287 and x.get('field') == 'ActionState' and _hides(x.get('values'))))]
            from .spells import info
            inf = info(c.hero.champ, self.spell_of(c))
            arm = (min(hide) - e['dt']) if hide else ((inf.data_value(('ArmTime', 'BoxArmTime', 'TrapArmTime', 'ArmingTime'), 1) if inf else None) or 1.0)
            u.armed_at = g.t + max(0.0, arm)
            # [data] the spell's own radius is how near an enemy sets it off (Shaco's box 300) [a: else 135]
            r = inf.radius(max(1, c.hero.spell_levels[c.tpl['slot']] if c.tpl['slot'] < 4 else 1)) if inf else 0.0
            if 50.0 <= r <= 600.0:
                u.trigger_range = r
            u.on_trigger = lambda u, enemies, c=c: self.trap_goes_off(c, u, enemies)

    def spell_of(self, c):
        for name, t in self.by_champ.get(c.hero.name, {}).items():
            if t is c.tpl:
                return name
        return ''

    def trap_goes_off(self, c, u, enemies):
        """an enemy champion stepped near an armed trap: what the real server did to the units such a trap caught (the
        template's 'spawn_other' buffs: fear, root, slow ...) on every enemy near; then a trap that can attack shows
        itself and fights for a while [a: 5 s], one that cannot is used up"""
        g = self.g
        sp = g.spells
        from .spells import info
        inf = info(c.hero.champ, self.spell_of(c))
        radius = inf.radius(max(1, c.hero.spell_levels[c.tpl['slot']] if c.tpl['slot'] < 4 else 1)) or 300.0
        caught = [o for d, o in g.enemies_near(u, radius + 50.0) if not o.is_structure] or enemies
        buffs = [x for x in c.tpl.get('trigger', []) if x['role'] in ('spawn_other', 'other') and x['pid'] == 435
                 and x['share'] >= 0.2 and isinstance(x.get('values'), dict) and isinstance(x['values'].get('+0x38'), str)]
        for o in caught:
            for x in buffs:
                v = x['values']
                ctx = dict(hero=c.hero, inf=inf, rank=1, slot=c.tpl['slot'])
                dur = _f32(v.get('+0x3c')) if isinstance(v.get('+0x3c'), str) else 1.0
                sp.template_effects(ctx, o, [(int(v['+0x38'], 16), _u32(v.get('+0x64')), dur)])
        u.trap = False
        u.on_trigger = None
        for e in c.tpl.get('trigger', []):
            if e['core'] and e['role'] == 'spawn' and e['pid'] not in SIMULATED and e['dt'] <= MAX_DT:
                if e['dt'] <= 0.001:
                    self.emit(c, e)
                else:
                    g.at(g.t + e['dt'], lambda t2, e=e, c=c: self.emit(c, e))
        for key, b in list(getattr(u, 'buff_list', {}).items()):
            if b.get('args', (0, 0, 0))[2] == 6:            # it shows itself
                u.buff_list.pop(key, None)
                g.q += g.pk.buff_remove(u.net, b['slot'], b['hash'])
        u.stealth_until = 0.0
        if u.base_ad > 0 and u.range > 0:
            u.expires = g.t + 5.0
            u.target = min(caught, key=lambda o: dist(o.pos, u.pos)).net if caught else None
        else:
            g.summons.remove(u)

    def spawn_end(self, c, e):
        """the template's death (1112) / removal (1090) of a unit the cast made"""
        g = self.g
        n = self.net_of(c, e)
        u = g.units.get(n) if n else None
        if u is None or getattr(g, 'summons', None) is None:
            return
        if e['pid'] == 1112:
            later = any(x['pid'] == 1090 and x['role'] == 'spawn' for x in self.core(c.tpl))
            g.summons.remove(u, after=None if later else 4.0)
        elif u.net in g.units:
            if u.alive:
                g.summons.remove(u, after=None)
            g.remove(u)

    def missile(self, c, e, v):
        """a missile spell of the cast (223) as the real server made it: the template's own fields (the missile's
        speed, acceleration, slot ...) with this cast's places; how many, at which angles, from where and at whom
        from the spell's measured geometry (tools/spell_geom16.py); what it does to what it meets from the missile
        spell's data (spells.mspec). Kinds:
          primary    starts at the caster, not aimed back at it: the spell's hits (one per unit for the whole cast)
          returning  aimed at the caster (Ahri's orb coming back): hits on its way when every cast has it; one that
                     only some casts have (what a hit gives back) is made only if the cast hit something [a]
          homing     at a unit: hits it on arrival
          other      neither: shown, hits nothing"""
        import math
        from .spells import Missile, mspec
        g, pk = self.g, self.g.pk
        hero, sc = c.hero, c.sctx
        cs = v.get('+0xf8') or {}
        hx = cs.get('+0x18')
        h, slot = _u32(hx), int(cs.get('+0x60', '00'), 16)
        gm = ((c.tpl.get('geom') or {}).get('missiles') or {}).get(hx) or {}
        name = self.spell_by_hash(hero, h)
        ms = mspec((hero.champ.spell(name) or {}).get('mSpell') if name else None)
        base_dir = (sc or {}).get('direction') or hero.facing
        n = max(1, min(int(gm.get('n') or 1), 24))
        angles = gm.get('angles') or [0.0]
        homing = gm.get('homing', 0.0) >= 0.5 if gm else bool(cs.get('+0x8'))
        to_caster = gm.get('to_caster', 0.0) >= 0.5
        from_caster = gm.get('from_caster', 1.0) >= 0.5
        if to_caster and e['share'] < 0.9 and sc is not None and not sc.get('hits'):
            return
        speed = gm.get('speed') or _f32(v.get('+0x98')) or ms['speed'] or 1200.0
        ln = gm.get('len') or {}
        fixed = bool(ln) and ln['hi'] - ln['lo'] <= 40.0 and ln['med'] > 50.0
        primary = from_caster and not to_caster
        if primary:
            hits = c.__dict__.setdefault('primary_hits', set())
        elif to_caster:
            hits = c.__dict__.setdefault('return_hits', set())
        else:
            hits = set()
        rank = sc['rank'] if sc is not None else 1
        chosen = (sc or {}).get('targets') if homing and not to_caster else None
        if callable(chosen):
            chosen = chosen()
        if chosen is not None:
            n = len(chosen)                              # the kit picked whom this cast's missiles fly at (core/kits)
        for i in range(n):
            ang = math.radians(angles[i] if i < len(angles) else 0.0)
            d = (base_dir[0] * math.cos(ang) - base_dir[1] * math.sin(ang), base_dir[0] * math.sin(ang) + base_dir[1] * math.cos(ang))
            start = hero.pos if from_caster else (getattr(c, 'last_end', None) or c.places.get('end') or hero.pos)
            tgt = None
            if homing and chosen is not None and not to_caster:
                tgt = chosen[i] if chosen[i].alive else None
                if tgt is None:
                    continue
                end = tgt.pos
            elif homing:
                tgt = hero if to_caster else ((sc or {}).get('tgt') or c.target)
                if tgt is not None and (not tgt.alive or (tgt is not hero and tgt.team == hero.team and not to_caster and
                                                          ms['collide'])):
                    tgt = None
                if tgt is None and not to_caster:
                    near = [(dist(o.pos, start), o) for o in g.spells.enemies(hero) if dist(o.pos, start) <= 700.0]
                    tgt = min(near, key=lambda x: (not x[1].is_hero, x[0]))[1] if near else None
                if tgt is None:
                    continue                             # nothing to fly at
                end = tgt.pos
            elif fixed:
                # [m: Akshan's Avengerang flies at a point 25000 away and turns back at its range] a "fixed" length
                # beyond any real reach is the missile's far aim point: it goes the spell's range
                far = ln['med'] if ln['med'] <= 5000.0 or sc is None else sc['inf'].range(rank)
                end = (start[0] + d[0] * far, start[1] + d[1] * far)
            elif ms['project'] and ms['range'] > 0:
                end = (start[0] + d[0] * ms['range'], start[1] + d[1] * ms['range'])
            else:
                end = c.places.get('aim') or c.places.get('end') or start
            mid = g.new_net()
            k = sum(1 for x in c.nets if x.startswith('missile'))
            c.nets[f'missile{k}'] = mid
            g.spells.casts += 1
            g.q += pk.missile_launch(hero, mid)          # [the replays: 12500 of 13806 missile spells] 938 + 743 first
            g.q += pk.spell_missile(g.t, mid, hero.net, h, slot, g.spells.casts, g.new_net(), start, end, abs(speed),
                                    package=G.package_hash(hero.name), champion=hero.name,
                                    target=tgt.net if tgt is not None else 0, base=v if i == 0 else self.fill(c, e.get('values')),
                                    owner_place=hero.pos)
            if primary:
                c.last_end = end
            reach = dist(start, end)
            if sc is None or speed <= 0:
                # no flight of ours (one that circles its owner ...): it is there for a while [a: 1.5 s]
                life = reach / speed if speed > 0 else 1.5
                g.at(g.t + life, lambda t2, mid=mid: g.q.extend(pk.missile_end(mid)))
                continue
            dv = ((end[0] - start[0]) / reach, (end[1] - start[1]) / reach) if reach > 1.0 else d
            width = ms['width'] or sc['inf'].width or 60.0
            if tgt is not None:
                m = Missile(mid, hero, sc['inf'], rank, start, dv, abs(speed), 0.0, tgt, width, ms['accel'], ms['vmin'], ms['vmax'],
                            stops=False, collide=to_caster and e['share'] >= 0.9, returning=to_caster, hit=hits)
            else:
                collide = primary and (ms['collide'] or not ms['has'])
                on_end = None
                if primary and not fixed and not ms['project'] and (ms['on_complete'] or not collide):
                    radius = ms['radius'] or sc['inf'].radius(rank) or 150.0
                    on_end = lambda p, sc=sc, radius=radius: g.spells.area(sc, p, radius)
                    collide = False
                m = Missile(mid, hero, sc['inf'], rank, start, dv, min(abs(speed), 30000.0), reach, None, width, ms['accel'],
                            ms['vmin'], ms['vmax'], stops=ms['stops'] if ms['has'] else sc['inf'].stops_first,
                            collide=collide, hit=hits, on_end=on_end)
            g.spells.missiles.append((m, sc))

    def subcast(self, c, v):
        """another of the champion's spells cast by this one (an extra slot: a dagger's spin, a recast's own spell)"""
        g, pk = self.g, self.g.pk
        cs = v.get('+0x18') or {}
        h, slot = _u32(cs.get('+0x18')), int(cs.get('+0x60', '00'), 16)
        aim = c.places.get('aim') or c.hero.pos
        g.spells.casts += 1
        g.q += pk.cast(g.t, c.hero.net, h, slot, g.spells.casts, g.new_net(), g.new_net(), aim, c.places.get('end') or aim,
                       c.hero.pos, c.hero.facing, _f32(cs.get('+0x4c')), _f32(cs.get('+0xa8')), _f32(cs.get('+0x80')), 0.0,
                       c.target.net if c.target is not None else 0, package=G.package_hash(c.hero.name), champion=c.hero.name)

    def effect(self, c, e, v):
        """a scripted effect (10) with the recorded key, bones and flags, on the unit it was bound to"""
        fx = self.g.fx
        if fx is None:
            return
        for grp in v.get('+0x10') or []:
            key = _u32(grp.get('+0x20'))
            inst = (grp.get('+0x10') or [{}])[0]
            bound = self.g.units.get(_u32(inst.get('+0x34'))) if isinstance(inst.get('+0x34'), str) else None
            target = self.g.units.get(_u32(inst.get('+0xb8'))) if isinstance(inst.get('+0xb8'), str) else None
            place = None if bound is not None else (c.places.get('aim') or c.hero.pos)
            fid = fx.create(key, c.hero, bound=bound, target=target, place=place,
                            owner_place=inst.get('+0xe') not in (None, struct.pack('<h', -3679).hex()),
                            flags=int.from_bytes(bytes.fromhex(grp.get('+0x50', '2000')), 'little'),
                            bone=_u32(grp.get('+0xc')), target_bone=_u32(grp.get('+0x38')),
                            keyword=_u32(inst.get('+0x3c')) != 0, old_name=_u32(grp.get('+0x8')))
            # [m: tools/fx_life16.py] taken away (584) after the real median life when at least half of the real
            # ones were; else it ends by itself
            kh = grp.get('+0x20') if grp.get('+0x20') not in (None, '00000000') else 'old:' + str(grp.get('+0x8'))
            life = fx_life().get(c.hero.name, {}).get(kh)
            if life and life[0] >= 3 and life[1] * 2 >= life[0] and life[2] is not None:
                fx.until.append((self.g.t + life[2], fid))


_fx_life = None


def fx_life():
    global _fx_life
    if _fx_life is None:
        try:
            _fx_life = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'fx_life16.json')))
        except Exception:
            _fx_life = {}
    return _fx_life


def _hides(v):
    try:
        a, b = v['ActionState'][:2]
        return bool(b & STEALTH_BIT and not a & STEALTH_BIT)
    except Exception:
        return False


def _varies(v):
    if isinstance(v, dict):
        return v.get('$') == 'vary' or any(_varies(x) for x in v.values())
    if isinstance(v, list):
        return any(_varies(x) for x in v)
    return False


def _own_cooldown(e):
    """a 635 that starts one of the champion's four slots' cooldown, its seconds differing by rank / haste (Garen's E
    after its cancel): written with this champion's own cooldown"""
    try:
        v = e['values']
        return e['pid'] == 635 and e['role'] == 'caster' and isinstance(v.get('+0x24'), str) and             0 <= (0xae - int(v['+0x24'], 16)) // 4 < 4 and isinstance(v.get('+0x10'), dict)
    except Exception:
        return False


def _extra_slot(e):
    """a 78 that names a spell of an extra slot (a missile spell's 0x2d ...): part of a launch, never of a buff's end"""
    try:
        return e['pid'] == 78 and int(e['values']['+0x10']['+0xf'], 16) >= 4
    except Exception:
        return False


def _slot_of(e):
    try:
        return int(e['values']['+0x18']['+0x60'], 16)
    except Exception:
        return None


def setup(game, session=None):
    game.templates = Templates(game)
