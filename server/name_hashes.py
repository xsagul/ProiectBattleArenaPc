"""A dictionary hash -> name for the 32-bit names packets carry (buffs, spells, particles): every printable text in
the property bins of the given wads (replay champions + Garen, Global, DATA, Map11), each prefix of length >= 4 (bin
texts are stored with a length, so a scan sees trailing bytes), hashed with ELF (spell / buff names in 49 and 16)
and FNV-1a lower case (bin entry and field names). Cached in data/exe133/name_hashes.json.

  name_hashes.py build
  name_hashes.py find <hex> [<hex> ...]
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, HERE)
import spell_info as SI  # noqa: E402

FINAL = r'C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game\DATA\FINAL'
CHAMPS = ['Darius', 'Nidalee', 'Talon', 'Kalista', 'Alistar', 'Jax', 'LeeSin', 'Azir', 'Jhin', 'Blitzcrank', 'Garen']
OUT = os.path.join(ROOT, 'data', 'exe133', 'name_hashes.json')


def fnv(s):
    h = 0x811c9dc5
    for c in s.lower().encode():
        h = ((h ^ c) * 0x01000193) & 0xffffffff
    return h


def wads():
    out = [os.path.join(FINAL, 'Champions', f'{c}.wad.client') for c in CHAMPS]
    out += [os.path.join(FINAL, n) for n in ('Global.wad.client', 'DATA.wad.client', 'DATA2.wad.client')]
    out += [os.path.join(FINAL, 'Maps', 'Shipping', 'Map11.wad.client')]
    return [w for w in out if os.path.exists(w)]


def build():
    from wadx import Wad
    texts = set()
    for path in wads():
        w = Wad(path)
        n = 0
        for h in list(w.entries):
            try:
                d = w.read(h)
            except Exception:
                continue
            if not d or d[:4] not in (b'PROP', b'PTCH'):
                continue
            n += 1
            for m in re.finditer(rb'[\x20-\x7e]{4,200}', d):
                texts.add(m.group().decode())
        print(path, n, 'bins', len(texts), 'texts', flush=True)
    names = {}
    for s in texts:
        cands = {s[:k] for k in range(4, len(s) + 1)}
        cands |= {c.split('/')[-1].split('.')[0] for c in list(cands) if '/' in c or '.' in c}
        for c in cands:
            names.setdefault(f'elf:{SI.elf(c):08x}', c)
            names.setdefault(f'fnv:{fnv(c):08x}', c)
    json.dump(names, open(OUT, 'w'))
    print(len(names), 'hashes ->', OUT)


_d = None


def find(h):
    global _d
    if _d is None:
        _d = json.load(open(OUT))
    return [(k, _d[f'{k}:{h:08x}']) for k in ('elf', 'fnv') if f'{k}:{h:08x}' in _d]


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build()
    else:
        for x in sys.argv[2:]:
            print(x, find(int(x, 16)))
