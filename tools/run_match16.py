"""Start the 16.20 game copy (game16) in match mode against a local server script for a few
seconds and collect what both sides saw.

    python tools/run_match16.py <seconds> <name> [server command ...]

The server command gets the port as its last argument and is stopped at the end; default:
tools/udp_listen.py (answers nothing). Keep <seconds> under 20 without a working server: the
13.3 client showed "Failed to Connect" at 30 s. Output in data/exe1620/match_<name>/:
server.txt, ba16.log (our DLL), r3dlog / netlog (the client's own logs).
Refuses to start while the Vanguard driver (vgk) is loaded.
"""
import glob, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game16")
PORT = 5119
KEY = "17BLOhi6KZsTtldTsizvHg=="


def main():
    seconds, name, server = float(sys.argv[1]), sys.argv[2], sys.argv[3:]
    if "RUNNING" in subprocess.run(["sc", "query", "vgk"], capture_output=True, text=True).stdout:
        sys.exit("vgk is loaded: exit Vanguard from its tray icon first")
    out = os.path.join(ROOT, "data", "exe1620", f"match_{name}")
    os.makedirs(out, exist_ok=True)
    srv_txt = os.path.join(out, "server.txt")
    if server:
        srv = subprocess.Popen(server + [str(PORT)], stdout=open(srv_txt, "w"), stderr=subprocess.STDOUT, cwd=ROOT)
    else:
        srv = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "udp_listen.py"), str(PORT),
                                str(seconds + 2), srv_txt])
    time.sleep(1)
    log = os.path.join(GAME, "ba16.log")
    if os.path.exists(log):
        os.remove(log)
    before = set(os.listdir(os.path.join(GAME, "Logs", "GameLogs")))
    game = subprocess.Popen([os.path.join(GAME, "League of Legends.exe"), f"127.0.0.1 {PORT} {KEY} 1", "-Product=LoL",
                             "-PlayerID=1", "-GameID=1", f"-GameBaseDir={GAME}", "-Region=EUW", "-PlatformID=EUW1",
                             "-Locale=en_US", "-SkipBuild", "-UseNewX3D=1", "-UseNewX3DFramebuffers=1"], cwd=GAME)
    t0 = time.time()
    helpers = []
    # BA_SHOTS="20,40": screenshots at those seconds -> shot_1.png ...; BA_INPUT="<plan>": tools/game_input.ps1
    if os.environ.get("BA_SHOTS"):
        helpers.append(subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "tools", "screenshot.ps1"),
                                         os.path.join(out, "shot.png"), os.environ["BA_SHOTS"]]))
    if os.environ.get("BA_INPUT"):
        helpers.append(subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", os.path.join(ROOT, "tools", "game_input.ps1"),
                                         os.environ["BA_INPUT"], os.path.join(out, "input.log")], env=dict(os.environ, BA_GAME_PROCESS="League of Legends")))
    while time.time() - t0 < seconds and game.poll() is None:
        time.sleep(0.5)
    print(f"game {'exited, code %#x' % game.returncode if game.poll() is not None else 'running'} after {time.time() - t0:.1f} s")
    if game.poll() is None:
        game.kill()
    for h in helpers:
        if h.poll() is None:
            h.kill()
    time.sleep(1)
    if srv.poll() is None:
        srv.kill()
    if os.path.exists(log):
        shutil.copy(log, os.path.join(out, "ba16.log"))
    for d in sorted(set(os.listdir(os.path.join(GAME, "Logs", "GameLogs"))) - before):
        for f in glob.glob(os.path.join(GAME, "Logs", "GameLogs", d, "*")):
            shutil.copy(f, os.path.join(out, os.path.basename(f).split("_", 1)[1]))
    for f in sorted(os.listdir(out)):
        print(f"{os.path.getsize(os.path.join(out, f)):9} {f}")


if __name__ == "__main__":
    main()
