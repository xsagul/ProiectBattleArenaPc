"""Templates of what Riot's server sends for a spell, cut from the replay (the caster's and the target's packets in
one tick), decoded once with the learnt schemas and saved, so the test server can rewrite them with its own values.

  spell_templates.py cut <name> <t> <caster hex> [target hex] [skip ids,...]   -> research/exe133/templates/<name>.json
      (WITH_GLOBAL=1: also the packets of object 0 in that tick, e.g. a kill's announcement)
  spell_templates.py show <name>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import packet_emu as P  # noqa: E402
import replay_window as RW  # noqa: E402

OUT = os.path.join(HERE, '..', '..', 'research', 'exe133', 'templates')


def cut(name, t, caster, target=None, skip=(), with_global=False):
    P.KINDS, P.ENTRY = (1,), None
    out = []
    for tt, ch, pid, obj, body in P.packets(P.ROFL):
        if tt < t - 0.002 or pid in RW.NOISE or pid in skip:
            continue
        if tt > t + 0.002:
            break
        who = 'caster' if obj == caster else 'target' if obj == target else 'global' if (with_global and obj == 0) else None
        if who is None:
            continue
        v = RW.decode(pid, obj, body)
        out.append({'pid': pid, 'ch': ch, 'who': who, 'values': v, 'raw': body.hex() if v is None else None})
    os.makedirs(OUT, exist_ok=True)
    json.dump({'t': t, 'caster': caster, 'target': target, 'packets': out}, open(os.path.join(OUT, f'{name}.json'), 'w'), indent=1)
    return out


def load(name):
    return json.load(open(os.path.join(OUT, f'{name}.json')))


if __name__ == '__main__':
    if sys.argv[1] == 'cut':
        skip = {int(x) for x in sys.argv[6].split(',')} if len(sys.argv) > 6 else set()
        res = cut(sys.argv[2], float(sys.argv[3]), int(sys.argv[4], 16), int(sys.argv[5], 16) if len(sys.argv) > 5 and sys.argv[5] else None, skip,
                  with_global=os.environ.get('WITH_GLOBAL') == '1')
    else:
        res = load(sys.argv[2])['packets']
    for p in res:
        print(p['pid'], p['ch'], p['who'], RW.pretty(p['values']) if p['values'] is not None else f"raw {p['raw']}")
