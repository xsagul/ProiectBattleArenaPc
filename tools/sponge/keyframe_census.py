"""What the replay's first keyframe (the match's start state) holds: packets by id, the objects they are about, and
the order they come in -- the list of what our own server must send for a match without the replay.

  keyframe_census.py [rofl]       -> research/exe133/keyframe1_census.txt
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rofl_packets as R  # noqa: E402

ROOT = os.path.join(HERE, '..', '..')
ROFL = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'research', 'rofl', 'KR-6363178603_13.3.rofl')
OUT = os.path.join(ROOT, 'research', 'exe133', 'keyframe1_census.txt')


def kind_of(net):
    """the net id's family (high byte): 0x40 game objects (heroes, minions, missiles), 0xff map objects, 0 none"""
    if net == 0:
        return 'none'
    return f'{net >> 24:02x}'


def main():
    r = R.Rofl(ROFL)
    kf = next(e for e in r.entries if e['type'] == 2 and e['id'] == 1)
    rows = list(R.blocks(r.payload(kf)))
    by_id = collections.OrderedDict()
    for i, (bt, ch, pid, obj, body) in enumerate(rows):
        d = by_id.setdefault(pid, {'n': 0, 'first': i, 'objs': collections.Counter(), 'bytes': 0, 'ch': set(), 't': set()})
        d['n'] += 1
        d['objs'][kind_of(obj)] += 1
        d['bytes'] += len(body)
        d['ch'].add(ch)
        d['t'].add(round(bt, 2))
    objs = collections.Counter(obj for _, _, _, obj, _ in rows)
    lines = [f'keyframe 1 of {os.path.basename(ROFL)}: {len(rows)} packets, {len(by_id)} kinds, {len(objs)} objects', '',
             'id    count  first  channel  bytes   objects by family (40 = units, ff = map objects)   times']
    for pid, d in by_id.items():
        lines.append(f'{pid:<5} {d["n"]:>5}  {d["first"]:>5}  {sorted(d["ch"])!s:<7}  {d["bytes"]:>6}   '
                     f'{dict(d["objs"])!s:<45} {sorted(d["t"])[:4]}')
    lines += ['', 'objects with the most packets:']
    for obj, n in objs.most_common(40):
        kinds = collections.Counter(pid for _, _, pid, o, _ in rows if o == obj)
        lines.append(f'  {obj:08x} {n:>4}  {dict(kinds.most_common(8))}')
    open(OUT, 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:80]))


if __name__ == '__main__':
    main()
