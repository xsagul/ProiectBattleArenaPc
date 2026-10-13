"""The LoL wiki's ability data for every champion (as packed by Meraki Analytics into one file: cooldown, cost, what
each ability does by rank, the passive's text), cut down to what the server uses and set against our own numbers.

    python tools/wiki16.py build      data/wiki/meraki/champions.json -> data/exe1620/gamedata/wiki16.json
    python tools/wiki16.py check      our cooldown / cost / damage (game data 16.20) against the wiki's
                                      -> data/exe1620/spells16/wiki_check.txt

wiki16.json: {champion alias: {'patch', 'P': {'name', 'text'}, 'Q'..'R': {'name', 'text', 'cooldown' [by rank],
'cost' [by rank], 'damage': {'type' 0 physical | 1 magic | 2 true, 'base' [by rank], 'ratios' [[percent by rank,
'AP' | 'AD' | 'bonus AD' | ...]], 'attribute'}, 'cc': {'stun' | 'root' | 'silence' | 'knockup' | 'charm' | 'fear' |
'taunt' | 'sleep' | 'suppress' | 'disable': [seconds by rank], 'slow': [percent by rank], 'slow_time': [seconds]}}}}
The file is other people's data: it is only read as JSON (python -I when run by hand on a fresh download).
The wiki's patch (25.15, August 2025) is not the client's (16.20): where the game's own data gives a number, that
number is the one used; the wiki fills what the data cannot say.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'wiki', 'meraki', 'champions.json')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'gamedata', 'wiki16.json')
CHECK = os.path.join(ROOT, 'data', 'exe1620', 'spells16', 'wiki_check.txt')
NOT_THE_HIT = ('bonus', 'minion', 'monster', 'reduced', 'increased', 'capped', 'non-champion', 'per stack', 'reduction',
               'stored', 'shield', 'heal')
CC_WORDS = (('stun', 'stun'), ('root', 'root'), ('silence', 'silence'), ('knock up', 'knockup'), ('knockup', 'knockup'),
            ('airborne', 'knockup'), ('charm', 'charm'), ('fear', 'fear'), ('flee', 'fear'), ('taunt', 'taunt'),
            ('sleep', 'sleep'), ('suppress', 'suppress'), ('disable', 'disable'))
TYPES = {'PHYSICAL_DAMAGE': 0, 'MAGIC_DAMAGE': 1, 'TRUE_DAMAGE': 2}


def nums(mod):
    return [float(x) for x in (mod or {}).get('values') or [] if isinstance(x, (int, float))]


def unit(mod):
    u = (mod or {}).get('units') or ['']
    return (u[0] or '').strip()


def ability(ab):
    out = {'name': ab.get('name'), 'text': ' '.join((e.get('description') or '').strip() for e in ab.get('effects') or [])[:1200],
           'cooldown': nums(((ab.get('cooldown') or {}).get('modifiers') or [None])[0]),
           'cost': nums(((ab.get('cost') or {}).get('modifiers') or [None])[0]), 'cc': {}}
    dmg = None
    for e in ab.get('effects') or []:
        for lv in e.get('leveling') or []:
            name = (lv.get('attribute') or '').lower()
            mods = lv.get('modifiers') or []
            if not mods:
                continue
            first = nums(mods[0])
            if 'damage' in name and not any(w in name for w in NOT_THE_HIT) and unit(mods[0]) == '' and first:
                rank = (0 if name in ('magic damage', 'physical damage', 'true damage') else
                        1 if name.startswith(('total', 'minimum')) else 2)
                if dmg is None or rank < dmg[0]:
                    typ = 2 if 'true' in name else 1 if 'magic' in name else 0 if 'physical' in name else TYPES.get(ab.get('damageType'), 1)
                    dmg = (rank, {'type': typ, 'base': first, 'attribute': lv.get('attribute'),
                                  'ratios': [[nums(m), unit(m).lstrip('% ').strip()] for m in mods[1:] if unit(m).startswith('%')]})
            elif name == 'slow' and first:
                out['cc']['slow'] = first
            elif 'slow' in name and 'duration' in name and first:
                out['cc']['slow_time'] = first
            elif 'duration' in name and first and max(first) <= 6.0:
                for word, kind in CC_WORDS:
                    if word in name:
                        out['cc'][kind] = first
                        break
    out['damage'] = dmg[1] if dmg else None
    # durations written in the text only ("stunning them for 1.5 seconds")
    low = out['text'].lower()
    for word, kind in CC_WORDS:
        if kind not in out['cc']:
            m = re.search(word + r'\w*\s+(?:\w+\s+){0,6}?for\s+(\d+(?:\.\d+)?)\s+seconds?', low)
            if m and float(m.group(1)) <= 6.0:
                out['cc'][kind] = [float(m.group(1))]
    if 'slow' not in out['cc']:
        m = re.search(r'slow\w*\s+(?:\w+\s+){0,6}?by\s+(\d+(?:\.\d+)?)%', low)
        if m:
            out['cc']['slow'] = [float(m.group(1))]
    return out


def build():
    sys.path.insert(0, ROOT)
    os.environ.setdefault('BA_PATCH', '1620')
    from server.core import gamedata as G
    ours = {c['alias'].lower(): c['alias'] for c in G.champion_index()}
    byname = {str(c.get('name', '')).lower().replace(' ', '').replace("'", '').replace('.', ''): c['alias'] for c in G.champion_index()}
    d = json.load(open(SRC, encoding='utf-8'))
    out, missing = {}, []
    for key, c in d.items():
        alias = ours.get(str(c.get('key', key)).lower()) or ours.get(key.lower()) or \
            byname.get(str(c.get('name', '')).lower().replace(' ', '').replace("'", '').replace('.', ''))
        if alias is None:
            missing.append(key)
            continue
        e = {'patch': c.get('patchLastChanged')}
        for slot, lst in (c.get('abilities') or {}).items():
            if not lst:
                continue
            if slot == 'P':
                e['P'] = {'name': lst[0].get('name'), 'text': ' '.join((x.get('description') or '').strip() for ab in lst for x in ab.get('effects') or [])[:2000]}
            else:
                e[slot] = ability(lst[0])
                if len(lst) > 1:
                    e[slot]['forms'] = [ability(x) for x in lst[1:]]
        out[alias] = e
    extra = os.path.join(ROOT, 'data', 'wiki', 'extra16.json')       # champions the file lacks, entered by hand from the wiki
    if os.path.exists(extra):
        for alias, e in json.load(open(extra, encoding='utf-8')).items():
            if not alias.startswith('_') and alias not in out:
                out[alias] = e
    json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=0)
    not_in_wiki = sorted(set(ours.values()) - set(out))
    print(len(out), 'champions written;', 'in the file but not ours:', missing, '| ours but not in the file:', not_in_wiki)


def wiki_damage(w, rank, ad, bonus_ad, ap):
    """the wiki's damage of an ability at a rank for these stats; None when a ratio is of something else"""
    dm = w.get('damage')
    if not dm or not dm['base']:
        return None
    v = dm['base'][min(rank, len(dm['base'])) - 1]
    for vals, of in dm['ratios']:
        if not vals:
            continue
        pct = vals[min(rank, len(vals)) - 1] / 100.0
        o = of.lower()
        if o == 'ap':
            v += pct * ap
        elif o == 'bonus ad':
            v += pct * bonus_ad
        elif o == 'ad':
            v += pct * (ad + bonus_ad)
        else:
            return None
    return v


def check():
    sys.path.insert(0, os.path.join(ROOT, 'server'))
    sys.path.insert(0, ROOT)
    os.environ.setdefault('BA_PATCH', '1620')
    from server.core import gamedata as G
    from core import spells as S

    class H:
        base_ad, ap, base_armor, base_mr, max_hp, speed, max_par, crit, attack_speed, level = 100.0, 100.0, 80.0, 50.0, 2000.0, 340.0, 800.0, 0.0, 1.0, 13
        bonus = collections.defaultdict(float, ad=50.0, hp=500.0)
    w = json.load(open(OUT, encoding='utf-8'))
    lines, n = [], collections.Counter()
    for c in G.champion_index():
        alias = c['alias']
        ch = G.champion(alias)
        for i, sp in enumerate(ch.spells[:4]):
            a = (w.get(alias) or {}).get('QWER'[i])
            n['spells'] += 1
            if not a:
                n['not in the wiki file'] += 1
                continue
            inf = S.info(ch, sp)
            ranks = 3 if i == 3 else 5
            cd = [round(inf.cooldown(r), 2) for r in range(1, ranks + 1)]
            if a['cooldown'] and len(a['cooldown']) >= ranks:
                if all(abs(x - y) < 0.06 for x, y in zip(cd, a['cooldown'])):
                    n['cooldown same'] += 1
                else:
                    n['cooldown differs'] += 1
                    lines.append(f"{alias:14s} {'QWER'[i]} {sp:26s} cooldown  ours {cd} wiki {a['cooldown'][:ranks]}")
            cost = [round(inf.mana(r), 1) for r in range(1, ranks + 1)]
            if a['cost'] and len(a['cost']) >= ranks:
                if all(abs(x - y) < 0.6 for x, y in zip(cost, a['cost'])):
                    n['cost same'] += 1
                else:
                    n['cost differs'] += 1
                    lines.append(f"{alias:14s} {'QWER'[i]} {sp:26s} cost      ours {cost} wiki {a['cost'][:ranks]}")
            for r in (1, ranks):
                wd = wiki_damage(a, r, 100.0, 50.0, 100.0)
                od = inf.damage(H(), r)[0]
                if wd is None:
                    continue
                if od <= 0:
                    n['damage: ours none, wiki has'] += r == 1
                    if r == 1:
                        lines.append(f"{alias:14s} {'QWER'[i]} {sp:26s} damage    ours none wiki {wd:.0f} at rank 1 ({a['damage']['attribute']})")
                elif abs(od - wd) <= 0.05 * wd + 2:
                    n['damage same (rank %d)' % r] += 1
                else:
                    n['damage differs (rank %d)' % r] += 1
                    lines.append(f"{alias:14s} {'QWER'[i]} {sp:26s} damage    rank {r}: ours {od:.0f} wiki {wd:.0f} ({a['damage']['attribute']})")
    head = ['ours (game data 16.20) against the wiki file (25.15): ' + ', '.join(f'{k} {v}' for k, v in sorted(n.items())), '']
    open(CHECK, 'w', encoding='utf-8').write('\n'.join(head + lines) + '\n')
    print(head[0])


if __name__ == '__main__':
    (build if sys.argv[1:] == ['build'] else check)()
