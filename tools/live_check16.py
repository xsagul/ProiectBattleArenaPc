"""Do the learnt formats (data/exe1620/codec, learnt mostly on the replay) carry what the LIVE server sends? For
every server packet id of a live recording: n packets spread over the match, read by the client's own reader,
written again by our encoder, read back.

    python tools/live_check16.py data/live/<gameId> [n per id, default 30] [workers, default 4] [id ...]
        -> <gameId>/codec_check.txt   one line per id: identical / not read / not encodable / different / no format

An id whose format fails here must be learnt again on the live packets (BA_LIVE=<gameId> tools/batch_learn16.py).
"""
import concurrent.futures, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))


def one(game, pid, n):
    env = dict(os.environ, BA_PATCH="1620", BA_LIVE=game, PYTHONIOENCODING="utf-8")
    code = f"""
import sys; sys.path.insert(0, {os.path.join(ROOT, 'server')!r})
import live16, codec16, pkt_schema as PS
from emu_backend import P
pid = {pid}
if not codec16.has(pid):
    print('no format'); raise SystemExit
allp = [(net, body) for k in (3, 2, 1) for t, ch, p, net, body in P.live_packets()[k] if p == pid]
step = max(1, len(allp) // {n})
sample = allp[::step][:{n}]
same = bad_read = bad_enc = differ = 0
first = ''
for net, body in sample:
    try:
        v = codec16.decode(pid, net, body)
    except Exception as e:
        v = None
        first = first or f'decode {{type(e).__name__}} {{e}}'
    if v is None:
        bad_read += 1
        continue
    try:
        ours = codec16.encode(pid, v)
    except Exception as e:
        bad_enc += 1
        first = first or f'encode {{e}}'
        continue
    back = codec16.decode(pid, net, ours)
    if back == v:
        same += 1
    else:
        differ += 1
print(f'{{len(sample)}} of {{len(allp)}}: {{same}} identical, {{bad_read}} not read, {{bad_enc}} not encodable, {{differ}} different' + (f' | {{first[:120]}}' if first else ''))
"""
    try:
        p = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=3600, cwd=ROOT)
        lines = [l for l in (p.stdout + p.stderr).splitlines() if l.strip()]
        return pid, (lines[-1][:220] if lines else "(no output)")
    except subprocess.TimeoutExpired:
        return pid, "timeout"


def main():
    game = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    ids = [int(a) for a in sys.argv[4:]]
    if not ids:
        import re
        ids = [int(m.group(1)) for m in re.finditer(r"^=== (\d+)", open(os.path.join(game, "digest.txt"), encoding="utf-8").read(), re.M)]
    out = os.path.join(game, "codec_check.txt")
    with concurrent.futures.ThreadPoolExecutor(workers) as ex, open(out, "a", encoding="utf-8") as f:
        for pid, line in ex.map(lambda p: one(game, p, n), ids):
            f.write(f"{pid} | {line}\n")
            f.flush()
            print(pid, line, flush=True)


if __name__ == "__main__":
    main()
