"""Summoner spells (slots D and F) and the recall.

The live server's form [measured: Garen's Flash at 387.167 s]: 1215 with the spell's name (SummonerFlash ...), slot 4
or 5, the cooldown (300 for Flash) and the package hash shared by summoner spells and items; a Flash is then a
teleport entry in the movement packet. Which two spells a champion has travels in its "enters sight" container
(1255, recorded). What each spell does is LoL's well known rule [a: the usual values]:
    Flash 400 units, 300 s      Ignite 70-410 true damage over 5 s, 180 s      Heal 80-318 + 30 % speed, 240 s
    Ghost +24-48 % speed for 15 s, 240 s     Barrier 120-480 shield 2.5 s, 180 s    Exhaust -40 % speed 3 s, 240 s
    Cleanse, Teleport, Smite: cooldown only for now
Recall: 8 s standing still, then the fountain (331 RecallChannelingUpdate is not written yet: the client shows no bar).
"""
import math

from . import gamedata as G
from . import packets as P
from .units import dist

FLASH, IGNITE, HEAL, GHOST, BARRIER, EXHAUST, TELEPORT, SMITE, CLEANSE = (
    'SummonerFlash', 'SummonerDot', 'SummonerHeal', 'SummonerHaste', 'SummonerBarrier', 'SummonerExhaust',
    'SummonerTeleport', 'SummonerSmite', 'SummonerBoost')
COOLDOWN = {FLASH: 300.0, IGNITE: 180.0, HEAL: 240.0, GHOST: 240.0, BARRIER: 180.0, EXHAUST: 240.0, TELEPORT: 300.0,
            SMITE: 90.0, CLEANSE: 240.0}
RECALL_TIME = 8.0
RECALL_LEAD = 0.5                 # [m] the recall's cast time before its channel begins
RECALL_UPDATE = 0.2625            # [m] 32 "RecallChannelingUpdate" in 8.02 s


class _Named:
    """the little a buff needs to know about a spell that is not a champion's"""
    def __init__(self, name):
        self.name = name


IGNITE_BONE = 0x0201a113           # [m] the target bone the recording's ignite effects name (an ELF hash)

def spells_of(hero):
    return getattr(hero, 'summoners', None) or [FLASH, IGNITE]


def cast(sp, hero, slot, aim, target):
    g, t = sp.g, sp.g.t
    name = spells_of(hero)[slot - 4]
    if not hero.alive or t < hero.cc_until:
        return f'{hero.name} {name}: cannot cast now'
    if t < hero.cooldowns[slot]:
        return f'{hero.name} {name}: on cooldown {hero.cooldowns[slot] - t:.0f} s'
    here = hero.pos
    dx, dz = aim[0] - here[0], aim[1] - here[1]
    d = math.hypot(dx, dz)
    direction = (dx / d, dz / d) if d > 1.0 else hero.facing
    tgt = g.units.get(target) if target else None
    if name in (IGNITE, EXHAUST, SMITE):
        if tgt is None:
            near = [(dist(o.pos, aim), o) for o in g.units.values() if o.alive and o.targetable and o.team != hero.team
                    and (o.is_hero if name != SMITE else o.kind in ('minion', 'monster')) and dist(o.pos, aim) <= 300.0]
            tgt = min(near, key=lambda x: x[0])[1] if near else None
        if tgt is None or dist(here, tgt.pos) > 700.0 + tgt.radius:
            return f'{hero.name} {name}: no target in range'
    cd = COOLDOWN.get(name, 240.0)
    sp.casts += 1
    end = aim
    if name == FLASH:
        reach = min(400.0, d) if d > 1.0 else 400.0
        end = g.nav.nearest_free(here[0] + direction[0] * reach, here[1] + direction[1] * reach) or here
    g.q += g.pk.cast(t, hero.net, name, slot, sp.casts, g.new_net(), g.new_net(), aim, end, here, direction, 0.0, 0.0, cd, 0.0,
                     tgt.net if tgt else 0, package=G.PACKAGE_GLOBAL, champion=hero.name)
    hero.cooldowns[slot] = t + cd
    inf = _Named(name)
    lvl = hero.level
    if name == FLASH:
        g.q += g.pk.face(hero, direction)
        hero.blink(end)
    elif name == IGNITE:
        total = 70.0 + 20.0 * (lvl - 1)
        sp.buff(hero, tgt, inf, 13, 5.0)
        fx = g.fx
        if fx is not None:                               # [m] Global_SS_Ignite on the target, a tick effect with each tick
            fx.shared('Global_SS_Ignite', hero, tgt, lasting=5.0, target_bone=IGNITE_BONE, target=True)

        def tick(t2, tgt=tgt):
            if tgt.alive:
                if fx is not None:
                    fx.shared('Global_SS_Ignite_Tick', hero, tgt, target_bone=IGNITE_BONE, target=True)
                g.deal(hero, tgt, total / 5.0, P.TRUE, basic=False, source=P.SRC_PERIODIC, spell_hash=P.elf(name))
        # [m: the replays' SummonerDot] five ticks of a 1 s script timer, the first at the buff's first update
        g.script_timer(1.0, tick, count=5)
    elif name == HEAL:
        amount = 80.0 + 14.0 * (lvl - 1)
        hero.set_hp(hero.hp + amount)
        ally = min((h for h in g.heroes if h is not hero and h.team == hero.team and h.alive and dist(h.pos, here) <= 850.0),
                   key=lambda h: h.hp / h.max_hp, default=None)
        if ally is not None:
            ally.set_hp(ally.hp + amount)
        sp.haste(hero, inf, 0.30, 1.0)
    elif name == GHOST:
        sp.haste(hero, inf, 0.24 + 0.24 * (lvl - 1) / 17.0, 15.0)
    elif name == BARRIER:
        hero.set_hp(hero.hp + 0.0)                       # shields are not modelled yet
    elif name == EXHAUST:
        sp.slow(hero, tgt, inf, 0.40, 3.0)
    elif name == SMITE:
        if g.fx is not None:
            g.fx.shared('SS_BaseSmite', hero, tgt, target_bone=P.elf('C_BUFFBONE_GLB_CHEST_LOC'), owner_place=False)
        g.deal(hero, tgt, 600.0, P.TRUE, basic=False, source=P.SRC_PERIODIC, spell_hash=P.elf(name))
        hero.cooldowns[slot] = t + 15.0                 # [a] smite's charges as a short cooldown
    return f'{hero.name} casts {name}' + (f' on {tgt.name}' if tgt else '')


def recall(sp, hero):
    g, t = sp.g, sp.g.t
    if not hero.alive or t < hero.cc_until or hero.recalling is not None:
        return f'{hero.name} recall: not now'
    if hero.path:
        hero.stop()
    hero.order = None
    hero.target = None
    # [m: a champion's recall in the live recording] the cast (slot 13, 0.5 s), then for 8.02 s: 612 {1, 7}, 794 (the
    # animation "Recall" / "recall"), 331 "RecallLeadIn" and 331 "RecallChannelingUpdate" every 0.26 s, the buff
    # (435: slot 1, type 1, 7.9 s, the map's package) and the old particle TeleportHome on the champion; at its end
    # 584 (the particle), 794 (empty), 262, and the champion is at its fountain
    hero.recalling = t + RECALL_LEAD + RECALL_TIME
    token = hero.recalling
    sp.casts += 1
    pk = g.pk
    g.q += pk.cast(t, hero.net, 'recall', 13, sp.casts, g.new_net(), g.new_net(), hero.pos, hero.pos, hero.pos, hero.facing,
                   RECALL_LEAD, RECALL_LEAD + RECALL_TIME, 0.0, 0.0, hero.net, package=G.PACKAGE_MAP, champion=hero.name,
                   flag=4)
    state = {'fx': None, 'on': False}

    def text331(s):
        return (1, 331, hero.net, pk.enc(331, {'+0x10': P.text(s)}))

    def channel(t2):
        if not hero.alive or hero.recalling != token:
            return
        state['on'] = True
        g.q.append((1, 612, hero.net, pk.enc(612, {'+0x10': '01', '+0x11': '07', '+0x12': '0000'})))
        g.q.append((1, 794, hero.net, pk.enc(794, {'+0x10': P.text('Recall'), '+0x20': P.text('recall'), '+0x30': '00'})))
        g.q.append(text331('RecallLeadIn'))
        if g.fx is not None:
            state['fx'] = g.fx.shared('TeleportHome', hero, hero, target=True, old='particles')
        g.q += pk.buff_add(hero.net, hero.net, 1, 1, P.elf('recall'), RECALL_TIME - 0.1, package=G.PACKAGE_MAP)
        n = int(RECALL_TIME / RECALL_UPDATE)
        for i in range(n):
            g.at(t2 + 0.11 + i * RECALL_UPDATE, lambda t3: hero.recalling == token and g.q.append(text331('RecallChannelingUpdate')))

    def end(t2=None):
        """the channel's packets taken back (its end, or it was broken)"""
        if not state['on']:
            return
        state['on'] = False
        if state['fx'] is not None and g.fx is not None:
            g.fx.remove(state['fx'])
        g.q.append((1, 794, hero.net, pk.enc(794, {'+0x10': P.text(''), '+0x20': P.text(''), '+0x30': '00'})))
        g.tell_all(pk.buff_remove(hero.net, 1, P.elf('recall')))

    def done(t2):
        if hero.alive and hero.recalling == token:
            hero.recalling = None
            end()
            hero.teleport(hero.home)
    hero.recall_end = end
    g.at(t + RECALL_LEAD, channel)
    g.at(t + RECALL_LEAD + RECALL_TIME, done)
    return f'{hero.name} recalls'
