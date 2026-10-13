"""Which name a spell's damage carries on Riot's server (150 +0x2c), from the cast evidence of every replay
(data/replays16/casts, tools/replay_evidence16.py): the damage the caster deals within a cast's window often names
another spell than the cast - KindredQ's damage is KindredQMissile's, XerathArcanopulseChargeUp's XerathArcanopulse2.

    python tools/damage_names16.py      -> data/exe1620/damage_names16.json {cast spell: damage name}

Counted once per cast: the names of the damage the caster deals within min(window, 'until' = its next own cast)
that are not basic attacks; a name is taken when it is in at least half of the casts that dealt spell damage.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import replay_evidence16 as E  # noqa: E402

CASTS = os.path.join(ROOT, 'data', 'replays16', 'casts')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'damage_names16.json')
WINDOW = 4.0


def main():
    seen = collections.defaultdict(collections.Counter)      # spell -> damage name -> casts
    dealt = collections.Counter()                            # spell -> casts with any spell damage
    for f in sorted(os.listdir(CASTS)):
        try:
            d = E.load_casts(os.path.join(CASTS, f))
        except Exception as x:
            print(f, 'unreadable', x)
            continue
        for c in d['casts']:
            end = min(WINDOW, c.get('until', WINDOW))
            names = set()
            for e in c['events']:
                if e[1] != 150 or e[0] > end or e[2] not in ('other', 'spawn', 'missile'):
                    continue
                s = e[4] if isinstance(e[4], dict) else {}
                nm = str(s.get('spell') or '')
                if not nm or 'BasicAttack' in nm or 'CritAttack' in nm:
                    continue
                names.add(nm)
            if names:
                dealt[c['spell']] += 1
                seen[c['spell']].update(names)
        print(f, len(seen), flush=True)
    out = {}
    for spell, c in seen.items():
        nm, k = c.most_common(1)[0]
        if k * 2 >= dealt[spell] and nm != spell:
            out[spell] = nm
    json.dump(out, open(OUT, 'w'), indent=0, sort_keys=True)
    print(len(out), 'spells whose damage carries another name ->', OUT)


if __name__ == '__main__':
    main()
