"""bainfo's text dump of a property bin (`bainfo bin <wad> <bin> "" research/hashes`) turned into Python values, so
spell data (mSpellCalculations, mEffectAmount, mDataValues...) can be used by code instead of read by eye.

Dump grammar (two spaces per level):
    {hash} (Class)              an entry               -> {'_type': Class, field: value...}
    field: scalar               a scalar ("text", number, {hash})
    field: [n] / field: {n}     a list / a map; their items are the deeper lines (a map: "key K" then the value)
    field: Class                an embedded struct; its fields are the deeper lines
    Class                       a struct item inside a list / map

  bin_tree.py <champion> <SpellScriptName>     prints one SpellObject as JSON
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
BAINFO = os.path.join(ROOT, 'build-test', 'bin', 'bainfo.exe')
GAME = r'C:\Users\Sorin\Desktop\lol13.3\DATA\FINAL\Champions'
_cache = {}


def scalar(s):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def _parse(lines, i, indent):
    """the block of lines deeper than `indent` starting at i -> (list of (head, children)), next i"""
    out = []
    while i < len(lines):
        ind = len(lines[i]) - len(lines[i].lstrip(' '))
        if ind <= indent:
            break
        head = lines[i].strip()
        kids, i = _parse(lines, i + 1, ind)
        out.append((head, kids))
    return out, i


def _value(head_rest, kids):
    """the value of a field whose text after ':' is head_rest and whose deeper lines are kids"""
    m = re.fullmatch(r'\[(\d+)\]', head_rest)
    if m:
        return [_item(h, k) for h, k in kids]
    m = re.fullmatch(r'\{(\d+)\}', head_rest)
    if m:
        out, key = {}, None
        for h, k in kids:
            if h.startswith('key '):
                key = scalar(h[4:])
            else:
                out[key] = _item(h, k)
        return out
    if re.fullmatch(r'[A-Za-z_]\w*', head_rest) and kids:
        return _struct(head_rest, kids)
    if re.fullmatch(r'[A-Za-z_]\w*', head_rest) and not kids and head_rest[0].isupper():
        return {'_type': head_rest}
    return scalar(head_rest)


def _item(head, kids):
    if re.fullmatch(r'[A-Za-z_]\w*', head) and head[0].isupper():
        return _struct(head, kids)
    return scalar(head)


def _struct(typ, kids):
    out = {'_type': typ}
    for h, k in kids:
        if ': ' in h:
            name, rest = h.split(': ', 1)
            out[name] = _value(rest, k)
        elif h.endswith(':'):
            out[h[:-1]] = _value('', k)
        else:
            out.setdefault('_items', []).append(_item(h, k))
    return out


def entries(wad, binpath):
    """every entry of a bin: [(hash text, class, value)]"""
    key = (wad, binpath)
    if key in _cache:
        return _cache[key]
    out = subprocess.run([BAINFO, 'bin', wad, binpath, '', os.path.join(ROOT, 'research', 'hashes')],
                         capture_output=True, text=True).stdout.splitlines()
    res = []
    i = 0
    while i < len(out):
        m = re.match(r'^(\{[0-9a-f]+\}|\S+) \((\w+)\)$', out[i])
        if m:
            kids, i = _parse(out, i + 1, 0)
            res.append((m.group(1), m.group(2), _struct(m.group(2), kids)))
        else:
            i += 1
    _cache[key] = res
    return res


def champion_spells(champion):
    """{mScriptName: SpellObject value} of a champion's main bin"""
    wad = os.path.join(GAME, f'{champion}.wad.client')
    out = {}
    for h, cls, v in entries(wad, f'data/characters/{champion.lower()}/{champion.lower()}.bin'):
        if cls == 'SpellObject' and 'mScriptName' in v:
            out[v['mScriptName']] = v
    return out


def character_record(champion):
    wad = os.path.join(GAME, f'{champion}.wad.client')
    for h, cls, v in entries(wad, f'data/characters/{champion.lower()}/{champion.lower()}.bin'):
        if cls == 'CharacterRecord':
            return v
    return None


if __name__ == '__main__':
    print(json.dumps(champion_spells(sys.argv[1]).get(sys.argv[2]), indent=1)[:6000])
