"""The jungle: camps of neutral monsters.

Measured on the live recording (every creation of the match, tools/build_forms16.py -> forms16.json 'jungle'):
  - a monster is created for everyone, seen or not, with 514 (camp unit: a hash, the spawn animation's length, the
    monster's net id, the camp's number, the place) and 568 (its name "<Character>.<camp>.<index>", the place, the
    net id, the spawn animation's length and name, the camp's number, 3 / 4 for the red / blue buff, the camp's
    level, the time, the side 100 / 200 / 300, the character), then its replicated values (the lane minion's tables)
    and 967 {0, 1}
  - it is created one spawn animation before the camp's own time: the buffs, raptors and wolves are due at 55.1 s,
    gromp and krugs at 67.1, the river crabs at 175.1, the dragon at 300.1, the void grubs at 480.1, the herald at
    900.1, the baron at 1200.1 (creation time + animation length, every camp)
  - monsters attack with the minion's attack packet (390)
Where each monster of a camp stands, and its numbers: the map's own entities and the characters' records
(gamedata). Ours [a]: the times to come back after a camp is cleared (LoL's usual: 135 s, buffs 300 s, crabs 150 s,
dragon 300 s, baron 360 s), a monster's patience (it gives up 900 away from its camp and heals), the buffs' effect.
"""
import math

from . import gamedata as G
from . import packets as P
from .units import Monster, dist, NEUTRAL

DUE = {'SRU_Red': 55.1, 'SRU_Blue': 55.1, 'SRU_Razorbeak': 55.1, 'SRU_Murkwolf': 55.1, 'SRU_Gromp': 67.1, 'SRU_Krug': 67.1,
       'Sru_Crab': 175.1, 'SRU_Horde': 480.1, 'SRU_RiftHerald': 900.1, 'SRU_Baron': 1200.1}
RESPAWN = {'SRU_Red': 300.0, 'SRU_Blue': 300.0, 'Sru_Crab': 150.0, 'SRU_Baron': 360.0, 'SRU_Horde': None, 'SRU_RiftHerald': None}
EPIC = ('SRU_Baron', 'SRU_RiftHerald', 'SRU_Horde', 'sru_dragon')
DRAGONS = ['sru_dragon_air', 'sru_dragon_earth', 'sru_dragon_fire', 'sru_dragon_water', 'sru_dragon_hextech', 'sru_dragon_chemtech']
BUFF_TIME = 120.0


def hp_growth(character, level):
    """[m: the replays' replicated mMaxHP of every camp by its level] +10 % a level up to 11, then +5 % (the buffs +10 %)"""
    late = 0.10 if character in ('SRU_Blue', 'SRU_Red') else 0.05
    return 1.0 + 0.1 * (min(level, 11) - 1) + late * max(0, level - 11)


def ad_growth(level):
    """[m: the camps' damage on champions by level, 5 replays (the small monsters exact)] +5 % a level up to 6, +10 % up
    to 10, then +15 %"""
    return 1.0 + 0.05 * (min(level, 6) - 1) + 0.1 * max(0, min(level, 10) - 6) + 0.15 * max(0, level - 10)


def xp_growth(level):
    """[m: the jungler's mExp at each kill, levels 1 and 4 - 8] 1.0 at level 1, 1.3 at 4, + 5 % a level, at most 1.5
    (levels 2 - 3 not seen [a])"""
    return 1.0 if level <= 1 else min(1.5, 1.1 + 0.05 * level)


class Jungle:
    def __init__(self, game):
        self.g = game
        forms = game.pk.forms['jungle']
        placed = [m for m in game.data['monsters']]
        self.camps = {}
        for name, e in forms.items():
            cid = e['camp']
            c = self.camps.setdefault(cid, {'id': cid, 'side': e['side'], 'pos': (e['pos'][0], e['pos'][2]), 'members': [],
                                            'units': [], 'alive': False, 'due': None, 'level': 1})
            if e['character'].lower().startswith('sru_dragon'):
                if any(m['character'].lower().startswith('sru_dragon') for m in c['members']):
                    continue                        # one dragon stands in the pit at a time: the kind is chosen at spawn
            c['members'].append({'name': name, 'character': e['character'], 'anim': e['anim'], 'values': e['values'],
                                 'camp_unit': e.get('camp_unit'),
                                 'wait': P.struct.unpack('<f', bytes.fromhex(e['values']['+0x48']))[0]})
        # where each member stands: the map's own monster of that character nearest to the camp, each used once
        for c in self.camps.values():
            for m in c['members']:
                ch = m['character']
                if ch.lower().startswith('sru_dragon'):
                    cand = [p for p in placed if p['character'].lower().startswith('sru_dragon')]
                else:
                    cand = [p for p in placed if p['character'] == ch and dist(p['pos'], c['pos']) < 900.0]
                if cand:
                    best = min(cand, key=lambda p: dist(p['pos'], c['pos']))
                    m['pos'] = tuple(best['pos'])
                    if not ch.lower().startswith('sru_dragon'):
                        placed.remove(best)
                else:
                    k = c['members'].index(m)
                    m['pos'] = (c['pos'][0] + 90.0 * math.cos(k * 1.3), c['pos'][1] + 90.0 * math.sin(k * 1.3))
            first = c['members'][0]['character']
            key = 'sru_dragon' if first.lower().startswith('sru_dragon') else first
            c['kind'] = key
            due = 300.1 if key == 'sru_dragon' else DUE.get(key, 67.1)
            c['respawn'] = 300.0 if key == 'sru_dragon' else RESPAWN.get(key, 135.0)
            wait = max(m['wait'] for m in c['members'])
            game.at(due - wait, lambda t, c=c, due=due: self.spawn(c, due))
        self.dragons = 0

    # ------------------------------------------------------------------ a camp appears
    def spawn(self, c, due):
        g, t = self.g, self.g.t
        if g.over:
            return
        c['units'] = []
        c['alive'] = True
        c['due'] = due
        heroes = [h.level for h in g.heroes]
        # [m: 4 replays, every 568 +0x58] the first camps are level 1; a camp that comes back is the champions'
        # average level rounded down, + 1 (dragons: their own rule, not measured yet)
        first = c.get('spawned', 0) == 0
        c['spawned'] = c.get('spawned', 0) + 1
        c['level'] = 1 if first else max(1, min(18, int(sum(heroes) / len(heroes) + 1e-6) + 1))
        for m in c['members']:
            ch = m['character']
            if c['kind'] == 'sru_dragon':
                ch = 'sru_dragon_elder' if self.dragons >= 4 else DRAGONS[(self.dragons + g.rng.randrange(1)) % len(DRAGONS)]
            base = G.unit(ch) or G.unit(m['character'])
            if base is None:
                continue
            base = dict(base)
            base['hp'] *= hp_growth(ch, c['level'])
            base['ad'] *= ad_growth(c['level'])
            net = g.new_net()
            u = Monster(g, net, ch, m['pos'], base, c['id'])
            u.targetable = False
            u.member = m
            g.monsters.append(g.add(u))
            c['units'].append(u)
            name = f"{ch}.{c['id']}.{c['members'].index(m) + 1}"
            u.spawn_name = name                          # [m] the monster's own name (568), the same in Riot's matches
            v = dict(m['camp_unit'] or g.pk.form('camp_unit')[1])
            v.update({'+0x14': m['values']['+0x48'], '+0x18': P.u32(net), '+0x1c': f"{c['id']:02x}",
                      '+0x20': P.vec3(u.pos[0], 60.0, u.pos[1])})
            g.q_all.append((1, 514, 0, g.pk.enc(514, v)))
            v = dict(m['values'])
            v.update({'+0x10': P.text(name), '+0x20': g.pk.at3(u.pos), '+0x2c': P.u32(net), '+0x3c': g.pk.at3(u.pos),
                      '+0x58': P.u32(c['level']), '+0x60': P.f32(t), '+0x64': g.pk.at3(u.pos), '+0x80': P.text(name),
                      '+0xb0': P.text(ch)})
            g.q_all.append((1, 568, net, g.pk.enc(568, v)))
            g.q_all += g.pk.leash_state(net, 1)
            g.stat_outputs(u, queue='q_all')
            g.q_all.append((1, 967, net, g.pk.enc(967, {'+0x10': '00', '+0x11': '01'})))
            u.dirty = self.values(u)
            u.level = 1
            u.camp_level = c['level']
            g.entered(u)
        g.at(due, lambda t2, c=c: self.open(c))

    def values(self, u):
        mv = self.g.pk.forms['monster_values']
        v = dict(next(iter(mv.values()))) if mv else {}
        v.update({'mHP': u.hp, 'mMaxHP': u.max_hp, 'mBaseAttackDamage': u.base_ad, 'mArmor': u.armor, 'mSpellBlock': u.mr,
                  'mAttackRange': u.range, 'mMoveSpeed': u.speed, 'mIsTargetable': 0, 'mIsTargetableToTeamFlags': 3,
                  'mPAR': 0.0, 'mMaxPAR': 0.0, 'mCritDamageMultiplier': 2.0})
        return v

    def open(self, c):
        for u in c['units']:
            if u.alive:
                u.targetable = True
                u.set_many({'mIsTargetable': 1, 'mIsTargetableToTeamFlags': 4})

    # ------------------------------------------------------------------ a monster dies
    def on_death(self, u, killer):
        g = self.g
        c = self.camps.get(u.camp)
        if c is None:
            return
        if any(x.alive for x in c['units']):
            return
        c['alive'] = False
        kind = c['kind']
        if killer is not None and killer.is_hero:
            if kind in ('SRU_Red', 'SRU_Blue'):
                self.buff(killer, kind)
            elif kind == 'sru_dragon':
                self.dragons += 1
                for h in g.heroes:
                    if h.team == killer.team:
                        h.add_gold(25.0)
                        h.add_mods(f'dragon{self.dragons}', {'ad': 4.0, 'ap': 6.0})
            elif kind == 'SRU_Baron':
                for h in g.heroes:
                    if h.team == killer.team:
                        h.add_gold(300.0)
                        h.add_mods('baron', {'ad': 24.0, 'ap': 40.0})
                        g.at(g.t + 180.0, lambda t2, h=h: h.remove_mods('baron'))
            g.log(f'{killer.name} clears camp {c["id"]} ({kind})')
        if c['respawn']:
            due = g.t + c['respawn']
            wait = max(m['wait'] for m in c['members'])
            g.at(due - wait, lambda t2, c=c, due=due: self.spawn(c, due))

    def buff(self, hero, kind):
        """[a] the buffs as modifiers for two minutes: blue = mana regeneration and ability haste, red = health
        regeneration (its burn and slow on attacks are not modelled)"""
        g = self.g
        if kind == 'SRU_Blue':
            hero.add_mods('blue_buff', {'par_regen': 5.0 + 0.01 * hero.max_par, 'haste': 10.0})
            g.at(g.t + BUFF_TIME, lambda t2: hero.remove_mods('blue_buff'))
        else:
            hero.add_mods('red_buff', {'hp_regen': 0.01 * hero.max_hp / 5.0 * 3.0})
            g.at(g.t + BUFF_TIME, lambda t2: hero.remove_mods('red_buff'))

    # ------------------------------------------------------------------ for the bots
    def next_camp(self, hero):
        """the nearest living camp of the champion's own side that it can take alone"""
        side = hero.team
        best = None
        for c in self.camps.values():
            if not c['alive'] or not any(u.alive and u.targetable for u in c['units']):
                continue
            if c['kind'] in ('SRU_Baron', 'SRU_RiftHerald', 'SRU_Horde') or (c['kind'] == 'sru_dragon' and hero.level < 9):
                continue
            if c['side'] not in (side, 300) or (c['side'] == 300 and hero.level < 3):
                continue
            d = dist(hero.pos, c['pos'])
            if best is None or d < best[0]:
                best = (d, c)
        return best[1] if best else None


def setup(game, session=None):
    game.jungle = Jungle(game)
