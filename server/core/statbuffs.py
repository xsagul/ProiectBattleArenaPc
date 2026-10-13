"""What abilities do to their own champion's stats: bonus attack speed / move speed for a time or for the next basic
attacks, and basic attack timer resets - the wiki's numbers (tools/stat_buffs16.py -> stat_buffs16.json, 72
champions), played at the cast.

Why [m: the golden test, replay 4012247271]: the puppets' attacks came slower than the real ones (LeeSin 1.57 s
median between attacks, real 1.01; Kindred 1.47, real 1.07): Flurry, Dance of Arrows ... were shown (their buffs) but
changed nothing.

  an active's effect      at its own cast (Q W E R by slot), the first effect per stat of the ability
  a passive's effect      "after casting an ability": at every Q W E R cast
  'attacks': n            ends when the n-th basic attack has begun, or at its time
  'decays'                falls linearly to 0 over its time
  'reset'                 the basic attack may begin at once
Values by rank, or by level ('steps': the listed values spread over levels 1 - 18; 'range': from the first at level 1
to the last at 18).
"""
import json
import os

from . import gamedata as G
from . import packets as P
from .units import FRAME

KEYS = 'QWER'
# Lethal Tempo (8008) [m: 12 replays - the buff's counter against the replicated mPercentAttackSpeedMod and the attacks]:
#   a stack when an attack at an enemy champion is let go (its windup's end), up to 6; 6 % bonus attack speed a stack in
#   melee, 4.8 % at range, at every level; the buff (type 27) lasts 6 s from the last stack, then the stacks fall one
#   at a time: the buff ends, one frame later it is given again with one stack less for 0.25 s, ends a script update later
LETHAL_TEMPO = P.elf('ASSETS/Perks/Styles/Precision/LethalTempo/LethalTempo.lua')
LT_MAX, LT_TIME, LT_FALL, LT_MELEE, LT_RANGED = 6, 6.0, 0.25, 0.06, 0.048
# Fleet Footwork (8021) [wiki: 6 charges a basic attack, 1 per 24 units travelled, 100 = energized: the next attack heals
# 15 - 182.73 (melee) / 9 - 109.64 (ranged) by level (+ 10 / 6 % bonus AD, + 5 / 3 % AP) and gives 20 / 15 % move speed
# for 1 s; m: 16 of 16 holders in 40 replays hold buff 85c8fd05 (type 2) whose counter (430) shows the charges, told on
# the holder's script updates when they changed (+10 an update on the fountain's speed, +3.3 walking); spent: the buff
# goes the frame after the attack, the move speed buff e10edb06 (type 15, 1 s) and the charges' buff again 0.5 s later]
FLEET, FLEET_HASTE = 0x05fdc885, 0x06db0ee1
# Conqueror (8010) [wiki: damage to enemy champions: 2 stacks (1 for a ranged basic attack), not for periodic / proc
# damage, an ability's once every 4 s; 5 s, refreshed, up to 12; 1.08 - 2.56 AD or 1.8 - 4.26 AP a stack (adaptive);
# at 12: heal 8 / 5 % of the damage; m: replay 4012247271 Sylas - its buff (Conqueror.lua, type 2, 5 s): 435 + 430 at
# the first stacks, then 282 (5 s, 1) + 430 at each gain, 262 5.2 s after the last]
CONQUEROR = 0x0d318fd1
# Hail of Blades (9923) [m: 12 replays, Ekko / Fiora / Viego / Cho'Gath / Rek'Sai, the buffs against the replicated
#   attack speed and the attacks]: a ready buff (type 1) from the start; an attack begun at an enemy champion while
#   ready swaps it in the same slot for the active buff (type 2, 3 s): 90 % bonus attack speed for that attack and the
#   next two - every further attack begun renews it (282, 3 s), it ends when the third is let go or its time is out;
#   then a cooldown buff (type 3, 10 s, a script timer) in the same slot, then ready again. Ranged champions: no
#   recorded one, their amount is not known - not played for them
HOB_READY, HOB_ACTIVE, HOB_COOLDOWN = (int.from_bytes(bytes.fromhex(h), 'little') for h in ('d1a68609', 'f1bd2c06', '51b04c0e'))
HOB_AS, HOB_ATTACKS, HOB_TIME, HOB_CD = 0.90, 3, 3.0, 10.0
# attack speed that stacks with basic attacks [the wiki's numbers, Meraki 25.15]:
#   Jinx Q (Pow-Pow, the minigun): a stack per attack for 2.5 s, up to 3; the first gives 15 / 27.5 / 40 / 52.5 / 65 %
#     by Q's rank, every further one half of it (7.5 ... 32.5 %); not with Fishbones (Q toggles the weapon)
#   Jax P (Relentless Assault): a stack per attack for 2.5 s, up to 8; 5 % - 12.5 % each by level
STACK_AS = {'Jinx': {'first': [0.15, 0.275, 0.40, 0.525, 0.65], 'rank_slot': 0, 'half_after': True, 'max': 3, 'time': 2.5,
                     'form': 'minigun'},
            'Jax': {'level': (0.05, 0.125), 'max': 8, 'time': 2.5}}
_table = None


def table():
    global _table
    if _table is None:
        try:
            _table = json.load(open(os.path.join(G.ROOT, 'data', 'exe1620', 'stat_buffs16.json'), encoding='utf-8'))
        except Exception:
            _table = {}
    return _table


def amount(e, hero, rank):
    vals = e['values']
    if len(vals) == 1:
        return vals[0]
    if e.get('per') == 'level':
        x = (min(18, max(1, hero.level)) - 1) / 17.0
        if e.get('scale') == 'range':
            return vals[0] + (vals[-1] - vals[0]) * x
        return vals[min(len(vals) - 1, int(x * len(vals)))]
    return vals[min(len(vals) - 1, max(0, rank - 1))]


class StatBuffs:
    def __init__(self, game):
        self.g = game
        self.active = []                 # [hero, source key, stat, full amount, start, end, attacks left, decays]
        self.started = False

    def effects(self, hero, key):
        seen, out = set(), []
        for e in (table().get(hero.name) or {}).get(key, []):
            k = 'reset' if e.get('reset') else e['stat']
            if k not in seen:
                seen.add(k)
                out.append(e)
        return out

    def on_cast(self, hero, slot, rank):
        if not 0 <= slot < 4:
            return
        g = self.g
        if hero.name == 'Nidalee' and slot == 3:
            # [wiki] Aspect of the Cougar: the cougar attacks in melee (125), the human at range (525, a missile)
            cougar = not getattr(hero, 'cougar', False)
            hero.cougar = cougar
            if not hasattr(hero, 'human_base'):
                hero.human_base = (hero.base.get('range', 525.0), hero.missile_speed)
            hero.base['range'] = 125.0 if cougar else hero.human_base[0]
            hero.missile_speed = 0.0 if cougar else hero.human_base[1]
            hero.recompute()
        if hero.name == 'Jinx' and slot == 0:
            hero.jinx_rockets = not getattr(hero, 'jinx_rockets', False)     # Q swaps Pow-Pow and Fishbones
            if hero.jinx_rockets:
                hero.remove_mods(('stacks', 'as'))
        for key, which in ((KEYS[slot], 'cast'), ('P', 'any_cast')):
            for e in self.effects(hero, key):
                if e.get('reset'):
                    if key != 'P':
                        hero.attack_ready = min(hero.attack_ready, g.t)
                    continue
                if e.get('on') != which:
                    continue
                t = e['time'] if isinstance(e['time'], (int, float)) else e['time'][min(len(e['time']) - 1, max(0, rank - 1))]
                v = amount(e, hero, rank)
                src = ('ability', key, e['stat'])
                self.active = [b for b in self.active if not (b[0] is hero and b[1] == src)]
                self.active.append([hero, src, e['stat'], v, g.t, g.t + t, e.get('attacks'), bool(e.get('decays'))])
                hero.add_mods(src, {e['stat']: v})

    def takedown(self, victim):
        """Jinx's passive [wiki]: a takedown of a champion, an epic monster, a turret or an inhibitor she damaged within
        3 s: a stack of Get Excited! for 6 s (25 % TOTAL attack speed each, up to 5; past the first only from
        champions) and 175 % bonus move speed decaying over 6 s"""
        g = self.g
        epic = victim.kind == 'monster' and any(k in victim.name for k in ('Baron', 'Dragon', 'dragon', 'Herald', 'Horde'))
        if not (victim.is_hero or victim.is_structure or epic):
            return
        for h in g.heroes:
            if h.name != 'Jinx' or not h.alive or h.team == victim.team:
                continue
            if g.t - victim.last_hit_by.get(h.net, -99.0) > 3.0:
                continue
            st = h.__dict__.setdefault('excited', {'n': 0, 'until': 0.0})
            n = st['n'] if g.t < st['until'] else 0
            st['n'] = min(5, n + 1) if victim.is_hero else max(1, n)
            st['until'] = g.t + 6.0
            h.remove_mods(('excited', 'as'))
            ratio = h.base.get('as_ratio', h.base.get('as', 0.625)) or 0.625
            h.add_mods(('excited', 'as'), {'as': 0.25 * st['n'] * h.attack_speed / ratio})
            src = ('excited', 'ms')
            self.active = [b for b in self.active if not (b[0] is h and b[1] == src)]
            self.active.append([h, src, 'ms_pct', 1.75, g.t, g.t + 6.0, None, True])
            h.add_mods(src, {'ms_pct': 1.75})
            until = st['until']
            g.at(until + 0.01, lambda t, h=h, u=until: h.excited['until'] <= u and h.remove_mods(('excited', 'as')))

    def stack_attack(self, hero):
        """an attack of a champion whose attack speed stacks with its attacks (STACK_AS)"""
        r = STACK_AS.get(hero.name)
        if r is None or (r.get('form') == 'minigun' and getattr(hero, 'jinx_rockets', False)):
            return
        g = self.g
        st = hero.__dict__.setdefault('as_stacks', {'n': 0, 'until': 0.0})
        st['n'] = min(r['max'], (st['n'] if g.t < st['until'] else 0) + 1)
        st['until'] = g.t + r['time']
        if 'first' in r:
            rank = max(1, hero.spell_levels[r['rank_slot']])
            first = r['first'][min(len(r['first']) - 1, rank - 1)]
            bonus = first + (st['n'] - 1) * first * (0.5 if r.get('half_after') else 1.0)
        else:
            lo, hi = r['level']
            bonus = st['n'] * (lo + (hi - lo) * (min(18, hero.level) - 1) / 17.0)
        hero.add_mods(('stacks', 'as'), {'as': bonus})
        until = st['until']
        g.at(until + 0.01, lambda t, h=hero, u=until: (h.as_stacks['until'] <= u) and (h.remove_mods(('stacks', 'as')),
                                                                                     h.as_stacks.update(n=0)))

    def perks(self, hero):
        tips = getattr(self.g, 'tooltips', None)
        return tips.perks(hero) if tips is not None else []

    def on_fire(self, hero, tgt):
        """an attack is let go (the end of its windup)"""
        if tgt.is_hero and tgt.team != hero.team and 8008 in self.perks(hero):
            self.tempo_stack(hero)
        st = getattr(hero, 'hail', None)
        if st is not None and st['state'] == 'active' and st['attacks'] >= HOB_ATTACKS:
            self.hail_end(hero)

    def tempo_buff(self, hero, duration, n):
        g, sp = self.g, self.g.spells
        if not hasattr(hero, 'buff_list'):
            hero.buff_list = {}
        slot = sp.buff_slot(hero) if sp is not None else 0x30
        known = g.vision is None or not g.vision.hidden(hero)
        hero.buff_list[('lethal_tempo',)] = {'slot': slot, 'until': g.t + duration, 'hash': LETHAL_TEMPO, 'undo': None,
                                             'known': known, 'args': (hero.net, slot, 27, LETHAL_TEMPO, 0)}
        if known:
            g.q += g.pk.buff_add(hero.net, hero.net, slot, 27, LETHAL_TEMPO, duration)
            g.q += g.pk.buff_counter(hero.net, slot, LETHAL_TEMPO, n)

    def tempo_end(self, hero):
        b = getattr(hero, 'buff_list', {}).pop(('lethal_tempo',), None)
        if b is not None and b.get('known', True):
            self.g.tell_all(self.g.pk.buff_remove(hero.net, b['slot'], LETHAL_TEMPO))

    def tempo_mods(self, hero, n):
        hero.remove_mods(('rune', 8008))
        if n > 0:
            melee = hero.base.get('range', 500.0) <= 300.0
            hero.add_mods(('rune', 8008), {'as': n * (LT_MELEE if melee else LT_RANGED)})

    def tempo_stack(self, hero):
        g = self.g
        st = hero.__dict__.setdefault('tempo', {'n': 0, 'until': 0.0})
        b = getattr(hero, 'buff_list', {}).get(('lethal_tempo',))
        n = min(LT_MAX, (st['n'] if b is not None else 0) + 1)
        if b is None:
            self.tempo_buff(hero, LT_TIME, n)
        else:
            b['until'] = g.t + LT_TIME
            if b.get('known', True):
                g.q += g.pk.buff_count(hero.net, b['slot'], hero.net, LT_TIME, 1)
                if n != st['n']:
                    g.q += g.pk.buff_counter(hero.net, b['slot'], LETHAL_TEMPO, n)
        st['n'], st['until'] = n, g.t + LT_TIME
        self.tempo_mods(hero, n)
        g.at(st['until'], lambda t, h=hero, u=st['until']: self.tempo_fall(h, u))

    def tempo_fall(self, hero, until):
        """the stacks' time is over: one falls (the buff ends and comes back a frame later with one less)"""
        g, st = self.g, hero.tempo
        if st['until'] > until + 1e-6:
            return                                   # a later stack renewed it
        self.tempo_end(hero)
        st['n'] = st['n'] - 1 if hero.alive else 0
        self.tempo_mods(hero, st['n'])
        if st['n'] <= 0:
            st['n'] = 0
            return
        from .game import SCRIPT_UPDATE

        def again(t, n=st['n']):
            if hero.tempo['n'] != n or ('lethal_tempo',) in getattr(hero, 'buff_list', {}) or not hero.alive:
                return
            self.tempo_buff(hero, LT_FALL, n)
            hero.tempo['until'] = t + SCRIPT_UPDATE
            g.at(hero.tempo['until'], lambda t2, u=hero.tempo['until']: self.tempo_fall(hero, u))
        g.at(g.t + FRAME, again)

    @staticmethod
    def melee(hero):
        return hero.base.get('range', 500.0) <= 300.0

    def hail_set(self, hero, name_hash, btype, duration, remove=None):
        """the Hail of Blades buff of this state, in the slot the last one had"""
        g = self.g
        if not hasattr(hero, 'buff_list'):
            hero.buff_list = {}
        old = hero.buff_list.pop(('hail',), None)
        if old is not None and old.get('known', True) and remove is not None:
            g.tell_all(g.pk.buff_remove(hero.net, old['slot'], remove))
        slot = old['slot'] if old else (g.spells.buff_slot(hero) if g.spells is not None else 0x30)
        known = g.vision is None or not g.vision.hidden(hero)
        hero.buff_list[('hail',)] = {'slot': slot, 'until': g.t + duration, 'hash': name_hash, 'undo': None,
                                     'known': known, 'args': (hero.net, slot, btype, name_hash, 0)}
        if known:
            g.q += g.pk.buff_add(hero.net, hero.net, slot, btype, name_hash, duration)

    def hail_start(self):
        for h in self.g.heroes:
            if 9923 in self.perks(h) and self.melee(h):
                h.hail = {'state': 'ready', 'attacks': 0, 'until': 0.0}
                self.hail_set(h, HOB_READY, 1, 25000.0)

    def hail_attack(self, hero, tgt):
        st = getattr(hero, 'hail', None)
        if st is None or tgt is None:
            return
        g = self.g
        if st['state'] == 'ready' and tgt.is_hero and tgt.team != hero.team:
            st.update(state='active', attacks=1, until=g.t + HOB_TIME)
            self.hail_set(hero, HOB_ACTIVE, 2, HOB_TIME, remove=HOB_READY)
            hero.add_mods(('rune', 9923), {'as': HOB_AS})
        elif st['state'] == 'active':
            st['attacks'] += 1
            st['until'] = g.t + HOB_TIME                  # its 282 at each attack: core/renewals.py (measured cause)
        else:
            return
        g.at(st['until'], lambda t, h=hero, u=st['until']: h.hail['state'] == 'active' and h.hail['until'] <= u + 1e-6
             and self.hail_end(h))

    def hail_end(self, hero):
        g, st = self.g, hero.hail
        st['state'] = 'cooldown'
        hero.remove_mods(('rune', 9923))
        self.hail_set(hero, HOB_COOLDOWN, 3, HOB_CD, remove=HOB_ACTIVE)

        def ready(t):
            if st['state'] == 'cooldown':
                st['state'] = 'ready'
                self.hail_set(hero, HOB_READY, 1, 25000.0, remove=HOB_COOLDOWN)
        g.script_timer(HOB_CD, ready, count=1, first=False)

    # ------------------------------------------------------------------ Conqueror
    def on_damage(self, src, tgt, dealt, basic, source, spell_hash):
        if not (src is not None and src.is_hero and tgt.is_hero and tgt.team != src.team and dealt > 0):
            return
        if 8010 not in self.perks(src) or source == P.SRC_PERIODIC or spell_hash in (P.elf('SummonerDot'), P.elf('Burning')):
            return
        g = self.g
        st = getattr(src, 'conq', None)
        if st is None:
            st = src.conq = {'n': 0, 'until': 0.0, 'by': {}, 'slot': None}
        if not basic:
            if g.t - st['by'].get(spell_hash, -99.0) < 4.0:
                return
            st['by'][spell_hash] = g.t
        melee = self.melee(src)
        gain = 1 if (basic and not melee) else 2
        if st['n'] >= 12:
            src.heal((0.08 if melee else 0.05) * dealt)
        first = st['n'] <= 0 or g.t >= st['until']
        st['n'] = min(12, (0 if first else st['n']) + gain)
        st['until'] = g.t + 5.0
        sp = g.spells
        if first or st['slot'] is None:
            st['slot'] = sp.buff_slot(src) if sp is not None else 0x30
            g.q += g.pk.buff_add(src.net, src.net, st['slot'], 2, CONQUEROR, 5.0)
        else:
            g.q += g.pk.buff_count(src.net, st['slot'], src.net, 5.0, 1)
        g.q += g.pk.buff_counter(src.net, st['slot'], CONQUEROR, st['n'])
        lvl = min(18, src.level)
        ad = 1.08 + (2.56 - 1.08) * (lvl - 1) / 17.0
        ap = 1.8 + (4.26 - 1.8) * (lvl - 1) / 17.0
        adaptive = {'ad': ad * st['n']} if src.bonus.get('ad', 0.0) >= src.bonus.get('ap', 0.0) else {'ap': ap * st['n']}
        src.add_mods(('rune', 8010), adaptive)
        until = st['until']

        def end(t, h=src, until=until):
            c = h.conq
            if c['until'] != until:
                return
            c['n'] = 0
            h.remove_mods(('rune', 8010))
            if c['slot'] is not None:
                g.q += g.pk.buff_remove(h.net, c['slot'], CONQUEROR)
                c['slot'] = None
        g.at(until + 0.2, end)

    # ------------------------------------------------------------------ Fleet Footwork
    def fleet_start(self, hero):
        st = hero.fleet = {'n': 0.0, 'told': None, 'last': hero.pos, 'on': False, 'energized': False}
        self.g.script_timer(0.0, lambda t, h=hero: self.fleet_update(h), alive=lambda: not self.g.over)
        return st

    def fleet_set(self, hero, on):
        g, sp = self.g, self.g.spells
        st = hero.fleet
        if on == st['on'] or sp is None:
            return
        st['on'] = on
        if not hasattr(hero, 'buff_list'):
            hero.buff_list = {}
        if on:
            slot = sp.buff_slot(hero)
            hero.buff_list[('fleet',)] = {'slot': slot, 'until': g.t + 3600.0, 'hash': FLEET, 'undo': None, 'known': True,
                                          'args': (hero.net, slot, 2, FLEET, 0)}
            g.q += g.pk.buff_add(hero.net, hero.net, slot, 2, FLEET, 25000.0)
            st['told'] = None
        else:
            b = hero.buff_list.pop(('fleet',), None)
            if b is not None:
                g.q += g.pk.buff_remove(hero.net, b['slot'], FLEET)

    def fleet_update(self, hero):
        st = getattr(hero, 'fleet', None)
        if st is None or not hero.alive:
            return
        moved = ((hero.pos[0] - st['last'][0]) ** 2 + (hero.pos[1] - st['last'][1]) ** 2) ** 0.5
        st['last'] = hero.pos
        if moved > 1500.0:
            moved = 0.0                                  # a teleport (recall, respawn)
        if not st['on']:
            if moved <= 0.0 or getattr(st, 'wait', 0.0) > self.g.t:
                return
            self.fleet_set(hero, True)
        st['n'] = min(100.0, st['n'] + moved / 24.0)
        self.fleet_tell(hero)

    def fleet_tell(self, hero):
        st = hero.fleet
        n = int(st['n'])
        b = hero.buff_list.get(('fleet',))
        if b is not None and n != st['told']:
            st['told'] = n
            self.g.q += self.g.pk.buff_counter(hero.net, b['slot'], FLEET, n)

    def fleet_attack(self, hero):
        st = getattr(hero, 'fleet', None)
        if st is None or not st['on']:
            return
        if st['n'] >= 100.0:
            g = self.g
            melee = self.melee(hero)
            lvl = min(18, hero.level)
            heal = (15.0 + (182.73 - 15.0) * (lvl - 1) / 17.0) if melee else (9.0 + (109.64 - 9.0) * (lvl - 1) / 17.0)
            heal += (0.10 if melee else 0.06) * hero.bonus.get('ad', 0.0) + (0.05 if melee else 0.03) * hero.bonus.get('ap', 0.0)
            st['n'], st['told'] = 0.0, None

            def spend(t, h=hero):
                self.fleet_set(h, False)
                g.after_frames(15, lambda t2, h=h: self.fleet_set(h, True))
            g.after_frames(1, spend)

            def land(t, h=hero, heal=heal, melee=melee):
                if not h.alive:
                    return
                h.heal(heal)
                h.add_mods(('rune', 8021), {'ms_pct': 0.20 if melee else 0.15})
                if g.spells is not None:
                    g.spells.respeed(h)
                    slot = g.spells.buff_slot(h)
                    g.q += g.pk.buff_add(h.net, h.net, slot, 15, FLEET_HASTE, 1.0)

                    def off(t2, h=h, slot=slot):
                        h.remove_mods(('rune', 8021))
                        g.spells.respeed(h)
                        g.q += g.pk.buff_remove(h.net, slot, FLEET_HASTE)
                    g.at(g.t + 1.0, off)
            g.at(g.t + (0.0 if melee else 0.47), land)
        else:
            st['n'] = min(100.0, st['n'] + 6.0)

    def on_attack(self, hero):
        """a basic attack has begun: the buffs for the next n attacks count it"""
        if getattr(hero, 'fleet', None) is not None:
            self.fleet_attack(hero)
        self.stack_attack(hero)
        self.hail_attack(hero, self.g.units.get(hero.windup_target))
        if hero.name == 'Jhin':
            # [wiki] Death in 4 Acts: four rounds, then a reload of 2.5 s
            hero.jhin_rounds = getattr(hero, 'jhin_rounds', 4) - 1
            if hero.jhin_rounds <= 0:
                hero.jhin_rounds = 4
                hero.attack_ready = max(hero.attack_ready, self.g.t + 2.5)
        for b in self.active:
            if b[0] is hero and b[6]:
                b[6] -= 1
                if b[6] <= 0:
                    b[5] = self.g.t                     # ends now; the attack under way keeps its speed

    def tick(self, t, dt):
        if not self.started:
            self.started = True
            self.hail_start()
            for h in self.g.heroes:
                if 8021 in self.perks(h):
                    self.fleet_start(h)
        keep = []
        for b in self.active:
            hero, src, stat, v, t0, t1, n, decays = b
            if t >= t1 or not hero.alive:
                hero.remove_mods(src)
                continue
            if decays:
                hero.add_mods(src, {stat: v * max(0.0, 1.0 - (t - t0) / max(0.01, t1 - t0))})
            keep.append(b)
        self.active = keep


def setup(game, session=None):
    game.statbuffs = StatBuffs(game)
    game.systems.append(game.statbuffs.tick)
