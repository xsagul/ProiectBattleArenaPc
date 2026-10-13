"""Spell templates of every champion from the real matches' replays: what Riot's server sends after each cast, in
order, every field either FIXED (the same in all the casts seen: names, buff types, animations, effect keys - copied
as they are) or computed from the cast (its caster, target, the units it created, its missiles, its places, times).

    python tools/spell_templates16.py [Champion ..]     -> data/exe1620/spells16/<Champion>.json (every champion with
                                                           samples when none is given)
    python tools/spell_templates16.py show <Champion> [Q|W|E|R|spell]

Input: data/replays16/samples/*.pkl (tools/replay_evidence16.py samples). One template per spell:
  {'slot', 'samples', 'cast': the cast struct's fixed fields, 'events': [
      {'pid', 'name' (the client's own packet name), 'role' (caster | spawn | missile | other: whose packet),
       'share' (of the casts that had it), 'dt' (s after the cast, median), 'dt_lo', 'dt_hi', 'rank' (order within
       a frame), 'repeat' (times per cast), 'ch', 'grouped' (rode in a 239 container),
       'net' (the packet's own net id, computed), 'values' (fields; computed ones as {'$': kind, ...})}]}
Computed fields:
  {'$': 'net', 'of': 'caster' | 'target' | 'self' | 'spawn<k>' | 'missile<k>' | 'cast'}   a unit's net id
  {'$': 'time', 'off': s}                     the game time of the cast + off
  {'$': 'place', 'of': 'launch' | 'aim' | 'end', 'dy': y offset}   a place of the cast (vec3)
  {'$': 'vary', 'ex': [up to 4 values]}       none of these: counters, the unit's buff slot, ...
"""
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
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)
SAMPLES = os.path.join(ROOT, 'data', 'replays16', 'samples')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'spells16')
NAMES = json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'packet_names16.json')))
CORE, OFTEN = 0.5, 0.25


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and len(h) == 8 else None


def f32(h):
    try:
        return struct.unpack('<f', bytes.fromhex(h))[0] if isinstance(h, str) and len(h) == 8 else None
    except Exception:
        return None


def vec3(h):
    try:
        return struct.unpack('<fff', bytes.fromhex(h)) if isinstance(h, str) and len(h) == 24 else None
    except Exception:
        return None


def text(v):
    try:
        return bytes.fromhex(v['text']).decode('latin-1').rstrip('\0')
    except Exception:
        return ''


# ------------------------------------------------------------------------------------------------ what an event is
def signature(pid, role, v, extra=None):
    """the identity of an event, comparable between casts: its kind and the fields that say what it is"""
    if pid == 287:
        k, (a, b) = next(iter(extra.items()))
        return (pid, role, k, json.dumps(b))
    if pid == 61:
        return (pid, role, 'teleport' if isinstance(v, dict) and v.get('teleport') is not None else 'move')
    if not isinstance(v, dict):
        return (pid, role)
    try:
        if pid == 435:
            return (pid, role, v['+0x38'], v['+0x64'], 'self' if v.get('+0x1c') == v.get('_me') else 'other')
        if pid == 262:
            return (pid, role, v['+0x14'])
        if pid == 78:
            return (pid, role, v['+0x10'].get('+0xf'), text(v['+0x20']))
        if pid == 223:
            return (pid, role, v['+0xf8']['+0x18'], v['+0xf8']['+0x60'])
        if pid == 1215:
            return (pid, role, v['+0x18']['+0x18'], v['+0x18']['+0x60'])
        if pid == 626:
            return (pid, role, text(v['+0x38']), text(v['+0x70']))
        if pid == 1038:
            return (pid, role, text(v.get('+0x10', {})), text(v.get('+0x58', {})))
        if pid in (1088, 982):
            return (pid, role, text(v.get('+0x10' if pid == 1088 else '+0x28', {})))
        if pid == 10:
            g = v.get('+0x10') or []
            return (pid, role, g[0].get('+0x20') if g and isinstance(g[0], dict) else None)
        if pid in (291, 236):
            return (pid, role, v.get('+0x10'), v.get('+0x14'))
        if pid in (947, 596):
            s = v.get('+0x10') or {}
            return (pid, role, s.get('+0x8'), s.get('+0xc'))
        if pid == 150:
            return (pid, role, v['+0x18'], v['+0x1a'], v['+0x2c'])
        if pid == 699:
            return (pid, role, v.get('+0x10'))
        if pid == 280:
            return (pid, role, v.get('+0x14'))
        if pid == 41:
            r = v.get('+0x10') or {}
            return (pid, role, r.get('+0x28'), v.get('+0x58'), r.get('+0x0d'), r.get('+0x24'), r.get('+0x2c'), r.get('+0x3c'))
        if pid == 904:
            return (pid, role, json.dumps(v.get('+0x10'), sort_keys=True)[:200])
    except Exception:
        pass
    return (pid, role)


# ------------------------------------------------------------------------------------------------ one spell
def context(s):
    """the units, places and time of one sampled cast"""
    c = (s['cast'] or {}).get('+0x18') or {}
    ctx = {'caster': s['net'], 'cast': u32(c.get('+0x8c')), 't': s['t']}
    tl = c.get('+0x8') or []
    if tl and isinstance(tl[0], dict):
        ctx['target'] = u32(tl[0].get('+0x8'))
    for k in ('+0x124', '+0x40', '+0xac'):
        ctx[{'+0x124': 'launch', '+0x40': 'aim', '+0xac': 'end'}[k]] = vec3(c.get(k))
    spawns, missiles = [], []
    if u32(c.get('+0xbc')):
        missiles.append(u32(c.get('+0xbc')))
    for dt, pid, role, net, ch, cont, v, raw in s['events']:
        if role == 'spawn' and net not in spawns and pid in (626, 1038):
            spawns.append(net)
        if role == 'missile' and net not in missiles:
            missiles.append(net)
    for k, n in enumerate(spawns):
        ctx[f'spawn{k}'] = n
    for k, n in enumerate(missiles):
        ctx[f'missile{k}'] = n
    return ctx


NET_ROLES = ('caster', 'target', 'self', 'cast')


def classify(vals, ctxs, nets, own=False):
    """one field over the instances -> the template value (as is, or {'$': ...}); own: the packet's own net id
    (never 'self')"""
    first = vals[0]
    if all(json.dumps(x, sort_keys=True) == json.dumps(first, sort_keys=True) for x in vals):
        return first
    if all(isinstance(x, dict) and 'text' not in x for x in vals):
        keys = list(first.keys())
        if all(list(x.keys()) == keys for x in vals):
            return {k: classify([x[k] for x in vals], ctxs, nets) for k in keys}
    if all(isinstance(x, list) for x in vals):
        n = len(first)
        if all(len(x) == n for x in vals):
            return [classify([x[i] for x in vals], ctxs, nets) for i in range(n)]
        return {'$': 'vary', 'ex': vals[:4]}
    if all(isinstance(x, str) for x in vals):
        if all(len(x) == 8 for x in vals):
            got = [u32(x) for x in vals]
            roles = [r for r in NET_ROLES if not (own and r == 'self')] + sorted({k for c in ctxs for k in c if k.startswith(('spawn', 'missile'))})
            for r in roles:
                want = [nets[i] if r == 'self' else ctxs[i].get(r) for i in range(len(vals))]
                if all(w is not None and w == g for w, g in zip(want, got)):
                    return {'$': 'net', 'of': r}
            fl = [f32(x) for x in vals]
            if all(f is not None for f in fl):
                offs = [f - c['t'] for f, c in zip(fl, ctxs)]
                if max(offs) - min(offs) < 0.07 and -1.0 < statistics.median(offs) < 600.0 and min(abs(f) for f in fl) > 1.0:
                    return {'$': 'time', 'off': round(statistics.median(offs), 3)}
        if all(len(x) == 16 for x in vals):
            # [10-13] a place as (x, z) - the regions' (41) +0x14
            try:
                ps = [struct.unpack('<ff', bytes.fromhex(x)) for x in vals]
            except Exception:
                ps = None
            for r in ('launch', 'aim', 'end'):
                if ps and all(c.get(r) is not None and abs(p[0] - c[r][0]) <= 4.0 and abs(p[1] - c[r][2]) <= 4.0
                              for p, c in zip(ps, ctxs)):
                    return {'$': 'place2', 'of': r}
            if ps and all(abs(p[0] - c['launch'][0]) <= 60.0 and abs(p[1] - c['launch'][2]) <= 60.0 for p, c in zip(ps, ctxs)
                          if c.get('launch')):
                return {'$': 'place2', 'of': 'caster'}
        if all(len(x) == 24 for x in vals):
            ps = [vec3(x) for x in vals]
            for r in ('launch', 'aim', 'end'):
                ok, dys = True, []
                for p, c in zip(ps, ctxs):
                    q = c.get(r)
                    if p is None or q is None or abs(p[0] - q[0]) > 4.0 or abs(p[2] - q[2]) > 4.0:
                        ok = False
                        break
                    dys.append(p[1] - q[1])
                if ok:
                    return {'$': 'place', 'of': r, 'dy': round(statistics.median(dys), 1)}
    return {'$': 'vary', 'ex': vals[:4]}


ACTIVE = frozenset({938, 1215, 906, 390, 51, 134})        # a unit doing something of its own: missiles, casts, attacks


def trigger_time(s):
    """when the first unit the cast made began to act (a trap set off, a pet's first attack) - after it was armed
    (made invisible: ActionState bit 0x20 or an invisibility buff) when it was; None: it never acted"""
    spawned = armed = None
    for dt, pid, role, net, ch, cont, v, raw in s['events']:
        if role != 'spawn':
            continue
        if pid in (626, 1038) and spawned is None:
            spawned = dt
        elif pid == 287 and isinstance(v, dict) and 'ActionState' in v and armed is None:
            a, b = v['ActionState'][:2]
            if isinstance(a, int) and isinstance(b, int) and b & 0x20 and not a & 0x20:
                armed = dt
        elif pid == 435 and isinstance(v, dict) and v.get('+0x38') == '06' and armed is None:
            armed = dt
    if spawned is None:
        return None
    start = armed if armed is not None else spawned
    for dt, pid, role, net, ch, cont, v, raw in s['events']:
        if dt <= start + 0.01:
            continue
        if (role == 'spawn' and pid in ACTIVE) or (role == 'spawn_other' and pid in (435, 150)):
            return dt
    return None


def own_events(s):
    """the events of a sampled cast that are its own: the champion's (and what it did to others) until its next cast
    of a spell / summoner spell / item / recall (that cast's 1215 and its frame included: dt >= until), the units
    it created before then and what those did"""
    until = own_until(s) - 0.005
    late = {net for dt, pid, role, net, ch, cont, v, raw in s['events'] if role == 'spawn' and pid in (626, 1038) and dt >= until}
    early = {net for dt, pid, role, net, ch, cont, v, raw in s['events'] if role == 'spawn' and pid in (626, 1038) and dt < until}
    out = []
    for e in s['events']:
        dt, pid, role, net = e[0], e[1], e[2], e[3]
        if role in ('caster', 'other', 'missile') and dt >= until:
            continue
        if role == 'spawn' and (net in late or (not early and dt >= until)):
            continue
        if role == 'spawn_other' and not early:
            continue
        if pid == 61 and isinstance(e[6], dict) and 'teleport' not in e[6]:
            mv = move_of(e[6], s['net'])
            if mv is None:
                continue
            e = tuple(e[:6]) + (mv,) + tuple(e[7:])
        out.append(e)
    return out


def own_until(s):
    """when the champion's next cast of its own began: its next 1215 of a spell / summoner spell / item / recall
    (slot <= 13) - not a cast of a spell this cast put in a slot (78: Shaco's R casts HallucinateGuide at once, a
    recast form is the same ability going on)"""
    recast = set()
    for dt, pid, role, net, ch, cont, v, raw in s['events']:
        if role != 'caster' or not isinstance(v, dict):
            continue
        if pid == 78:
            sl = v.get('+0x10', {}).get('+0xf') if isinstance(v.get('+0x10'), dict) else None
            name = text(v.get('+0x20', {}))
            if sl is not None and int(sl, 16) < 4 and name:
                recast.add(_hex(_elf(name)))
        elif pid == 1215:
            c = v.get('+0x18') or {}
            try:
                slot = int(c.get('+0x60', 'ff'), 16)
            except ValueError:
                continue
            # a recast form cast in the cast's own frame is the script's (Shaco's R casts HallucinateGuide at once);
            # one cast later is the player's second press: what follows is that cast's (its own template)
            if slot <= 13 and (c.get('+0x18') not in recast or dt > 0.05):
                return dt
    return s.get('until', 99.0) if not recast else 99.0


def _elf(name):
    h = 0
    for ch in name.lower().encode():
        h = (h << 4) + ch
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h


def move_of(v, net):
    """a movement packet's entry for the champion -> {'teleport': its teleport id or None, 'n': points}"""
    import waypoints
    try:
        es = [x for x in waypoints.parse(bytes.fromhex(v['+0x18']['text'])) if x['net'] == net]
    except Exception:
        return None
    return {'teleport': es[0]['teleport'], 'n': len(es[0]['points'])} if es else None


_damage_names = None


def hit_state(s, spell):
    """what this cast did, from its own packets: {'hit': first time its damage hit anything, 'hit_hero': first time
    it hit a champion} (None: never) - the damage counted is the spell's own name or the name its damage carries
    (damage_names16.json), so the caster's later attacks do not count"""
    global _damage_names
    if _damage_names is None:
        try:
            _damage_names = json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'damage_names16.json')))
        except Exception:
            _damage_names = {}
    names = {spell, _damage_names.get(spell, spell)}
    hashes = {int(n[1:], 16) if n.startswith('#') else _elf(n) for n in names}
    out = {'hit': None, 'hit_hero': None}
    for dt, pid, role, net, ch, cont, v, raw in s['events']:
        if pid != 150 or role != 'other' or not isinstance(v, dict):
            continue
        if u32(v.get('+0x2c')) not in hashes or u32(v.get('+0x1c')) != s['net']:
            continue
        if out['hit'] is None:
            out['hit'] = dt
        if out['hit_hero'] is None and 0x40000000 < net < 0x40000100:
            out['hit_hero'] = dt
    return out


def conditions(events, lists, spell):
    """[m: the casts' own hits] an event most casts do not have, explained by what the cast did: it is played only
    when the cast does that ('cond': 'hit' | 'hit_hero'), 'dt_cond' s after that moment"""
    states = [hit_state(s, spell) for s, evs in lists]
    for ev in events:
        if ev['core'] or ev['pid'] in (150, 1215) or not ev.get('_inst'):
            continue
        have = {si: dt for si, ei, dt in ev['_inst']}
        best = None
        for cond in ('hit_hero', 'hit'):
            yes = [i for i, st in enumerate(states) if st[cond] is not None]
            no = [i for i, st in enumerate(states) if st[cond] is None]
            if len(yes) < 3:
                continue
            p_yes = sum(1 for i in yes if i in have) / len(yes)
            p_no = sum(1 for i in no if i in have) / len(no) if no else 0.0
            if p_yes >= 0.7 and p_no <= 0.25 and (best is None or p_yes - p_no > best[1]):
                after = [have[i] - states[i][cond] for i in yes if i in have and have[i] >= states[i][cond] - 0.05]
                if len(after) >= 2:
                    best = (cond, p_yes - p_no, statistics.median(after), p_yes, p_no)
        if best:
            ev['cond'], ev['dt_cond'] = best[0], round(max(0.0, best[2]), 3)
            ev['cond_share'] = [round(best[3], 2), round(best[4], 2)]
            ev['core'] = True
    for ev in events:
        ev.pop('_inst', None)
    return events


def build_spell(samples, spell=''):
    """-> (events after the cast, events after the cast's unit began to act (dt from that moment))"""
    main, trig = [], []
    for s in samples:
        s = dict(s, events=own_events(s), _until=own_until(s))
        t = trigger_time(s)
        if t is None:
            main.append((s, list(s['events'])))
            continue
        # what the unit and the champion did to others from that moment on (a trap's fear, its damage) is the trap's
        main.append((s, [e for e in s['events'] if not (e[2] in ('spawn', 'spawn_other', 'other') and e[0] >= t - 0.005)]))
        trig.append((s, [(round(e[0] - t, 3),) + tuple(e[1:]) for e in s['events']
                         if e[2] in ('spawn', 'spawn_other', 'other') and e[0] >= t - 0.005]))
    return conditions(aggregate(main), main, spell), ([e for e in aggregate(trig) if not e.pop('_inst', None) and True] if len(trig) >= 2 else [])


def aggregate(lists):
    n = len(lists)
    untils = [s.get('_until', 99.0) for s, evs in lists]      # how long each cast was watched (its next own cast)
    occ = collections.defaultdict(list)           # signature -> [(sample index, event index, dt)]
    for si, (s, evs) in enumerate(lists):
        for ei, (dt, pid, role, net, ch, cont, v, raw) in enumerate(evs):
            if pid == 287:
                sig = signature(pid, role, None, v)          # v = {field: [before, after]}
            else:
                sig = signature(pid, role, dict(v, _me=_hex(s['net'])) if isinstance(v, dict) else v)
            occ[sig].append((si, ei, dt))
    events = []
    for sig, lst in occ.items():
        per = collections.Counter(si for si, ei, dt in lst)
        firsts = {}
        for si, ei, dt in lst:
            firsts.setdefault(si, (ei, dt))
        dts = [dt for ei, dt in firsts.values()]
        # its share among the casts still watched at its time: a cast followed at once by another (Zed's W then E
        # within 0.27 s) says nothing about what comes later (the shadow at +0.27)
        watched = sum(1 for u in untils if u >= statistics.median(dts) - 0.02)
        share = len(per) / max(len(per), watched)
        if share < OFTEN or len(per) < 2:
            continue
        ranks = [ei / max(1, len(lists[si][1])) for si, (ei, dt) in firsts.items()]
        inst = [(si,) + firsts[si] for si in sorted(firsts)]
        pid, role = sig[0], sig[1]
        inst_all = inst
        ev = {'pid': pid, 'name': NAMES.get(str(pid), '?'), 'role': role, 'share': round(share, 3),
              'dt': round(statistics.median(dts), 3), 'dt_lo': round(min(dts), 3), 'dt_hi': round(max(dts), 3),
              'rank': round(statistics.median(ranks), 4), 'repeat': round(statistics.median(per.values()), 1),
              'seen': len(per), 'core': share >= CORE and len(per) >= max(2, 0.15 * n), '_inst': inst_all}
        if pid == 287:
            ev['values'] = lists[inst[0][0]][1][inst[0][1]][6]
            ev['field'] = sig[2]
        else:
            vals, ctxs, nets = [], [], []
            for si, ei, dt in inst[:12]:
                e = lists[si][1][ei]
                if e[6] is None:
                    continue
                vals.append(e[6])
                ctxs.append(context(lists[si][0]))
                nets.append(e[3])
            if vals:
                ev['values'] = classify(vals, ctxs, nets)
                ev['net'] = classify([_hex(x) for x in nets], ctxs, nets, own=True)
            else:
                ev['raw'] = lists[inst[0][0]][1][inst[0][1]][7]
            e0 = lists[inst[0][0]][1][inst[0][1]]
            ev['ch'] = e0[4]
            ev['grouped'] = e0[5] is not None
        events.append(ev)
    events.sort(key=lambda e: (round(e['dt'], 2), e['rank']))
    return events


def _hex(n):
    return struct.pack('<I', n & 0xffffffff).hex() if isinstance(n, int) else n


BY_CHAMP = os.path.join(ROOT, 'data', 'replays16', 'by_champ')


def _read(p):
    import gzip
    with open(p, 'rb') as f:
        gz = f.read(2) == b'\x1f\x8b'
    return pickle.load(gzip.open(p, 'rb') if gz else open(p, 'rb'))


def shard():
    """every replay's samples split by champion, read once -> data/replays16/by_champ/<Champion>.pkl (a pickle
    stream: one dict per replay)"""
    import shutil
    if os.path.isdir(BY_CHAMP):
        shutil.rmtree(BY_CHAMP)
    os.makedirs(BY_CHAMP)
    files = sorted(glob.glob(os.path.join(SAMPLES, '*.pkl')))
    for i, p in enumerate(files):
        d = _read(p)
        per = collections.defaultdict(dict)
        for (hero, spell), lst in d.items():
            per[hero][(hero, spell)] = lst
        for hero, part in per.items():
            with open(os.path.join(BY_CHAMP, f'{hero}.pkl'), 'ab') as f:
                pickle.dump(part, f, protocol=4)
        if (i + 1) % 16 == 0:
            print(f'{i + 1} of {len(files)} sample files split', flush=True)


def load_samples(champ=None):
    out = collections.defaultdict(list)
    sp = os.path.join(BY_CHAMP, f'{champ}.pkl') if champ else None
    if sp and os.path.exists(sp):
        with open(sp, 'rb') as f:
            while True:
                try:
                    part = pickle.load(f)
                except EOFError:
                    break
                for k, lst in part.items():
                    out[k] += lst
        return out
    import gzip
    for p in sorted(glob.glob(os.path.join(SAMPLES, '*.pkl'))):
        with open(p, 'rb') as f:
            gz = f.read(2) == b'\x1f\x8b'
        d = pickle.load(gzip.open(p, 'rb') if gz else open(p, 'rb'))
        for (hero, spell), lst in d.items():
            if champ is None or hero.lower() == champ.lower():
                out[(hero, spell)] += lst
    return out


def build(champ):
    from server.core import gamedata as G
    ch = G.champion(champ)
    smp = load_samples(champ)
    out = {}
    for (hero, spell), lst in sorted(smp.items()):
        if len(lst) < 2:
            continue
        cast = classify([s['cast'] for s in lst if s['cast']][:12], [context(s) for s in lst if s['cast']][:12],
                        [s['net'] for s in lst if s['cast']][:12]) if any(s['cast'] for s in lst) else None
        events, trigger = build_spell(lst, spell)
        out[spell] = {'slot': lst[0]['slot'], 'samples': len(lst), 'games': len({s['game'] for s in lst}),
                      'qwer': 'QWER'[ch.spells.index(spell)] if spell in ch.spells else None,
                      'cast': cast, 'events': events, 'trigger': trigger,
                      'triggered': round(sum(1 for s in lst if trigger_time(s) is not None) / len(lst), 3)}
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, f'{champ}.json'), 'w'), indent=0)
    return out


def show(champ, which=None):
    d = json.load(open(os.path.join(OUT, f'{champ}.json')))
    for spell, t in d.items():
        if which and which.upper() != (t.get('qwer') or '') and which.lower() != spell.lower():
            continue
        print(f"== {t.get('qwer') or '-'} {spell} slot {t['slot']}: {t['samples']} casts in {t['games']} games")
        for e in t['events'] + [dict(x, role='TRIG:' + x['role']) for x in t.get('trigger', [])]:
            if not e['core'] and not which:
                continue
            what = e.get('values') if e['pid'] != 287 else e.get('values')
            s = json.dumps(what)[:260] if what is not None else 'raw ' + str(e.get('raw'))[:60]
            print(f"  {'*' if e['core'] else ' '}{e['share'] * 100:4.0f}% {e['dt']:+6.2f} [{e['dt_lo']:+.2f},{e['dt_hi']:+.2f}] x{e['repeat']:<3} "
                  f"{e['role']:7s} {e['pid']:5d} {e['name'][:28]:28s} net={json.dumps(e.get('net'))[:40]} {s}")


CC_NAMES = {5: 'stun', 6: 'invisible', 7: 'silence', 8: 'taunt', 10: 'polymorph', 11: 'slow', 12: 'snare', 15: 'haste',
            18: 'invulnerable', 22: 'fear', 23: 'charm', 25: 'suppress', 29: 'flee', 30: 'knockup', 31: 'knockback',
            32: 'disarm', 33: 'grounded', 35: 'asleep'}


def census():
    """what each champion's spells do, by the templates: -> data/exe1620/spells16/census.txt"""
    from server.core import gamedata as G
    rows, have, total = [], 0, 0
    for c in G.champion_index():
        name = c['alias']
        p = os.path.join(OUT, f'{name}.json')
        d = json.load(open(p)) if os.path.exists(p) else {}
        ch = G.champion(name)
        for i, spell in enumerate(ch.spells[:4]):
            total += 1
            t = d.get(spell)
            if t is None:
                rows.append(f'{name:14s} {"QWER"[i]} {spell:28s} --- no template')
                continue
            have += 1
            tags = []
            for e in t['events']:
                if not e['core'] and e['share'] < 0.4:
                    continue
                v = e.get('values') if isinstance(e.get('values'), dict) else {}
                if e['pid'] == 626 and e['role'] == 'spawn':
                    tags.append('spawn:' + text(v.get('+0x38', {})) + '/' + text(v.get('+0x70', {})))
                elif e['pid'] == 1038 and e['role'] == 'spawn':
                    tags.append('pet:' + text(v.get('+0x10', {})) + '/' + text(v.get('+0x58', {})))
                elif e['pid'] == 435 and isinstance(v.get('+0x38'), str):
                    k = CC_NAMES.get(int(v['+0x38'], 16))
                    if k:
                        tags.append(('hit:' if e['role'] == 'other' else 'self:' if e['role'] == 'caster' else e['role'] + ':') + k)
                elif e['pid'] == 78 and e['role'] == 'caster':
                    sl = int(v.get('+0x10', {}).get('+0xf', 'ff'), 16) if isinstance(v.get('+0x10'), dict) else 255
                    if sl < 4:
                        tags.append('recast:' + text(v.get('+0x20', {})))
                elif e['pid'] == 982:
                    tags.append('transform:' + text(v.get('+0x28', {})))
                elif e['pid'] in (291, 947, 596, 236):
                    tags.append({291: 'stealthflags', 947: 'fade', 596: 'fade', 236: 'alpha'}[e['pid']])
                elif e['pid'] == 287 and 'Shield' in str(e.get('field')):
                    tags.append('shield')
                elif e['pid'] == 1215 and e['role'] == 'caster':
                    tags.append('subcast')
                elif e['pid'] == 223:
                    tags.append('missile')
                elif e['pid'] == 10:
                    tags.append('fx')
            seen = []
            for x in tags:
                if x not in seen:
                    seen.append(x)
            rows.append(f'{name:14s} {"QWER"[i]} {spell:28s} {t["samples"]:3d} casts {t["games"]:2d} games  {" ".join(seen)[:200]}')
    rows.insert(0, f'{have} of {total} Q/W/E/R spells have a template')
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'census.txt'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
    return rows


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'census':
        print('\n'.join(census()[:5]))
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] == 'shard':
        shard()
        sys.exit()
    if not sys.argv[1:]:
        shard()
        champs = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(BY_CHAMP, '*.pkl')))
    else:
        champs = sys.argv[1:]
    import spell_geom16                          # each spell's 'geom' (missiles, dashes, reach) is written in a second
    for c in champs:                             # pass: a template built without it loses its missiles' shapes
        try:
            out = build(c)
            spell_geom16.build(c)
            print(c, len(out), 'spells', flush=True)
        except Exception as e:
            print(c, 'failed:', e, flush=True)
