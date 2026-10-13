"""Every server packet of a live recording through our plain-Python reader and writer (pkt_schema.parse / encode):
per id, how many read and write back to the same values. Fast (no emulator): the whole match in a minute or two.

    python tools/live_roundtrip16.py data/live/<gameId>   -> <gameId>/roundtrip.txt (only the ids not fully carried
                                                           are printed)
"""
import collections, os, sys, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.environ["BA_PATCH"] = "1620"
sys.modules.setdefault("decoded", types.ModuleType("decoded"))
import live16, pkt_schema as PS   # noqa: E402


def main():
    game = sys.argv[1]
    by = collections.defaultdict(list)
    for t, way, ch, pid, net, body in live16.rows(os.path.join(game, 'packets.tsv')):
        if way == 'S2C':
            by[pid].append(body)
    lines, full = [], 0
    for pid in sorted(by):
        try:
            sc = PS.Schema.load(pid)
        except FileNotFoundError:
            lines.append(f'{pid} no format ({len(by[pid])} packets)')
            continue
        ok = err = diff = 0
        first = ''
        for b in by[pid]:
            try:
                v = PS.parse(sc, b)
                w = PS.parse(sc, sc.encode(v))
            except Exception as e:
                err += 1
                first = first or f'{type(e).__name__} {e}'
                continue
            ok += v == w
            diff += v != w
        n = len(by[pid])
        if ok == n:
            full += 1
        else:
            lines.append(f'{pid} {ok} of {n} same values, {err} errors, {diff} different | {first[:100]}')
    head = f'{full} of {len(by)} server packet ids read and written back to the same values in every packet'
    open(os.path.join(game, 'roundtrip.txt'), 'w').write(head + '\n' + '\n'.join(lines) + '\n')
    print(head)
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
