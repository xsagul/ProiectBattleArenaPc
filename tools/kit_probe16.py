"""What our server does with one champion's kit, offline: the champion (level, spell ranks chosen) casts one spell (and its
recasts) at an enemy champion, a lane minion and a jungle monster placed in front of it, and every effect is logged with
its time: damage (amount, type, name), crowd control and buffs given (type, seconds), dashes / teleports, heals, the
caster's stats when they change, its spell slots and cooldowns. Used champion by champion against the wiki's text.

    python tools/kit_probe16.py <Champion> <Q|W|E|R|A> [--level 18] [--rank 5] [--recast 1.2,1.2] [--dist 300]
                                [--seconds 5] [--attacks n]
      A = basic attacks only (n attacks at the champion)
"""
import argparse
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
os.environ.setdefault('BA_PATCH', '1620')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('champion')
    ap.add_argument('slot')
    ap.add_argument('--level', type=int, default=18)
    ap.add_argument('--rank', type=int, default=0)
    ap.add_argument('--recast', default='')
    ap.add_argument('--dist', type=float, default=300.0)
    ap.add_argument('--seconds', type=float, default=5.0)
    ap.add_argument('--attacks', type=int, default=0)
    ap.add_argument('--enemy', default='Garen')
    ap.add_argument('--before', default='', help='slots cast before the probed one (e.g. W for Aphelios)')
    a = ap.parse_args()

    from core.session import Session
    from core.game import DT
    from core import packets as P
    import elf_names16
    logs = []
    enemy = a.enemy if a.enemy != a.champion else 'Darius'
    roster = [{'champion': a.champion}] + [{} for _ in range(4)] + [{'champion': enemy}] + [{} for _ in range(4)]
    s = Session(roster, log=logs.append, options={'no_fog': True})
    g = s.game
    g.start_packets()
    me, foe = s.player, g.heroes[5]
    for h in g.heroes:
        h.brain = None
    table = g.data['xp_per_level']
    if a.level > 1:
        me.add_xp(table[min(a.level, len(table)) - 2] + 1)
    for _ in range(18):
        for slot in (3, 0, 1, 2):
            if a.rank and me.spell_levels[slot] >= (min(a.rank, 3) if slot == 3 else a.rank):
                continue
            me.level_spell(slot)
    base = (7000.0, 7000.0)
    me.teleport(base)
    me.facing = (1.0, 0.0)
    foe.teleport((base[0] + a.dist, base[1]))
    foe.set_hp(foe.max_hp)
    # a minion and a monster near the champion target, for the spell's other rules
    minion = next((m for m in g.minions if m.alive and m.team != me.team), None)
    monster = next((m for m in g.monsters if m.alive), None)
    for u, off in ((minion, (a.dist + 120.0, 120.0)), (monster, (a.dist + 120.0, -140.0))):
        if u is not None:
            u.teleport((base[0] + off[0], base[1] + off[1]))
            u.path = None
            u.brain = None if hasattr(u, 'brain') else None
            u.next_think = 1e9
    watch = {me.net: me.name, foe.net: 'champion ' + foe.name}
    if minion is not None:
        watch[minion.net] = 'minion'
    if monster is not None:
        watch[monster.net] = 'monster ' + monster.name
    for _ in range(3):                                   # the kits' first tick (their start state) before the cast
        g.step(DT)
    me.cooldowns = [0.0] * len(me.cooldowns)             # the cast is probed, not the match's start (Aurelion Sol's W)
    me.teleport(base)
    foe.teleport((base[0] + a.dist, base[1]))
    t0 = g.t
    events = []

    def who(n):
        return watch.get(n, f'{n:08x}')
    real_deal = g.deal

    def deal(src, tgt, amount, dtype=P.PHYSICAL, basic=False, source=P.SRC_ATTACK, crit=False, spell_hash=0):
        hp = tgt.hp
        out = real_deal(src, tgt, amount, dtype, basic, source, crit, spell_hash)
        if src is me or tgt is me:
            nm = elf_names16.name(P.u32(spell_hash)) if spell_hash else ('basic' if basic else '')
            events.append((g.t - t0, f'damage {who(src.net) if src else "-"} -> {who(tgt.net)}: {amount:.1f} raw, {out:.1f} taken '
                                     f'({["physical", "magic", "true"][dtype] if dtype in (0, 1, 2) else dtype}) {nm or ""}'))
        return out
    g.deal = deal

    class Hook:
        def on_buff_add(self, tgt, caster, slot, h):
            if tgt in watch or caster in watch:
                events.append((g.t - t0, f'buff + {elf_names16.name(P.u32(h)) or P.u32(h)} on {who(tgt)} by {who(caster)}'))

        def on_buff_remove(self, tgt, slot):
            if tgt in watch:
                events.append((g.t - t0, f'buff - slot {slot:02x} on {who(tgt)}'))
    g.pk.buff_hooks.append(Hook())
    last = {}

    def snap():
        st = {'hp': round(me.hp, 1), 'ad': round(me.base_ad + me.bonus['ad'], 1), 'as': round(me.attack_speed, 3),
              'ms': round(me.speed, 1), 'range': round(me.base.get('range', 0) + me.bonus.get('range', 0), 1),
              'pos': (round(me.pos[0]), round(me.pos[1])), 'foe': (round(foe.pos[0]), round(foe.pos[1])),
              'foe_ms': round(foe.speed, 1), 'slots': tuple(me.spell_name(i) for i in range(4)),
              'cd': tuple(round(max(0.0, c - g.t), 1) for c in me.cooldowns[:4])}
        for k, v in st.items():
            if last.get(k) != v:
                if k != 'cd' or k not in last or any(x > y + 0.05 for x, y in zip(v, last[k])):
                    events.append((g.t - t0, f'{k} {last.get(k)} -> {v}'))
                last[k] = v
    snap()
    slot = 'QWER'.index(a.slot) if a.slot in 'QWER' else None
    for b in a.before:
        events.append((g.t - t0, 'before: ' + g.spells.cast(me, 'QWER'.index(b), foe.pos, foe.net)))
        for _ in range(30):
            g.step(DT)
    recasts = [float(x) for x in a.recast.split(',') if x]
    when = [0.0]
    for x in recasts:
        when.append(when[-1] + x)
    casted = set()
    n_att = 0
    while g.t - t0 < a.seconds:
        el = g.t - t0
        if slot is not None:
            for i, w in enumerate(when):
                if i not in casted and el >= w:
                    casted.add(i)
                    events.append((el, 'cast: ' + g.spells.cast(me, slot, foe.pos, foe.net)))
        if a.attacks and n_att < a.attacks and me.target != foe.net:
            me.target = foe.net
            me.order = ('attack', foe.net)
        g.step(DT)
        snap()
    for t, e in events:
        print(f'{t:6.2f}  {e}')


if __name__ == '__main__':
    main()
