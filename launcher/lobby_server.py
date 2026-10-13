"""Development server for the 13.3 out-of-game client page (launcher/www): serves the League Client 13.3 front-end files
at the addresses the client itself uses, like lobby.exe does, so the page can be built and checked in a browser.

    /fe/<name>/<file>              data/lcu/13.3/plugins/rcp-fe-<name>/global/default/<file>
    /lol-game-data/assets/<file>   data/lcu/13.3/plugins/rcp-be-lol-game-data/global/default/<file> (case-insensitive)
    /lol/champions                 every champion of 13.3 (champion-summary.json without the "None" entry), with the
                                   base skin's splash and the pick voice / stinger of the champion's own JSON
    /lol/me                        the player (the Windows account name)
    POST /lol/start                champion=<alias>&skin=<n>: starts our game server (server/lnp_server.py) and the
                                   unpacked 13.3 game with that champion as player slot 1
    /lol/status                    {inGame}: the game process is still running
    /<file>                        launcher/www/<file>

  lobby_dev_server.py [port=5180]
"""
import http.server
import json
import mimetypes
import os
import socketserver
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
LCU = os.path.join(ROOT, 'data', 'lcu', '13.3', 'plugins')
WWW = os.path.join(ROOT, 'launcher', 'www')
GD = os.path.join(LCU, 'rcp-be-lol-game-data', 'global', 'default')
_lower = {}
GAME_DIR = r'C:\Users\Sorin\Desktop\ProiectBattleArenaPc\game'
GAME_EXE = os.path.join(GAME_DIR, 'League of Legends.unpacked.exe')
REPLAY = os.path.join(ROOT, 'data', 'rofl', 'KR-6363178603_13.3.rofl')
# Lane minions: until server/world.py's own spawn packets make the client walk a new minion out of its barracks
# (2026-10-10: ours pile up on the spawn point, the real server's do not - measured with these very options), the
# match takes the real stream's minion packets. Set to [] for our own world.
MINION_SOURCE = []
GAME_PORT = 5119
GAME_KEY = '17BLOhi6KZsTtldTsizvHg=='
SERVER_LOG = os.path.join(ROOT, 'data', 'exe133', 'play_server.log')
game = {'server': None, 'client': None}
_champions = []


def champions():
    """the champion list with what champion select needs from each champion's own JSON"""
    if not _champions:
        summ = json.load(open(os.path.join(GD, 'v1', 'champion-summary.json'), encoding='utf8'))
        for c in summ:
            if c['id'] <= 0:
                continue
            item = dict(c)
            try:
                full = json.load(open(os.path.join(GD, 'v1', 'champions', f"{c['id']}.json"), encoding='utf8'))
                item.update(splashPath=full['skins'][0]['splashPath'], chooseVoPath=full.get('chooseVoPath'),
                            stingerSfxPath=full.get('stingerSfxPath'),
                            # every skin: its number in the game (id = champion id * 1000 + number), name, splash
                            skins=[{'num': s['id'] % 1000, 'name': s['name'], 'splashPath': s['splashPath']}
                                   for s in full['skins'] if 'splashPath' in s])
            except (OSError, KeyError, IndexError):
                pass
            _champions.append(item)
    return _champions


def in_game():
    return game['client'] is not None and game['client'].poll() is None


def kill_existing_server():
    """Ensure any existing game server or process holding GAME_PORT is stopped."""
    if game.get('server') is not None:
        try:
            if game['server'].poll() is None:
                game['server'].kill()
                game['server'].wait(timeout=2)
        except Exception:
            pass
        game['server'] = None
    try:
        import socket
        ts = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            ts.bind(('127.0.0.1', GAME_PORT))
            ts.close()
        except OSError:
            # Port is occupied, force kill process holding it
            cmd = f"Get-NetUDPEndpoint -LocalPort {GAME_PORT} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=5)
            time.sleep(0.5)
    except Exception:
        pass


# The 16.20 client (game16, a separate copy of the live client) with our 16.20 server (server/main16.py, package
# server/core): the default. BA_PATCH=133 in the environment brings the 13.3 pair back.
PATCH = os.environ.get('BA_PATCH', '1620').replace('.', '')
GAME16_DIR = os.path.join(ROOT, 'game16')
SERVER_LOG16 = os.path.join(ROOT, 'data', 'exe1620', 'play_server.log')
ICONS16 = os.path.join(ROOT, 'data', 'exe1620', 'icons')
_champions16 = []


def champions16():
    """every champion of the 16.20 game copy, from its own data (server/core/gamedata.champion_index): the square
    icon and the loading-screen picture come out of the champion's own wad (/lol/icon16, /lol/load16); the display
    name, the positions and the pick sounds are the 13.3 client's where it knows the champion"""
    if not _champions16:
        sys.path.insert(0, os.path.join(ROOT, 'server'))
        os.environ['BA_PATCH'] = '1620'
        from core import gamedata as G
        old = {c['id']: c for c in champions()}
        for c in sorted(G.champion_index(), key=lambda c: c['alias']):
            o = old.get(c['id'], {})
            _champions16.append({'id': c['id'], 'name': o.get('name') or c['alias'], 'alias': c['alias'],
                                 'squarePortraitPath': f"/lol/icon16/{c['alias']}.png",
                                 'splashPath': o.get('splashPath') or f"/lol/load16/{c['alias']}.jpg",
                                 'roles': o.get('roles') or [t for t in c['tags'] if t],
                                 'chooseVoPath': o.get('chooseVoPath'), 'stingerSfxPath': o.get('stingerSfxPath'),
                                 'skins': o.get('skins') or []})
        _champions16.sort(key=lambda c: c['name'])
    return _champions16


def picture16(kind, alias):
    """a champion's square icon ('icon') or loading-screen art ('load') as a file, made once from the texture in
    its wad (server/wad.py)"""
    os.makedirs(ICONS16, exist_ok=True)
    out = os.path.join(ICONS16, f'{alias}_{kind}.' + ('png' if kind == 'icon' else 'jpg'))
    if os.path.isfile(out):
        return out
    sys.path.insert(0, os.path.join(ROOT, 'server'))
    os.environ['BA_PATCH'] = '1620'
    from core import gamedata as G
    import wad
    c = next((c for c in G.champion_index() if c['alias'] == alias), None)
    h = c and c['square' if kind == 'icon' else 'load']
    if not h:
        return None
    data = wad.read(os.path.join(GAME16_DIR, 'DATA', 'FINAL', 'Champions', f'{alias}.wad.client'), int(h, 16))
    im = wad.texture(data)
    if im is None:
        return None
    if kind == 'icon':
        im.save(out)
    else:
        im.convert('RGB').save(out, quality=88)
    return out


def start_game16(champion, skin, spells='', runes=''):
    """our 16.20 server with a roster (the picked champion, nine bots by position from the champions whose class
    fits it), then the 16.20 game copy connected to it"""
    if in_game():
        raise RuntimeError('a game is already running')
    kill_existing_server()
    if 'RUNNING' in subprocess.run(['sc', 'query', 'vgk'], capture_output=True, text=True).stdout:
        raise RuntimeError('Vanguard is running: exit it from its tray icon first (the 16.20 copy is only run without it)')
    exe = os.path.join(GAME16_DIR, 'League of Legends.exe')
    if not os.path.isfile(exe):
        raise RuntimeError('game not found: ' + exe)
    if champion not in [c['alias'] for c in champions16()]:
        raise RuntimeError('unknown champion ' + champion)
    log = open(SERVER_LOG16, 'w', encoding='utf8')
    extra = []
    if str(skin).isdigit() and int(skin) > 0:
        extra += ['--skin', str(int(skin))]
    picked = [s for s in spells.split(',') if s.isalnum()]
    if len(picked) == 2:
        extra += ['--summoners', ','.join(picked)]
    if runes.isalnum():
        extra += ['--runes', runes]
    server = subprocess.Popen(
        [sys.executable, '-W', 'ignore', '-u', os.path.join(ROOT, 'server', 'main16.py'), '--champion', champion,
         '--bots', 'random', '--seed', str(int(time.time()) % 100000 + 1)] + extra + [str(GAME_PORT)],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    time.sleep(2.5)        # the server builds the match (data from the bin cache, about a second)
    if server.poll() is not None:
        raise RuntimeError('the game server stopped at once, see ' + SERVER_LOG16)
    client = subprocess.Popen(
        [exe, f'127.0.0.1 {GAME_PORT} {GAME_KEY} 1', '-Product=LoL', '-PlayerID=1', '-GameID=1',
         f'-GameBaseDir={GAME16_DIR}', '-Region=EUW', '-PlatformID=EUW1', '-Locale=en_US', '-SkipBuild', '-UseNewX3D=1',
         '-UseNewX3DFramebuffers=1'], cwd=GAME16_DIR)
    game.update(server=server, client=client)

    def watch():
        client.wait()
        time.sleep(1)
        if server.poll() is None:
            server.kill()
        log.close()
    threading.Thread(target=watch, daemon=True).start()
    print(f'16.20 game started: {champion} (server pid {server.pid}, game pid {client.pid}); server log {SERVER_LOG16}', flush=True)


def start_game(champion, skin, spells='', runes=''):
    """our game server, then the game client connected to it. The match starts from the 13.3 replay's start state
    (keyframe 1: map objects, the ten heroes at their fountains) and nothing of the replay after it (--start-only):
    the world is our server's. The player is slot 1, with the chosen champion in the player list (574, loading
    screen) and in the hero's creation (79)."""
    if PATCH == '1620':
        return start_game16(champion, skin, spells, runes)
    if in_game():
        raise RuntimeError('a game is already running')
    kill_existing_server()
    if not os.path.isfile(GAME_EXE):
        raise RuntimeError('game not found: ' + GAME_EXE)
    ids = {c['alias']: c['id'] for c in champions()}
    if champion not in ids:
        raise RuntimeError('unknown champion ' + champion)
    player = os.environ.get('USERNAME', 'Player')
    log = open(SERVER_LOG, 'w', encoding='utf8')
    server = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, 'server', 'lnp_server.py'), '--replay-574', '--slot', '1',
         '--own-574', '--set574', f'1.champion={champion};1.champion_id={ids[champion]};1.skin={int(skin)};1.name={player}',
         '--hero', '4000001e', '--own-79', '--set79', f'1.champion={champion};1.skin={int(skin)}',
         '--start-only', *MINION_SOURCE, '--stream', REPLAY, str(GAME_PORT)],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    time.sleep(2)
    if server.poll() is not None:
        raise RuntimeError('the game server stopped at once, see ' + SERVER_LOG)
    client = subprocess.Popen(
        [GAME_EXE, f'127.0.0.1 {GAME_PORT} {GAME_KEY} 1', '-Product=LoL', '-PlayerID=1', '-GameID=1',
         f'-GameBaseDir={GAME_DIR}', '-Region=EUW', '-PlatformID=EUW1', '-Locale=en_US', '-SkipBuild', '-UseDX11=1:1'],
        cwd=GAME_DIR)
    game.update(server=server, client=client)

    def watch():   # the game window closed: stop our server (by its own process, never by image name)
        client.wait()
        time.sleep(1)
        if server.poll() is None:
            server.kill()
        log.close()
    threading.Thread(target=watch, daemon=True).start()
    print(f'game started: {champion} (server pid {server.pid}, game pid {client.pid})', flush=True)


def find_ci(base, rel):
    """a file below base by a path whose letter case may differ from the file's (game data paths are lower-cased
    in some JSON and not in others)"""
    p = os.path.join(base, rel)
    if os.path.isfile(p):
        return p
    if base not in _lower:
        idx = {}
        for d, _, fs in os.walk(base):
            for f in fs:
                full = os.path.join(d, f)
                idx[os.path.relpath(full, base).replace('\\', '/').lower()] = full
        _lower[base] = idx
    return _lower[base].get(rel.replace('\\', '/').lower())


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, data, ctype='application/octet-stream'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def file(self, path):
        if not path or not os.path.isfile(path):
            return self.send(404, b'not found', 'text/plain')
        ctype = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if path.endswith('.webm'):
            ctype = 'video/webm'
        if path.endswith('.ogg'):
            ctype = 'audio/ogg'
        self.send(200, open(path, 'rb').read(), ctype)

    def do_GET(self):
        p = self.path.split('?')[0]
        from urllib.parse import unquote
        p = unquote(p)
        if p.startswith('/fe/'):
            name, _, rel = p[4:].partition('/')
            return self.file(find_ci(os.path.join(LCU, 'rcp-fe-' + name, 'global', 'default'), rel))
        if p.startswith('/lol-game-data/assets/'):
            return self.file(find_ci(GD, p[len('/lol-game-data/assets/'):]))
        if p == '/lol/champions':
            return self.send(200, json.dumps(champions16() if PATCH == '1620' else champions()).encode(), 'application/json')
        if p.startswith('/lol/icon16/') or p.startswith('/lol/load16/'):
            kind = 'icon' if p.startswith('/lol/icon16/') else 'load'
            alias = os.path.basename(p).split('.')[0]
            if not alias.isalnum():
                return self.send(404, b'not found', 'text/plain')
            return self.file(picture16(kind, alias))
        if p == '/lol/status':
            return self.send(200, json.dumps({'inGame': in_game()}).encode(), 'application/json')
        if p == '/lol/me':
            # the local player: name = the Windows account; icon / level are this installation's own values (no
            # account service): icon 0 (one of the starter icons 0-28; 29 is the client's blank helmet), level 30 (ranked queues need 30)
            me = {'name': os.environ.get('USERNAME', 'Player'), 'profileIconId': 0, 'summonerLevel': 30}
            return self.send(200, json.dumps(me).encode(), 'application/json')
        if p == '/':
            p = '/index.html'
        return self.file(os.path.join(WWW, p.lstrip('/')))


    def do_POST(self):
        from urllib.parse import parse_qs
        n = int(self.headers.get('Content-Length') or 0)
        form = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if self.path.split('?')[0] == '/lol/start':
            try:
                start_game(form.get('champion', ''), form.get('skin', '0'), form.get('spells', ''), form.get('runes', ''))
                return self.send(200, b'{"ok": true}', 'application/json')
            except Exception as e:  # noqa: BLE001
                return self.send(500, json.dumps({'ok': False, 'error': str(e)}).encode(), 'application/json')
        return self.send(404, b'not found', 'text/plain')


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5180
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', port), H) as s:
        print(f'http://127.0.0.1:{port}/', flush=True)
        s.serve_forever()
