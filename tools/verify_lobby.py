"""Real-process launcher regression: config rejection, concurrent Start, client join, exit cleanup, replay.

python tools/verify_lobby.py --bin build-test/bin --port 21339
Starts a real game client, then terminates only this test's child processes. Requires psutil.
The existing last_match.basr is backed up before this test writes a new recording.
"""
import argparse
import concurrent.futures
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.parse
import urllib.request

import psutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bin', default='build-test/bin')
    parser.add_argument('--port', type=int, default=21339)
    args = parser.parse_args()
    folder = Path(args.bin).resolve()
    base = f'http://127.0.0.1:{args.port}'
    record = folder / 'last_match.basr'
    if record.exists():
        shutil.copy2(record, folder / f'pre-parity-test-{time.time_ns()}.basr')
    children = []
    proc = subprocess.Popen([str(folder / 'lobby.exe'), '--no-browser', '1', '--port', str(args.port)],
                            cwd=folder, creationflags=subprocess.CREATE_NO_WINDOW)
    owner = psutil.Process(proc.pid)

    def request(path, body=None):
        data = urllib.parse.urlencode(body).encode() if body is not None else None
        with urllib.request.urlopen(urllib.request.Request(base + path, data=data), timeout=70) as response:
            return json.load(response)

    def until(check, seconds=90):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if proc.poll() is not None:
                raise RuntimeError(f'lobby exited: {proc.returncode}')
            try:
                value = check()
                if value:
                    return value
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(0.1)
        raise TimeoutError('test condition did not become true')

    try:
        until(lambda: request('/lol/modes'))
        assert request('/lol/modes') == [dict(gameMode='PRACTICETOOL', mapId=11, teamSize=1, mutatorId=1, available=True)]
        valid = dict(champion='Garen', name='Parity', gameMode='PRACTICETOOL', mapId=11)
        for override in [dict(gameMode='ARAM'), dict(mapId=12), dict(champion='NoSuchChampion'), dict(gameMode='')]:
            assert request('/lol/start', valid | override)['ok'] is False
        assert not request('/lol/status')['inGame']
        print('PASS mode/map/champion validation', flush=True)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda _: request('/lol/start', valid), range(2)))
        assert sorted(r['ok'] for r in responses) == [False, True], responses
        children = owner.children()
        clients = [p for p in children if Path(p.exe()).name.lower() == 'client.exe']
        servers = [p for p in children if Path(p.exe()).name.lower() == 'server.exe']
        assert len(clients) == len(servers) == 1, [(p.pid, p.name()) for p in children]
        assert request('/lol/status')['inGame']
        print('PASS concurrent Start launches exactly one client and one ready server', flush=True)
        until(lambda: record.exists() and b'Garen' in record.read_bytes(), 120)
        # Record another checkpoint after Hello/spawn, then close this test's client.
        initial_size = record.stat().st_size
        until(lambda: record.stat().st_size > initial_size + 17)
        print('PASS native client loaded and joined the server as Garen', flush=True)
        clients[0].terminate()
        until(lambda: not request('/lol/status')['inGame'])
        until(lambda: not owner.children())
        print('PASS client exit stops server and releases process handles', flush=True)
        result = subprocess.run([str(folder / 'server.exe'), '--replay', str(record)], cwd=folder,
                                capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
        print(result.stdout[-1600:], flush=True)
        assert result.returncode == 0, result.stderr
        print('PASS replay identical', flush=True)
    finally:
        if proc.poll() is None:
            # psutil Process handles check PID reuse; only descendants of our own launcher are stopped.
            for child in owner.children():
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            proc.terminate()
        proc.wait(timeout=10)


if __name__ == '__main__':
    main()
