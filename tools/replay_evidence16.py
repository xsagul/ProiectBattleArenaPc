"""What Riot's server did after every champion cast in the fetched replays (data/replays16/rofl, replay_fetch16.py):
the evidence each champion's abilities are built from in our 16.20 server.

    python tools/replay_evidence16.py scan [game ids ..]        -> data/replays16/casts/<game>.pkl (all replays not
                                                                  scanned yet when no id is given)
    python tools/replay_evidence16.py report [Champion ..]      -> data/replays16/evidence/<Champion>.txt + .json
    python tools/replay_evidence16.py show <Champion> <slot|spell> [n] [--window s]
                                                                  n casts of one spell, packet by packet
    python tools/replay_evidence16.py samples [game ids ..]     -> data/replays16/samples/<game>.pkl: the whole
                                                                  packets of the first casts of each spell

A cast = a champion's 1215 (NPC_CastSpellAns). What follows it within WINDOW seconds is kept when it is about:
  caster   the champion itself (buffs, stealth flags 291, fades 947 / 596 / 29, alpha 236, character data 982,
           spells put in its slots 78, ammo 835, its own teleport in 61, its dash in 1140, a team's sight of it 723 /
           1195, its replicated state 287: StatusFlags, ActionState, targetable, shields ...)
  spawn    a unit created (626) whose owner (+0x18) is the champion, from then on for SPAWN_WINDOW seconds
  missile  a missile of the cast (its +0xbc id) or a missile spell (223) the champion launched
  other    a buff (435) the champion gave another unit, damage (150) it dealt, an effect (10) it made
Packet names: data/exe1620/packet_names16.json (tools/pkt_names16.py, the client's own handler names).
"""
import bisect
import collections
import glob
import json
import os
import pickle
import statistics
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, ROOT)
os.environ.setdefault('BA_PATCH', '1620')
import replaydb16 as RD   # noqa: E402

DATA = os.path.join(ROOT, 'data', 'replays16')
WINDOW, SPAWN_WINDOW = 8.0, 20.0
NAMES = json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'packet_names16.json')))
# many a second, about everyone: only kept for the caster / its units (61, 287, 1140 are read for them alone)
BULK = {362, 755, 1052, 660, 1201, 287, 61, 1140, 723, 1195, 41, 584, 282, 430, 390, 972, 906, 515, 118, 743, 938, 433, 150, 10,
        435, 262, 1215, 223, 211, 699, 904, 1088, 280, 90, 1184, 447, 294, 1126, 264, 121, 635, 264}
# never kept: many a second about everyone, or read another way (287: the replicated fields below)
QUIET = frozenset({362, 755, 1052, 660, 1201, 287, 584, 282, 430, 390, 294, 1126, 121, 264})
# never read at all (the spectator's sight and position streams, ~80 % of a replay's packets): the lists stay small
DROP = frozenset({362, 755, 1052, 660, 1201, 584, 282, 430, 390, 294, 1126, 121, 264, 723, 1195})
REPL_FIELDS = ('StatusFlags', 'ActionState', 'ActionState2', 'mIsTargetable', 'mIsTargetableToTeamFlags', 'mAllShield',
               'mPhysicalShield', 'mMagicalShield', 'mSAR', 'mMaxSAR', 'mLifetime', 'mMaxLifetime', 'mPARState', 'mSARState',
               'mFollowTargetNetID', 'mAttackRange', 'mCombatType')


def vec3(h):
    try:
        return struct.unpack('<fff', bytes.fromhex(h)) if isinstance(h, str) and len(h) == 24 else None
    except Exception:
        return None


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and h else 0


def f32(h):
    return round(struct.unpack('<f', bytes.fromhex(h))[0], 3) if isinstance(h, str) and len(h) == 8 else None


def elf(name):
    h = 0
    for c in name.lower().encode():
        h = (h << 4) + c
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


# ------------------------------------------------------------------------------------------------ names
_hashes = None


def hash_names():
    """ELF hash -> name, from every champion's spell objects (spells and buffs are named by them) and the
    strings of its main bin and pets' bins, plus summoner spells / items / runes from the global bins"""
    global _hashes
    if _hashes is not None:
        return _hashes
    p = os.path.join(DATA, 'elf_names.json')
    if os.path.exists(p):
        _hashes = {int(k): v for k, v in json.load(open(p)).items()}
        return _hashes
    import re
    import wad
    from server.core import gamedata as G
    names = set()
    for c in G.champion_index():
        name = c['alias']
        try:
            ch = G.champion(name)
            names.update(ch.objects)
        except Exception:
            pass
        w = os.path.join(G.GAME, 'Champions', f'{name}.wad.client')
        d = wad.read(w, f'data/characters/{name.lower()}/{name.lower()}.bin')
        if d:
            names.update(m.group().decode() for m in re.finditer(rb'[A-Za-z][A-Za-z0-9_]{3,80}', d))
    for f in ('Global.wad.client',):
        w = os.path.join(G.GAME, f)
        for h in list(wad.toc(w))[:20000]:
            try:
                d = wad.read(w, h)
            except Exception:
                continue
            if d and d[:4] in (b'PROP', b'PTCH'):
                names.update(m.group().decode() for m in re.finditer(rb'[A-Za-z][A-Za-z0-9_]{3,80}', d))
    _hashes = {}
    for n in sorted(names):
        _hashes.setdefault(elf(n), n)
    os.makedirs(DATA, exist_ok=True)
    json.dump({str(k): v for k, v in _hashes.items()}, open(p, 'w'))
    return _hashes


def hname(h):
    return hash_names().get(h, f'#{h:08x}')


# ------------------------------------------------------------------------------------------------ one replay
def summary(R, pid, net, body, me, v=False):
    """the fields of a packet that say what happened (short, comparable between casts); v: its values when they
    were read already"""
    if v is False:
        v = R.parse(pid, body)
    if v is None:
        return {'raw': body.hex()[:64]}
    try:
        if pid == 435:
            return {'type': int(v['+0x38'], 16), 'name': hname(u32(v['+0x64'])), 'dur': f32(v['+0x3c']),
                    'count': int(v['+0x40'], 16), 'by': 'self' if u32(v['+0x1c']) == me else ('target' if u32(v['+0x1c']) == net else 'other')}
        if pid == 262:
            return {'name': hname(u32(v['+0x14']))}
        if pid == 626:
            return {'name': RD.text(v['+0x38']), 'char': RD.text(v['+0x70']), 'owner': 'self' if u32(v['+0x18']) == me else u32(v['+0x18']),
                    'f5c': v.get('+0x5c'), 'f60': v.get('+0x60'), 'f81': v.get('+0x81'), 'f84': v.get('+0x84'), 'f8e': v.get('+0x8e')}
        if pid == 1038:
            return {'char': RD.text(v.get('+0x10', {})), 'name': RD.text(v.get('+0x58', {})), 'ai': RD.text(v.get('+0x70', {})),
                    'owner': 'self' if u32(v.get('+0x48')) == me else u32(v.get('+0x48')), 'dur': f32(v.get('+0x50'))}
        if pid in (947, 596):
            s = v['+0x10'] if isinstance(v.get('+0x10'), dict) else {}
            return {'alpha': f32(s.get('+0x8')), 'time': f32(s.get('+0xc'))}
        if pid in (291, 236):
            return {'a': v.get('+0x10'), 'b': v.get('+0x14')}
        if pid == 78:
            s = v['+0x10'] if isinstance(v.get('+0x10'), dict) else {}
            return {'slot': int(s.get('+0xf', '0'), 16), 'spell': RD.text(v.get('+0x20', {}))}
        if pid == 982:
            return {'name': RD.text(v.get('+0x28', {})), 'id': u32(v.get('+0x20')), 'flags': [v.get(k) for k in ('+0x24', '+0x40', '+0x71', '+0x72')]}
        if pid == 1088:
            return {'anim': RD.text(v.get('+0x10', {}))}
        if pid == 150:
            return {'dmg': f32(v['+0x10']), 'type': int(v['+0x18'], 16), 'kind': int(v['+0x1a'], 16), 'spell': hname(u32(v['+0x2c']))}
        if pid == 1215 or pid == 223:
            c = v['+0x18'] if pid == 1215 else v['+0xf8']
            return {'spell': hname(u32(c['+0x18'])), 'slot': int(c['+0x60'], 16)}
        if pid == 10:
            return {'fx': [g.get('+0x20') for g in (v.get('+0x10') or []) if isinstance(g, dict)][:3]}
    except Exception as e:
        return {'err': str(e)[:40]}
    flat = {k: x for k, x in v.items() if isinstance(x, str) and len(x) <= 16}
    return {'v': dict(list(flat.items())[:6])}


def scan(gid):
    path = os.path.join(DATA, 'rofl', f'{gid}.rofl')
    R = RD.Replay(path, cache=False)
    heroes = {n: h['champion'] for n, h in R.heroes.items() if n < 0x40000100}
    rows = list(R.flat(skip=DROP))
    times = [r[0] for r in rows]
    # units the champions created (626: +0x18 the owner)
    owner, spawned = {}, []
    for i, (t, ch, pid, net, body, inc) in enumerate(rows):
        if pid in (626, 1038):
            v = R.parse(pid, body)
            o = u32((v or {}).get('+0x18' if pid == 626 else '+0x48'))
            if o in heroes:
                owner[net] = o
                spawned.append((t, net, owner[net]))
    # replicated fields of the champions and their units, as they change
    import replication
    import repl16
    track = set(heroes) | set(owner)
    repl = collections.defaultdict(list)
    last = collections.defaultdict(dict)
    for t, ch, pid, net, body, inc in rows:
        if pid != RD.REPL:
            continue
        v = R.parse(pid, body)
        if v is None:
            continue
        try:
            units = replication.parse(bytes.fromhex(v['+0x20']['text']))
        except Exception:
            continue
        for n, groups in units:
            if n not in track:
                continue
            vals = None
            for cls in (('AIHero',) if n in heroes else ('lane_minion', 'AIMinionCommon')):
                try:
                    vals = repl16.read_unit(groups, cls)
                    break
                except Exception:
                    pass
            if not vals:
                continue
            for k in REPL_FIELDS:
                if k in vals and last[n].get(k) != vals[k]:
                    if k in last[n]:
                        repl[n].append((t, k, last[n][k], vals[k]))
                    last[n][k] = vals[k]
    parsed = {}

    def val(i):
        """a row's values, read once (the windows of a champion's casts overlap: each row is in many)"""
        if i not in parsed:
            parsed[i] = R.parse(rows[i][2], rows[i][4])
        return parsed[i]

    # indexes: the rows about each unit, the rows that name a champion inside (movement, dashes, buffs it gave,
    # damage it dealt, effects it made), the spawns and missile spells by time
    regions = []                                   # (t, row, team '01' / '02', (x, z)) of the 41s bound to no unit
    by_net = collections.defaultdict(list)
    names = collections.defaultdict(list)          # unit -> rows whose DECODED fields name it (a packet's fields are
    by_pid = collections.defaultdict(list)         # written through byte tables: the raw body never holds the id)
    import waypoints
    for i, (t, ch, pid, net, body, inc) in enumerate(rows):
        if pid in QUIET:
            continue
        by_net[net].append(i)
        if pid in (626, 223, 1038):
            by_pid[pid].append(i)
        if pid == 41:
            # [10-13] a region (perception bubble): bound to a unit (+0x10 +0x8) or standing at a place (+0x14 x, z)
            v = val(i)
            reg = (v or {}).get('+0x10') or {}
            u = u32(reg.get('+0x8'))
            if u:
                names[u].append(i)
            elif isinstance(reg.get('+0x14'), str) and len(reg['+0x14']) == 16:
                regions.append((t, i, reg.get('+0x25'), struct.unpack('<ff', bytes.fromhex(reg['+0x14']))))
            continue
        if pid not in (61, 1140, 435, 150, 10):
            continue
        v = val(i)
        if v is None:
            continue
        found = set()
        try:
            if pid == 61:
                found = {e['net'] for e in waypoints.parse(bytes.fromhex(v['+0x18']['text']))}
            elif pid == 1140:
                blob = bytes.fromhex(v['+0x18']['text'])
                found = {struct.unpack_from('<I', blob, 2)[0]} if len(blob) >= 6 else set()
            elif pid in (435, 150):
                found = {u32(v.get('+0x1c'))}
            elif pid == 10:
                found = {u32(inst.get('+0x18')) for grp in (v.get('+0x10') or []) for inst in (grp.get('+0x10') or [])
                         if isinstance(inst, dict)}
        except Exception:
            found = set()
        for n2 in found:
            if n2 and n2 != net:
                names[n2].append(i)
    pid_t = {k: [rows[i][0] for i in v] for k, v in by_pid.items()}

    def window(idx, a, b):
        ts = [rows[i][0] for i in idx] if len(idx) < 64 else None
        if ts is None:
            lo, hi = 0, len(idx)
            while lo < hi:
                mid = (lo + hi) // 2
                if rows[idx[mid]][0] < a:
                    lo = mid + 1
                else:
                    hi = mid
            out = []
            for i in idx[lo:]:
                if rows[i][0] > b:
                    break
                out.append(i)
            return out
        return [i for i, x in zip(idx, ts) if a <= x <= b]

    import waypoints
    casts = []
    for i0, (t, ch, pid, net, body, inc) in enumerate(rows):
        if pid != RD.CAST or net not in heroes:
            continue
        v = R.parse(pid, body)
        if v is None:
            continue
        c = v['+0x18']
        me = net
        spell = hname(u32(c['+0x18']))
        slot = int(c['+0x60'], 16)
        mid = u32(c.get('+0xbc'))
        cast = {'game': gid, 't': round(t, 3), 'i': i0, 'hero': heroes[me], 'net': me, 'spell': spell, 'slot': slot,
                'cast_time': f32(c.get('+0x4c')), 'total': f32(c.get('+0xa8')), 'cd': f32(c.get('+0x80')), 'events': []}
        roles = {}
        for i in window(by_net[me], t, t + WINDOW):
            roles[i] = 'caster'
        for i in window(names[me], t, t + WINDOW):
            if rows[i][2] == 61 and rows[i][0] > t + 1.0:
                continue                                 # a walk later on: not the spell's
            roles.setdefault(i, 'caster' if rows[i][2] in (61, 1140) else 'other')
        units, missiles = set(), ({mid} if mid else set())
        for sp_pid, own_at in ((626, '+0x18'), (1038, '+0x48')):
            ts_ = pid_t.get(sp_pid, [])
            for k in range(bisect.bisect_left(ts_, t), bisect.bisect_right(ts_, t + WINDOW)):
                i = by_pid[sp_pid][k]
                vv = val(i)
                if vv is not None and u32(vv.get(own_at)) == me:
                    units.add(rows[i][3])
        for k in range(bisect.bisect_left(pid_t.get(223, []), t), bisect.bisect_right(pid_t.get(223, []), t + WINDOW)):
            i = by_pid[223][k]
            vv = val(i)
            if vv is not None and u32((vv.get('+0xf8') or {}).get('+0x78')) == me:
                missiles.add(rows[i][3])
        for n in units:
            for i in window(by_net[n], t, t + SPAWN_WINDOW):
                roles.setdefault(i, 'spawn')
            # what the unit does to others: buffs it gives (fear ...), damage it deals, effects; its own movement
            for i in window(names[n], t, t + SPAWN_WINDOW):
                roles.setdefault(i, 'spawn' if rows[i][2] in (61, 1140) else 'spawn_other')
        for n in missiles:
            for i in window(by_net[n], t, t + WINDOW):
                roles.setdefault(i, 'missile')
        # the caster's regions: bound to it (above, via names) or standing near the cast's places, of its team, after it
        team = '01' if sorted(heroes).index(me) < 5 else '02'
        places = [p for p in (vec3(c.get('+0x40')), vec3(c.get('+0xac')), vec3(c.get('+0x124'))) if p]
        for (t2, i2, tm, (x, z)) in regions:
            if t <= t2 <= t + WINDOW and tm == team and any(abs(x - p[0]) < 250 and abs(z - p[2]) < 250 for p in places):
                roles.setdefault(i2, 'caster')
        for i2 in list(roles):
            if rows[i2][2] == 41:
                roles[i2] = 'caster'
        roles.pop(i0, None)
        for i in sorted(roles):
            t2, ch2, p2, n2, b2, inc2 = rows[i]
            dt, role = round(t2 - t, 3), roles[i]
            if p2 == 61:
                vv = val(i)
                try:
                    es = [e for e in waypoints.parse(bytes.fromhex(vv['+0x18']['text'])) if e['net'] == me]
                except Exception:
                    es = []
                who = me if role == 'caster' else None
                es = es if who == me else []
                if not es:
                    continue
                e0 = es[0]
                cast['events'].append((dt, 61, role, n2, {'teleport': e0['teleport'], 'n': len(e0['points']), 'speed': round(e0['speed']),
                                                           'flags': e0['flags'], 'to': e0['points'][-1]}, i))
                continue
            cast['events'].append((dt, p2, role, n2, summary(R, p2, n2, b2, me, val(i)), i))
        for n in [me] + sorted(units):
            for (t2, k, a, b) in repl.get(n, []):
                if t <= t2 <= t + (WINDOW if n == me else SPAWN_WINDOW):
                    cast['events'].append((round(t2 - t, 3), 287, 'caster' if n == me else 'spawn', n, {k: [a, b]}, None))
        cast['events'].sort(key=lambda e: e[0])
        casts.append(cast)
    # how long each cast had the champion to itself: until its next own cast of a spell, summoner spell, item or recall
    nxt = {}
    for c in reversed(casts):
        c['until'] = round(nxt[c['net']] - c['t'], 3) if c['net'] in nxt else WINDOW
        if c['slot'] <= 13:
            nxt[c['net']] = c['t']
    os.makedirs(os.path.join(DATA, 'casts'), exist_ok=True)
    d = {'game': gid, 'heroes': heroes, 'casts': casts, 'spawned': spawned}
    import gzip
    with gzip.open(os.path.join(DATA, 'casts', f'{gid}.pkl'), 'wb', compresslevel=5) as f:
        pickle.dump(d, f, protocol=4)
    samples(gid, R=R, d=d)                       # the whole packets of its first casts, from the same read
    cache = os.path.splitext(path)[0] + '.rows.pkl'
    if os.path.exists(cache):
        os.remove(cache)                         # [disk] 60-130 MB a replay; the .rofl stays
    return heroes, len(casts)


def load_casts(p):
    import gzip
    with open(p, 'rb') as f:
        head = f.read(2)
    return pickle.load(gzip.open(p, 'rb') if head == b'\x1f\x8b' else open(p, 'rb'))


# ------------------------------------------------------------------------------------------------ full packets
SAMPLES_PER_REPLAY = 6


def samples(gid, R=None, d=None):
    """the whole packets of the first casts of every champion spell of one replay (the template builder compares
    them field by field) -> data/replays16/samples/<game>.pkl
    {(champion, spell): [{'game', 't', 'net', 'slot', 'cast': its 1215's values,
                          'events': [(dt, pid, role, net, channel, container row or None, values, raw hex or None)]}]}"""
    R = R or RD.Replay(os.path.join(DATA, 'rofl', f'{gid}.rofl'), cache=False)
    d = d or load_casts(os.path.join(DATA, 'casts', f'{gid}.pkl'))
    rows = list(R.flat(with_container=True, skip=DROP))
    out = collections.defaultdict(list)
    for c in d['casts']:
        key = (c['hero'], c['spell'])
        if len(out[key]) >= SAMPLES_PER_REPLAY or c.get('i') is None:
            continue
        t, ch, pid, net, body, inc, cont = rows[c['i']]
        s = {'game': gid, 't': c['t'], 'net': c['net'], 'slot': c['slot'], 'until': c.get('until', WINDOW),
             'cast': R.parse(pid, body), 'events': []}
        for e in c['events']:
            i = e[5] if len(e) > 5 else None
            if i is None:
                s['events'].append((e[0], e[1], e[2], e[3], None, None, e[4], None))
                continue
            t2, ch2, p2, n2, b2, inc2, cont2 = rows[i]
            v = R.parse(p2, b2)
            s['events'].append((e[0], p2, e[2], n2, ch2, cont2, v, b2.hex() if v is None else None))
        out[key].append(s)
    os.makedirs(os.path.join(DATA, 'samples'), exist_ok=True)
    import gzip
    with gzip.open(os.path.join(DATA, 'samples', f'{gid}.pkl'), 'wb', compresslevel=5) as f:
        pickle.dump(dict(out), f, protocol=4)
    return len(out)


# ------------------------------------------------------------------------------------------------ reports
def all_casts(champ=None):
    for p in sorted(glob.glob(os.path.join(DATA, 'casts', '*.pkl'))):
        d = load_casts(p)
        for c in d['casts']:
            if champ is None or c['hero'].lower() == champ.lower():
                yield c


def signature(e):
    """what an event is, without its time and unit: comparable between casts"""
    dt, pid, role, net, s = e[:5]
    keep = {k: s[k] for k in s if k not in ('dur', 'dmg', 'to', 'raw', 'count')} if isinstance(s, dict) else {}
    return (pid, role, json.dumps(keep, sort_keys=True, default=str))


def report(champ):
    from server.core import gamedata as G
    ch = G.champion(champ)
    by = collections.defaultdict(list)
    for c in all_casts(champ):
        by[c['spell']].append(c)
    order = {n: i for i, n in enumerate(ch.spells)}
    out, js = [], {}
    games = {c['game'] for cs in by.values() for c in cs}
    out.append(f'{champ}: {sum(len(v) for v in by.values())} casts in {len(games)} replays')
    for spell, cs in sorted(by.items(), key=lambda x: (order.get(x[0], 9), x[0])):
        slot = 'QWER'[order[spell]] if spell in order else f'slot {cs[0]["slot"]}'
        out.append(f'\n== {slot} {spell}: {len(cs)} casts (cast time {cs[0]["cast_time"]}, total {cs[0]["total"]})')
        seen = collections.defaultdict(list)
        for c in cs:
            first = {}
            for e in c['events']:
                k = signature(e)
                if k not in first:
                    first[k] = e
            for k, e in first.items():
                seen[k].append(e)
        rows = []
        for k, es in seen.items():
            share = len(es) / len(cs)
            if share < 0.15 and len(es) < 3:
                continue
            dts = [e[0] for e in es]
            durs = [e[4].get('dur') for e in es if isinstance(e[4], dict) and e[4].get('dur') is not None]
            extra = f' dur~{statistics.median(durs):.2f}' if durs else ''
            rows.append((-share, statistics.median(dts), k, len(es), extra))
        rows.sort()
        js[spell] = []
        for nshare, mdt, (pid, role, s), n, extra in rows[:60]:
            name = NAMES.get(str(pid), '?')
            out.append(f'  {-nshare * 100:5.0f}%  {mdt:+6.2f}s  {role:7s} {pid:5d} {name[:34]:34s} {s}{extra}')
            js[spell].append({'share': round(-nshare, 3), 'dt': mdt, 'role': role, 'pid': pid, 'name': name, 'what': json.loads(s), 'n': n})
    os.makedirs(os.path.join(DATA, 'evidence'), exist_ok=True)
    open(os.path.join(DATA, 'evidence', f'{champ}.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    json.dump(js, open(os.path.join(DATA, 'evidence', f'{champ}.json'), 'w'), indent=0)
    return out


def show(champ, which, n=3):
    from server.core import gamedata as G
    ch = G.champion(champ)
    spell = ch.spells['QWER'.index(which.upper())] if which.upper() in ('Q', 'W', 'E', 'R') else which
    k = 0
    for c in all_casts(champ):
        if c['spell'].lower() != spell.lower():
            continue
        print(f'--- game {c["game"]} t {c["t"]:.2f} {c["hero"]} {c["spell"]} slot {c["slot"]}')
        for e in c['events']:
            print(f'   {e[0]:+7.3f} {e[2]:7s} {e[1]:5d} {NAMES.get(str(e[1]), "?")[:30]:30s} {e[3]:08x} {e[4]}')
        k += 1
        if k >= n:
            break


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'scan':
        ids = sys.argv[2:] or [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(DATA, 'rofl', '*.rofl')))
                               if not os.path.exists(os.path.join(DATA, 'casts', os.path.basename(p)[:-5] + '.pkl'))]
        hash_names()
        for gid in ids:
            heroes, n = scan(gid)
            print(gid, n, 'casts', sorted(heroes.values()), flush=True)
    elif cmd == 'samples':
        ids = sys.argv[2:] or [os.path.basename(p)[:-4] for p in sorted(glob.glob(os.path.join(DATA, 'casts', '*.pkl')))
                               if not os.path.exists(os.path.join(DATA, 'samples', os.path.basename(p)))]
        for gid in ids:
            print(gid, samples(gid), 'spells', flush=True)
    elif cmd == 'report':
        champs = sys.argv[2:] or sorted({c['hero'] for c in all_casts()})
        for c in champs:
            out = report(c)
            if len(sys.argv) > 2:
                print('\n'.join(out))
    elif cmd == 'show':
        show(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 3)
