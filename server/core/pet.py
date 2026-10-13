"""The jungle item's companion (the pet): its attacks on monsters, as Riot's server deals them [m: 6 replays, 4,500 hits]:
  - it attacks while its jungler fights monsters: a 1 s script timer (hits 1.069 / 1.069 / 1.069 / 0.802 s apart)
  - every tick hits ALL the monsters of the camp at once (1, 2, 3 or 6 hits in the same frame)
  - the ticks alternate their name: DogSlashAttack, DogSlashAttackSmall (two animations, as often each)
  - true damage by the jungler's level (the medians): 21.8, 29.0, 37.0, 47.6, 56.1, 67.4, 78.5, 88.7 ...
The jungle item's burn on monsters [m: 10 replays, 2,000 ticks]: every hit of the jungler (or its pet) on a monster
puts Burning on it (435 type 13, 3 s; a new hit renews it: 282 3 s), a tick at once and then on a 1 s script timer while
it lasts: true damage max(5, the jungler's level).
A jungler = a champion in the jungle position (the role quest's) or a bot jungler.
The jungle item's other effects [wiki: Gustwalker Hatchling / Mosstomper Seedling / Scorchclaw Pup, V26.x]: the jungler
takes 50 % damage from non-epic monsters and deals them 10 % more (not true damage); while the pet attacks, the jungler
heals 6 - 36 (by level) a second; killing a large monster heals up to 90 - 250 (by the champions' average level), 1.25 %
of that per 1 % missing health [m: replay 4012247271, 23 kills: heal = that x min(1, 1.25 x missing) within the
regeneration's noise]; the treat flies to the jungler as a missile (78 slot 0x34 DoggySnaxMissile at the kill) and
heals on arrival [m: 0.90 - 0.97 s after the kill, the 699 of the heal 0.90 s after]; 80 bonus experience (150 more for
the first).
"""
import struct

from . import packets as P
from .units import dist, ORDER

DAMAGE = [21.84, 28.99, 37.03, 47.58, 56.13, 67.43, 78.47, 88.71]
NAMES = (P.elf('DogSlashAttack'), P.elf('DogSlashAttackSmall'))
CAMP_RADIUS = 600.0              # [a] the monsters of one camp around the one being fought
FIGHT = 2.5                      # [a] the pet keeps attacking this long after the jungler's last hit on a monster


EPIC = ('SRU_Dragon', 'SRU_Baron', 'SRU_RiftHerald', 'SRU_Horde', 'SRU_Atakhan', 'SRU_ElderDragon')
LARGE = ('SRU_Blue', 'SRU_Red', 'SRU_Gromp', 'SRU_Murkwolf', 'SRU_Razorbeak', 'SRU_Krug', 'Sru_Crab')
SNAX_DELAY = 0.93                # [m] the treat's flight: the heal 0.90 - 0.97 s after the kill
SNAX_SLOT = 0x34


def is_epic(u):
    return any(u.name.startswith(e) for e in EPIC)


def is_large(u):
    return u.name in LARGE or (u.name.startswith('SRU_Dragon') or u.name.startswith('SRU_Baron') or
                               u.name.startswith('SRU_RiftHerald') or u.name.startswith('SRU_Atakhan'))


def by_level(lo, hi, level):
    """[wiki] a value growing evenly from level 1 to level 18 [a: linear]"""
    return lo + (hi - lo) * (min(18.0, max(1.0, level)) - 1.0) / 17.0


BURNING = P.elf('Burning')
# the camps' crests [m: every Red / Blue kill of 4 replays: the killer's 435 type 2, 120 s - BlessingoftheLizardElder,
# 1dcf7b04]; Crest of Cinders [wiki V26.x]: on-hit slow 10 / 15 / 25 % (melee) or 5 / 7.5 / 12.5 % (ranged) by level
# for 3 s [m: buff e76c750d, type 11, 3 s; renewed by 282] and the burn (Burning above, measured); it goes to the
# champion that kills its holder
RED_CREST, BLUE_CREST, CINDER_SLOW = P.elf('BlessingoftheLizardElder'), 0x047bcf1d, 0x0d756ce7
CREST_TIME = 120.0
# the jungle item's treats [m: replays - at the purchase, before its 63: buff b25acf0e (type 27, 25000 s, the quests'
# package) with its counter (430) and the item slot's charges (1126 {count, slot}) = 35 treats to go; each large monster
# killed feeds one: 1126 (twice) and the counter one lower]
JUNGLE_ITEMS = (1101, 1102, 1103)
TREATS, TREAT_BUFF = 35, 0x0ecf5ab2
BURN_TIME = 3.0


def damage(level):
    if level <= len(DAMAGE):
        return DAMAGE[max(1, level) - 1]
    return DAMAGE[-1] + 11.0 * (level - len(DAMAGE))      # [a] the measured steps go on (~11 a level)


class Pets:
    def __init__(self, game):
        self.g = game
        self.state = {}                  # hero net -> {'last': time of its last hit on a monster, 'at': monster, 'n': tick}

    def is_jungler(self, h):
        return getattr(h, 'jungler', False) or getattr(h, 'role', None) == 'JUNGLE'

    def burn(self, src, tgt):
        """Burning on a monster the jungler or its pet hit"""
        g, sp = self.g, self.g.spells
        if sp is None or not tgt.alive:
            return
        if not hasattr(tgt, 'buff_list'):
            tgt.buff_list = {}
        key = ('burning', src.net)
        b = tgt.buff_list.get(key)
        if b is not None:
            b['until'] = g.t + BURN_TIME
            from .renewals import handles
            if b.get('known', True) and not handles(BURNING):
                g.q += g.pk.buff_count(tgt.net, b['slot'], src.net, BURN_TIME, 1)
            sp.buffs.append([b['until'], tgt, key])
            return
        slot = sp.buff_slot(tgt)
        known = g.vision is None or not g.vision.hidden(tgt)
        b = tgt.buff_list[key] = {'slot': slot, 'until': g.t + BURN_TIME, 'hash': BURNING, 'undo': None, 'known': known,
                                  'args': (src.net, slot, 13, BURNING, 0)}
        if known:
            g.q += g.pk.buff_add(tgt.net, src.net, slot, 13, BURNING, BURN_TIME)
        sp.buffs.append([b['until'], tgt, key])

        def tick(t, b=b):
            if tgt.buff_list.get(key) is b and tgt.alive:
                g.deal(src, tgt, max(5.0, float(src.level)), P.TRUE, basic=False, source=P.SRC_PERIODIC, spell_hash=BURNING)
        tick(g.t)
        g.script_timer(1.0, tick, first=False, alive=lambda b=b: tgt.buff_list.get(key) is b and tgt.alive)

    def on_hit(self, src, tgt, spell_hash=0):
        """a champion (or its pet) damaged a monster: the pet joins the fight, the monster burns"""
        if not (src.is_hero and tgt.kind == 'monster' and self.is_jungler(src)):
            return
        # Burning is not the jungle item's: it is Crest of Cinders' (on_attack_hit) [m 10-13: the first Burning and slow
        # of each jungler follow its Red kill]
        if spell_hash in NAMES or spell_hash == BURNING:
            return
        st = self.state.get(src.net)
        if st is None:
            st = self.state[src.net] = {'n': 0, 'running': False}
        st['last'], st['at'] = self.g.t, tgt
        if not st['running']:
            st['running'] = True
            self.g.script_timer(1.0, lambda t, h=src: self.tick(h), alive=lambda h=src: self.state[h.net]['running'])

    def crest(self, h, which, duration=CREST_TIME):
        """a camp's crest on a champion (the killer of Red / Blue, or of a crest's holder)"""
        g, sp = self.g, self.g.spells
        if sp is None or h is None or not h.is_hero:
            return
        name_hash = RED_CREST if which == 'red' else BLUE_CREST
        if not hasattr(h, 'buff_list'):
            h.buff_list = {}
        key = ('crest', which)
        old = h.buff_list.get(key)
        slot = old['slot'] if old else sp.buff_slot(h)
        h.buff_list[key] = {'slot': slot, 'until': g.t + duration, 'hash': name_hash, 'undo': None, 'known': True,
                            'args': (h.net, slot, 2, name_hash, 0)}
        g.q += g.pk.buff_add(h.net, h.net, slot, 2, name_hash, duration)
        sp.buffs.append([g.t + duration, h, key])
        setattr(h, which + '_crest_until', g.t + duration)

    def bought(self, h, item_id, slot):
        g = self.g
        if item_id not in JUNGLE_ITEMS or getattr(h, 'treats', None) is not None or g.spells is None:
            return
        from .tooltips import QUEST_PACKAGE
        h.treats = TREATS
        if not hasattr(h, 'buff_list'):
            h.buff_list = {}
        bslot = g.spells.buff_slot(h)
        h.buff_list[('pet', 'treats')] = {'slot': bslot, 'until': g.t + 3600.0 * 10, 'hash': TREAT_BUFF, 'undo': None,
                                          'known': True, 'args': (h.net, bslot, 27, TREAT_BUFF, QUEST_PACKAGE)}
        g.q += g.pk.buff_add(h.net, h.net, bslot, 27, TREAT_BUFF, 25000.0, package=QUEST_PACKAGE)
        g.q += g.pk.buff_counter(h.net, bslot, TREAT_BUFF, TREATS)
        self.charges(h, slot)

    def charges(self, h, slot, times=1):
        g = self.g
        for _ in range(times):
            g.q.append((1, 1126, h.net, g.pk.enc(1126, {'+0x10': P.u32(h.treats)[:4], '+0x12': f'{slot:02x}'})))

    def feed(self, h):
        if getattr(h, 'treats', None) is None or h.treats <= 0:
            return
        h.treats -= 1
        slot = next((i for i, it in enumerate(h.inventory) if it in JUNGLE_ITEMS), None)
        if slot is not None:
            self.charges(h, slot, 2)
        b = h.buff_list.get(('pet', 'treats'))
        if b is not None:
            self.g.q += self.g.pk.buff_counter(h.net, b['slot'], TREAT_BUFF, h.treats)

    def holder_killed(self, victim, killer):
        """a crest's holder slain by an enemy champion: the crest goes to the killer, with its time left"""
        for which in ('red', 'blue'):
            left = getattr(victim, which + '_crest_until', 0.0) - self.g.t
            if left > 0 and killer is not None and killer.is_hero and killer.team != victim.team:
                setattr(victim, which + '_crest_until', 0.0)
                self.crest(killer, which, left)

    def on_attack_hit(self, src, tgt):
        """a basic attack landed: Crest of Cinders' burn and slow"""
        g = self.g
        if not (src.is_hero and g.t < getattr(src, 'red_crest_until', 0.0) and tgt.alive and not tgt.is_structure):
            return
        self.burn(src, tgt)
        melee = src.base.get('range', 500.0) <= 300.0
        pct = ([0.10, 0.15, 0.25] if melee else [0.05, 0.075, 0.125])[0 if src.level < 6 else 1 if src.level < 11 else 2]
        if not hasattr(tgt, 'buff_list'):
            tgt.buff_list = {}
        key = ('cinder_slow', src.net)
        b = tgt.buff_list.get(key)
        if b is not None and g.t < b['until']:
            b['until'] = g.t + 3.0
            from .renewals import handles
            if not handles(CINDER_SLOW):
                g.q += g.pk.buff_count(tgt.net, b['slot'], src.net, 3.0, 1)
        else:
            slot = g.spells.buff_slot(tgt)
            b = tgt.buff_list[key] = {'slot': slot, 'until': g.t + 3.0, 'hash': CINDER_SLOW, 'undo': None, 'known': True,
                                      'args': (src.net, slot, 11, CINDER_SLOW, 0)}
            g.q += g.pk.buff_add(tgt.net, src.net, slot, 11, CINDER_SLOW, 3.0)
        g.spells.buffs.append([b['until'], tgt, key])
        slows = tgt.__dict__.setdefault('slows', {})
        slows['CrestOfCinders'] = pct
        g.spells.respeed(tgt)
        until = b['until']

        def off(t, tgt=tgt, until=until, key=key):
            cur = tgt.buff_list.get(key)
            if cur is None or cur['until'] <= until + 1e-6:
                tgt.slows.pop('CrestOfCinders', None)
                g.spells.respeed(tgt)
        g.at(until + 0.01, off)

    def modify(self, src, tgt, dealt, dtype):
        """[wiki] the jungle item: half the damage of non-epic monsters, 10 % more on them (not true damage)"""
        if src is None:
            return dealt
        if tgt.is_hero and src.kind == 'monster' and self.is_jungler(tgt) and not is_epic(src):
            return dealt * 0.5
        if src.is_hero and tgt.kind == 'monster' and dtype != P.TRUE and self.is_jungler(src) and not is_epic(tgt):
            return dealt * 1.1
        return dealt

    def on_kill(self, h, m):
        """a large monster killed by a jungler: the treat flies to it and heals it on arrival; bonus experience"""
        g = self.g
        if h is not None and h.is_hero and m.name in ('SRU_Red', 'SRU_Blue'):
            self.crest(h, 'red' if m.name == 'SRU_Red' else 'blue')
        if not (h is not None and h.is_hero and self.is_jungler(h) and is_large(m)):
            return
        self.feed(h)
        g.q += g.pk.spell_in_slot(h.net, SNAX_SLOT, 'DoggySnaxMissile')
        first = not getattr(h, 'had_large_kill', False)
        h.had_large_kill = True
        h.add_xp(80.0 + (150.0 if first else 0.0))

        def land(t, h=h):
            if not h.alive:
                return
            avg = sum(x.level for x in g.heroes) / max(1, len(g.heroes))
            missing = 1.0 - h.hp / max(1.0, h.max_hp)
            h.heal(by_level(90.0, 250.0, avg) * min(1.0, 1.25 * missing))
        g.at(g.t + SNAX_DELAY, land)

    def tick(self, h):
        g, st = self.g, self.state[h.net]
        if not h.alive or g.t - st['last'] > FIGHT:
            st['running'] = False
            return
        center = st['at'].pos
        camp = [m for m in g.monsters if m.alive and dist(m.pos, center) <= CAMP_RADIUS]
        if not camp:
            st['running'] = False
            return
        name = NAMES[st['n'] % 2]
        st['n'] += 1
        amount = by_level(6.0, 36.0, h.level)
        h.heal(amount)                                   # [wiki] the jungler heals while its pet attacks
        # [m: every pet tick of 4 replays] its 699 heal event, before the hits: the tick's attack name as the cause;
        # the 12 bytes after the amount are the team's own (order 31440300 01a99015, chaos 33440300 02aa9015) + the jungler
        mid = bytes.fromhex('3144030001a99015' if h.team == ORDER else '3344030002aa9015') + struct.pack('<I', h.net)
        g.q += g.pk.heal_event(h.net, h.net, amount, cause=name, mid=mid, tail=bytes.fromhex('ffffffff01070000'))
        for m in camp:
            g.deal(h, m, damage(h.level), P.TRUE, basic=False, source=P.SRC_DIRECT, spell_hash=name)


def setup(game, session=None):
    game.pets = Pets(game)
