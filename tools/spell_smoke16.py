"""Every champion's Q / W / E / R cast by our server at an enemy champion standing near, offline (no client): each
spell's template is played, so every packet it makes is encoded - a field our writers cannot fill shows as an error.

    python tools/spell_smoke16.py [Champion ..] [--workers n]     -> data/exe1620/spells16/smoke.txt (+ printed)

Per spell: what the cast request answered, the packets the 4 s after it held (by id), the template errors.
"""
import collections
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
os.environ.setdefault('BA_PATCH', '1620')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'spells16')


def smoke(champ, enemy='Garen'):
    from core.session import Session
    from core.game import DT
    logs = []
    roster = [{'champion': champ}] + [{} for _ in range(4)] + [{'champion': enemy if enemy != champ else 'Darius'}] + [{} for _ in range(4)]
    s = Session(roster, log=logs.append, options={'no_fog': True})
    g = s.game
    g.start_packets()
    me = s.player
    foe = g.heroes[5]
    for h in g.heroes:
        h.brain = None
    me.add_xp(g.data['xp_per_level'][16] + 1)
    for _ in range(18):
        for slot in (3, 0, 1, 2):
            me.level_spell(slot)
    out = []
    for slot in range(4):
        me.teleport((7000.0, 7000.0))
        foe.teleport((7350.0, 7000.0))
        foe.set_hp(foe.max_hp)
        me.cooldowns = [0.0] * 6
        me.set_par(me.max_par)
        me.slot_names = list(me.champ.spells)
        n0 = len(logs)
        res = g.spells.request(me, {'slot': slot, 'target': foe.net, 'target_place': foe.pos, 'cursor': foe.pos,
                                    'caster_place': me.pos, 'flags': 0, 'hash': 0})
        sent = collections.Counter()
        t_end = g.t + 4.0
        while g.t < t_end:
            for ch, pid, net, body in g.step(DT):
                sent[pid] += 1
        errs = [x for x in logs[n0:] if 'template' in x]
        tpl = g.templates.of(champ, me.champ.spells[slot]) if getattr(g, 'templates', None) else None
        out.append({'slot': 'QWER'[slot], 'spell': me.champ.spells[slot], 'template': tpl is not None, 'answer': res,
                    'sent': dict(sorted(sent.items())), 'errors': errs[:5]})
    return out


def worker(champs, q):
    for c in champs:
        try:
            q.put((c, smoke(c)))
        except Exception as e:
            import traceback
            q.put((c, [{'slot': '-', 'spell': '-', 'template': False, 'answer': f'CRASH {e!r}',
                        'sent': {}, 'errors': traceback.format_exc().splitlines()[-4:]}]))


def main():
    argv = sys.argv[1:]
    workers = 6
    if '--workers' in argv:
        i = argv.index('--workers')
        workers = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith('--')]
    if not args:
        sys.path.insert(0, ROOT)
        from server.core import gamedata as G
        args = [c['alias'] for c in G.champion_index()]
    import multiprocessing as mp
    q = mp.Queue()
    parts = [args[i::workers] for i in range(workers)]
    procs = [mp.Process(target=worker, args=(p, q)) for p in parts if p]
    for p in procs:
        p.start()
    lines, bad = [], 0
    for _ in range(len(args)):
        c, res = q.get()
        for r in res:
            flag = 'ERR' if r['errors'] or str(r['answer']).startswith('CRASH') else 'ok '
            bad += flag == 'ERR'
            line = f"{flag} {c:14s} {r['slot']} {r['spell']:26s} tpl={'Y' if r['template'] else '-'} | {str(r['answer'])[:70]:70s} | " \
                   f"{' '.join(f'{k}x{v}' for k, v in r['sent'].items() if k not in (61, 287))[:160]}"
            lines.append(line)
            for e in r['errors']:
                lines.append('      ' + str(e)[:200])
        print(lines[-1] if lines else c, flush=True)
    for p in procs:
        p.join()
    lines.sort()
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'smoke.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + f'\n{bad} spells with errors\n')
    print(bad, 'spells with errors ->', os.path.join(OUT, 'smoke.txt'))


if __name__ == '__main__':
    main()
