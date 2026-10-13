"""Property bins of game16 as Python values (server/bin_tree.py: bainfo's text dump parsed, kept as a pickle under
data/exe1620/bincache/ - the dump and its parse are paid once per bin).

    import bindump16 as B
    B.entries('map')                 the map's game bin  (data/maps/shipping/map11/map11.bin)      [(key, class, value)]
    B.entries('mapgeo')              the map's placeables (data/maps/mapgeometry/map11/base_srx.materials.bin)
    B.entries('champion', 'Garen')   a champion's main bin
    B.entries('items') / ('global', path) / ('wad', '<wad under DATA/FINAL>|<bin path>')
    B.by_class(entries, 'BarracksConfig') -> {key: value}

    python tools/bindump16.py map                       the classes of a bin with counts
    python tools/bindump16.py map BarracksConfig        the entries of a class as JSON
    python tools/bindump16.py all-champions             fill the cache for every champion
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
os.environ.setdefault('BA_PATCH', '1620')
import bin_tree as BT   # noqa: E402

GAME = os.path.join(ROOT, 'game16', 'DATA', 'FINAL')

KNOWN = {
    'map': ('Maps/Shipping/Map11.wad.client', 'data/maps/shipping/map11/map11.bin'),
    'mapgeo': ('Maps/Shipping/Map11.wad.client', 'data/maps/mapgeometry/map11/base_srx.materials.bin'),
    'items': ('Global.wad.client', '{1d720f4f42640c18}'),
}


def where(kind, name=None):
    if kind == 'champion':
        return f'Champions/{name}.wad.client', f'data/characters/{name.lower()}/{name.lower()}.bin'
    if kind == 'skin':
        return f'Champions/{name}.wad.client', f'data/characters/{name.lower()}/skins/skin0.bin'
    if kind == 'global':
        return 'Global.wad.client', name
    if kind == 'wad':
        w, p = name.split('|')
        return w, p
    return KNOWN[kind]


def entries(kind, name=None):
    wad, path = where(kind, name)
    return BT.entries(os.path.join(GAME, wad), path)


def by_class(ents, cls):
    return {k: v for k, c, v in ents if c == cls}


def classes(ents):
    return collections.Counter(c for k, c, v in ents)


def champions():
    """names of the champions that have a wad (and a CharacterRecord in it is checked by the caller)"""
    out = []
    for f in sorted(os.listdir(os.path.join(GAME, 'Champions'))):
        if f.endswith('.wad.client') and f.count('.') == 2:
            out.append(f.split('.')[0])
    return out


if __name__ == '__main__':
    kind = sys.argv[1]
    if kind == 'all-champions':
        ok = 0
        for c in champions():
            n = len(entries('champion', c))
            ok += n > 0
            print(c, n, flush=True)
        print(ok, 'champions with a bin')
        sys.exit()
    name = sys.argv[2] if kind in ('champion', 'skin', 'global', 'wad') else None
    rest = sys.argv[3:] if name else sys.argv[2:]
    ents = entries(kind, name)
    if not rest:
        for c, n in classes(ents).most_common():
            print(n, c)
    else:
        for k, v in by_class(ents, rest[0]).items():
            if len(rest) > 1 and rest[1] not in k and rest[1] not in json.dumps(v)[:400]:
                continue
            print(k, json.dumps(v, indent=1)[:int(rest[2]) if len(rest) > 2 else 3000])
