"""A window of a live recording as text, every packet parsed (containers opened, replication by name, movement as
world points), one line per packet, run-lengths for repeats of the same (id, net id).

    python tools/live_dump16.py <from game s> <to game s> [out file] [--game data/live/<id>] [--ids a,b,c] [--net hex,hex] [--c2s]
Game time 0 = the start of part 2; the start state is at about -0.38 .. 0.
"""
import os, struct, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import livedb   # noqa: E402


def text(L, pid, net, body, width=100000):
    v = L.parse(pid, body)
    if v is None:
        return 'RAW ' + body.hex()
    if pid == livedb.CONTAINER:
        return 'CONTAINER ' + ' || '.join(f'{p} {n:08x} {text(L, p, n, b)}' for p, n, b in L.inner(v))
    if pid == livedb.REPL:
        return 'REPL ' + ' || '.join(f'{n:08x} ' + str({k: (round(x, 3) if isinstance(x, float) else x) for k, x in vals.items()})
                                     for n, vals in L.repl(body))
    if pid == livedb.MOVE:
        return 'MOVE ' + ' || '.join(f"{e['net']:08x} speed {e.get('speed', 0):.0f} flags {e.get('flags', 0)} {e['world']}" for e in L.moves(body))
    return str(v)


def main():
    a, b = float(sys.argv[1]), float(sys.argv[2])
    args = sys.argv[3:]
    out = open(args[0], 'w', encoding='utf-8') if args and not args[0].startswith('--') else sys.stdout
    game = args[args.index('--game') + 1] if '--game' in args else livedb.DEFAULT
    ids = {int(x) for x in args[args.index('--ids') + 1].split(',')} if '--ids' in args else None
    nets = [int(x, 16) for x in args[args.index('--net') + 1].split(',')] if '--net' in args else None
    keys = [struct.pack('<I', n).hex() for n in nets] if nets else []
    L = livedb.Live(game)
    last = None
    for t, way, ch, pid, net, body in L.rows:
        if t < a:
            continue
        if t > b:
            break
        if way == 'C' and '--c2s' not in args:
            continue
        if ids is not None and pid not in ids:
            continue
        s = text(L, pid, net, body) if way == 'S' else 'C2S ' + body.hex()
        if nets and net not in nets and not any(k in s for k in keys) and not any(f'{n:08x}' in s for n in nets):
            continue
        key = (way, pid, net, s)
        if last and last[0] == key:
            last[1] += 1
            continue
        if last and last[1] > 1:
            out.write(f'          ... x{last[1]}\n')
        last = [key, 1]
        out.write(f'{t:9.3f} {way} ch{ch} {pid:5} {net:08x} {s}\n')
    if last and last[1] > 1:
        out.write(f'          ... x{last[1]}\n')


if __name__ == '__main__':
    main()
