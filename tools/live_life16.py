"""Everything a recorded live match says about one unit, in order, fields in clear (the live counterpart of
server/x_life.py): packets whose net id is the unit, and with --mention also packets that carry its net id in a
field (an attack on it, damage to it, a movement / replication entry for it).

    python tools/live_life16.py data/live/<gameId> <net id hex> [seconds after its first packet, default 8] [--mention]
"""
import os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"


def main():
    game, unit = sys.argv[1], int(sys.argv[2], 16)
    secs = float(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else 8.0
    mention = '--mention' in sys.argv
    os.environ.setdefault('BA_LIVE', game)
    import live16
    import codec16
    import replication
    import repl16
    import waypoints
    cap = live16.Capture(game)
    key = struct.pack('<I', unit).hex()
    t0 = None
    for t, way, ch, pid, net, body in live16.rows(cap.path):
        if way != 'S2C':
            continue
        if t0 is not None and t > t0 + secs:
            break
        if net != unit and t0 is None:
            continue
        if net != unit and not mention and pid not in (61, 287):
            continue
        v = codec16.decode(pid, net, body) if codec16.has(pid) else None
        extra = ''
        if pid == 287 and v:
            for n, groups in replication.parse(bytes.fromhex(v['+0x20']['text'])):
                if n == unit:
                    try:
                        extra = str({k: round(x, 2) if isinstance(x, float) else x for k, x in repl16.read_unit(groups, 'lane_minion').items()})
                    except Exception:
                        try:
                            extra = str(repl16.read_unit(groups))
                        except Exception as e:
                            extra = f'groups {sorted(groups)} ({e})'
            if not extra:
                continue
        elif pid == 61 and v:
            try:
                for e in waypoints.parse(bytes.fromhex(v['+0x18']['text'])):
                    if e['net'] == unit:
                        extra = f"speed {e['speed']:.0f} points {[tuple(round(c) for c in waypoints.to_world(p)) for p in e['points']]}"
            except Exception as e:
                extra = f'(entries not read: {e})'
            if not extra:
                continue
        elif net != unit:
            if v is None or key not in str(v):
                continue
        if t0 is None:
            t0 = t
        shown = extra or (str(v) if v is not None else body.hex())
        print(f'{t:9.3f} +{t - t0:6.3f} {pid:5} {"self " if net == unit else f"{net:08x}"} {shown[:400]}')


if __name__ == '__main__':
    main()
