"""Real 16.20 matches as replays, fetched through the player's own League client (its local API, the lockfile's port
and password): the evidence of what Riot's server sends for every champion in many different situations.

    python tools/replay_fetch16.py status
    python tools/replay_fetch16.py pool [--tiers CHALLENGER,GRANDMASTER,MASTER] [--per-player 20] [--players n]
        every player of those apex leagues (this region), their last games -> data/replays16/pool.json
        {game id: {queue, version, map, created, duration, champions: {champion id: team}, full}}
    python tools/replay_fetch16.py plan [--per-champion 3] [--first Shaco,..] [--max 150]
        the games to fetch so that every champion is in at least n of them (greedy; a game's ten champions are
        read from the server when it is picked) -> data/replays16/plan.json
    python tools/replay_fetch16.py fetch [--max n]
        each planned game's replay, one at a time -> data/replays16/rofl/<game id>.rofl; data/replays16/fetched.json
    python tools/replay_fetch16.py cover
        how many fetched replays hold each champion; the champions none holds

Only Summoner's Rift games of the client's own version can be fetched (the server keeps the current patch's
replays). The replays name the other players (their Riot ids): data/replays16/ stays on this computer (.gitignore).
"""
import json
import os
import shutil
import sys
import time

import requests
import urllib3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'replays16')
LOCKFILE = r'C:\Riot Games\League of Legends\lockfile'
RIFT_QUEUES = {420, 440, 400, 430, 490}           # solo, flex, draft, blind, quickplay: Summoner's Rift, matched
PAUSE = 0.12                                       # s between two requests to the client (they go on to Riot)
urllib3.disable_warnings()


class Client:
    def __init__(self):
        parts = open(LOCKFILE).read().split(':')
        self.base = f'https://127.0.0.1:{parts[2]}'
        self.s = requests.Session()
        self.s.verify = False
        self.s.auth = ('riot', parts[3])

    def get(self, path, **params):
        for k in range(4):
            time.sleep(PAUSE)
            try:
                r = self.s.get(self.base + path, params=params or None, timeout=40)
            except requests.RequestException:
                time.sleep(2 + 3 * k)
                continue
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(3 + 5 * k)
                continue
            return r.json() if r.status_code == 200 else None
        return None

    def post(self, path, body=None):
        time.sleep(PAUSE)
        r = self.s.post(self.base + path, json=body if body is not None else {}, timeout=40)
        return r.status_code, (r.json() if r.content and r.headers.get('content-type', '').startswith('application/json') else r.text)


def load(name, default):
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save(name, value):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    json.dump(value, open(p + '.tmp', 'w'), indent=0)
    os.replace(p + '.tmp', p)


def champion_names():
    sys.path.insert(0, ROOT)
    from server.core import gamedata as G
    return {c['id']: c['alias'] for c in G.champion_index()}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


# ------------------------------------------------------------------------------------------------ the game pool
def pool():
    c = Client()
    version = c.get('/lol-replays/v1/configuration')['gameVersion']
    games = load('pool.json', {})
    seen_players = set(load('players_done.json', []))
    tiers = (arg('--tiers') or 'CHALLENGER,GRANDMASTER,MASTER').split(',')
    per = int(arg('--per-player', 20))
    limit = int(arg('--players', 100000))
    players = []
    for tier in tiers:
        j = c.get(f'/lol-ranked/v1/apex-leagues/RANKED_SOLO_5x5/{tier}') or {}
        for d in j.get('divisions', []):
            players += [s['puuid'] for s in d.get('standings', []) if s.get('puuid')]
    print(len(players), 'players in', tiers, flush=True)
    # every history request takes the client about 2 s (it asks Riot's servers): four at a time
    from concurrent.futures import ThreadPoolExecutor
    todo = [p for p in players[:limit] if p not in seen_players]

    def history(puuid):
        return puuid, c.get(f'/lol-match-history/v1/products/lol/{puuid}/matches', begIndex=0, endIndex=per) or {}
    done = 0
    with ThreadPoolExecutor(int(arg('--workers', 4))) as ex:
        for puuid, h in ex.map(history, todo):
            for g in h.get('games', {}).get('games', []):
                if g.get('gameVersion') != version or g.get('mapId') != 11 or g.get('queueId') not in RIFT_QUEUES:
                    continue
                e = games.setdefault(str(g['gameId']), {'queue': g['queueId'], 'version': g['gameVersion'], 'map': 11,
                                                        'created': g['gameCreation'], 'duration': g['gameDuration'],
                                                        'type': g.get('gameType', 'MATCHED_GAME'), 'champions': {}, 'full': False})
                for p in g.get('participants', []):
                    e['champions'][str(p['championId'])] = p.get('teamId', 0)
            seen_players.add(puuid)
            done += 1
            if done % 50 == 0:
                save('pool.json', games)
                save('players_done.json', sorted(seen_players))
                print(f'{done} players, {len(games)} games', flush=True)
    save('pool.json', games)
    save('players_done.json', sorted(seen_players))
    print(f'{len(games)} games of version {version} in the pool')


def merged():
    """the pool (written by `pool` alone) with the games whose ten champions were read (details.json)"""
    games = load('pool.json', {})
    for gid, champs in load('details.json', {}).items():
        if gid in games:
            games[gid] = dict(games[gid], champions=champs, full=True)
    return games


def full_game(c, gid, details):
    """the game's ten champions from the server -> details.json"""
    g = c.get(f'/lol-match-history/v1/games/{gid}')
    if not g:
        return None
    details[gid] = {str(p['championId']): p.get('teamId', 0) for p in g.get('participants', [])}
    return details[gid]


# ------------------------------------------------------------------------------------------------ which games to fetch
def plan():
    c = Client()
    names = champion_names()
    ids = {v.lower(): k for k, v in names.items()}
    games = merged()
    details = load('details.json', {})
    need_n = int(arg('--per-champion', 3))
    first = [ids[x.lower()] for x in (arg('--first') or '').split(',') if x and x.lower() in ids]
    maxg = int(arg('--max', 150))
    fetched = load('fetched.json', {})
    chosen = [g for g in load('plan.json', []) if g in games]
    have = {cid: 0 for cid in names}
    for gid in set(fetched) | set(chosen):
        for cid in (games.get(gid) or fetched.get(gid, {})).get('champions', {}):
            if int(cid) in have:
                have[int(cid)] += 1
    while len(chosen) < maxg:
        want = {cid for cid, n in have.items() if n < need_n}
        if not want:
            break
        # the champions asked for first, then any game that adds champions still short
        best, best_score = None, 0
        for gid, e in games.items():
            if gid in chosen or gid in fetched:
                continue
            cs = {int(x) for x in e['champions']}
            gain = len(cs & want)
            if not gain:
                continue
            score = gain + 10 * len(cs & set(first) & want) + (0.5 if e['full'] else 0) + e['duration'] / 1e5
            if score > best_score:
                best, best_score = gid, score
        if best is None:
            break
        e = games[best]
        if not e['full']:
            champs = full_game(c, best, details)
            if champs is None:
                e['champions'] = {}
                continue
            e['champions'], e['full'] = champs, True
            if not {int(x) for x in champs} & want:
                continue
        chosen.append(best)
        for cid in e['champions']:
            if int(cid) in have:
                have[int(cid)] += 1
        if len(chosen) % 10 == 0:
            save('details.json', details)
            save('plan.json', chosen)
            print(f'{len(chosen)} games planned; champions short of {need_n}: '
                  f'{sum(1 for n in have.values() if n < need_n)}', flush=True)
    save('details.json', details)
    save('plan.json', chosen)
    missing = sorted(names[cid] for cid, n in have.items() if n == 0)
    short = sorted(names[cid] for cid, n in have.items() if 0 < n < need_n)
    print(f'{len(chosen)} games planned; champions in none of them ({len(missing)}): {missing}')
    print(f'in fewer than {need_n} ({len(short)}): {short}')


# ------------------------------------------------------------------------------------------------ fetching
def fetch_one(c, gid, e, folder):
    """one game's replay -> its state ('watch' = on disk)"""
    meta = c.get(f'/lol-replays/v1/metadata/{gid}')
    if meta is None:
        c.post(f'/lol-replays/v1/metadata/{gid}/create/gameVersion/{e["version"]}/gameType/{e.get("type", "MATCHED_GAME")}'
               f'/queueId/{e["queue"]}')
    state, t0 = None, time.time()
    while time.time() - t0 < 60:
        meta = c.get(f'/lol-replays/v1/metadata/{gid}') or {}
        state = meta.get('state')
        if state not in (None, 'checking', 'found'):
            break
        time.sleep(1.0)
    if state in ('download', 'retryDownload'):
        c.post(f'/lol-replays/v1/rofls/{gid}/download', {'componentType': 'replay-button_match-history'})
        t0 = time.time()
        while time.time() - t0 < 900:
            meta = c.get(f'/lol-replays/v1/metadata/{gid}') or {}
            state = meta.get('state')
            if state not in ('downloading', 'download', 'checking'):
                break
            time.sleep(1.5)
    return state


def fetch():
    """the planned games one after the other; with --follow it waits for more to be planned"""
    c = Client()
    folder = c.get('/lol-replays/v1/rofls/path')
    os.makedirs(os.path.join(OUT, 'rofl'), exist_ok=True)
    maxn = int(arg('--max', 100000))
    follow = '--follow' in sys.argv
    n = 0
    while n < maxn:
        games = merged()
        fetched = load('fetched.json', {})
        failed = load('failed.json', {})
        todo = [g for g in load('plan.json', []) if g not in fetched and g not in failed and g in games]
        if not todo:
            if not follow:
                break
            time.sleep(30)
            continue
        gid = todo[0]
        e = games[gid]
        state = fetch_one(c, gid, e, folder)
        src = os.path.join(folder, f'EUN1-{gid}.rofl')
        if state == 'watch' and os.path.exists(src):
            dst = os.path.join(OUT, 'rofl', f'{gid}.rofl')
            shutil.move(src, dst)
            fetched[gid] = {'champions': e['champions'], 'queue': e['queue'], 'duration': e['duration'],
                            'size': os.path.getsize(dst)}
            save('fetched.json', fetched)
            n += 1
            print(f'{gid}: {os.path.getsize(dst) / 1e6:.1f} MB, {e["duration"] // 60} min ({len(fetched)} fetched)', flush=True)
        else:
            failed[gid] = state
            save('failed.json', failed)
            print(f'{gid}: not fetched (state {state})', flush=True)


def cover():
    names = champion_names()
    fetched = load('fetched.json', {})
    have = {cid: 0 for cid in names}
    for e in fetched.values():
        for cid in e['champions']:
            if int(cid) in have:
                have[int(cid)] += 1
    print(len(fetched), 'replays,', sum(e.get('size', 0) for e in fetched.values()) / 1e6, 'MB')
    for cid, n in sorted(have.items(), key=lambda x: (x[1], names[x[0]])):
        print(f'{names[cid]:14s} {n}')


def status():
    c = Client()
    print('client', c.get('/lol-replays/v1/configuration'))
    print('pool', len(load('pool.json', {})), 'planned', len(load('plan.json', [])), 'fetched', len(load('fetched.json', {})),
          'failed', len(load('failed.json', {})))


if __name__ == '__main__':
    {'status': status, 'pool': pool, 'plan': plan, 'fetch': fetch, 'cover': cover}[sys.argv[1]]()
