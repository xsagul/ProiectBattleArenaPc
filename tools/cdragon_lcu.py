"""The out-of-game client (LCU) of a patch, from CommunityDragon's archive of Riot's client files
(https://raw.communitydragon.org/<patch>/plugins/<plugin>/global/default/...): the plugins' pages, style sheets,
pictures, sounds and texts exactly as the patch shipped them.

    python tools/cdragon_lcu.py list  <plugin> [<plugin> ...]      walks the plugins, writes research/lcu141/listing/<plugin>.txt
    python tools/cdragon_lcu.py fetch <plugin> [--only <regex>]    downloads a plugin's files into lcu-data/14.1/plugins/<plugin>/
    python tools/cdragon_lcu.py get   <plugin>/<path> [...]        downloads single files

Files land under lcu-data/14.1/plugins/<plugin>/global/default/, the layout the client itself serves them in
(/fe/<plugin>/... and /lol-game-data/assets/...).
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.parse
import urllib.request

PATCH = '14.1'
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'lcu-data', PATCH, 'plugins')
LISTS = os.path.join(ROOT, 'research', 'lcu141', 'listing')
RAW = f'https://raw.communitydragon.org/{PATCH}/plugins/'
JSON = f'https://raw.communitydragon.org/json/{PATCH}/plugins/'


def http(url, tries=4):
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'BattleArena-research'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def walk(plugin):
    """Every file of a plugin: (path below the plugin, size)."""
    files = []
    todo = ['global/default/']
    with cf.ThreadPoolExecutor(12) as pool:
        while todo:
            batch, todo = todo, []
            for d, body in zip(batch, pool.map(lambda d: http(JSON + plugin + '/' + urllib.parse.quote(d)), batch)):
                for e in json.loads(body):
                    if e['type'] == 'directory':
                        todo.append(d + e['name'] + '/')
                    else:
                        files.append((d + e['name'], e.get('size', 0)))
    return sorted(files)


def listing(plugin):
    path = os.path.join(LISTS, plugin + '.txt')
    if os.path.exists(path):
        out = []
        for line in open(path, encoding='utf-8'):
            size, name = line.rstrip('\n').split(' ', 1)
            out.append((name, int(size)))
        return out
    files = walk(plugin)
    os.makedirs(LISTS, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for name, size in files:
            f.write(f'{size} {name}\n')
    return files


def download(plugin, name, size=None):
    dest = os.path.join(OUT, plugin, *name.split('/'))
    if os.path.exists(dest) and (size is None or os.path.getsize(dest) == size):
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = http(RAW + plugin + '/' + urllib.parse.quote(name))
    with open(dest + '.part', 'wb') as f:
        f.write(data)
    os.replace(dest + '.part', dest)
    return len(data)


def main():
    cmd = sys.argv[1]
    if cmd == 'list':
        for plugin in sys.argv[2:]:
            files = listing(plugin)
            print(f'{plugin}: {len(files)} files, {sum(s for _, s in files) / 1e6:.1f} MB')
    elif cmd == 'fetch':
        plugin = sys.argv[2]
        only = re.compile(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == '--only' else None
        files = [(n, s) for n, s in listing(plugin) if not only or only.search(n)]
        total = 0
        with cf.ThreadPoolExecutor(12) as pool:
            for got in pool.map(lambda f: download(plugin, f[0], f[1]), files):
                total += got
        print(f'{plugin}: {len(files)} files, {total / 1e6:.1f} MB downloaded')
    elif cmd == 'get':
        for item in sys.argv[2:]:
            plugin, name = item.split('/', 1)
            print(item, download(plugin, 'global/default/' + name if not name.startswith('global/') else name))


if __name__ == '__main__':
    main()
