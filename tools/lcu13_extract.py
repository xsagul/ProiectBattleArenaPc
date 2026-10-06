"""The League Client 13.3 front-end files (rcp-fe-* plugins, and rcp-be-lol-game-data's assets) out of the local
install (Desktop\\lol13.3-clients\\LeagueClient\\Plugins\\<plugin>\\assets.wad), into data/lcu/13.3/plugins/<plugin>/
global/default/... -- the same layout lobby.exe serves.

The wads name their entries by xxh64 of the path "plugins/<plugin>/global/default/<file>" (checked: index.html,
rcp-fe-lol-parties.js). Paths come from: CommunityDragon's listings of 13.1 and 13.4 (13.3 is not archived there),
our 14.1 copy, and every path-like string inside the files already extracted (repeated until nothing new is found).

  lcu13_extract.py <plugin> [<plugin> ...]       e.g. rcp-fe-lol-parties rcp-fe-lol-navigation
"""
import json
import os
import re
import sys
import urllib.request

import xxhash

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'server'))
from wadx import Wad  # noqa: E402

LCU = r'C:\Users\Sorin\Desktop\lol13.3-clients\LeagueClient\Plugins'
OUT = os.path.join(ROOT, 'data', 'lcu', '13.3', 'plugins')
CACHE = os.path.join(ROOT, 'data', 'clients133', 'cdragon_lists')


def cdragon_list(version, plugin):
    """every file path under plugins/<plugin>/global/default/ in CommunityDragon's archive of that version"""
    os.makedirs(CACHE, exist_ok=True)
    cache = os.path.join(CACHE, f'{version}_{plugin}.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    out = []

    def walk(rel):
        url = f'https://raw.communitydragon.org/json/{version}/plugins/{plugin}/global/default/{rel}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
            items = json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            return
        for it in items:
            p = rel + it['name']
            if it['type'] == 'directory':
                walk(p + '/')
            else:
                out.append(p)
    walk('')
    json.dump(out, open(cache, 'w'))
    return out


def local_141(plugin):
    base = os.path.join(ROOT, 'data', 'lcu', '14.1', 'plugins', plugin, 'global', 'default')
    out = []
    for d, _, fs in os.walk(base):
        for f in fs:
            out.append(os.path.relpath(os.path.join(d, f), base).replace('\\', '/'))
    return out


PATHLIKE = re.compile(rb'''["'(]\.?/?([A-Za-z0-9_\-./]+\.(?:png|jpg|jpeg|webm|ogg|mp3|wav|svg|css|js|json|html|woff2?|ttf|otf|gif|webp|map))["')?#]''')


def extract(plugin):
    wad_path = os.path.join(LCU, plugin, 'assets.wad')
    if not os.path.exists(wad_path):
        wad_path = os.path.join(LCU, plugin, 'default-assets.wad')
    w = Wad(wad_path)
    prefix = f'plugins/{plugin}/global/default/'
    found = {}
    cands = set(local_141(plugin))
    for v in ('13.4', '13.1'):
        cands |= set(cdragon_list(v, plugin))
    cands |= {'index.html', 'description.json', f'{plugin}.js', 'trans.json', 'index.js', 'plugin.js'}
    tried = set()
    base = os.path.join(OUT, plugin, 'global', 'default')
    while True:
        new = cands - tried
        if not new:
            break
        tried |= new
        for rel in new:
            rel = rel.lstrip('./')
            h = xxhash.xxh64((prefix + rel).lower().encode()).intdigest()
            if h in w.entries and h not in found:
                try:
                    data = w.read(h)
                except Exception:
                    continue
                if data is None:
                    continue
                found[h] = rel
                dst = os.path.join(base, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, 'wb').write(data)
                if rel.endswith(('.js', '.css', '.html', '.json')):
                    for m in PATHLIKE.finditer(data):
                        p = m.group(1).decode(errors='ignore')
                        cands.add(p)
                        d = os.path.dirname(rel)
                        if d:
                            cands.add(os.path.normpath(os.path.join(d, p)).replace('\\', '/'))
    print(f'{plugin}: {len(found)} of {len(w.entries)} entries named and extracted')
    return found


if __name__ == '__main__' and sys.argv[1:2] != ['game-data']:
    for p in sys.argv[1:]:
        extract(p)


def extract_game_data(limit_champions=None):
    """rcp-be-lol-game-data: summary / queues / maps / game modes JSON, then every champion's JSON and the assets they
    name (icons, splashes, tiles, choose / ban sounds), then whatever the new JSON files name, until nothing is new"""
    plugin = 'rcp-be-lol-game-data'
    w = Wad(os.path.join(LCU, plugin, 'default-assets.wad'))
    prefix = f'plugins/{plugin}/global/default/'
    base = os.path.join(OUT, plugin, 'global', 'default')
    todo = ['v1/champion-summary.json', 'v1/queues.json', 'v1/maps.json', 'v1/game-modes.json', 'v1/game-types.json',
            'v1/map-assets/map-assets.json', 'v1/summoner-spells.json', 'v1/profile-icons.json', 'v1/skins.json',
            'v1/perks.json', 'v1/perkstyles.json', 'v1/items.json', 'v1/champion-icons/-1.png']
    done, got = set(), 0
    ref = re.compile(r'/lol-game-data/assets/([^"\']+)')
    while todo:
        rel = todo.pop()
        key = rel.lower()
        if key in done:
            continue
        done.add(key)
        h = xxhash.xxh64((prefix + key).encode()).intdigest()
        if h not in w.entries:
            continue
        data = w.read(h)
        if data is None:
            continue
        dst = os.path.join(base, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
        got += 1
        if rel.endswith('.json'):
            text = data.decode('utf8', errors='ignore')
            for m in ref.finditer(text):
                todo.append(m.group(1))
            if rel == 'v1/champion-summary.json':
                for c in json.loads(text):
                    if limit_champions and c['alias'] not in limit_champions:
                        continue
                    todo.append(f'v1/champions/{c["id"]}.json')
                    todo.append(f'v1/champion-icons/{c["id"]}.png')
    print(f'{plugin}: {got} files extracted')


if __name__ == '__main__' and sys.argv[1:2] == ['game-data']:
    extract_game_data(set(sys.argv[2:]) or None)
