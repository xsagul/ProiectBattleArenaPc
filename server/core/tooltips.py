"""The numbers behind tooltips: packet 1052 [m: the live recording - 1993 packets in 900 s; the replays - the most
frequent packet of all]. Riot's server tells every client, for every champion, the variables its item, rune, spell
and passive tooltips show: a list of entries {kind, champion, id, values [(index, float)]}; a series' first entry
carries all 16 values, later ones only those that changed.

  kind 3  an item slot (id = the slot)          kind 5  a rune (id = the perk's id)
  kind 1  a spell slot                          kind 2  the passive (id 63)

Each series is the item's / rune's own script on Riot's server; written here are the ones whose rule was measured:
  (3, 8)  the role quest [m: 12 replays, every laner]: values [0, goal, a, b, 12.5, 30, 10] by the champion's
          position - top 1200 / 0.5 / 15, mid 1350 / 0.5 / 25, bottom 1350 / 0.75 / 15 (jungle [0, 35], support
          [0, 400]: other quests, not played yet). Value 0 grows from 65 s on by 1.5 a second of the quest's own
          clock and by 4 a for every minion the champion kills (2 top / mid, 3 bottom; kills before 65 s count).
          The clock is a script timer of 1 s run on updates every 0.2673 s (QUEST_GRID): it fires on the update
          where its time reached 1 s, the rest carried, so the steps are 1.069, 1.069, (1.069,) 0.802 s - first at
          66.28-66.31 s in all twelve replays. The position's quest buff (435 type 1 at 0 s, 25000 s) shows int(value 0)
          as its counter (430): told on every firing and at once at a kill; the kill's 1052 waits for the next update.
  (3, 6)  the trinket [m]: [0, 0, 90, 210, 2, 3]; values 2 and 3 are the ward's recharge times at the champions'
          average level L: 90 + 30 (L - 1) / 17 and 210 - 120 (L - 1) / 17, told again whenever anyone gains a level.
Runes (kind 5), spells and passives: not yet - each is a counter of its own (Overgrowth 8451: minions that died
near, Press the Attack 8005: damage dealt ...).
"""
from . import packets as P

QUEST_START, QUEST_RATE = 65.0, 1.5
QUEST_GRID = 0.26729             # [m] 553 firings over 533 s of one replay, 1994 updates
QUEST_FIRST = 66.29              # [m] the first firing (66.28 - 66.31)
QUEST_CARRY = 0.09               # [m] the timer's carry at the first firing: the 4, 4, 3 updates that follow
QUEST_PACKAGE = 0x451571c2       # [m] the quest buffs' package hash
# position -> (the quest buff's name hash, the series' first values) [m: the replays' 435 at 0 s and 1052]
QUESTS = {'TOP': (0x05ae24f4, [0.0, 1200.0, 0.5, 15.0, 12.5, 30.0, 10.0]),
          'MIDDLE': (0x09ae0264, [0.0, 1350.0, 0.5, 25.0, 12.5, 30.0, 10.0]),
          'BOTTOM': (0x09ae1af4, [0.0, 1350.0, 0.75, 15.0, 12.5, 30.0, 10.0]),
          'JUNGLE': (None, [0.0, 35.0]),
          'UTILITY': (None, [0.0, 400.0])}
# the support's quest [m: 12 replays, 24 supports]: its value (gold towards 400) grows by 0.75 every 2.5 s from 65.5 s
# (first counter 1 at 67.9 - 68.2 s); two buffs show int(value) - SUP_TOLD at once, SUP_SHOWN one update later with
# the 1052. Its charges: SUP_CHARGES counts them (+1 every 20.05 s from 65.75 s, at most 3); SUP_TIMER is the charge
# timer, renewed (262 + 435 for 20 s, 25000 s when full) whenever a charge comes, counting the same number.
SUP_TOLD, SUP_SHOWN, SUP_CHARGES, SUP_TIMER = 0x05dd9599, 0x0f9e0ca4, 0x0232ec53, 0x084e0759
SUP_START, SUP_PERIOD, SUP_GOLD = 65.5, 2.5, 0.75
CHARGE_START, CHARGE_PERIOD, CHARGE_MAX = 65.75, 20.05, 3
# [m: the live recording and every replay, the same values] six units of the start state (0x400000b9 - be, made in
# its part 1) tell their facing (1201) every four updates of the scripts' clock (4 x QUEST_GRID = 1.0692 s) from 1.335 s
STATIC_FACING = {0x400000b9: 'e75d7f3fdf9b22bd2e976d3d', 0x400000ba: '21df923ece016fbd24c974bf',
                 0x400000bb: 'fce5273f0c0192bb843f413f', 0x400000bc: '7c3233bf332d14bb88d236bf',
                 0x400000bd: '4a9e38bcf67793bc38f17f3f', 0x400000be: '3bc07fbfafad92bcdb1525bd'}
STATIC_FIRST = 1.335
# Legend: Alacrity's progress [m: the replays' 9104 series against the deaths]: the large monsters give 25, the epic
# ones (dragons, Voidgrubs ...) a stack at once; the small ones of a camp nothing
LARGE_MONSTERS = ('SRU_Krug', 'SRU_Razorbeak', 'SRU_Gromp', 'SRU_Murkwolf', 'SRU_Red', 'SRU_Blue', 'Sru_Crab')
EPIC_MONSTERS = ('Dragon', 'dragon', 'Baron', 'Herald', 'Horde', 'Atakhan')
ALACRITY_MAX = 10
# 264 [m: the replays (a spectator: all ten) and the live recording (a player: its own, the others only their first 0)]:
# a player's role quest progress = value / goal: +0x14 1, +0x15 the player's index, +0x18 the position (0 top,
# 1 jungle, 2 mid, 3 bottom, 4 support), +0x10 the fraction; told whenever the value changes, at the 430's moment
ROLE_ID = {'TOP': 0, 'JUNGLE': 1, 'MIDDLE': 2, 'BOTTOM': 3, 'UTILITY': 4}


class Tooltips:
    def __init__(self, game):
        self.g = game
        self.series = {}                 # (kind, id, hero net) -> [16 floats]
        self.dirty = {}                  # the same key -> set of indices (None: all of it, a first entry)
        self.quest = {}                  # hero net -> [value 0, the buff's slot, the counter told]
        # the global scripts' clock, in frames (an update every 8 frames whatever a frame lasted): the quest's first
        # firing and the static facings both fall on it [m: frames 1984 and 40 of 33.41 ms]
        from .units import FRAME
        first = int(round(QUEST_FIRST / FRAME))
        self.grid_frame = first % 8                      # the next update of the quest clock (a frame)
        self.last_update = None
        self.static_frame = int(round(STATIC_FIRST / FRAME))
        self.clock = None                # the quest timer's carried time (None: before its first firing)
        self.fired = None
        self.level_sum = None
        self.trinket_sent = False
        self.quests_made = False
        self.support = {}                # hero net -> {'value', 'charges', 'slots': {hash: slot}, 'told': {hash: n}}
        self.sup_next, self.charge_next = SUP_START, CHARGE_START
        self.later = []                  # [(time, hero, hash)] a counter told one update later
        self.static_next = STATIC_FIRST

    def put(self, hero, kind, ident, values):
        """set values {index: float} (or a full list) of a series; told with the frame's 1052"""
        key = (kind, ident, hero.net)
        cur = self.series.get(key)
        if cur is None:
            cur = self.series[key] = [0.0] * 16
            self.dirty[key] = None
        items = enumerate(values) if isinstance(values, (list, tuple)) else values.items()
        for i, v in items:
            if abs(cur[i] - v) > 1e-6:
                cur[i] = float(v)
                if self.dirty.get(key, set()) is not None:
                    self.dirty.setdefault(key, set()).add(i)

    def perks(self, hero):
        from . import runes
        page = getattr(hero, 'rune_page', None)
        return runes.PAGES[page][2] if page in runes.PAGES else []

    def minion_died_near(self, hero):
        """Overgrowth (8451) [m: Garen's series in the live recording]: value 1 counts the enemy minions and
        monsters that die near the champion; every 8 of them value 0 (its lasting bonus health) grows by 3"""
        if 8451 not in self.perks(hero) or (5, 8451, hero.net) not in self.series:
            return
        cur = self.series[(5, 8451, hero.net)]
        n = cur[1] + 1.0
        bonus = 3.0 * (n // 8)
        self.put(hero, 5, 8451, {1: n, 0: bonus})
        if bonus != getattr(hero, 'overgrowth_hp', 0.0):
            hero.overgrowth_hp = bonus
            hero.remove_mods(('rune', 8451))
            hero.add_mods(('rune', 8451), {'hp': bonus})

    def alacrity(self, hero, progress=0.0, stack=False):
        """Legend: Alacrity (9104) [m: 6 replays, 1,000 changes of its series]: value 1 = progress (+4 an enemy
        minion killed, +25 a large monster), at 100 a stack and progress back to 0; a champion takedown or an epic
        monster gives a stack at once (progress kept); value 2 = stacks (up to 10 [wiki]), value 0 = its bonus attack
        speed 3 % + 1.5 % a stack"""
        if 9104 not in self.perks(hero):
            return
        cur = self.series.get((5, 9104, hero.net)) or [0.0] * 16
        p, n = cur[1] + progress, cur[2]
        while p >= 100.0 - 1e-6:
            p -= 100.0
            n += 1
        if stack:
            n += 1
        n = min(ALACRITY_MAX, n)
        if n >= ALACRITY_MAX:
            p = 0.0                                # [a] no progress once the stacks are full
        bonus = 0.03 + 0.015 * n
        self.put(hero, 5, 9104, {0: bonus, 1: p, 2: n})
        hero.remove_mods(('rune', 9104))
        hero.add_mods(('rune', 9104), {'as': bonus})

    def unit_killed(self, u, killer, takers=()):
        """a death's rune rewards: killer = the champion that killed it, takers = the champions with a takedown"""
        if u.is_hero:
            for h in takers:
                self.alacrity(h, stack=True)
            return
        if killer is None or not killer.is_hero:
            return
        base = u.name.split('.')[0]
        if u.kind == 'minion' and u.team != killer.team:
            self.alacrity(killer, 4.0)
        elif u.kind == 'monster' and base in LARGE_MONSTERS:
            self.alacrity(killer, 25.0)
        elif u.kind == 'monster' and any(k in base for k in EPIC_MONSTERS):
            self.alacrity(killer, stack=True)

    def make_quests(self):
        """every champion's role quest by its position: the series, and for a lane its buff with the counter at 0"""
        g = self.g
        for h in g.heroes:
            h_buff, first = QUESTS.get(getattr(h, 'role', None) or 'MIDDLE', QUESTS['MIDDLE'])
            self.put(h, 3, 8, list(first))
            self.progress(h, 0.0, first=True)
            if getattr(h, 'role', None) == 'UTILITY':
                self.make_support(h)
            if h_buff is None:
                continue
            slot = g.spells.buff_slot(h) if g.spells is not None else 0x0b
            if not hasattr(h, 'buff_list'):
                h.buff_list = {}
            known = g.vision is None or not g.vision.hidden(h)
            h.buff_list[('quest',)] = {'slot': slot, 'until': g.t + 25000.0, 'hash': h_buff, 'undo': None, 'known': known,
                                      'args': (h.net, slot, 1, h_buff, QUEST_PACKAGE)}
            if known:
                g.q += g.pk.buff_add(h.net, h.net, slot, 1, h_buff, 25000.0, package=QUEST_PACKAGE)
            self.quest[h.net] = [0.0, slot, 0, h_buff, first[2]]
            g.q += g.pk.buff_counter(h.net, slot, h_buff, 0)

    def quest_buff(self, h, key, name_hash, btype, duration, renew=False):
        """a quest's buff on the champion (the caster itself, the quests' package); renew: ended and given again"""
        g = self.g
        if not hasattr(h, 'buff_list'):
            h.buff_list = {}
        old = h.buff_list.get(key)
        if old is not None and renew and old.get('known', True):
            g.q += g.pk.buff_remove(h.net, old['slot'], name_hash)
        slot = old['slot'] if old else (g.spells.buff_slot(h) if g.spells is not None else 0x0b)
        known = g.vision is None or not g.vision.hidden(h)
        h.buff_list[key] = {'slot': slot, 'until': g.t + duration, 'hash': name_hash, 'undo': None, 'known': known,
                            'args': (h.net, slot, btype, name_hash, QUEST_PACKAGE)}
        if known:
            g.q += g.pk.buff_add(h.net, h.net, slot, btype, name_hash, duration, package=QUEST_PACKAGE)
        return slot

    def make_support(self, h):
        g = self.g
        sp = {'value': 0.0, 'charges': 0, 'slots': {}, 'told': {}, 'due': CHARGE_START, 'used_at': None}
        self.support[h.net] = sp
        # [m] at 0 s: the charge timer (type 27, until 65 s), the charges, the shown counter (type 1); at 0.52 s the told one
        for key, hh, btype, dur in ((('sup', 3), SUP_TIMER, 27, 65.0), (('sup', 2), SUP_CHARGES, 1, 25000.0),
                                    (('sup', 1), SUP_SHOWN, 1, 25000.0), (('sup', 0), SUP_TOLD, 27, 250000.0)):
            sp['slots'][hh] = self.quest_buff(h, key, hh, btype, dur)
            sp['told'][hh] = 0
            g.q += g.pk.buff_counter(h.net, sp['slots'][hh], hh, 0)

    def sup_count(self, h, hh, n):
        sp = self.support[h.net]
        if sp['told'].get(hh) != n:
            sp['told'][hh] = n
            self.g.q += self.g.pk.buff_counter(h.net, sp['slots'][hh], hh, n)

    def support_tick(self, t):
        g = self.g
        while t >= self.sup_next:
            self.sup_next += SUP_PERIOD
            for h in g.heroes:
                sp = self.support.get(h.net)
                if sp is None:
                    continue
                sp['value'] += SUP_GOLD
                n = int(sp['value'])
                if n != sp['told'].get(SUP_TOLD):
                    self.sup_count(h, SUP_TOLD, n)
                    self.later.append((t + QUEST_GRID, h))
        for h in g.heroes:
            sp = self.support.get(h.net)
            # [m: replay 4012247271 Poppy] each support's own charge timer: a charge every 20 s, stopped while full,
            # started again by a charge spent at full
            while sp is not None and sp['due'] is not None and t >= sp['due']:
                sp['charges'] += 1
                full = sp['charges'] >= CHARGE_MAX
                sp['due'] = None if full else sp['due'] + CHARGE_PERIOD
                self.quest_buff(h, ('sup', 3), SUP_TIMER, 27, 25000.0 if full else CHARGE_PERIOD - 0.05, renew=True)
                self.sup_count(h, SUP_TIMER, sp['charges'])
                self.sup_count(h, SUP_CHARGES, sp['charges'])
        keep = []
        for when, h in self.later:
            if t >= when:
                sp = self.support[h.net]
                self.sup_count(h, SUP_SHOWN, int(sp['value']))
                self.put(h, 3, 8, {0: sp['value']})
                self.progress(h, sp['value'])
            else:
                keep.append((when, h))
        self.later = keep

    # ------------------------------------------------------------------ World Atlas: Shared Riches
    # [wiki World Atlas V26.x; m: replay 4012247271, Poppy's 23 charges spent] with an allied champion within 1050 a
    # charge is spent by: killing a minion (18 gold to the support, the minion's gold to the nearest ally - told as +gold
    # and -gold to the support), a basic attack leaving a minion below 50 % (melee) / 30 % (ranged) of its health (it is
    # executed first: 150 'fc29426a' of its health, before the attack's damage), damaging an enemy champion or structure
    # with an attack or ability (18 gold, once per attack / ability). The charge timer is renewed with the time left.
    def sup_ready(self, h):
        sp = self.support.get(h.net)
        if sp is None or sp['charges'] <= 0 or not h.alive:
            return None
        g = self.g
        allies = [x for x in g.heroes if x is not h and x.alive and x.team == h.team and
                  ((x.pos[0] - h.pos[0]) ** 2 + (x.pos[1] - h.pos[1]) ** 2) ** 0.5 <= 1050.0]
        return (sp, allies) if allies else None

    def sup_spend(self, h, sp, source_net):
        g = self.g
        sp['charges'] -= 1
        h.add_gold(18.0, source_net)
        if sp['due'] is None:                            # it was full: the timer starts now
            sp['due'] = g.t + CHARGE_PERIOD
        self.quest_buff(h, ('sup', 3), SUP_TIMER, 27, max(0.0, sp['due'] - g.t), renew=True)
        self.sup_count(h, SUP_TIMER, sp['charges'])
        self.sup_count(h, SUP_CHARGES, sp['charges'])

    def sup_execute(self, h, minion, dealt, ranged):
        """before a support's basic attack lands on a minion: True when Shared Riches executes it"""
        r = self.sup_ready(h)
        if r is None or minion.hp - dealt >= (0.3 if ranged else 0.5) * minion.max_hp:
            return False
        from .game import GENERIC_DAMAGE
        self.g.deal(h, minion, minion.hp, P.TRUE, basic=False, source=P.SRC_DIRECT, spell_hash=GENERIC_DAMAGE)
        return True

    def sup_minion_kill(self, h, minion, gold):
        """a support killed a minion: True when a charge was spent (the gold goes to the nearest ally)"""
        r = self.sup_ready(h)
        if r is None:
            return False
        sp, allies = r
        near = min(allies, key=lambda x: (x.pos[0] - h.pos[0]) ** 2 + (x.pos[1] - h.pos[1]) ** 2)
        h.add_gold(gold, minion.net)
        h.add_gold(-gold, minion.net)
        self.sup_spend(h, sp, minion.net)
        near.add_gold(gold, minion.net)
        return True

    def sup_hit(self, h, tgt, key):
        """a support damaged an enemy champion or structure (key: the attack / ability, spent once)"""
        r = self.sup_ready(h)
        if r is None:
            return
        sp, allies = r
        if sp.get('last_key') == key:
            return
        sp['last_key'] = key
        self.sup_spend(h, sp, tgt.net)

    def progress(self, h, value, first=False):
        g = self.g
        if not first and h.net not in getattr(g, 'watch', set()):
            return
        role = getattr(h, 'role', None) or 'MIDDLE'
        # [m] the support's fraction is its value / 800 (1.5 -> 0.001875, 2.25 -> 0.0028125), the others' value / goal
        goal = 800.0 if role == 'UTILITY' else (QUESTS.get(role, QUESTS['MIDDLE'])[1][1] or 1.0)
        g.q.append((1, 264, 0, g.pk.enc(264, {'+0x10': P.f32(value / goal), '+0x14': '01',
                                              '+0x15': f'{(getattr(h, "slot", 0) + 1) & 0xff:02x}', '+0x16': '00',
                                              '+0x18': P.u32(ROLE_ID.get(role, 2))})))

    def quest_count(self, h):
        """the quest buff's counter follows int(value 0)"""
        q = self.quest.get(h.net)
        n = int(q[0])
        if n != q[2]:
            q[2] = n
            self.g.q += self.g.pk.buff_counter(h.net, q[1], q[3], n)

    def minion_killed(self, h):
        """a lane quest's value grows by 4 a at once for every enemy minion the champion kills"""
        q = self.quest.get(h.net)
        if q is None:
            return
        q[0] += 4.0 * q[4]
        self.quest_count(h)
        self.progress(h, q[0])

    def quest_update(self, tg):
        """an update of the quests' clock at tg (8 frames apart): the 1 s timer fires on the update where it is due"""
        prev, self.last_update = self.last_update, tg
        self.last_update = prev
        try:
            self._quest_update(tg)
        finally:
            self.last_update = tg

    def _quest_update(self, tg):
        if tg < QUEST_START + 0.5:
            pass
        elif self.clock is None:
            if tg >= QUEST_FIRST - 0.05:
                self.clock = QUEST_CARRY
                self.fire(tg)
        else:
            self.clock += tg - self.last_update if self.last_update is not None else QUEST_GRID
            if self.clock >= 1.0:
                self.clock -= 1.0
                self.fire(tg)
        # a kill's new value is told with the next update
        for h in self.g.heroes:
            q = self.quest.get(h.net)
            if q is not None:
                self.put(h, 3, 8, {0: q[0]})

    def fire(self, tg):
        span = tg - (self.fired if self.fired is not None else QUEST_START)
        self.fired = tg
        for h in self.g.heroes:
            q = self.quest.get(h.net)
            if q is not None:
                q[0] += QUEST_RATE * span
                self.quest_count(h)
                self.progress(h, q[0])

    def tick(self, t, dt):
        g = self.g
        if not getattr(self, 'runes_sent', False) and t >= 0.4:
            # [m] every rune of every champion has its series from the start (all 16 values); the ones whose first
            # values are not zero in the recordings: the shards 5008 (value 1 = 5.4), 5001 (10), 8242 (10), 9104 (0.03)
            self.runes_sent = True
            first = {5008: {1: 5.4}, 5001: {0: 10.0}, 8242: {0: 10.0}, 9104: {0: 0.03}}
            for h in g.heroes:
                for perk in dict.fromkeys(self.perks(h)):
                    vals = [0.0] * 16
                    for i, x in first.get(perk, {}).items():
                        vals[i] = x
                    self.put(h, 5, perk, vals)
                    if perk == 9104:
                        h.add_mods(('rune', 9104), {'as': 0.03})
        if not self.quests_made:
            self.quests_made = True
            self.make_quests()
        if not self.trinket_sent and t >= 14.0:
            self.trinket_sent = True
            for h in g.heroes:
                self.put(h, 3, 6, [0.0, 0.0, 90.0, 210.0, 2.0, 3.0])
        levels = sum(h.level for h in g.heroes)
        if self.trinket_sent and levels != self.level_sum:
            first = self.level_sum is None
            self.level_sum = levels
            if not first:
                avg = levels / max(1, len(g.heroes))
                for h in g.heroes:
                    self.put(h, 3, 6, {2: 90.0 + 30.0 * (avg - 1.0) / 17.0, 3: 210.0 - 120.0 * (avg - 1.0) / 17.0})
        while g.frame >= self.static_frame:
            self.static_frame += 32
            for net, d in STATIC_FACING.items():
                g.q.append((1, 1201, net, g.pk.enc(1201, {'+0x10': 'abaaaa3d', '+0x14': d, '+0x20': '00'})))
        if self.support:
            self.support_tick(t)
        while g.frame >= self.grid_frame:
            self.quest_update(t)
            self.grid_frame += 8
        if self.dirty:
            self.flush()

    def flush(self):
        g = self.g
        entries = []
        for key, idx in self.dirty.items():
            kind, ident, net = key
            cur = self.series[key]
            which = range(16) if idx is None else sorted(idx)
            entries.append({'+0x8': P.u32(kind), '+0xc': P.u32(net), '+0x10': '0000',
                            '+0x18': [{'+0x8': P.f32(cur[i]), '+0xc': f'{i:02x}'} for i in which], '+0x28': P.u32(ident)})
        self.dirty = {}
        # [m] one to six entries a packet mostly: a packet per champion's change
        for i in range(0, len(entries), 4):
            try:
                g.q.append((1, 1052, 0, g.pk.enc(1052, {'+0x10': entries[i:i + 4]})))
            except Exception as x:
                g.log(f'tooltips 1052: {x!r}')
                return


def setup(game, session=None):
    game.tooltips = Tooltips(game)
    game.systems.append(game.tooltips.tick)
