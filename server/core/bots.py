"""Champions nobody plays: a brain per bot, thinking four times a second.

What a bot knows comes from the game's own data wherever Riot left it there for its bots:
  - the skill order: the champion's RecSpellRankUpInfolist (mEarlyLevelOverrides for the first levels, then
    mDefaultPriority), LoL's own level rules (heroes.Hero.level_spell)
  - what to buy: the champion's ItemRecommendationOverrideSet for Summoner's Rift (a starting bundle, then the
    recommended items in order; a component of the next one when the whole is too dear)
  - what a spell is for: its BotData (damage calculation, effect tags) through spells.Info: a damaging spell goes
    at an enemy champion in its range (aimed ahead of a walking target by the missile's flight), an area spell also
    at three or more minions when mana is plenty, a heal when hurt, a dash to finish a kill or to get away
The rest is ours [a] (LoL's bots are scripts that are not shipped): the lane a role takes, standing behind the own
wave, last hits (attack a minion a basic attack would kill), trading with a champion in reach when healthier,
never under an enemy turret without two own minions there, going home to heal and shop when low or rich.
"""
import math

from . import gamedata as G
from . import packets as P
from . import spells as S
from .units import dist, ORDER, CHAOS, NEUTRAL

THINK = 0.25
LEAVE_BASE = 15.6                # the spawn barrier lifts at 15.084 [m]
ROLE_LANE = {'TOP': 'top', 'MIDDLE': 'mid', 'BOTTOM': 'bot', 'UTILITY': 'bot', 'JUNGLE': 'jungle'}
TURRET_REACH = 750.0 + 88.4
BOOTS = (3006, 3009, 3020, 3047, 3111, 3117, 3158, 3010, 3013, 1001)


class Brain:
    def __init__(self, game, hero):
        self.g, self.h = game, hero
        self.lane = ROLE_LANE.get(getattr(hero, 'role', 'MIDDLE'), 'mid')
        lanes = game.data['lanes']
        lane = self.lane if self.lane in lanes else 'mid'
        pts = [tuple(p) for p in lanes[lane]]
        self.path = pts if hero.team == ORDER else pts[::-1]          # from the own base to the enemy's
        self.cum = [0.0]
        for a, b in zip(self.path, self.path[1:]):
            self.cum.append(self.cum[-1] + dist(a, b))
        self.next_think = 0.0
        self.mode = 'base'               # base | lane | home | recall
        self.goal = None
        self.last_path = -9.0
        self.bought_start = False
        self.next_cast = 0.0
        self.jungle_i = 0
        self.stuck_since = None
        if self.lane == 'jungle':
            hero.jungler = True
            if 'SummonerSmite' not in getattr(hero, 'summoners', None) or []:
                hero.summoners = [S_FLASH, 'SummonerSmite']
        elif not getattr(hero, 'summoners', None):
            hero.summoners = [S_FLASH, 'SummonerHeal' if self.lane == 'bot' else 'SummonerDot']

    # ------------------------------------------------------------------ helpers
    def summoner(self, name):
        """the slot (4 / 5) that holds a summoner spell when it is ready, else None"""
        h = self.h
        if name in h.summoners:
            slot = 4 + h.summoners.index(name)
            if self.g.t >= h.cooldowns[slot]:
                return slot
        return None

    def along(self, p):
        """how far along the lane the point nearest to p is (and how far from the lane p is)"""
        best = (1e18, 0.0)
        for i in range(len(self.path) - 1):
            a, b = self.path[i], self.path[i + 1]
            dx, dz = b[0] - a[0], b[1] - a[1]
            L2 = dx * dx + dz * dz or 1.0
            k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / L2))
            d = math.hypot(p[0] - (a[0] + dx * k), p[1] - (a[1] + dz * k))
            if d < best[0]:
                best = (d, self.cum[i] + k * math.sqrt(L2))
        return best[1], best[0]

    def at_lane(self, s):
        s = max(0.0, min(self.cum[-1], s))
        for i in range(len(self.path) - 1):
            if s <= self.cum[i + 1]:
                a, b = self.path[i], self.path[i + 1]
                k = (s - self.cum[i]) / ((self.cum[i + 1] - self.cum[i]) or 1.0)
                return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        return self.path[-1]

    def walk(self, goal, t, force=False):
        h = self.h
        if not force and self.goal is not None and dist(self.goal, goal) < 120.0 and h.path:
            return
        if not force and t - self.last_path < 0.5 and h.path:
            return
        if dist(h.pos, goal) < 40.0:
            return
        self.goal, self.last_path = goal, t
        h.order = ('move', goal)
        h.target = None
        # along the lane when both ends are on it (open ground, no search), else the navigation grid
        s0, d0 = self.along(h.pos)
        s1, d1 = self.along(goal)
        if d0 < 350.0 and d1 < 350.0:
            lo, hi = min(s0, s1), max(s0, s1)
            mids = [p for p, c in zip(self.path, self.cum) if lo + 50 < c < hi - 50]
            if s1 < s0:
                mids.reverse()
            h.go(mids + [goal])
        else:
            h.path_to(goal)

    def danger(self, p, slack=120.0):
        """an enemy turret that would shoot a champion standing at p (fewer than two own minions in its reach)"""
        g, h = self.g, self.h
        for tu in g.turrets:
            if tu.alive and tu.team != h.team and dist(p, tu.pos) < (1250.0 if tu.tier == 'fountain' else TURRET_REACH) + h.radius + slack:
                if tu.tier == 'fountain':
                    return tu
                cover = sum(1 for m in g.minions if m.alive and m.team == h.team and dist(m.pos, tu.pos) < TURRET_REACH + 60)
                if cover < 2 or tu.target == h.net:
                    return tu
        return None

    # ------------------------------------------------------------------ levels and items
    def on_level(self):
        h = self.h
        c = h.champ
        guard = 0
        while h.skill_points() > 0 and guard < 6:
            guard += 1
            order = []
            if h.level <= len(c.skill_early):
                order.append(c.skill_early[h.level - 1])
            order += [3] + list(c.skill_priority) + [0, 1, 2]
            if not any(h.level_spell(s) for s in order):
                break

    def shop(self):
        g, h = self.g, self.h
        shop = getattr(g, 'shop', None)
        if shop is None or not shop.in_range(h):
            return
        rec = h.champ.items
        db = shop.db
        if not self.bought_start:
            self.bought_start = True
            for item in (rec['start'][0] if rec['start'] else [1055, 2003]):
                shop.buy(h, item)
            shop.buy(h, 3340)
        for _ in range(8):
            core = [i for i in rec['core'] if i in db and db[i]['in_store']] or [3078, 3071, 3053]
            owned = [i for i in h.inventory[:6] if i is not None]
            if not any(i in BOOTS for i in owned) and h.gold >= 300 and len(owned) >= 2:
                want = 1001
            else:
                want = next((i for i in core if i not in owned), None)
            if want is None:
                break
            item = self.affordable(want, db)
            if item is None:
                break
            if len([i for i in h.inventory[:6] if i is not None]) >= 6 and not S_price(item, h.inventory)[1]:
                # full: sell a starting item or a potion to make room
                slot = next((s for s, i in enumerate(h.inventory[:6]) if i in (1054, 1055, 1056, 2003, 1082, 1083, 3070)), None)
                if slot is None:
                    break
                shop.sell(h, slot)
            if 'buys' not in shop.buy(h, item):
                break

    def affordable(self, want, db, depth=0):
        """the item itself when the gold is enough, else its dearest component that is (and not owned)"""
        h = self.h
        cost, used = S_price(want, h.inventory)
        if cost <= h.gold:
            return want
        if depth > 3:
            return None
        best = None
        for c in db[want]['comps']:
            if c in h.inventory:
                continue
            x = self.affordable(c, db, depth + 1)
            if x is not None and (best is None or db[x]['total'] > db[best]['total']):
                best = x
        return best

    def next_cost(self):
        h = self.h
        shop = getattr(self.g, 'shop', None)
        if shop is None:
            return 1e9
        owned = [i for i in h.inventory[:6] if i is not None]
        core = [i for i in h.champ.items['core'] if i in shop.db and shop.db[i]['in_store']] or [3078, 3071, 3053]
        want = next((i for i in core if i not in owned), None)
        return S_price(want, h.inventory)[0] if want else 1e9

    # ------------------------------------------------------------------ thinking
    def think(self, t):
        h, g = self.h, self.g
        if t < self.next_think or not h.alive:
            if not h.alive:
                self.mode = 'base'
            return
        self.next_think = t + THINK
        if h.skill_points() > 0:
            self.on_level()
        if h.dashing or t < h.casting_until or t < h.cc_until:
            return
        at_home = dist(h.pos, h.home) < 900.0
        if self.mode == 'base':
            self.shop()
            if t >= LEAVE_BASE and h.hp >= 0.95 * h.max_hp:
                self.mode = 'lane'
            return
        if self.mode == 'recall':
            if h.recalling is None:
                self.mode = 'base' if at_home else 'lane'
            return
        low = h.hp < 0.28 * h.max_hp
        calm = not any(e.alive and e.team != h.team and dist(e.pos, h.pos) < 1300.0 and g.seen_by(h.team, e) for e in g.heroes)
        # enough for the next item, or for a good part of it: time to shop [a: 1250 gold]
        rich = h.gold >= max(900.0, min(self.next_cost(), 1250.0)) and (h.hp < 0.75 * h.max_hp or calm)
        if self.mode != 'home' and (low or rich):
            self.mode = 'home'
        if self.mode == 'home':
            return self.go_home(t)
        if self.lane == 'jungle' and g.jungle is not None:
            foes = [e for e in g.heroes if e.alive and e.team != h.team and dist(e.pos, h.pos) < 900.0 and g.seen_by(h.team, e)]
            foe = self.pick_foe(foes)
            if foe is not None and h.hp > 0.5 * h.max_hp:      # a champion in its jungle: fight it
                self.use_spells(t, foe, [])
                if h.target != foe.net:
                    h.order_attack(foe.net)
                return
            return self.jungle(t)
        self.laning(t)

    def go_home(self, t):
        h, g = self.h, self.g
        if dist(h.pos, h.home) < 900.0:
            self.mode = 'base'
            return
        threats = [e for e in g.heroes if e.alive and e.team != h.team and dist(e.pos, h.pos) < 1400.0 and g.seen_by(h.team, e)]
        if not threats and not self.danger(h.pos) and h.recalling is None and t >= h.in_combat_until - 2.0:
            if g.spells is not None:
                g.spells.recall(h)
                self.mode = 'recall'
                return
        if threats:
            self.escape(t, threats)
        s, off = self.along(h.pos)
        self.walk(self.at_lane(max(0.0, s - 1500.0)) if s > 1600.0 else h.home, t)

    def escape(self, t, threats):
        """use what gets it away: a dash or blink towards home, Flash when nearly dead"""
        h, g = self.h, self.g
        if g.spells is None or t < self.next_cast:
            return
        near = min(dist(e.pos, h.pos) for e in threats)
        away = self.at_lane(max(0.0, self.along(h.pos)[0] - 600.0))
        for slot in range(min(4, len(h.champ.spells))):
            inf = S.info(h.champ, h.spell_name(slot))
            if (inf.dash or inf.blink) and g.spells.can_cast(h, slot) is None and near < 700.0:
                g.spells.cast(h, slot, away)
                self.next_cast = t + 0.6
                return
        flash = self.summoner(S_FLASH)
        if flash is not None and h.hp < 0.15 * h.max_hp and near < 500.0:
            g.spells.summoner(h, flash, away, 0)
            self.next_cast = t + 0.6
        for name in ('SummonerHeal', 'SummonerBarrier'):
            slot = self.summoner(name)
            if slot is not None and h.hp < 0.3 * h.max_hp:
                g.spells.summoner(h, slot, h.pos, 0)

    def laning(self, t):
        h, g = self.h, self.g
        here = h.pos
        s_here, off = self.along(here)
        # --- what is around
        foes = [e for e in g.heroes if e.alive and e.team != h.team and dist(e.pos, here) < 1300.0 and g.seen_by(h.team, e)]
        minions = [m for m in g.minions if m.alive and m.team != h.team and dist(m.pos, here) < 1100.0 and g.seen_by(h.team, m)]
        mine = [m for m in g.minions if m.alive and m.team == h.team and m.lane == self.lane]
        tower = self.danger(here)
        if tower is not None and (tower.target == h.net or not foes):
            # under an enemy turret without cover: out, along the lane
            h.target = None
            self.walk(self.at_lane(max(0.0, self.along(tower.pos)[0] - TURRET_REACH - 350.0)), t, force=h.order is None or h.order[0] != 'move')
            return
        if h.hp < 0.4 * h.max_hp and g.spells is not None and foes:
            for name in ('SummonerHeal', 'SummonerBarrier'):
                slot = self.summoner(name)
                if slot is not None:
                    g.spells.summoner(h, slot, here, 0)
                    break
        # --- an enemy champion in reach
        foe = self.pick_foe(foes)
        if foe is not None:
            self.use_spells(t, foe, minions)
            if h.in_reach(foe, 250.0) and not self.danger(foe.pos, 0.0):
                if h.target != foe.net:
                    h.order_attack(foe.net)
                return
        elif g.spells is not None and t >= self.next_cast and h.par > 0.55 * h.max_par and len(minions) >= 3:
            self.farm_spell(t, minions)
        # --- minions: the one a basic attack kills first, else the weakest in reach
        target = None
        reach = h.range + h.radius
        cand = [m for m in minions if dist(m.pos, here) <= reach + m.radius + 320.0 and not self.danger(m.pos, -40.0)]
        if cand:
            kill = [m for m in cand if m.hp <= g.mitigate(h, m, h.ad, P.PHYSICAL) * 1.05]
            target = min(kill, key=lambda m: m.hp) if kill else None
            if target is None and (not foes or h.hp > 0.6 * h.max_hp):
                near = [m for m in cand if dist(m.pos, here) <= reach + m.radius + 60.0]
                target = min(near, key=lambda m: m.hp) if near else None
        if target is None:
            # --- a structure, with the own wave on it
            for s_ in g.structures:
                if s_.alive and s_.targetable and s_.team != h.team and dist(s_.pos, here) <= reach + s_.radius + 500.0:
                    cover = sum(1 for m in g.minions if m.alive and m.team == h.team and dist(m.pos, s_.pos) < TURRET_REACH + 100)
                    if (cover >= 2 or s_.kind != 'turret') and not [e for e in foes if dist(e.pos, s_.pos) < 900.0 and e.hp > h.hp]:
                        target = s_
                        break
        if target is not None:
            if h.target != target.net:
                h.order_attack(target.net)
            return
        # --- nothing to hit: stand behind the own wave
        if h.target is not None:
            h.order_stop()
        front = max((self.along(m.pos)[0] for m in mine), default=None)
        back = 150.0 if h.champ.melee else 480.0
        if front is None:
            own = [self.along(tu.pos)[0] for tu in g.turrets if tu.alive and tu.team == h.team and tu.lane == self.lane and tu.tier in ('outer', 'inner', 'inhibitor')]
            s = (max(own) - 200.0) if own else 1500.0
        else:
            s = front - back
        spot = self.at_lane(s)
        for _ in range(8):
            if not self.danger(spot, 60.0):
                break
            s -= 250.0
            spot = self.at_lane(s)
        if dist(here, spot) > 140.0:
            self.walk(spot, t)

    def pick_foe(self, foes):
        h = self.h
        best = None
        for e in foes:
            d = dist(e.pos, h.pos)
            if d > max(h.range + 500.0, 900.0):
                continue
            ratio = (h.hp / h.max_hp) - (e.hp / e.max_hp)
            if ratio < -0.25 and e.hp > 250.0:
                continue                           # it is the healthier one by far: not a fight to pick
            score = d + e.hp
            if best is None or score < best[0]:
                best = (score, e)
        return best[1] if best else None

    def use_spells(self, t, foe, minions):
        h, g = self.h, self.g
        sp = g.spells
        if sp is None or t < self.next_cast:
            return
        d = dist(h.pos, foe.pos)
        for slot in (3, 0, 1, 2):
            if slot >= len(h.champ.spells) or sp.can_cast(h, slot) is not None:
                continue
            inf = S.info(h.champ, h.spell_name(slot))
            rank = h.spell_levels[slot]
            if slot == 3 and foe.hp > 0.6 * foe.max_hp and 'Trait_Ultimate' in inf.tags:
                continue
            rng = inf.range(rank)
            if inf.targeting in S.SELF_TYPES:
                reach = inf.radius(rank) if (inf.aoe or inf.dot) and inf.radius(rank) > 0 else h.range + 250.0
                if d > reach + foe.radius:
                    continue
                aim = h.pos
            elif inf.dash or inf.blink:
                if not (foe.hp < 0.4 * foe.max_hp and d > h.range and d < rng + 200.0) or self.danger(foe.pos, 0.0):
                    continue
                aim = foe.pos
            else:
                if d > rng + foe.radius - 30.0:
                    continue
                aim = foe.pos
                if inf.missile_speed > 0 and foe.path:      # ahead of a walking target by the missile's flight
                    lead = inf.cast_time + d / inf.missile_speed
                    aim = (foe.pos[0] + foe.facing[0] * foe.speed * lead, foe.pos[1] + foe.facing[1] * foe.speed * lead)
            text = sp.cast(h, slot, aim, foe.net if inf.targeting in ('Target', 'TargetOrLocation') else 0)
            if ' casts ' in text:
                self.next_cast = t + 0.45
                return
        dot = self.summoner('SummonerDot')
        if dot is not None and foe.hp < 0.3 * foe.max_hp and d < 600.0:
            sp.summoner(h, dot, foe.pos, foe.net)

    def farm_spell(self, t, minions):
        h, sp = self.h, self.g.spells
        if not minions:
            return
        for slot in (0, 1, 2):
            if slot >= len(h.champ.spells) or sp.can_cast(h, slot) is not None:
                continue
            inf = S.info(h.champ, h.spell_name(slot))
            if inf.dash or inf.blink or inf.dmg_calc is None:
                continue
            rank = h.spell_levels[slot]
            if inf.targeting in S.SELF_TYPES:
                r = inf.radius(rank)
                if r > 0 and sum(1 for m in minions if dist(m.pos, h.pos) <= r) >= 3:
                    sp.cast(h, slot, h.pos)
                    self.next_cast = t + 1.0
                    return
            elif inf.aoe or not inf.stops_first:
                c = min(minions, key=lambda m: dist(m.pos, h.pos))
                if dist(c.pos, h.pos) <= inf.range(rank):
                    sp.cast(h, slot, c.pos, c.net if inf.targeting == 'Target' else 0)
                    self.next_cast = t + 1.0
                    return

    def jungle(self, t):
        """the jungler: the nearest living camp of its side, then the next"""
        h, g = self.h, self.g
        camp = g.jungle.next_camp(h)
        if camp is None:
            return self.laning(t)
        mo = min((m for m in camp['units'] if m.alive), key=lambda m: m.hp, default=None)
        if mo is None:
            return
        if h.in_reach(mo, 500.0) and g.seen_by(h.team, mo):
            if h.target != mo.net:
                h.order_attack(mo.net)
            big = max((m for m in camp['units'] if m.alive), key=lambda m: m.max_hp)
            smite = self.summoner('SummonerSmite')
            if smite is not None and big.max_hp > 1000 and big.hp <= 620.0 and g.spells is not None:
                g.spells.summoner(h, smite, big.pos, big.net)
            if g.spells is not None and t >= self.next_cast:
                self.farm_spell(t, [m for m in camp['units'] if m.alive])
        else:
            self.walk(mo.pos, t)


S_FLASH = 'SummonerFlash'


def S_price(item, inventory):
    from . import shop
    return shop.price(item, inventory)


def setup(game, session=None):
    player = session.player if session is not None else None
    for h in game.heroes:
        if h is not player and h.bot:
            h.brain = Brain(game, h)
