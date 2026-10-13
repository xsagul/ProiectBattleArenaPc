"""Take the working image for the 16.20 learners: the client in a match from our own server (server/lnp16.py with
the replay), then
  - its main module image          -> data/exe1620/exe_image_live.bin (+ _pages.txt)
  - the pages outside the image that the packet readers touch (singletons the image only points to), fetched while
    every packet kind of the replay is run through its reader -> data/exe1620/live_pages/<address>.bin
Afterwards server/packet_emu16.py works offline from these files.

    python tools/snapshot16.py [seconds in game before the snapshot, default 25]

Refuses to start while the Vanguard driver (vgk) is loaded.
"""
import os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game16")
OUT = os.path.join(ROOT, "data", "exe1620")
ROFL = os.path.join(os.path.expanduser("~"), "Documents", "League of Legends", "Replays", "EUN1-4013530370.rofl")
PORT, KEY = 5119, "17BLOhi6KZsTtldTsizvHg=="


def main():
    wait = float(sys.argv[1]) if len(sys.argv) > 1 else 25
    if "RUNNING" in subprocess.run(["sc", "query", "vgk"], capture_output=True, text=True).stdout:
        sys.exit("vgk is loaded: exit Vanguard from its tray icon first")
    srv = subprocess.Popen([sys.executable, "-W", "ignore", "-u", os.path.join(ROOT, "server", "lnp16.py"), "--replay", ROFL,
                            "--slot", "2", "--start", "--stream", str(PORT)], stdout=subprocess.DEVNULL, cwd=ROOT)
    time.sleep(1)
    game = subprocess.Popen([os.path.join(GAME, "League of Legends.exe"), f"127.0.0.1 {PORT} {KEY} 1", "-Product=LoL",
                             "-PlayerID=1", "-GameID=1", f"-GameBaseDir={GAME}", "-Region=EUW", "-PlatformID=EUW1",
                             "-Locale=en_US", "-SkipBuild", "-UseNewX3D=1", "-UseNewX3DFramebuffers=1"], cwd=GAME)
    try:
        time.sleep(wait)
        if game.poll() is not None:
            sys.exit(f"the game exited early, code {game.returncode:#x}")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "dump_image64.py"), str(game.pid),
                        os.path.join(OUT, "exe_image_live")], check=True)
        shutil.rmtree(os.path.join(OUT, "live_pages"), ignore_errors=True)
        table = os.path.join(OUT, "packet_table.json")
        if os.path.exists(table):
            os.remove(table)
        env = dict(os.environ, BA_LIVE_PID=str(game.pid))
        subprocess.run([sys.executable, os.path.join(ROOT, "server", "packet_emu16.py"), "check", "400"], env=env)
    finally:
        if game.poll() is None:
            game.kill()
        srv.kill()
    n = len(os.listdir(os.path.join(OUT, "live_pages"))) if os.path.isdir(os.path.join(OUT, "live_pages")) else 0
    print(n, "pages kept from outside the image")


if __name__ == "__main__":
    main()
