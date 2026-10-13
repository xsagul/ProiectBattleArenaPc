"""Recipes: what the real server sent for one occurrence of an event, as values with the units replaced by roles,
taken from a live recording (data/live/<gameId>) and written again for our own units.

A recipe is a list of steps (delay from the event, channel, packet id, whose net id: a role or 0, values); inside
the values every 8-hex net id of a role is written '{ROLE}'. make(name, roles, change) puts our net ids back and
lets the caller set fields (places, amounts) by packet id.

The occurrences are found in the recording once (game times, measured on match 4013831789) and saved to
<gameId>/events16.json; `python server/events16.py <gameId>` rebuilds that file and prints every recipe.
"""
import copy
import json
import os
import struct
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('BA_PATCH', '1620')
sys.modules.setdefault('decoded', types.ModuleType('decoded'))
import pkt_schema as PS   # noqa: E402

GARE, ZAAHEN, LISS, TRISTANA, MORG = 0x400000ae, 0x400000af, 0x400000b0, 0x400000b1, 0x400000b2
TRYND, YI, GALIO, MF, XERATH = 0x400000b3, 0x400000b4, 0x400000b5, 0x400000b6, 0x400000b7

# name: (from game s, to game s, {role: net id}, only packets about / mentioning the roles, packet ids left out)
OCCURRENCES = {
    # the chaos top outer turret's first attacks on a minion (120.888 rec = 111.621 game)
    'turret_first_attack': (111.62, 111.63, {'T': 0x400000a1, 'X': 0x400003a2, 'M': 0x40001014}, True, {287, 61}),
    'turret_missile': (111.88, 111.89, {'T': 0x400000a1, 'M': 0x40001014}, True, {287, 61}),
    'turret_next_attack': (112.95, 112.96, {'T': 0x400000a1, 'X': 0x400003a2}, True, {287, 61}),
    # the chaos top outer turret falls to the player (Garen) at 789.18
    'turret_falls': (789.17, 789.19, {'T': 0x400000a1, 'K': GARE}, True, {287, 61, 150, 699}),
    # the player buys Doran's Blade at 12.776: 1122 (purchase count) + 63 (item bought)
    'item_bought': (12.775, 12.777, {'H': GARE}, True, {287, 61}),
    # the player's Garen E at 66.737: cast, cooldown, animation
    'spell_cast': (66.736, 66.738, {'H': GARE}, True, {287, 61, 150, 699, 88, 78, 515, 280, 435}),
    # the player dies to Master Yi at 1081.915, comes back at 1120.398
    'hero_dies': (1081.914, 1081.916, {'H': GARE, 'K': YI}, True, {287, 61, 150, 699, 584, 282, 430, 635, 88, 262, 1166, 211,
                                                                   1126, 435, 78, 938, 41, 139, 827, 683}),
    'hero_returns': (1120.39, 1120.41, {'H': GARE}, True, {287, 61}),
    # the chaos nexus falls to Lissandra at 2129.405; the end of the match 3.5 s later
    'nexus_falls': (2129.404, 2129.406, {'N': 0x400000a8, 'K': LISS, 'P': GARE}, 'or0', {287, 61, 88, 1126, 29, 280, 118, 515, 699}),
    'match_ends': (2132.90, 2132.92, {}, False, {287, 61, 88, 1126, 29, 280, 1201, 904, 584, 430, 435, 262, 10}),
}


def _key(n):
    return struct.pack('<I', n).hex()


def _to_roles(v, keys):
    if isinstance(v, dict):
        return {k: _to_roles(x, keys) for k, x in v.items()}
    if isinstance(v, list):
        return [_to_roles(x, keys) for x in v]
    if isinstance(v, str) and v in keys:
        return '{' + keys[v] + '}'
    return v


def _from_roles(v, nets):
    if isinstance(v, dict):
        return {k: _from_roles(x, nets) for k, x in v.items()}
    if isinstance(v, list):
        return [_from_roles(x, nets) for x in v]
    if isinstance(v, str) and v.startswith('{') and v.endswith('}'):
        return nets.get(v[1:-1], '00000000')
    return v


def extract(game):
    import live16
    cap = live16.Capture(game)
    g0 = cap.gates[2]
    sc = {}

    def parse(pid, body):
        if pid not in sc:
            try:
                sc[pid] = PS.Schema.load(pid)
            except FileNotFoundError:
                sc[pid] = None
        if sc[pid] is None:
            return None
        try:
            return PS.parse(sc[pid], body)
        except Exception:
            return None
    rows = [(t - g0, ch, pid, net, body) for t, way, ch, pid, net, body in live16.rows(cap.path) if way == 'S2C' and t >= g0]
    out = {}
    for name, (a, b, roles, about_only, drop) in OCCURRENCES.items():
        keys = {_key(n): r for r, n in roles.items()}
        steps = []
        for gt, ch, pid, net, body in rows:
            if gt < a:
                continue
            if gt > b:
                break
            if pid in drop:
                continue
            v = parse(pid, body)
            if about_only and net not in roles.values() and not (v is not None and any(k in json.dumps(v) for k in keys))                     and not (about_only == 'or0' and net == 0):
                continue
            role = next((r for r, n in roles.items() if n == net), None)
            steps.append({'dt': round(gt - a, 4), 'ch': ch, 'pid': pid, 'about': role or (f'{net:08x}' if net else 0),
                          'values': _to_roles(v, keys) if v is not None else None, 'raw': body.hex() if v is None else None})
        out[name] = steps
    path = os.path.join(game, 'events16.json')
    json.dump(out, open(path, 'w'), indent=1)
    return out


class Events:
    def __init__(self, game):
        path = os.path.join(game, 'events16.json')
        self.recipes = json.load(open(path)) if os.path.exists(path) else extract(game)
        self.sc = {}

    def schema(self, pid):
        if pid not in self.sc:
            self.sc[pid] = PS.Schema.load(pid)
        return self.sc[pid]

    def values(self, name, pid, k=0):
        """the k-th step's values of a packet id in a recipe (a template)"""
        steps = [s for s in self.recipes[name] if s['pid'] == pid]
        return copy.deepcopy(steps[k]['values'])

    def make(self, name, roles, change=None, skip=()):
        """-> [(delay, channel, pid, net id, body)] of a recipe with our units; change: {pid: fn(values) or dict}"""
        nets = {r: _key(n) for r, n in roles.items()}
        out = []
        for s in self.recipes[name]:
            if s['pid'] in skip:
                continue
            about = s['about']
            net = roles.get(about, 0) if isinstance(about, str) and len(about) <= 2 else (int(about, 16) if about else 0)
            if s['values'] is None:
                body = bytes.fromhex(s['raw'])
            else:
                v = _from_roles(copy.deepcopy(s['values']), nets)
                c = (change or {}).get(s['pid'])
                if callable(c):
                    v = c(v) or v
                elif c:
                    v.update(c)
                body = self.schema(s['pid']).encode(v)
            out.append((s['dt'], s['ch'], s['pid'], net, body))
        return out


if __name__ == '__main__':
    rec = extract(sys.argv[1])
    for name, steps in rec.items():
        print(f'== {name}: {len(steps)} packets')
        for s in steps:
            print(f'   +{s["dt"]:.3f} {s["pid"]:5} about {s["about"]}  {str(s["values"] if s["values"] is not None else "RAW " + s["raw"])[:220]}')
