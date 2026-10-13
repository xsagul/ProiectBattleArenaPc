"""The jungle plants' packet forms, as Riot's server sends them [m: the 16.20 replays] -> data/exe1620/plants16.json

    python tools/plant_forms16.py [game id ..]          (default: the first replays at hand)

For every plant (a 626 unit named Plant*: PlantVision = Scryer's Bloom, PlantSatchel = Blast Cone, PlantHealth /
PlantHealthMirrored = Honeyfruit, PlantHealthPack = a fruit) the packets about the plant itself in each step of its life:
  spawn    the frame its 626 comes (272, 802, 294, 626, 684, 294)
  grow     its first 1088 'Grow_idle' (60 s later): 904, 1088 and 1005 (Scryer's Bloom) / 435 (Blast Cone's idle buff)
  trigger  its 314 'Trigger' (a champion's attack hit it): 435, 904 x2, 314, 262; the region (41) bound to it; the
           attacker's 331 ('Attack<plant>')
  death    its 314 'Death' 30 s after: 262, 904 x2, 314
  die      150 + 1112 150 s after; delete 1090 4 s after that
and the missiles a trigger sends (Scryer's Bloom: the attacker's 78 + 223 for each seed; Honeyfruit: the plant's).
Values are kept parsed; core/plants.py writes its own net ids, places and times into them.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)
import replaydb16 as RD

OUT = os.path.join(ROOT, 'data', 'exe1620', 'plants16.json')
ROFL = os.path.join(ROOT, 'data', 'replays16', 'rofl')


def text(v):
    try:
        return bytes.fromhex(v['text']).rstrip(b'\0').decode(errors='replace')
    except Exception:
        return ''


def scan(gid, forms):
    R = RD.Replay(os.path.join(ROFL, f'{gid}.rofl'))
    plants = {}                       # net -> name
    frame = collections.defaultdict(list)     # (net, t) -> [(pid, values)]
    phase_at = {}                     # (net, phase) -> t
    by_t = collections.defaultdict(list)
    for t, ch, p, net, body, inc in R.flat():
        by_t[round(t, 3)].append((p, net, body))
    for t in sorted(by_t):
        rows = by_t[t]
        for p, net, body in rows:
            if p == 626:
                v = R.parse(p, body)
                nm = text(v['+0x38'])
                if nm.startswith('Plant') and net not in plants:
                    plants[net] = nm
                    phase_at[(net, 'spawn')] = t
            if net in plants:
                if p == 1088 and text(R.parse(p, body)['+0x10']) == 'Grow_idle':
                    phase_at.setdefault((net, 'grow'), t)
                elif p == 314:
                    nm = text(R.parse(p, body)['+0x10'])
                    phase_at.setdefault((net, 'trigger' if nm == 'Trigger' else 'death' if nm == 'Death' else nm), t)
                elif p == 1112:
                    phase_at.setdefault((net, 'die'), t)
                elif p == 1090:
                    phase_at.setdefault((net, 'delete'), t)
    for (net, phase), t in phase_at.items():
        name = plants[net]
        f = forms.setdefault(name, {})
        if phase in f:
            continue
        hexid = net.to_bytes(4, 'little').hex()
        seen, own, other = set(), [], []
        for p, n, body in by_t[t]:
            if body in seen and p not in (904, 294):
                continue
            seen.add(body)
            if n == net:
                own.append((p, R.parse(p, body)))
            elif p == 41 and hexid in json.dumps(R.parse(p, body)):
                other.append(('region', p, R.parse(p, body)))
            elif p == 331 and phase == 'trigger' and text(R.parse(p, body)['+0x10']).startswith('Attack'):
                other.append(('attacker', p, R.parse(p, body)))
            elif p == 435 and phase == 'trigger' and (R.parse(p, body) or {}).get('+0x38') == '1f':
                other.append(('knocked', p, R.parse(p, body)))           # Blast Cone's knock-back on a champion
            elif p == 41 and phase == 'trigger' and (R.parse(p, body) or {}).get('+0x10', {}).get('+0x8') not in ('00000000', hexid):
                other.append(('knocked_region', p, R.parse(p, body)))    # a region bound to the champion knocked
        entry = {'own': own, 'other': other, 'replay': gid, 'net': hexid, 't': t}
        if phase == 'trigger':
            # the missiles of the trigger: 78 (their spell in slot 0x34) then 938 / 743 / 223 for each
            ms = []
            for p, n, body in by_t[t]:
                if p in (78, 223, 743):
                    v = R.parse(p, body)
                    if p == 78 and text(v['+0x20']).startswith('Plant'):
                        ms.append({'pid': 78, 'of': 'plant' if n == net else 'attacker', 'values': v})
                    elif p in (223, 743) and ms:
                        ms.append({'pid': p, 'values': v})
            entry['missiles'] = ms
            if name == 'PlantVision':
                # the seeds' regions: the next 2.2 s of 41s with no unit (place, radius, time from the trigger)
                regs = []
                for t2 in sorted(by_t):
                    if t < t2 <= t + 2.2:
                        for p, n, body in by_t[t2]:
                            if p == 41 and body not in seen:
                                seen.add(body)
                                v = R.parse(p, body)
                                if v['+0x10']['+0x8'] == '00000000':
                                    regs.append({'dt': round(t2 - t, 3), 'values': v})
                entry['regions'] = regs
        f[phase] = entry
    return len(plants)


def main():
    ids = sys.argv[1:] or sorted(x[:-5] for x in os.listdir(ROFL) if x.endswith('.rofl'))[:6]
    forms = {}
    for gid in ids:
        n = scan(gid, forms)
        print(gid, n, 'plants;', {k: sorted(v) for k, v in forms.items()})
    json.dump(forms, open(OUT, 'w'), indent=1)
    print('->', OUT)


if __name__ == '__main__':
    main()
