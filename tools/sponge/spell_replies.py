"""What Riot's server sends with every cast of one spell in the replay: the caster's packets in the same tick as the
cast (49), decoded, and how much they vary from cast to cast (fields that never change = part of the spell; fields
that change = times, ids, targets, ranks).

  spell_replies.py <caster net id hex> <spell name> [window s=0.001]
"""
import bisect
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import spell_info as SI  # noqa: E402
import replay_window as RW  # noqa: E402


def flat(v, path=''):
    if isinstance(v, dict) and 'text' not in v:
        for k, x in v.items():
            yield from flat(x, path + k)
    elif isinstance(v, list):
        yield path + '[]', json.dumps(v)
    else:
        yield path, json.dumps(v)


def main():
    hero = int(sys.argv[1], 16)
    spell = sys.argv[2]
    win = float(sys.argv[3]) if len(sys.argv) > 3 else 0.001
    h = f'{SI.elf(spell):08x}'
    want = bytes.fromhex(h)[::-1].hex()
    casts = []
    for line in open(os.path.join(RW.S.OUT, '49.all.jsonl')):
        r = json.loads(line)
        if r['obj'] == hero and r['v'] and r['v']['+0xc']['+0xbc'] == want:
            casts.append(r['t'])
    print(len(casts), 'casts of', spell)
    P.KINDS, P.ENTRY = (1,), None
    pk = [(t, pid, obj, b) for t, ch, pid, obj, b in P.packets(P.ROFL) if obj == hero and pid not in RW.NOISE]
    ts = [x[0] for x in pk]
    seqs = collections.Counter()
    fields = collections.defaultdict(collections.Counter)
    for t in casts:
        i = bisect.bisect_left(ts, t - 1e-4)
        seq = []
        while i < len(pk) and pk[i][0] <= t + win:
            _, pid, obj, b = pk[i]
            seq.append(pid)
            v = RW.decode(pid, obj, b)
            if v is not None:
                for k, x in flat(v):
                    fields[(pid, seq.count(pid), k)][x] += 1
            i += 1
        seqs[tuple(seq)] += 1
    for s, n in seqs.most_common(5):
        print(n, 'x', s)
    print('fields (pid, n-th, path): values')
    for k in sorted(fields):
        c = fields[k]
        if len(c) == 1:
            print(f'  {k} FIXED {RW.pretty(json.loads(next(iter(c))))}')
        else:
            print(f'  {k} {len(c)} values, e.g. {[RW.pretty(json.loads(x)) for x, _ in c.most_common(3)]}')


if __name__ == '__main__':
    main()
