"""Development server for the 13.3 out-of-game client page (lobby/www13): serves the League Client 13.3 front-end files
at the addresses the client itself uses, like lobby.exe does, so the page can be built and checked in a browser.

    /fe/<name>/<file>              lcu-data/13.3/plugins/rcp-fe-<name>/global/default/<file>
    /lol-game-data/assets/<file>   lcu-data/13.3/plugins/rcp-be-lol-game-data/global/default/<file> (case-insensitive)
    /lol/champions                 every champion of 13.3 (champion-summary.json without the "None" entry), with the
                                   base skin's splash and the pick voice / stinger of the champion's own JSON
    /lol/me                        the player (the Windows account name)
    POST /lol/start                champion=<alias>&skin=<n>: starts our game server (tools/sponge/lnp_server.py) and the
                                   unpacked 13.3 game with that champion as player slot 1
    /lol/status                    {inGame}: the game process is still running
    /<file>                        lobby/www13/<file>

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
LCU = os.path.join(ROOT, 'lcu-data', '13.3', 'plugins')
WWW = os.path.join(ROOT, 'lobby', 'www13')
GD = os.path.join(LCU, 'rcp-be-lol-game-data', 'global', 'default')
_lower = {}
GAME_DIR = r'C:\Users\Sorin\Desktop\lol13.3'
GAME_EXE = os.path.join(GAME_DIR, 'League of Legends.unpacked.exe')
REPLAY = os.path.join(ROOT, 'research', 'rofl', 'KR-6363178603_13.3.rofl')
GAME_PORT = 5119
GAME_KEY = '17BLOhi6KZsTtldTsizvHg=='
SERVER_LOG = os.path.join(ROOT, 'research', 'exe133', 'play_server.log')
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
                            stingerSfxPath=full.get('stingerSfxPath'))
            except (OSError, KeyError, IndexError):
                pass
            _champions.append(item)
    return _champions


def in_game():
    return game['client'] is not None and game['client'].poll() is None


def start_game(champion, skin):
    """our game server, then the game client connected to it. The match starts from the 13.3 replay's start state
    (keyframe 1: map objects, the ten heroes at their fountains) and nothing of the replay after it (--start-only):
    the world is our server's. The player is slot 1, with the chosen champion in the player list (574, loading
    screen) and in the hero's creation (79)."""
    if in_game():
        raise RuntimeError('a game is already running')
    if not os.path.isfile(GAME_EXE):
        raise RuntimeError('game not found: ' + GAME_EXE)
    ids = {c['alias']: c['id'] for c in champions()}
    if champion not in ids:
        raise RuntimeError('unknown champion ' + champion)
    player = os.environ.get('USERNAME', 'Player')
    log = open(SERVER_LOG, 'w', encoding='utf8')
    server = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, 'tools', 'sponge', 'lnp_server.py'), '--replay-574', '--slot', '1',
         '--own-574', '--set574', f'1.champion={champion};1.champion_id={ids[champion]};1.skin={int(skin)};1.name={player}',
         '--hero', '4000001e', '--own-79', '--set79', f'1.champion={champion};1.skin={int(skin)}',
         '--start-only', '--stream', REPLAY, str(GAME_PORT)],
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
            return self.send(200, json.dumps(champions()).encode(), 'application/json')
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
                start_game(form.get('champion', ''), form.get('skin', '0'))
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
