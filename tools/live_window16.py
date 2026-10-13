"""Every server packet of a live recording in a window of GAME time, parsed (plain-Python reader), optionally only
the ones about / mentioning given net ids.

    python tools/live_window16.py data/live/<gameId> <from s> <to s> [net id hex ...]
"""
import os, struct, sys, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
sys.modules.setdefault("decoded", types.ModuleType("decoded"))
import forms16, live16, pkt_schema as PS   # noqa: E402

_sc = {}


def parse(pid, body):
    try:
        if pid not in _sc:
            _sc[pid] = PS.Schema.load(pid)
        return PS.parse(_sc[pid], body)
    except Exception:
        return None


def main():
    game, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    nets = [int(x, 16) for x in sys.argv[4:]]
    keys = [struct.pack('<I', n).hex() for n in nets]
    cap = live16.Capture(game)
    g0 = cap.gates[2]
    for t, way, ch, pid, net, body in live16.rows(cap.path):
        gt = t - g0
        if gt < a or way != 'S2C':
            continue
        if gt > b:
            break
        v = parse(pid, body)
        s = str(v) if v is not None else 'RAW ' + body.hex()
        if pid == forms16.CONTAINER and v is not None:
            s = 'CONTAINER ' + str([(p, f'{n:08x}', str(parse(p, bb))[:200]) for p, n, bb in forms16.unpack(v)])
        if nets and net not in nets and not any(k in s for k in keys):
            continue
        print(f'{gt:9.3f} {pid:5} {net:08x} {s[:500]}')


if __name__ == '__main__':
    main()
