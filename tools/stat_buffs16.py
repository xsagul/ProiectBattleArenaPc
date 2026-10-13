"""What abilities and passives do to their champion's own stats, from the wiki's ability data (Meraki, wiki 25.15 -
data/wiki/meraki/champions.json; the user's accepted source for numbers): bonus attack speed / move speed for a time
or for the next basic attacks, and basic attack timer resets.

    python tools/stat_buffs16.py [show <Champion>]    -> data/exe1620/stat_buffs16.json

{champion: {key P|Q|W|E|R: [{'stat': 'as'|'ms_pct', 'values': [per rank or per level], 'per': 'rank'|'level',
 'time': seconds, 'attacks': n or None, 'on': 'cast'|'any_cast', 'text': the sentence}, {'reset': True} ...]}}
'on': a passive that works "after casting an ability" fires on any of Q W E R; an active on its own cast. The phrases
read are the wiki's set ones ("gain X% bonus attack speed for N seconds", "next N basic attacks within M seconds gain
X% bonus attack speed", "resets ... basic attack timer"); everything else is left out (and counted).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
SRC = os.path.join(ROOT, 'data', 'wiki', 'meraki', 'champions.json')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'stat_buffs16.json')

NUM = r'[\d.]+(?:\s*/\s*[\d.]+)*'
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'next': 1}
STATS = (('as', r'(?:bonus\s+)?attack speed'), ('ms_pct', r'(?:bonus\s+)?movement speed'))


def nums(s):
    return [float(x) for x in re.findall(r'[\d.]+', s) if x != '.']


def leveled(effect, stat_word):
    """per-rank values of a leveling attribute naming the stat ('Bonus Attack Speed') in %"""
    for lv in effect.get('leveling', []) or []:
        if stat_word in (lv.get('attribute') or '').lower():
            for m in lv.get('modifiers', []) or []:
                units = m.get('units') or []
                if units and all(str(u).strip() == '%' for u in units):
                    return [float(v) for v in m['values']]
    return None


VAL = r'((?:[\d.]+%?\s*[/:]\s*)*[\d.]+)%'                 # "35%", "50% / 60% / 70%", "15% : 35%"
LVL = r'(?:\((?:\+ [^)]*|based on [^)]*)\) )*'                # "(+ 5% per mark) ", "(based on level) "


def values(text):
    """'50% / 60% / 70%' -> ([0.5, 0.6, 0.7], '/'); '15% : 35%' -> ([0.15, 0.35], ':' = from level 1 to 18)"""
    return [v / 100.0 for v in nums(text)], (':' if ':' in text else '/')


def parse(effect, key):
    text = re.sub(r'\s+', ' ', effect.get('description') or '')
    low = text.lower()
    out = []
    if re.search(r"resets? (?:\w+'s |her |his |its |the )?basic attack timer", low):
        out.append({'reset': True, 'text': text[:160]})
    if key == 'P' and not re.search(r'after (?:casting|using) an ability', low):
        return out                                  # a passive with another trigger: its own mechanism (not read)
    on = 'any_cast' if key == 'P' else 'cast'
    per = 'level' if 'based on level' in low else 'rank'
    for stat, word in STATS:
        sw = 'attack speed' if stat == 'as' else 'movement speed'
        got = None
        # "next two basic attacks within 4 seconds to [deal ... and] gain X% bonus attack speed"
        m = re.search(r'next (\w+) basic attacks? (?:on-attack )?within (' + NUM + r') seconds? (?:to )?[^.]{0,90}?gain (?:' + VAL +
                      r' )?' + LVL + r'(?:\d+ bonus range and )?' + word, low)
        if m:
            n = WORDS.get(m.group(1)) or (int(m.group(1)) if m.group(1).isdigit() else None)
            got = (values(m.group(3)) if m.group(3) else ([v / 100.0 for v in (leveled(effect, sw) or [])], '/'),
                   nums(m.group(2))[0], n, False, m.group(0))
        if got is None:
            # "gaining 35% (+ 5% per mark) bonus attack speed for 4 seconds"; "... bonus movement speed that decays over 1.5 seconds"
            m = re.search(r'gain(?:s|ing)? (?:' + VAL + r' )?' + LVL + word + r'( that decays| decaying)?(?: over| for) (' + NUM + r') seconds', low)
            if m:
                got = (values(m.group(1)) if m.group(1) else ([v / 100.0 for v in (leveled(effect, sw) or [])], '/'),
                       nums(m.group(3)), None, bool(m.group(2)), m.group(0))
        if got is None:
            # "for 2 seconds, she gains 30% / 40% (based on level) bonus movement speed"
            m = re.search(r'for (' + NUM + r') seconds, (?:she|he|it|they) gains? ' + VAL + r' ' + LVL + word, low)
            if m:
                got = (values(m.group(2)), nums(m.group(1)), None, False, m.group(0))
        if got is None:
            continue
        (vals, sep), t, n, decays, phrase = got
        if not vals or not t:
            continue
        if isinstance(t, list):
            t = t[0] if len(t) == 1 else t
        out.append({'stat': stat, 'values': vals, 'scale': 'range' if sep == ':' else 'steps', 'per': per, 'time': t,
                    'attacks': n, 'decays': decays, 'on': on, 'text': phrase[:160]})
    return out


def build():
    d = json.load(open(SRC, encoding='utf-8'))
    res, n_eff, n_found = {}, 0, 0
    for champ, c in d.items():
        for key in ('P', 'Q', 'W', 'E', 'R'):
            for a in (c.get('abilities') or {}).get(key, []) or []:
                for e in a.get('effects', []) or []:
                    low = (e.get('description') or '').lower()
                    if 'attack speed' in low or 'movement speed' in low or 'attack timer' in low:
                        n_eff += 1
                    got = parse(e, key)
                    if got:
                        n_found += 1
                        res.setdefault(c.get('key') or champ, {}).setdefault(key, []).extend(got)
    json.dump(res, open(OUT, 'w', encoding='utf-8'), indent=1)
    print(f'{len(res)} champions, {n_found} of {n_eff} effects that speak of attack / movement speed or the attack timer read -> {OUT}')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'show':
        print(json.dumps(json.load(open(OUT)).get(sys.argv[2]), indent=1))
    else:
        build()
