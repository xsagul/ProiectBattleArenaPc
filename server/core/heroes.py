"""Champions: any of the game's champions from its own data (gamedata.Champion), played by a client or by a bot.

Measured on the live recording (Garen, levels 1-4): the base statistics grow by LoL's curve
base + per level x (n x (0.7025 + 0.0175 n)), n = level - 1 - health, attack damage, armor, magic resist, health
regeneration and the attack speed bonus alike; a level-up is 969 {1, level} and the new values in the replication;
the client itself counts the skill points (level minus the spells' levels); passive gold is 1.02 every 0.5 s from
65 s; the can-cast bits (mReplicatedSpellCanCastBitsLower1) hold one bit per spell slot.
"""
import json
import math
import os

from . import gamedata as G
from . import packets as P
from .units import Unit, dist, ORDER, CHAOS

START_GOLD = 500.0
PASSIVE_FROM, PASSIVE_STEP, PASSIVE_GOLD = 65.0, 0.5, 1.02
REGEN_STEP = 0.5
KILL_GOLD, ASSIST_POOL, ASSIST_WINDOW = 300.0, 150.0, 10.0
KILL_GOLD_MIN = 100.0
# [m: the 1168 / 189 series of the live recording] a champion's worth: every farm kill adds 15 % of its gold to
# the champion's bounty (1168 {champion, 0, bounty}); a death clears the bounty and takes something off its kill
# gold (189 {champion, a, 3.5 a}), which farm pays back: 3.5 a falls by half of every farm kill's gold.
# [a] how much a death takes off (the recording's first deaths: 80 - 127): a flat 90, at most 200
BOUNTY_FARM, DEVALUE_FACTOR, DEVALUE_FARM, DEVALUE_STEP, DEVALUE_MAX = 0.15, 3.5, 0.5, 90.0, 200.0
RECAP_WINDOW = 15.0              # [a] s of damage the death recap looks back over
MULTIKILL_WINDOW = 10.0          # [m] 577 {1, killer} at a kill, {0, killer} 10.02 s later
FOUNTAIN_HEAL = 0.084            # share of max health per second at the fountain [wiki: 2.1 % per 0.25 s; m: replay
#                                  4012247271's health rises ~8.6 % a second besides the ticks below]
# [m: 7 arrivals of replay 4012247271] and a heal of 8 % of the MISSING health on arrival and on a 0.5 s script timer
# (its first update too) while the champion is hurt, each with its 699 heal event (cause 0993a255, the team's bytes)
FOUNTAIN_MISSING = 0.08
FOUNTAIN_RADIUS = 1250.0
BASE_BITS = 0x7070               # [m] the can-cast bits a champion starts with (summoner spells, recall, trinket)


_attack_slots = None
CRIT_SLOT = 0x49                 # [m: 906 +0x10 +0xd of the replays' critical strikes]


def hero_attack_variants(champ):
    """(names, chances) of a champion's attack variants: as often as the replays show each slot (tools/attack_slots16.py:
    the data's mAttackProbability is not what every champion does), else the data's; a form's own attacks (JinxQAttack)
    are left out - they belong to the form"""
    global _attack_slots
    if _attack_slots is None:
        try:
            _attack_slots = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'attack_slots16.json')))
        except Exception:
            _attack_slots = {}
    names = champ.attacks
    seen = _attack_slots.get(champ.name) or {}
    w = [float(seen.get(f'{0x40 + k:02x}', 0)) if 'BasicAttack' in n else 0.0 for k, n in enumerate(names)]
    if sum(w) <= 0:
        w = list(champ.attack_weights)
    return names, w


def hero_attack_slot(champ):
    """the spell slot a champion's every basic attack goes through, when the replays show one for > 90 % of its
    attacks [m: Kindred 0x30 3455 of 3456, Zeri 0x2f, Yunara 0x2e] - else None (0x40 + the variant)"""
    hero_attack_variants(champ)
    seen = {int(k, 16): n for k, n in (_attack_slots.get(champ.name) or {}).items()}
    total = sum(seen.values())
    low = [(n, s) for s, n in seen.items() if s < 0x40]
    if total and low and max(low)[0] > 0.9 * total:
        return max(low)[1]
    return None


class Hero(Unit):
    kind = 'hero'
    repl_cls = 'AIHero'
    is_hero = True

    def __init__(self, game, net, team, champion, pos, template_values, player_name='', bot=False, slot=0):
        self.champ = G.champion(champion)
        base = dict(self.champ.stats)
        if not self.champ.record.get('overrideGameplayCollisionRadius'):
            base['radius'] = 65.0                    # a champion's gameplay radius
        base['missile_speed'] = self.champ.attack_missile_speed() if not self.champ.melee else 0.0
        self.template = dict(template_values)
        super().__init__(game, net, team, champion, pos, base)
        self.player_name, self.bot, self.slot = player_name, bot, slot
        self.attack_slots = min(2, len(self.champ.attacks))
        self.attack_variants = lambda: hero_attack_variants(self.champ)
        self.own_attack_slot = hero_attack_slot(self.champ)
        self.home = self.pos
        self.xp = 0.0
        self.gold = START_GOLD
        self.gold_total = START_GOLD
        self.spell_levels = [0, 0, 0, 0]
        self.kills = self.deaths = self.assists = self.cs = 0
        self.bounty = 0.0                # gold a kill of this champion pays on top (1168)
        self.devalue = 0.0               # gold a kill of this champion pays less (189's first number)
        self.kill_glow_until = 0.0
        self.recap = []                  # (time, taken?, other unit, its name, spell hash, basic?, type, amount)
        self.respawn_at = None
        self.order = None               # ('move', goal) | ('attack', net) | None
        self.last_chase = -1.0
        self.next_regen = 0.0
        self.next_passive = PASSIVE_FROM
        self.cooldowns = [0.0] * 6      # when each slot (Q W E R D F) is ready again
        self.casting_until = 0.0
        self.inventory = [None] * 7
        self.item_stacks = [0] * 7
        self.brain = None               # a bot's brain (bots.py)
        self.in_combat_until = 0.0
        self.recalling = None
        self.buffs = {}
        self.sight = 1350.0
        self.dashing = False
        self.empowered = None
        self.silence_until = self.disarm_until = 0.0
        self.slot_names = list(self.champ.spells)      # the spell each slot holds now (a recast form after 78)

    def spell_name(self, slot):
        return self.slot_names[slot] if slot < len(self.slot_names) else self.champ.spells[slot]

    # ------------------------------------------------------------------ what the client holds about it
    def start_values(self):
        """the champion's full replicated state: the recorded champion's values as the form (every name the real
        server sets in the first seconds), with this champion's own numbers"""
        v = dict(self.template)
        v.update(self.stat_values())
        v.update({'mHP': self.hp, 'mPAR': self.par, 'mGold': self.gold, 'mGoldTotal': self.gold_total, 'mExp': self.xp,
                  'mLevelRef': self.level, 'mReplicatedSpellCanCastBitsLower1': self.cast_bits(),
                  'mCombatType': 1 if self.champ.melee else 2, 'mPAREnabled': 1,
                  'mPassiveCooldownEndTime': 0.0, 'mPassiveCooldownTotalTime': 0.0, 'mAllShield': 0.0})
        for i in range(4):
            v[f'ManaCost_{i}'] = self.mana_cost(i)
        # [m] the other team's champions were out of the recording player's sight at 14 s: their recorded values are
        # the pre-game ones (ActionState 0x5020003, ActionState2 0) - the state Zed has while his ultimate hides him
        # [the replays: 0x5000002 / 0]: the client does not draw such a champion. Everyone starts free to act.
        v['ActionState'], v['ActionState2'] = 0x100000f, 4
        return v

    def stat_values(self):
        return {'mMaxHP': self.max_hp, 'mMaxPAR': self.max_par, 'mBaseAttackDamage': self.base_ad,
                'mBaseAttackDamageSansPercentScale': self.base_ad, 'mFlatPhysicalDamageMod': self.bonus['ad'],
                'mFlatMagicDamageMod': self.ap, 'mArmor': self.armor, 'mSpellBlock': self.mr,
                'mBonusArmor': self.bonus['armor'], 'mBonusSpellBlock': self.bonus['mr'],
                'mAttackSpeedMod': 1.0 + self.as_bonus, 'mPercentAttackSpeedMod': self.as_bonus,
                'mAttackRange': self.range, 'mMoveSpeed': self.speed, 'mHPRegenRate': self.hp_regen,
                'mBaseHPRegenRate': G.level_stat(self.base['hp_regen'], self.base['hp_regen_lvl'], self.level),
                'mPARRegenRate': self.par_regen, 'mCrit': self.crit, 'mAbilityHasteMod': self.bonus['haste'],
                'mPercentLifeStealMod': self.bonus['lifesteal'], 'mPhysicalLethality': self.bonus['lethality']}

    def replicate_stats(self):
        self.set_many(self.stat_values())

    def recompute(self, first=False):
        super().recompute(first)
        b, L = self.base, self.level
        # health and mana regeneration grow by the same curve as the other statistics [m: 1.672 at level 2]
        self.hp_regen = G.level_stat(b['hp_regen'], b['hp_regen_lvl'], L) * (1.0 + self.bonus['hp_regen_pct']) + self.bonus['hp_regen']
        self.par_regen = G.level_stat(b['par_regen'], b['par_regen_lvl'], L) * (1.0 + self.bonus['par_regen_pct']) + self.bonus['par_regen']
        if not first:
            self.replicate_stats()

    def mana_cost(self, slot):
        if slot >= len(self.champ.spells):
            return 0.0
        sp = self.champ.spell_data(self.spell_name(slot)) or self.champ.spell_data(self.champ.spells[slot])
        # [m: the real casts' costs (1215 +0x11c), 403 spells in 25 replays: 399 are manaValues[rank - 1] - the
        # list starts at rank 1, and 'mana' is an older copy (Ekko Q, Jax Q, Tristana Q differ)]
        cost = (sp.get('manaValues') or {}).get('values') or sp.get('mana') or sp.get('mManaCost') or []
        if isinstance(cost, (int, float)):
            return float(cost)
        lvl = max(1, self.spell_levels[slot])
        return float(cost[min(lvl - 1, len(cost) - 1)]) if cost else 0.0

    def cast_bits(self):
        bits = BASE_BITS
        t = self.game.t
        for i in range(4):
            if self.spell_levels[i] > 0 and t >= self.cooldowns[i] and self.par >= self.mana_cost(i) - 1e-6:
                bits |= 1 << i
        return bits

    def refresh_bits(self):
        self.set('mReplicatedSpellCanCastBitsLower1', self.cast_bits())

    # ------------------------------------------------------------------ orders (a client's or a bot's)
    def order_move(self, goal):
        if not self.alive:
            return
        kits = getattr(self.game, 'kits', None)
        if kits is not None and kits.call(self, 'order', self, 'move', goal):
            return                                       # the kit took it (Ambessa's buffered dash)
        self.order = ('move', goal)
        self.target = None
        self.cancel_attack()
        self.recall_cancel()
        self.path_to(goal)

    def order_attack(self, net):
        if not self.alive:
            return
        kits = getattr(self.game, 'kits', None)
        if kits is not None and kits.call(self, 'order', self, 'attack', net):
            return
        if self.target != net:
            self.cancel_attack()
        self.recall_cancel()
        self.order = ('attack', net)
        self.target = net
        self.last_chase = -1.0

    def order_stop(self):
        self.order = None
        self.target = None
        self.cancel_attack()
        if self.path:
            self.stop()

    def recall_cancel(self):
        if self.recalling is not None:
            self.recalling = None
            end = getattr(self, 'recall_end', None)
            if end is not None:
                end()

    def blink(self, dest):
        """at once to a place near (Flash, a blink spell)"""
        self.order = None
        self.target = None
        self.teleport(dest)

    def skill_points(self):
        kits = getattr(self.game, 'kits', None)
        if kits is not None:
            n = kits.call(self, 'skill_points', self)
            if n is not None:
                return n
        return self.level - sum(self.spell_levels)

    def level_spell(self, slot):
        """a skill point into a slot -> True when given (LoL's rules: R at 6 / 11 / 16, a basic spell at most half
        the level rounded up, five ranks)"""
        if not 0 <= slot <= 3 or self.skill_points() <= 0:
            return False
        kits = getattr(self.game, 'kits', None)
        if kits is not None:
            took = kits.call(self, 'level_spell', self, slot)
            if took is not None:
                return took                              # the kit's own points (Aphelios' stat ranks)
        cur = self.spell_levels[slot]
        if slot == 3:
            if cur >= 3 or self.level < (6, 11, 16)[cur]:
                return False
        elif cur >= 5 or cur >= (self.level + 1) // 2:
            return False
        self.spell_levels[slot] = cur + 1
        g = self.game
        g.q += g.pk.skill_level(self.net, slot, cur + 1, self.skill_points())
        self.set(f'ManaCost_{slot}', self.mana_cost(slot))
        self.refresh_bits()
        return True

    # ------------------------------------------------------------------ the frame
    def tick(self, t, dt):
        g = self.game
        if not self.alive:
            if self.respawn_at is not None and t >= self.respawn_at:
                self.respawn(t)
            return
        if self.brain is not None:
            self.brain.think(t)
        if self.dashing or t < self.casting_until:
            state = 'busy'                       # a cast or a dash in progress: no attack begins, none is chased
        else:
            state = self.attack_tick(t)
        if state == 'far' and self.order and self.order[0] == 'attack':
            tgt = g.units.get(self.target)
            if tgt is not None and t - self.last_chase > 0.25 and t >= self.casting_until:      # chase, four times a second
                self.last_chase = t
                self.path_to(tgt.pos)
        elif state == 'idle' and self.order and self.order[0] == 'attack':
            self.order = None
        if t >= self.next_regen:
            self.next_regen = t + REGEN_STEP
            self.regen(REGEN_STEP)
        if self.alive and self.hp < self.max_hp and not getattr(self, 'fountain_on', False) and                 dist(self.pos, self.home) < FOUNTAIN_RADIUS:
            self.fountain_start()
        if t >= self.next_passive:
            self.next_passive += PASSIVE_STEP
            self.add_gold(PASSIVE_GOLD)

    def fountain_start(self):
        g = self.game
        self.fountain_on = True
        self.fountain_tick(0xa1)

        def going():
            ok = self.alive and self.hp < self.max_hp - 0.01 and dist(self.pos, self.home) < FOUNTAIN_RADIUS
            if not ok:
                self.fountain_on = False
            return ok
        g.script_timer(0.5, lambda t: self.fountain_tick(0xae), alive=going)

    def fountain_tick(self, kind):
        import struct
        g = self.game
        amount = FOUNTAIN_MISSING * (self.max_hp - self.hp)
        if amount <= 0:
            return
        self.heal(amount)
        mid = bytes.fromhex('0618da08') + bytes([1 if self.team == ORDER else 2, kind]) + bytes.fromhex('7be8') + struct.pack('<I', self.net)
        g.q += g.pk.heal_event(self.net, self.net, amount, cause=0x0993a255, name=0, flag=0, mid=mid,
                               tail=bytes.fromhex('ffffffff02077be8'))

    def regen(self, dt):
        hp, par = self.hp_regen * dt, self.par_regen * dt
        if dist(self.pos, self.home) < FOUNTAIN_RADIUS:
            hp += self.max_hp * FOUNTAIN_HEAL * dt
            par += self.max_par * FOUNTAIN_HEAL * dt
        if self.hp < self.max_hp and hp > 0:
            self.set_hp(self.hp + hp)
        if self.par < self.max_par and par > 0:
            self.set_par(self.par + par)

    def set_par(self, par):
        self.par = max(0.0, min(self.max_par, par))
        self.set('mPAR', self.par)

    # ------------------------------------------------------------------ economy
    def add_gold(self, amount, from_net=0):
        self.gold += amount
        if amount > 0:
            self.gold_total += amount
        self.set_many({'mGold': self.gold, 'mGoldTotal': self.gold_total})
        if from_net:
            # [m: live, 254 of 254] the gold popup (818) goes to the champion's own client only; 121 to everyone
            if self.net in self.game.watch:
                self.game.q += self.game.pk.gold(self.net, amount, from_net)
            self.game.q += self.game.pk.gold_mark(self.net)

    def add_xp(self, amount):
        g = self.game
        if amount <= 0 or self.level >= 18:
            return
        self.xp += amount
        self.set('mExp', self.xp)
        if self.team == g.player_team:               # [m] the xp a champion gains is told to its own team only
            g.q += g.pk.xp(self.net, amount)
        table = g.data['xp_per_level']
        while self.level < 18 and self.xp >= table[self.level - 1]:
            self.level += 1
            g.q += g.pk.level_up(self.net, self.level)
            if getattr(self, 'rune_page', None):         # the health shard grows with the level
                from . import runes
                runes.apply(self)
            self.recompute()
            self.set_many({'mLevelRef': self.level, 'mHP': self.hp})
            g.log(f'{self.name} reaches level {self.level}')
            if self.brain is not None:
                self.brain.on_level()

    # ------------------------------------------------------------------ death and return
    def death_time(self):
        d = self.game.data['death_times']
        base = d['mTimeDeadPerLevel'][min(self.level, len(d['mTimeDeadPerLevel'])) - 1]
        t = self.game.t
        pct = 0.0
        if t > d.get('mScalingStartTime', 1e9):
            points = [(d['mScalingStartTime'], d['mScalingPercentIncrease'])] + \
                     [(p['mStartTime'], p['mPercentIncrease']) for p in d.get('mScalingPoints', [])]
            step = d.get('mScalingIncrementTime', 30)
            for i, (start, inc) in enumerate(points):
                end = points[i + 1][0] if i + 1 < len(points) else t
                if t > start:
                    pct += inc * math.floor((min(t, end) - start) / step)
        return base * (1.0 + min(pct, d.get('mScalingPercentCap', 1.5) - 1.0))

    def recap_packet(self, t, killer_net):
        """the death recap: the last 15 s of damage taken, by source and spell, and of damage dealt"""
        taken, dealt = {}, {}
        names = {}
        for when, was_taken, other, name, h, basic, dtype, amount in self.recap:
            if t - when > RECAP_WINDOW:
                continue
            table = taken.setdefault(other, {}) if was_taken else dealt
            names[other] = name
            if basic and not h:
                src = self.game.units.get(other) if was_taken else self
                h = P.elf(getattr(src, 'attack_name', '') or (name + 'BasicAttack'))
            e = table.setdefault((h, basic), [0.0, 0.0, 0.0])
            e[{P.TRUE: 0, P.MAGIC: 1}.get(dtype, 2)] += amount

        def entries(table):
            return [(basic, e[0], e[1], e[2], h, 0x40 if basic else 0) for (h, basic), e in table.items()]
        sources = [(net, names.get(net, ''), entries(tb)) for net, tb in taken.items()]
        sources.sort(key=lambda s: -sum(e[1] + e[2] + e[3] for e in s[2]))
        self.recap = []
        return self.game.pk.death_recap(self.net, self.name, killer_net, sources[:5], entries(dealt))

    def score_packet(self):
        """437 [m]: the champion's score as the scoreboard shows it: assists, deaths, kills"""
        return (1, 437, self.net, self.game.pk.enc(437, {'+0x10': P.u32(self.assists), '+0x14': P.u32(self.deaths),
                                                          '+0x18': P.u32(self.kills)}))

    def worth_packets(self):
        pk = self.game.pk
        return [(1, 1168, 0, pk.enc(1168, {'+0x10': P.u32(self.net), '+0x14': P.u32(0), '+0x18': P.f32(self.bounty)})),
                (1, 189, 0, pk.enc(189, {'+0x10': P.u32(self.net), '+0x14': P.f32(self.devalue),
                                         '+0x18': P.f32(self.devalue * DEVALUE_FACTOR)}))]

    def farmed(self, gold):
        """a minion or monster kill's gold moves the champion's worth"""
        if gold <= 0:
            return
        if self.devalue > 0.0:
            self.devalue = max(0.0, self.devalue - DEVALUE_FARM * gold / DEVALUE_FACTOR)
            self.game.q.append(self.worth_packets()[1])
        else:
            self.bounty += BOUNTY_FARM * gold
            self.game.q.append(self.worth_packets()[0])

    def kill_gold(self):
        return max(KILL_GOLD_MIN, KILL_GOLD - self.devalue) + self.bounty

    def die(self, t, killer, helpers=()):
        """[m: the death frames of the live recording] 437 (score) of the dead and of who assisted, 563, the dead
        champion's worth (1168 bounty 0, 189), 121 {0, each one involved}, 577 {1, killer} (off again 10 s later),
        437 of the killer, 166 (seconds until it returns), 421 (the death: place, killer, seconds), 131; 1050 to
        the player when it was involved"""
        g = self.game
        pk, q = g.pk, g.q
        self.alive = False
        self.target = self.order = None
        self.windup_end = None
        self.path = None
        self.deaths += 1
        dead_for = self.death_time()
        self.respawn_at = t + dead_for
        credit = killer if killer is not None and killer.is_hero else None
        killer_net = killer.net if killer is not None else 0
        timer, tm = P.f32(dead_for), P.f32(t)
        here = self.pos
        q.append(self.score_packet())
        q.extend(a.score_packet() for a in helpers)
        q.append((1, 563, 0, pk.enc(563, {'+0x10': P.u32(0), '+0x14': P.u32(self.net)})))
        self.bounty = 0.0
        self.devalue = min(DEVALUE_MAX, self.devalue + DEVALUE_STEP)
        q.extend(self.worth_packets())
        involved = [self] + ([credit] if credit is not None else []) + list(helpers)
        q.extend((1, 121, 0, pk.enc(121, {'+0x10': P.f32(0.0), '+0x14': P.u32(x.net)})) for x in involved)
        if credit is not None:
            q.append((1, 577, 0, pk.enc(577, {'+0x10': '01', '+0x14': P.u32(credit.net)})))
            credit.kill_glow_until = t + MULTIKILL_WINDOW

            def off(t2, k=credit):
                if t2 >= k.kill_glow_until:
                    g.q.append((1, 577, 0, pk.enc(577, {'+0x10': '00', '+0x14': P.u32(k.net)})))
            g.at(t + MULTIKILL_WINDOW + 0.02, off)
            q.append(credit.score_packet())

        def death(v):
            v['+0x10']['+0x20'] = pk.at3(here)
            v['+0x50'] = P.u32(killer_net)
            v['+0x54'] = timer
            return v
        for dt_, ch, pid, net, body in pk.recipe('hero_dies', {'H': self.net, 'K': killer_net},
                                                 {166: {'+0x10': timer}, 421: death},
                                                 skip=(437, 563, 1168, 189, 121, 577, 515, 447, 1050)):
            q.append((ch, pid, net, body))
        for x in involved:
            if x.net in g.watch:
                q.append((1, 1050, x.net, pk.enc(1050, {'+0x10': P.u32(0), '+0x14': tm, '+0x18': tm})))
        if self.net in g.watch:
            q.extend(self.recap_packet(t, killer_net))
        g.q_moves.append(pk.move_entry(self.net, [here], self.speed))
        self.set_hp(0.0)
        g.log(f'{self.name} ({self.net:#x}) dies to {getattr(killer, "name", "?")}; back in {dead_for:.1f} s')

    def inventory_packet(self, v):
        """the recorded 491's entries rewritten for this champion's inventory: slots 0..6 from what it holds, the
        recorded slot 7 entry (item 2001, which every champion has from the start) kept"""
        import copy
        recorded = v['+0x10']['+0x8']
        plain = next(e for e in recorded if e['+0x10']['+0x70'] == '00')
        trinket = next((e for e in recorded if e['+0x10']['+0x70'] == '06'), plain)
        out = []
        catalog = self.game.shop.db if getattr(self.game, 'shop', None) is not None else {}
        for slot, item in enumerate(self.inventory):
            if not item:
                continue
            e = copy.deepcopy(trinket if slot == 6 else plain)
            price = 0.0 if slot == 6 else float((catalog.get(item) or {}).get('total', 0))
            e['+0x10'].update({'+0x18': P.u32(item), '+0x6c': P.f32(price), '+0x70': f'{slot:02x}',
                               '+0x71': f'{max(1, min(self.item_stacks[slot], 255)):02x}'})
            out.append(e)
        out += [copy.deepcopy(e) for e in recorded if e['+0x10']['+0x70'] == '07']
        v['+0x10']['+0x8'] = out
        return v

    def respawn(self, t):
        g = self.game
        self.alive = True
        self.respawn_at = None
        self.pos = self.home
        self.path = None
        tm = P.f32(t)
        own = self.team == g.player_team
        # [m] 158 (the place it returns to) goes to everyone; the sound (211) and the whole inventory (491: one
        # entry per filled slot) only to the champion's own team; 1050 only to its player
        for dt_, ch, pid, net, body in g.pk.recipe('hero_returns', {'H': self.net},
                                                   {1050: {'+0x14': tm, '+0x18': tm}, 491: self.inventory_packet,
                                                    211: {'+0x60': P.text(self.name)},
                                                    158: {'+0x14': P.struct.pack('<ff', self.home[0], self.home[1]).hex()}},
                                                   skip=() if own else (211, 491)):
            g.q.append((ch, pid, net, body))
        g.q_moves.append(g.pk.move_entry(self.net, [self.home], self.speed))
        self.hp, self.par = self.max_hp, self.max_par
        self.set_many({'mHP': self.hp, 'mPAR': self.par})
        if getattr(g, 'kits', None) is not None:
            g.kits.call(self, 'respawned', self)
        self.refresh_bits()
        g.log(f'{self.name} returns')
