"""The scripts' visual effects: packet 10 (an effect is created) and 584 (it is taken away).

What the client plays by itself and what the server must tell it [m]:
  - a champion's skin names its effects in a resource map (skin0.bin, ResourceResolver.resourceMap: key = FNV-1a of
    a lower-cased effect name such as "Garen_E_Spin" -> the VfxSystemDefinitionData in one of the bins the skin
    links). The effect's definition name ("Garen_Base_E_Spin") tells what it is for.
  - the keys a champion's data names itself (animation events' mEffectKey, a spell's mHitEffectKey /
    mMissileEffectKey ...) the client plays alone, from the cast / missile / animation.
  - every other key is the spell scripts': the real server sends packet 10 with that key (197 of the live
    recording's 376 effects are the ten champions' keys; the rest belong to items, runes, minions, the map).
Riot's scripts are not in the client, so WHEN each scripted effect is shown is taken from its name, by the rules
the live recording's effects follow (rules() below; scored against the recording by tools/fx_score16.py):
    <Champion>_<Skin>_<Q|W|E|R|P|BA>_<what>
    ..._Cas / _Cast / _Spin / _Buf / _Avatar ...  when the spell is cast, on the caster
    ..._Tar / _Hit ...                             on every unit the spell hits
    ..._Slow / _Stun / _Root ...                   on a unit while the spell's effect holds it
    ..._AoE / _Ring / _Indicator ...               at the place the spell is aimed at

Packet 10 [m]: a list of groups {+0x8 package hash (0 for champion effects), +0xc bone (ELF hash of the bone's
name, 0 = none; "root"), +0x20 the effect's key, +0x28 three hashes (the same one three times), +0x38 the
target's bone (ELF; a hit effect: "C_BUFFBONE_GLB_CHEST_LOC"), +0x50 flags, +0x10 the instances}. The three
hashes of +0x28 are the caster's package hash (gamedata.package_hash): whose resource map the key is from. An instance:
+0x18 the caster, +0x34 the unit it is bound to (0 = a place), +0xb8 the target, +0x3c the keyword unit, +0x38 the
effect's own net id, its place (+0xac = +0xb4 x cell, +0x30 = +0x4c height, +0x20 = +0x5c z cell), the owner's
place (+0xe x cell, +0xa8 height, +0x10 z cell; none = the constant -3679, -3706), +0x14 scale, +0x50 direction.
584 {0, the effect's net id} ends an effect that does not end by itself.
"""
import json
import os
import re
import struct

from . import gamedata as G
from . import packets as P
from .units import dist, FRAME

SLOTS = {'q': 0, 'w': 1, 'e': 2, 'r': 3}
# what an effect is for, from the words of its name (first match wins) -> trigger
HIT = r'(tar|hit|impact|target|unit)'
HELD = r'(slow|stun|root|snare|silence|debuff|mark|freeze|frozen|fear|charm|sleep|knockup|burn|curse|poison|shred|chain|tether)'
PLACE = r'(aoe|ring|ground|zone|area|circle|field|pool|reticle|warning|indicator|rune|puddle|crater)'
NEVER = (r'(mis|missile|proj|beam|end|cancel|expire|expired|death|kill|onkill|onbuffkill|detonate|deactivate|fade|faded|out|'
         r'recast|ready|loss|fail|emote|taunt|joke|dance|laugh|recall|respawn|homeguard|idle|sound|vo|audio|sfx|'
         r'execute|deflect|block|blockhit|bloodless|max|maxstart|stack|stacks|proc|update|test|dud|return)')
# an effect made in two colours: one for the caster's team, one for the other [the names; the real server sends each
# team its own]
FOR_ENEMIES, FOR_ALLIES = r'(red|enemy|enemies)', r'(green|ally|allies|allied|friendly)'
SELF = (r'(cas|cast|casting|activate|start|begin|flash|burst|swipe|slash|bloodslash|swing|spin|avatar|shoulder|buf|buff|'
        r'shield|selfshield|heal|haste|speed|glow|aura|wings|weapon|rweapon|lweapon|sword|hand|hands|body|self|loop|'
        r'channel|charge|trail|flare|flares|dr|tenacity|steam|smoke|dust|pose|eyeglint|flourish|chicken)')
LASTS = (r'(buf|buff|spin|avatar|shoulder|shield|selfshield|aura|loop|channel|haste|speed|glow|wings|charge|dr|tenacity|'
         r'weapon|rweapon|lweapon|slow|stun|root|snare|silence|mark|freeze|frozen|trail)')
NO_PLACE = (-3679, -3706)        # [m] the cells an instance carries when it has no owner place
BONE_ROOT, BONE_CHEST = P.elf('root'), P.elf('C_BUFFBONE_GLB_CHEST_LOC')
PAD = bytes.fromhex('f3f3f3f3aaaaaaaaaaaaaaaaaaaaaaaa4d4d4d4d000000001ce45433f77f00000000000000000000000000000000000000000000')
CONST = '20230000006000000000000062000000'
_cat = {}


def fnv(name):
    h = 0x811c9dc5
    for c in name.lower().encode():
        h = ((h ^ c) * 0x01000193) & 0xffffffff
    return h


def catalog(champ):
    """[{'key', 'name', 'data'}] for the champion's base skin: its resource map with each effect's definition name;
    data = the champion's own data names the key (the client plays it alone)"""
    if champ in _cat:
        return _cat[champ]
    path = os.path.join(G.OUT, 'fx', champ + '.json')
    if os.path.exists(path):
        _cat[champ] = json.load(open(path))
        return _cat[champ]
    import bin_tree as BT
    import wad
    import xxhash
    w = os.path.join(G.GAME, 'Champions', f'{champ}.wad.client')
    low = champ.lower()
    skin = f'data/characters/{low}/skins/skin0.bin'
    out = []
    d = wad.read(w, skin) if os.path.exists(w) else None
    if d is not None and d[:4] == b'PROP':
        n = struct.unpack_from('<I', d, 8)[0]
        at, linked = 12, []
        for i in range(n):
            ln = struct.unpack_from('<H', d, at)[0]
            linked.append(d[at + 2:at + 2 + ln].decode('latin-1'))
            at += 2 + ln
        number = lambda s: int(s[1:-1], 16) if s.startswith('{') else BT.fnv(s)
        vfx, resolver = {}, {}
        for f in [skin] + [x for x in linked if '_multi_' in x.lower() or '/skins/' in x.lower()]:
            h = xxhash.xxh64(f.lower().encode()).intdigest()
            if h not in wad.toc(w):
                continue
            for key, cls, v in BT.entries(w, f if f == skin else '{%016x}' % h):
                if cls == 'VfxSystemDefinitionData':
                    vfx[number(key)] = v.get('particleName') or str(v.get('particlePath', '')).split('/')[-1]
                elif cls == 'ResourceResolver' and f == skin:
                    for a, b in (v.get('resourceMap') or {}).items():
                        resolver[number(str(a))] = number(str(b))
        named = set()

        def walk(v):
            if isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
            elif isinstance(v, str) and len(v) < 80:
                h = int(v[1:-1], 16) if re.fullmatch(r'\{[0-9a-f]{8}\}', v) else BT.fnv(v)
                if h in resolver:
                    named.add(h)
        for f in (f'data/characters/{low}/{low}.bin', f'data/characters/{low}/animations/skin0.bin', skin):
            for key, cls, v in BT.entries(w, f):
                if cls != 'ResourceResolver':
                    walk(v)
        out = [{'key': k, 'name': vfx.get(v, ''), 'data': k in named} for k, v in sorted(resolver.items())]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, 'w'))
    _cat[champ] = out
    return out


def classify(champ, name):
    """an effect's definition name -> (slot 0..3 | 'p' | 'ba' | None, trigger 'cast' | 'hit' | 'held' | 'place' | None,
    lasts?)"""
    words = [w for w in re.split(r'[_\s]+', name.lower()) if w]
    if words and words[0] == champ.lower():
        words = words[1:]
    if words and (words[0] in ('base', 'steel', 'steellegion') or re.fullmatch(r'skin\d+', words[0])):
        words = words[1:]
    slot = None
    for i, w in enumerate(words[:2]):
        m = re.fullmatch(r'([qwer])\d?', w)
        if m:
            slot = SLOTS[m.group(1)]
        elif w in ('p', 'passive'):
            slot = 'p'
        elif w in ('ba', 'aa', 'attack', 'basicattack', 'crit', 'critattack'):
            slot = 'ba'
        if slot is not None:
            words = words[:i] + words[i + 1:]
            break
    if slot is None:
        return None, None, False
    words = [re.sub(r'\d+$', '', w) for w in words]
    words = [w for w in words if w]

    def has(pattern):
        return any(re.fullmatch(pattern, w) for w in words)
    lasts = has(LASTS)
    if has(NEVER):
        return slot, None, False
    if has(PLACE):
        return slot, 'place', lasts
    if has(HIT):
        return slot, 'hit', False
    if has(HELD):
        return slot, 'held', True
    if has(SELF):
        return slot, 'cast', lasts
    return slot, None, False


def side(name):
    """'enemy' / 'ally' when the effect is the version one team is shown, else None"""
    words = [re.sub(r'\d+$', '', w) for w in re.split(r'[_\s]+', name.lower())]
    if any(re.fullmatch(FOR_ENEMIES, w) for w in words):
        return 'enemy'
    if any(re.fullmatch(FOR_ALLIES, w) for w in words):
        return 'ally'
    return None


def rules(champ):
    """the champion's scripted effects by (slot, when): {(slot, when): [rule]}; a rule = {key, name, when, delay,
    where ('self' | 'unit' | 'place' | 'self place'), bone, target_bone, flags, scale, keyword, target, owner_place,
    lasts (seconds | True = as long as the spell's effect | None = ends by itself)}.
    A champion of the live recording gets what the real server did with each of its effects (fx_live.json, made by
    tools/fx_learn16.py); every other champion gets the name rules with the recording's usual way of sending."""
    global _live
    if _live is None:
        p = os.path.join(G.OUT, 'fx_live.json')
        _live = json.load(open(p)) if os.path.exists(p) else {}
    out = {}
    learnt = _live.get(champ)
    if learnt:
        for key, e in learnt.items():
            r = dict(e, key=int(key, 16))
            out.setdefault((r['slot'], r['when']), []).append(r)
        return out
    for e in catalog(champ):
        if e['data'] or not e['name']:
            continue
        slot, when, lasts = classify(champ, e['name'])
        if when is None or not base_skin(champ, e['name']):
            continue
        r = dict(USUAL[when], key=e['key'], name=e['name'], when=when, delay=0.0, scale=1.0, lasts=True if lasts else None,
                 side=side(e['name']))
        out.setdefault((slot, when), []).append(r)
    return out


def base_skin(champ, name):
    """the effect belongs to the base skin (not another skin's that the base resource map also lists)"""
    words = name.lower().split('_')
    return len(words) > 1 and words[0] == champ.lower() and words[1] == 'base'


_live = None
# how the real server usually sends an effect of each kind [m: tools/fx_learn16.py's last table, 154 effects]
USUAL = {
    'cast': dict(where='self', bone=0, target_bone=0, flags=0x20, keyword=False, target=True, owner_place=True),
    'hit': dict(where='unit', bone=0, target_bone=P.elf('C_BUFFBONE_GLB_CHEST_LOC'), flags=0x20, keyword=False, target=False, owner_place=True),
    'held': dict(where='unit', bone=0, target_bone=0, flags=0x20, keyword=False, target=False, owner_place=True),
    'place': dict(where='place', bone=0, target_bone=0, flags=0x20, keyword=True, target=False, owner_place=False),
}
DURATIONS = ('BuffDuration', 'Duration', 'ShieldDuration', 'SpinDuration', 'MoveSpeedDuration', 'HasteDuration',
             'TotalDuration', 'ZoneDuration', 'ChannelDuration', 'StealthDuration')


class Effects:
    """shows the scripted effects of what the spell engine does (spells.py calls on_cast / on_hit / on_held)"""
    def __init__(self, game):
        self.g = game
        self.until = []              # (time, effect net id): effects that last, to take away then
        self._rules = {}
        self._wanted = []
        self._worker = None
        self.recent = {}             # (caster, key, bound) -> (time, effect net id): the effects made this frame
        self.riding = {}             # (unit, buff slot) -> [effect net ids that end with that buff]
        self.key_of = {}             # effect net id -> its key as the tables name it

    def rules(self, hero):
        """the champion's rules; read on a thread of its own the first time (a champion whose catalog is not on disk
        yet costs seconds of bin parsing, which must not stop the match): until then it has no effects"""
        r = self._rules.get(hero.name)
        if r is None:
            self.prepare([hero.name])
            return self._rules.get(hero.name) or {}
        return r

    def prepare(self, names, wait=False):
        import threading
        self._wanted += [n for n in names if n not in self._rules and n not in self._wanted]

        def work():
            while self._wanted:
                name = self._wanted[0]
                try:
                    r = rules(name)
                except Exception as e:                   # a champion whose skin data we cannot read: no effects
                    self.g.log(f'effects of {name}: {e!r}')
                    r = {}
                self._rules[name] = r
                self._wanted.pop(0)
        if wait:
            work()
        elif self._wanted and (self._worker is None or not self._worker.is_alive()):
            self._worker = threading.Thread(target=work, daemon=True)
            self._worker.start()

    # ------------------------------------------------------------------ packets
    def create(self, key, caster, bound=None, target=None, place=None, owner_place=True, scale=1.0, flags=0x20,
               bone=0, target_bone=0, keyword=False, tag=None, old_name=0):
        """one effect -> its net id (queued as a packet 10); caster None = nobody's (a shared effect);
        old_name = the ELF hash of an old particle file path instead of a key (key 0)"""
        g, pk = self.g, self.g.pk
        fx = g.new_net()
        place = place or (bound.pos if bound is not None else caster.pos)
        cx, cz = P.cell(place)
        height = pk.y(place)
        caster_net = caster.net if caster is not None else 0
        if owner_place and caster is not None:
            ox, oz = P.cell(caster.pos)
            oh = pk.y(caster.pos)
        else:
            (ox, oz), oh = NO_PLACE, 0.0

        def i16(n):
            return struct.pack('<h', max(-32768, min(32767, n))).hex()
        inst = {'+0x8': P.u32(0), '+0xc': '5151', '+0xe': i16(ox), '+0x10': i16(oz), '+0x14': P.f32(scale),
                '+0x18': P.u32(caster_net), '+0x1c': P.u32(0), '+0x20': i16(cz), '+0x24': P.u32(0), '+0x28': P.u32(0),
                '+0x2c': P.u32(0), '+0x30': P.f32(height), '+0x34': P.u32(bound.net if bound is not None else 0),
                '+0x38': P.u32(fx), '+0x3c': P.u32(caster_net if keyword else 0), '+0x40': '00', '+0x41': '00',
                '+0x44': P.u32(0), '+0x48': P.f32(1.0), '+0x4c': P.f32(height), '+0x50': P.vec3(0.0, 0.0, 0.0),
                '+0x5c': i16(cz), '+0x60': P.u32(0), '+0x70': PAD.hex(), '+0xa8': P.f32(oh), '+0xac': i16(cx),
                '+0xb0': P.u32(0), '+0xb4': i16(cx), '+0xb8': P.u32(target.net if target is not None else 0)}
        if tag is None:                               # whose resource map the key is looked up in
            tag = G.package_hash(caster.name) if caster is not None else G.PACKAGE_GLOBAL
        group = {'+0x8': P.u32(old_name), '+0xc': P.u32(bone), '+0x10': [inst], '+0x20': P.u32(key), '+0x28': [P.u32(tag)] * 3,
                 '+0x38': P.u32(target_bone), '+0x40': CONST, '+0x50': struct.pack('<H', flags).hex()}
        g.q.append((1, 10, 0, pk.enc(10, {'+0x10': [group]})))
        self.recent[(caster_net, key or old_name, bound.net if bound is not None else 0)] = (g.t, fx)
        self.key_of[fx] = (P.u32(key) if key else 'old:' + P.u32(old_name))
        return fx

    def remove(self, fx):
        """584, as many times as the real server sends it for this effect [m: tools/fx_repeat16.py - Jinx's minigun casts
        every frame for 0.6 s, others twice in a frame]; offsets past a second are left out [a]"""
        g = self.g
        body = g.pk.enc(584, {'+0x10': '00', '+0x14': P.u32(fx)})
        for off in fx_repeat().get(self.key_of.pop(fx, None), (0,)):
            if off == 0:
                g.q.append((1, 584, 0, body))
            elif off <= 30:
                g.at(g.t + off * FRAME, lambda t, b=body: g.q.append((1, 584, 0, b)))

    def shared(self, name, caster, bound=None, place=None, lasting=None, target_bone=0, scale=1.0, target=False,
               owner_place=None, old=None):
        """an effect that is nobody's own. The real server names it in one of two ways [m]:
          - by key = the FNV of its particle name (101 keys of the recording are names of Global.wad's Shared / Items /
            Perks particles: Global_SS_Ignite, 3074_AoE ...), with the caster's package - or the global one and no
            caster (Global_Haste);
          - with key 0 and the ELF hash of an old file path of the particle (71 of the recording's effects):
            old='shared' -> "data/shared/particles/<name>.troy" (LOC_Stun, Global_Slow), old='particles' ->
            "data/particles/<name>.troy" (TeleportHome, the turrets' hit dust)."""
        if not self.seen(caster, bound):
            return None
        key, old_name = fnv(name), 0
        if old:
            key = 0
            old_name = P.elf(('data/shared/particles/' if old == 'shared' else 'data/particles/') + name + '.troy')
        fx = self.create(key, caster, bound=bound, place=place, target_bone=target_bone, scale=scale, old_name=old_name,
                         target=bound if target else None,
                         owner_place=(caster is not None and bound is not None) if owner_place is None else owner_place)
        if lasting:
            self.until.append((self.g.t + lasting, fx))
        return fx

    def seen(self, *units):
        v = self.g.vision
        return v is None or any(u is not None and not v.hidden(u) for u in units)

    def show(self, r, hero, unit=None, aim=None, lasting=None):
        """one rule's effect now: on the caster, on a unit, or at a place"""
        where = r['where']
        if r.get('side') and (r['side'] == 'ally') != (hero.team == self.g.player_team):
            return                                       # the other team's version of this effect
        if where == 'unit':
            if unit is None or not unit.alive:
                return
            bound, place, target = unit, None, None
        elif where == 'self':
            bound, place, target = hero, None, hero if r['target'] else None
        elif where == 'place':
            bound, place, target = None, aim or hero.pos, None
        else:                                            # at the caster's own place, bound to no unit
            bound, place, target = None, hero.pos, None
        fx = self.create(r['key'], hero, bound=bound, target=target, place=place, owner_place=r['owner_place'],
                         scale=r.get('scale', 1.0), flags=r['flags'], bone=r['bone'], target_bone=r['target_bone'],
                         keyword=r['keyword'])
        lasts = r.get('lasts')
        if lasts is True:
            lasts = lasting
        if lasts:
            self.until.append((self.g.t + min(float(lasts), 30.0), fx))

    # ------------------------------------------------------------------ what the spell engine reports
    def on_cast(self, hero, slot, inf, rank, aim, tgt=None):
        """a spell's cast begins: its 'cast' effects (and the ones the real server shows a moment 'after')"""
        if not self.seen(hero):
            return
        rules_ = self.rules(hero)
        lasting = inf.data_value(DURATIONS, rank) or max(inf.total_time, 2.0)
        for r in rules_.get((slot, 'cast'), ()):
            self.show(r, hero, tgt, aim, lasting)
        for r in rules_.get((slot, 'place'), ()):
            self.show(r, hero, tgt, aim, lasting)
        for r in rules_.get((slot, 'after'), ()):
            self.g.at(self.g.t + r['delay'], lambda t2, r=r: hero.alive and self.seen(hero) and self.show(r, hero, tgt, aim, lasting))

    def on_hit(self, hero, slot, tgt):
        """the spell hits a unit: its 'hit' effects on that unit"""
        if not self.seen(hero, tgt):
            return
        for r in self.rules(hero).get((slot, 'hit'), ()):
            self.show(r, hero, tgt)

    def on_held(self, hero, slot, tgt, duration):
        """the spell slows / stuns / roots a unit: its 'held' effects on that unit until it ends"""
        if not self.seen(hero, tgt):
            return
        for r in self.rules(hero).get((slot, 'held'), ()):
            self.show(r, hero, tgt, lasting=duration)

    def on_attack_hit(self, hero, tgt):
        if not self.seen(hero, tgt) or hero.name in attack_fx():
            return                                       # a champion with measured attack effects: on_attack_start
        for r in self.rules(hero).get(('ba', 'hit'), ()):
            self.show(r, hero, tgt)

    def on_attack_start(self, hero, tgt):
        """the effects the real server makes at a champion's basic attack [m: tools/attack_fx16.py, the replays]: a key
        is played when at least half of the real attacks at this distance (100-unit bins) had it, after its measured
        delay, bound as it was, and taken away (584) after its measured life when the real ones were"""
        champ = attack_fx().get(hero.name)
        if champ is None:
            return
        g = self.g
        d = dist(hero.pos, tgt.pos)
        b = str(int(d // 100))
        # keys that are variants of one effect (the same binding, bones, flags, package: Jinx's minigun Short /
        # Medium / Long / PointBlank by distance) form a family: played when the family had at least half of the
        # attacks at this distance, as its most frequent member there
        fam = {}
        for key, k in champ['fx'].items():
            n, w = (k['bins'].get(b) or [0, 0])
            share = w / n if n >= 4 else k['seen'] / max(1, champ['attacks'])
            f = fam.setdefault((k['bound'], k.get('target_bone'), k.get('flags'), k.get('tag')), [0.0, None, -1.0])
            f[0] += share
            if share > f[2]:
                f[1], f[2] = key, share
        for total, key, best in fam.values():
            if total < 0.5 or key is None:
                continue
            k = champ['fx'][key]
            g.at(g.t + max(0.0, k['delay']), lambda t2, key=key, k=k: self.attack_effect(hero, tgt, key, k))

    def attack_effect(self, hero, tgt, key, k):
        if not hero.alive or not self.seen(hero, tgt):
            return
        bound = hero if k['bound'] == 'caster' else tgt if k['bound'] == 'target' and tgt.alive else None
        old = 0
        if key.startswith('old:'):
            old, key_n = int.from_bytes(bytes.fromhex(key[4:]), 'little'), 0
        else:
            key_n = int.from_bytes(bytes.fromhex(key), 'little')
        u = lambda h: int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0
        fx = self.create(key_n, hero, bound=bound, target=tgt if k.get('target') else None,
                         place=None if bound is not None else tgt.pos, scale=struct.unpack('<f', bytes.fromhex(k['scale']))[0]
                         if isinstance(k.get('scale'), str) else 1.0, flags=u(k.get('flags')) or 0x20,
                         bone=u(k.get('bone')), target_bone=u(k.get('target_bone')), keyword=bool(k.get('keyword')),
                         tag=u(k.get('tag')) or None, old_name=old)
        if k.get('lasts'):
            self.until.append((self.g.t + k['lasts'], fx))

    # ------------------------------------------------------------------ the effects that ride with buffs
    def on_buff_add(self, tgt_net, caster_net, slot, name_hash):
        """a buff is given: the effects the real server makes with it [m: tools/buff_fx16.py], in the frame or the next;
        the ones that end with it are kept to take away at its end (a buff given again in its slot ends them too)"""
        self.on_buff_remove(tgt_net, slot)
        rules_ = buff_fx().get(P.u32(name_hash))
        if not rules_:
            return
        g = self.g
        tgt, caster = g.units.get(tgt_net), g.units.get(caster_net)
        if tgt is None or caster is None:
            return
        for r in rules_['fx']:
            if r['delay']:
                g.at(g.t + r['delay'] * FRAME, lambda t, r=r: self.buff_effect(tgt, caster, slot, r))
            else:
                self.buff_effect(tgt, caster, slot, r)

    def buff_effect(self, tgt, caster, slot, r):
        if not tgt.alive or not self.seen(caster, tgt):
            return
        key = r['key']
        old = 0
        if key.startswith('old:'):
            old, key_n = int.from_bytes(bytes.fromhex(key[4:]), 'little'), 0
        else:
            key_n = int.from_bytes(bytes.fromhex(key), 'little')
        bound = tgt if r['bound'] == 'target' else caster if r['bound'] == 'caster' else None
        made = self.recent.get((caster.net, key_n or old, bound.net if bound is not None else 0))
        if made is not None and abs(made[0] - self.g.t) < 1e-6:
            fx = made[1]                                 # made this frame already (a cast's effect, another buff's)
            self.until = [(w, f) for w, f in self.until if f != fx] if r['with_buff'] >= 0.5 else self.until
        else:
            u = lambda h: int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0
            fx = self.create(key_n, caster, bound=bound, target=tgt if r.get('target') else None,
                             place=None if bound is not None else tgt.pos,
                             scale=struct.unpack('<f', bytes.fromhex(r['scale']))[0] if isinstance(r.get('scale'), str) else 1.0,
                             flags=u(r.get('flags')) or 0x20, bone=u(r.get('bone')), target_bone=u(r.get('target_bone')),
                             keyword=bool(r.get('keyword')), tag=u(r.get('tag')) or None, old_name=old)
            if r.get('lasts') and r['with_buff'] < 0.5:
                self.until.append((self.g.t + min(30.0, r['lasts']), fx))
        if r['with_buff'] >= 0.5:
            self.riding.setdefault((tgt.net, slot), []).append(fx)

    def on_buff_remove(self, tgt_net, slot):
        for fx in self.riding.pop((tgt_net, slot), ()):
            self.remove(fx)

    def tick(self, t, dt):
        if self.recent:
            self.recent = {k: v for k, v in self.recent.items() if t - v[0] < 0.1}
        if self.until:
            keep = []
            for when, fx in self.until:
                if t >= when:
                    self.remove(fx)
                else:
                    keep.append((when, fx))
            self.until = keep


_attack_fx = None
_buff_fx = None
_fx_repeat = None


def fx_repeat():
    global _fx_repeat
    if _fx_repeat is None:
        try:
            _fx_repeat = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'fx_repeat16.json')))
        except Exception:
            _fx_repeat = {}
    return _fx_repeat


def buff_fx():
    global _buff_fx
    if _buff_fx is None:
        if os.environ.get('BA_NO_BUFF_FX'):        # measuring without them
            _buff_fx = {}
            return _buff_fx
        try:
            _buff_fx = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'buff_fx16.json')))
        except Exception:
            _buff_fx = {}
    return _buff_fx




def attack_fx():
    global _attack_fx
    if _attack_fx is None:
        try:
            _attack_fx = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'attack_fx16.json')))
        except Exception:
            _attack_fx = {}
    return _attack_fx


def setup(game, session=None):
    game.fx = Effects(game)
    game.pk.buff_hooks.append(game.fx)
    game.systems.append(game.fx.tick)
    # the roster's champions: at once when their catalogs are on disk (tools/fx_catalog16.py), else in the background
    names = sorted({h.name for h in game.heroes})
    on_disk = all(os.path.exists(os.path.join(G.OUT, 'fx', n + '.json')) for n in names)
    game.fx.prepare(names, wait=on_disk)
