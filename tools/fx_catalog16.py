"""Build every champion's effect catalog once (data/exe1620/gamedata/fx/<Champion>.json), so that no match has to
read a champion's skin bins at its first cast.

    python tools/fx_catalog16.py [Champion ...]      all champions when none is named; done ones are skipped

Per champion: the base skin's resource map (key -> effect definition name) and which keys the champion's own data
names (server/core/effects.catalog). A few seconds each the first time (the bins are parsed and cached).
"""
import os
import sys
import time

os.environ.setdefault('BA_PATCH', '1620')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
from core import effects, gamedata as G  # noqa: E402


def main():
    names = sys.argv[1:] or G.champions()
    t0 = time.time()
    done = 0
    for i, c in enumerate(names):
        path = os.path.join(G.OUT, 'fx', c + '.json')
        if os.path.exists(path):
            continue
        t = time.time()
        try:
            cat = effects.catalog(c)
            scripted = sum(1 for e in cat if not e['data'])
            rules = sum(len(v) for v in effects.rules(c).values())
            print(f'{i + 1:3d}/{len(names)} {c:14s} {len(cat):3d} keys, {scripted:3d} for scripts, {rules:3d} with a rule  {time.time() - t:5.1f} s', flush=True)
            done += 1
        except Exception as e:
            print(f'{i + 1:3d}/{len(names)} {c:14s} FAILED {e!r}', flush=True)
    print(f'{done} catalogs built in {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
