"""The evidence a champion's scripts left in the replays, as BuildingBlocks would see it: buff lifetimes and the
events around them -> data/bb16/evidence/<game id>.pkl

    python tools/bb_evidence16.py [game id ..] [--workers n]      (default: every replay at hand)

Per replay, for the ten champions and everything that names them:
  casts     (t, hero net, spell name hash, slot, target net)                 1215
  attacks   (t, attacker net, target net, attack name hash)                  906 (champions), 390 / 972 (others)
  hits      (t, target net, source net, amount, damage type, name hash)      150
  buffs     one row per buff instance on any unit: name hash, holder, caster, type, slot, added, duration, count at
            the add, [(t, 'renew', duration, count) / (t, 'count', n)], removed (or None)        435 / 282 / 430 / 262
  effects   (t, key, owner net, bound net, effect net id) and removals (t, effect net id)       10 / 584
  heals     (t, healer, healed, amount, flag, cause hash, name hash)                           699 e14f047c
  regions   (t, bound net, team, radius, duration)                                              41
  dashes    (t, unit net, speed)                                                                1140
  slots     (t, hero net, slot, spell name)                                                     78
  cooldowns (t, hero net, slot code, seconds)                                                   635
  anims     (t, net, name)                                                                      1088
  deaths    (t, net, killer)                                                                    1112
A buff instance is (holder, slot): a 435 opens it, 282 / 430 on that slot belong to it, 262 on that slot closes it.
"""
import collections
import json
import os
import pickle
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, HERE)
import replaydb16 as RD

ROFL = os.path.join(ROOT, 'data', 'replays16', 'rofl')
OUT = os.path.join(ROOT, 'data', 'bb16', 'evidence')
PIDS = (1215, 906, 390, 972, 150, 435, 282, 430, 262, 10, 584, 699, 41, 1140, 78, 635, 1088, 1112, 626)


def u32(h):
    try:
        return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) else 0
    except ValueError:
        return 0


def f32(h):
    try:
        return struct.unpack('<f', bytes.fromhex(h))[0] if isinstance(h, str) and len(h) == 8 else 0.0
    except Exception:
        return 0.0


def text(v):
    try:
        return bytes.fromhex(v['text']).rstrip(b'\0').decode(errors='replace')
    except Exception:
        return ''


def scan(gid):
    R = RD.Replay(os.path.join(ROFL, f'{gid}.rofl'))
    heroes = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    ev = collections.defaultdict(list)
    open_buffs = {}                  # (holder, slot) -> row
    buffs = []
    frame, seen = None, set()
    for t, ch, pid, net, body, inc in R.flat(ids=PIDS):
        if t != frame:
            frame, seen = t, set()
        v = R.parse(pid, body)
        if v is None:
            continue
        sig = (pid, net, json.dumps(v, sort_keys=True))
        if sig in seen:
            continue                 # the observers' copies of one packet
        seen.add(sig)
        t = round(t, 4)
        if pid == 1215:
            c = v.get('+0x18') or {}
            tl = c.get('+0x8') or []
            tgt = u32(tl[0].get('+0x8')) if tl and isinstance(tl[0], dict) else 0
            try:
                slot = int(c.get('+0x60', 'ff'), 16)
            except ValueError:
                slot = 255
            ev['casts'].append((t, net, u32(c.get('+0x18')), slot, tgt))
        elif pid == 906:
            a = v.get('+0x10') or {}
            ev['attacks'].append((t, net, u32(a.get('+0x20')), u32(((a.get('+0x28') or [{}])[0] or {}).get('+0x18')) if a.get('+0x28') else 0))
        elif pid in (390, 972):
            a = v.get('+0x10')
            ev['attacks'].append((t, net, u32(a.get('+0x20')) if isinstance(a, dict) else u32(a), 0))
        elif pid == 150:
            ev['hits'].append((t, u32(v.get('+0x14')), u32(v.get('+0x1c')), f32(v.get('+0x10')), v.get('+0x18'), u32(v.get('+0x2c'))))
        elif pid == 435:
            slot = v.get('+0x60')
            row = {'hash': u32(v.get('+0x64')), 'holder': net, 'caster': u32(v.get('+0x1c')), 'type': int(v.get('+0x38', '00'), 16),
                   'slot': slot, 'added': t, 'duration': round(f32(v.get('+0x3c')), 3), 'count': int(v.get('+0x40', '01'), 16),
                   'package': u32(v.get('+0x5c')), 'log': [], 'removed': None}
            old = open_buffs.get((net, slot))
            if old is not None and old['removed'] is None:
                old['removed'] = t
                old['replaced'] = True
            open_buffs[(net, slot)] = row
            buffs.append(row)
        elif pid in (282, 430, 262):
            slot = v.get('+0x18') if pid == 282 else v.get('+0x1c') if pid == 430 else v.get('+0x10')
            row = open_buffs.get((net, slot))
            if row is None:
                continue
            if pid == 282:
                row['log'].append((t, 'renew', round(f32(v.get('+0x10')), 3), int(v.get('+0x20', '00'), 16)))
            elif pid == 430:
                row['log'].append((t, 'count', u32(v.get('+0x10'))))
            else:
                row['removed'] = t
                del open_buffs[(net, slot)]
        elif pid == 10:
            for grp in v.get('+0x10') or []:
                if not isinstance(grp, dict):
                    continue
                for inst in grp.get('+0x10') or []:
                    if isinstance(inst, dict):
                        ev['effects'].append((t, u32(grp.get('+0xc')), u32(inst.get('+0x18')), u32(inst.get('+0x34')), u32(inst.get('+0x38'))))
        elif pid == 584:
            ev['fx_gone'].append((t, u32(v.get('+0x14'))))
        elif pid == 699 and v.get('+0x10') == 'e14f047c':
            try:
                b = bytes.fromhex(v['+0x18']['text'])
            except Exception:
                continue
            if len(b) == 52:
                ev['heals'].append((t, int.from_bytes(b[4:8], 'little'), int.from_bytes(b[20:24], 'little'),
                                    struct.unpack('<f', b[24:28])[0], b[12], int.from_bytes(b[8:12], 'little'),
                                    int.from_bytes(b[40:44], 'little')))
        elif pid == 41:
            r = v.get('+0x10') or {}
            ev['regions'].append((t, u32(r.get('+0x8')), r.get('+0x25'), round(f32(v.get('+0x58')), 1), round(f32(r.get('+0x28')), 2)))
        elif pid == 1140:
            ev['dashes'].append((t, net))
        elif pid == 78:
            ev['slots'].append((t, net, int((v.get('+0x10') or {}).get('+0xf', 'ff'), 16), text(v.get('+0x20'))))
        elif pid == 635:
            ev['cooldowns'].append((t, net, v.get('+0x24'), round(f32(v.get('+0x10')), 3)))
        elif pid == 1088:
            ev['anims'].append((t, net, text(v.get('+0x10'))))
        elif pid == 1112:
            ev['deaths'].append((t, net, u32((v.get('+0x10') or {}).get('+0x14')) if isinstance(v.get('+0x10'), dict) else 0))
        elif pid == 626:
            ev['units'].append((t, net, text(v.get('+0x38')), u32(v.get('+0x18'))))
    out = {'game': gid, 'heroes': heroes, 'buffs': buffs, **ev}
    os.makedirs(OUT, exist_ok=True)
    pickle.dump(out, open(os.path.join(OUT, f'{gid}.pkl'), 'wb'))
    return gid, len(buffs), {k: len(x) for k, x in ev.items()}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    workers = int(sys.argv[sys.argv.index('--workers') + 1]) if '--workers' in sys.argv else 6
    args = [a for a in args if not a.isdigit() or len(a) > 3]
    ids = args or sorted(x[:-5] for x in os.listdir(ROFL) if x.endswith('.rofl'))
    from multiprocessing import Pool
    with Pool(workers) as P:
        for gid, nb, counts in P.imap_unordered(scan, ids):
            print(gid, nb, 'buffs', counts, flush=True)


if __name__ == '__main__':
    main()
