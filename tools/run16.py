"""Run the 16.20 game copy (game16) on a replay for a while, then close it.

    python tools/run16.py <seconds> [rofl]

game16 is a full, separate copy of the 16.20 client (exe at its root, locale en_US) with our
DINPUT8.dll beside the exe; the live install is not involved.
Refuses to start while the Vanguard driver (vgk) is loaded.
Prints the game's state once per 5 s (official local API on port 2999) and our ba16.log.
"""
import glob, json, os, ssl, subprocess, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game16")
BASE_DIR = os.path.join(ROOT, "game16")
REPLAYS = os.path.expanduser(r"~\Documents\League of Legends\Replays")


def game_time():
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen("https://127.0.0.1:2999/liveclientdata/gamestats", context=ctx, timeout=2) as r:
            return json.loads(r.read()).get("gameTime")
    except Exception:
        return None


def main():
    seconds = int(sys.argv[1])
    rofl = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(os.path.join(REPLAYS, "*.rofl")))[-1]
    if "RUNNING" in subprocess.run(["sc", "query", "vgk"], capture_output=True, text=True).stdout:
        sys.exit("vgk is loaded: exit Vanguard from its tray icon first")
    log = os.path.join(GAME, "ba16.log")
    if os.path.exists(log):
        os.remove(log)
    args = [os.path.join(GAME, "League of Legends.exe"), rofl, f"-GameBaseDir={BASE_DIR}", "-SkipRads", "-SkipBuild",
            "-EnableLNP", "-UseNewX3D=1", "-UseNewX3DFramebuffers=1", "-Locale=en_US"]
    p = subprocess.Popen(args, cwd=GAME)
    print("pid", p.pid)
    t0 = time.time()
    try:
        while time.time() - t0 < seconds:
            time.sleep(5)
            if p.poll() is not None:
                print(f"t={time.time() - t0:.0f}s exited, code {p.returncode:#x}")
                break
            print(f"t={time.time() - t0:.0f}s alive, game time {game_time()}")
    finally:
        if p.poll() is None:
            p.kill()
    if os.path.exists(log):
        print("--- ba16.log")
        print(open(log).read())


if __name__ == "__main__":
    main()
