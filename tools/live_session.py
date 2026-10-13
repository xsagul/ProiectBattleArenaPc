"""Watch the live LCU and save what a match start hands to the game client.

Reads the LCU lockfile, polls /lol-gameflow/v1/session and, once a game is
starting, writes the session (server ip/port, team data) plus the game command
line (per-match key, LNP blob) into data/live/<gameId>/, then copies the game's
own net logs there when the match ends. Read-only: local LCU API and the game's
log files, nothing touches the game process.

    python tools/live_session.py
"""
import base64
import json
import os
import re
import shutil
import ssl
import sys
import time
import urllib.request

LOCKFILE = r"C:\Riot Games\League of Legends\lockfile"
GAMELOGS = r"C:\Riot Games\League of Legends\Logs\GameLogs"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "live")
ACTIVE = ("GameStart", "InProgress", "Reconnect")


def lcu_get(path):
    with open(LOCKFILE) as f:
        _, _, port, token, scheme = f.read().split(":")
    req = urllib.request.Request(f"{scheme}://127.0.0.1:{port}{path}")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"riot:{token}".encode()).decode())
    ctx = ssl._create_unverified_context()  # LCU serves Riot's self-signed cert on loopback
    with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
        return json.loads(r.read())


def game_log_dir(gid):
    """Newest GameLogs folder whose r3dlog was started for this game id, plus its command line.

    The process itself is protected (empty CommandLine in the OS process list), but the
    game writes its own arguments - address, port, per-match key, LNP blob - to the r3dlog.
    """
    try:
        names = sorted(os.listdir(GAMELOGS), reverse=True)[:5]
    except OSError:
        return None, ""
    for name in names:
        try:
            with open(os.path.join(GAMELOGS, name, name + "_r3dlog.txt"), encoding="utf-8", errors="replace") as f:
                head = f.read(16384)
        except OSError:
            continue
        if "-GameID=%s\"" % gid in head:
            for line in head.splitlines():
                if "Command Line:" in line:
                    cmd = line.split("Command Line:", 1)[1].strip()
                    # the Riot Client login token is not part of the game protocol; don't keep it
                    cmd = re.sub(r'\s*"-RiotClientAuthToken=[^"]*"', "", cmd)
                    return os.path.join(GAMELOGS, name), cmd
    return None, ""


def main():
    # runs across any number of matches; one folder per gameId
    last_phase, saved_session, saved_cmd, pending_logs = None, set(), set(), {}
    while True:
        try:
            s = lcu_get("/lol-gameflow/v1/session")
            phase = s.get("phase", "None")
        except Exception as e:  # no session yet (404) or client closed
            s, phase = None, "None"
            if not os.path.exists(LOCKFILE):
                print("LCU closed:", e)
                return
        if phase != last_phase:
            print(time.strftime("%H:%M:%S"), "phase:", phase, flush=True)
            last_phase = phase
        if s and phase in ACTIVE:
            gid = str(s.get("gameData", {}).get("gameId", 0))
            d = os.path.join(OUT, gid)
            os.makedirs(d, exist_ok=True)
            # 16.20: playerCredentials is gone, the server address sits in gameClient
            cred = dict(s.get("gameClient") or {})
            cred.update(s.get("gameData", {}).get("playerCredentials") or {})
            if gid not in saved_session and cred.get("serverIp"):
                s["capturedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(os.path.join(d, "session.json"), "w", encoding="utf-8") as f:
                    json.dump(s, f, indent=1)
                print("game %s: saved session.json, queue %s, server %s:%s, key %s" % (
                    gid, s.get("gameData", {}).get("queue", {}).get("id"),
                    cred.get("serverIp"), cred.get("serverPort"),
                    "present" if cred.get("encryptionKey") else "EMPTY"), flush=True)
                saved_session.add(gid)
            if gid not in saved_cmd:
                logdir, cmd = game_log_dir(gid)
                if cmd:
                    with open(os.path.join(d, "cmdline.txt"), "w", encoding="utf-8") as f:
                        f.write(cmd)
                    print("game %s: saved cmdline.txt (%d args) from %s" % (
                        gid, cmd.count('" "') + 1, os.path.basename(logdir)), flush=True)
                    saved_cmd.add(gid)
                    pending_logs[gid] = logdir
        elif pending_logs:
            # match over: keep the game's own net logs (netlog, netstats, r3dlog) next to the capture
            for gid, logdir in list(pending_logs.items()):
                dst = os.path.join(OUT, gid, "gamelogs")
                try:
                    shutil.copytree(logdir, dst, dirs_exist_ok=True)
                    print("game %s: copied game logs (%d files)" % (gid, len(os.listdir(dst))), flush=True)
                    del pending_logs[gid]
                except OSError as e:
                    print("game %s: game logs still locked (%s), retrying" % (gid, e), flush=True)
        time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
