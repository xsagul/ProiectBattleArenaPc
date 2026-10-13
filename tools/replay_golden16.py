"""The whole-match test of the server against a real match: the ten champions of a replay are played again on our
server as puppets - they walk where the replay's champions walked and cast what those cast, when they did - and
everything our server then sends is set against what Riot's server sent in that match, packet kind by packet kind.
A server that is complete sends the same packets; what is missing or extra is the list of work left.

    python tools/replay_golden16.py <game id> [--from s] [--to s]      -> data/exe1620/golden16/<game id>.txt
    python tools/replay_golden16.py batch [n] [--from s] [--to s]       the first n replays -> golden16/summary.txt
    python tools/replay_golden16.py list                               the replays at hand

What the puppets take from the replay (the replay holds no client requests: they are read back from what the server
told everyone): each champion's movement (61: its path), its casts (1215 of slots 0-5: aim, target), its basic
attacks at champions (906). A puppet that has drifted more than 300 units from where the replay's champion starts a
path is put there (counted: 'resyncs'). Spell ranks, cooldowns and mana are forced to allow each recorded cast.
The comparison: every packet of the replay in the window, but the spectator's own (spectator_only16.json), against
ours: same kind, same champion when it is about one (other units have other net ids in our match: by kind and time),
within 0.15 s. Per kind: how many the replay has, how many we sent, how many pair up.
[a] minions, monsters and bots' own choices are not the replay's: world packets can only agree in number.
"""
import collections
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, ROOT)
os.environ.setdefault('BA_PATCH', '1620')
DATA = os.path.join(ROOT, 'data', 'replays16')
OUT = os.path.join(ROOT, 'data', 'exe1620', 'golden16')
TOL = 0.15


def vec3(h):
    try:
        return struct.unpack('<fff', bytes.fromhex(h)) if isinstance(h, str) and len(h) == 24 else None
    except Exception:
        return None


def u32(h):
    return int.from_bytes(bytes.fromhex(h), 'little') if isinstance(h, str) and len(h) == 8 else 0


def inputs_of(R, heroes, t0, t1, minions=()):
    """the champions' doings in the replay -> [(t, kind, hero net, data)] and the replay's packets [(t, pid, net)]"""
    import waypoints
    import replication
    import repl16
    spectator = set(json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'spectator_only16.json'))))
    ins, theirs = [], []
    plants_seen = set()
    frame_t, frame_seen = None, set()
    for t, ch, pid, net, body, inc in R.flat():
        if t > t1:
            break
        # [m: 1052's entries come six times over at one time] a replay holds a packet once for every observer it was
        # sent to: the same packet (kind, unit, bytes) again in the same frame is the same packet
        if t != frame_t:
            frame_t, frame_seen = t, set()
        sig = (pid, net, body)
        if t >= t0 and pid not in (61, 287, 239):         # the copies' bytes differ (each packet's own byte table): by content
            pv = R.parse(pid, body)
            if pv is not None:
                sig = (pid, net, json.dumps(pv, sort_keys=True))
        if sig in frame_seen and pid not in (61,):
            continue
        frame_seen.add(sig)
        if pid == 61:
            v = R.parse(pid, body)
            try:
                es = waypoints.parse(bytes.fromhex(v['+0x18']['text']))
            except Exception:
                es = []
            for e in es:
                if e['net'] in heroes:
                    pts = [(waypoints.CENTER[0] + x * waypoints.CELL, waypoints.CENTER[1] + z * waypoints.CELL) for x, z in e['points']]
                    ins.append((t, 'teleport' if e['teleport'] is not None else 'move', e['net'], pts))
                elif e['net'] in minions and e['points']:
                    x, z = e['points'][0]
                    ins.append((t, 'minion_at', e['net'], (waypoints.CENTER[0] + x * waypoints.CELL, waypoints.CENTER[1] + z * waypoints.CELL)))
        elif pid == 287 and minions:
            # [m] a lane minion's health as the real server replicated it (lane_minion mHP / mMaxHP)
            v = R.parse(pid, body)
            try:
                units = replication.parse(bytes.fromhex(v['+0x20']['text'])) if v else []
            except Exception:
                units = []
            for n, groups in units:
                if n in minions:
                    try:
                        vals = repl16.read_unit(groups, 'lane_minion')
                    except Exception:
                        continue
                    if 'mHP' in vals:
                        ins.append((t, 'minion_hp', n, (vals['mHP'], vals.get('mMaxHP'))))
        elif pid == 626:
            # [m] a jungle plant grows: where and which is Riot's random pick among Plants.lua's spots (the map's
            # dice, like the minions' identities) - the test takes it; what the plant does is ours (core/plants.py).
            # A fruit (PlantHealthPack) is the Honeyfruit's own doing
            v = R.parse(pid, body) or {}
            try:
                name = bytes.fromhex(v['+0x38']['text']).rstrip(b'\0').decode()
            except Exception:
                name = ''
            p3 = vec3(v.get('+0x1c'))
            if name.startswith('Plant') and name != 'PlantHealthPack' and p3 and net not in plants_seen:
                plants_seen.add(net)
                ins.append((t, 'plant', net, (name, (p3[0], p3[2]))))
        elif pid == 1215 and net in heroes:
            v = R.parse(pid, body) or {}
            c = v.get('+0x18') or {}
            try:
                slot = int(c.get('+0x60', 'ff'), 16)
            except ValueError:
                slot = 255
            if slot <= 14:
                aim, end = vec3(c.get('+0x40')), vec3(c.get('+0xac'))
                place = aim if aim and aim[0] > 200 and aim[2] > 200 else end
                tl = c.get('+0x8') or []
                target = u32(tl[0].get('+0x8')) if tl and isinstance(tl[0], dict) else 0
                ins.append((t, 'cast', net, (slot, (place[0], place[2]) if place else None, target, u32(c.get('+0x18')))))
        elif pid == 63 and net in heroes:
            # [m] what the player bought (BuyItemAns: +0x18 +0x18 the item, +0x70 its slot) - a choice, like a cast
            v = R.parse(pid, body) or {}
            it = v.get('+0x18') or {}
            ins.append((t, 'buy', net, u32(it.get('+0x18'))))
        elif pid == 447 and net in heroes:
            # [m] a champion's 447 is its player's attack order on a champion (sent before any attack, 0 when given
            # up) - an input like a move
            v = R.parse(pid, body) or {}
            if not os.environ.get('GOLDEN_NO_TARGETS'):
                ins.append((t, 'target', net, u32(v.get('+0x10'))))
        elif pid == 810 and net in heroes:
            # [m] NPC_UpgradeSpellAns: +0x11 the new rank, +0x12 the slot - the player's choice of what to level
            v = R.parse(pid, body) or {}
            try:
                ins.append((t, 'skill', net, (int(v['+0x12'], 16), int(v['+0x11'], 16))))
            except Exception:
                pass
        elif pid == 1196 and net in heroes:
            v = R.parse(pid, body) or {}
            if v.get('+0x16') == '01':                   # [m: the live sells] a slot sold
                ins.append((t, 'sell', net, int(v.get('+0x14', '00'), 16)))
        elif pid == 906 and net in heroes:
            # [m] 906 +0x10: +0x8 the attack counter, +0x10 the target's place, +0x20 the target (reading +0x8 as the
            # target made every puppet attack the unit nearest to itself - never a champion, rarely the minion hit)
            v = R.parse(pid, body) or {}
            a = v.get('+0x10') or {}
            place = vec3(a.get('+0x10'))
            # +0x48: where the attacker stands as its attack begins [m: 4,432 of 4,432 have it]
            me = struct.unpack('<ff', bytes.fromhex(v['+0x48'])) if isinstance(v.get('+0x48'), str) and len(v['+0x48']) == 16 else None
            ins.append((t, 'attack', net, (u32(a.get('+0x20')) if isinstance(a.get('+0x20'), str) else 0,
                                           (place[0], place[2]) if place else None, me)))
        if t >= t0 and pid not in spectator and pid not in (239, 755):
            # [m: the live recording of a player's own match, same minutes] 755 is never sent to a player, and damage
            # (150) only when a champion deals or takes it - the replay is a spectator's stream and has every unit's
            if pid == 150:
                v = R.parse(pid, body) or {}
                if net not in heroes and u32(v.get('+0x1c') if isinstance(v.get('+0x1c'), str) else '') not in heroes:
                    continue
                theirs.append((t, pid, net, v.get('+0x2c'), u32(v.get('+0x1c')) if isinstance(v.get('+0x1c'), str) else 0))
                continue
            if pid in (10, 584) and PLAYER is not None:
                v = R.parse(pid, body) or {}
                if pid == 584:
                    theirs.append((t, pid, net, ('fx', u32(v.get('+0x14')) if isinstance(v.get('+0x14'), str) else 0)))
                    continue
                units, ids = set(), set()
                for grp in v.get('+0x10') or []:
                    for inst in (grp.get('+0x10') or []) if isinstance(grp, dict) else []:
                        if isinstance(inst, dict):
                            units |= {u32(inst.get(k)) for k in ('+0x18', '+0x34') if isinstance(inst.get(k), str)}
                            ids.add(u32(inst.get('+0x38')) if isinstance(inst.get('+0x38'), str) else 0)
                theirs.append((t, pid, net, ('fx', frozenset(units - {0}), frozenset(ids - {0}))))
                continue
            if pid == 264:
                v = R.parse(pid, body) or {}
                try:
                    theirs.append((t, pid, net, (u32(v.get('+0x18')), int(v.get('+0x15', '00'), 16))))
                except Exception:
                    theirs.append((t, pid, net))
                continue
            theirs.append((t, pid, net))
    return ins, theirs


LAST_GAME = None
KEEP_BODY = {}                   # pid -> True: keep our packets' bodies too (analysis tools)


def frame_times(R, t1, frame=0.0334113):
    """the real server's frame moments up to t1: every packet time, the frames without packets put back evenly in the
    gaps (a 0.067 s gap = two frames)"""
    ts = sorted({round(r[0], 4) for r in R.rows if 0.0 < r[0] <= t1})
    out, prev = [], 0.0
    for t in ts:
        gap = t - prev
        n = max(1, int(round(gap / frame)))
        out += [prev + gap * i / n for i in range(1, n + 1)]
        prev = t
    return out


def minion_idents(R, t1):
    """replay minion net -> its identity (barracks, kind, wave, number within them) [m: 439 +0x14 barracks, +0x18 kind,
    +0x1c the minion, +0x20 wave]: our server spawns the same minions at the same times (checked: every barracks,
    kind and wave within 0.15 s), so the identity names the same minion in both matches"""
    out, n = {}, collections.Counter()
    for t, ch, pid, net, body, inc in R.flat(ids=(439,)):
        if t > t1:
            break
        v = R.parse(pid, body) or {}
        me = u32(v.get('+0x1c')) if isinstance(v.get('+0x1c'), str) else net
        if me in out:
            continue
        key = (v.get('+0x14'), v.get('+0x18'), v.get('+0x20'))
        out[me] = key + (n[key],)
        n[key] += 1
    return out


PLAYER = int(os.environ['GOLDEN_PLAYER']) if os.environ.get('GOLDEN_PLAYER') else None


def team_sight(R, t1):
    """{team '01' | '02': {net: [(t enter, t leave)]}} from the spectator's 723 / 1195 [m: +0x10 the team]"""
    out = {'01': collections.defaultdict(list), '02': collections.defaultdict(list)}
    open_ = {}
    for t, ch, pid, net, body, inc in R.flat(ids=(723, 1195)):
        if t > t1:
            break
        tm = (R.parse(pid, body) or {}).get('+0x10')
        if tm not in out:
            continue
        k = (tm, net)
        if pid == 723:
            open_.setdefault(k, t)
        elif k in open_:
            out[tm][net].append((open_.pop(k), t))
    for (tm, net), t0 in open_.items():
        out[tm][net].append((t0, 1e9))
    return out


def player_view(R, theirs, nets, player, t1):
    """the replay's packets a player's client gets [m: the live recording - a player gets 47 % of a spectator's
    packets]: about its team's units, about the units its team sees at that moment (723 / 1195), the global ones;
    damage (150) only when its champion deals or takes it, the role quest progress (264) only for its position"""
    me = nets[player]
    team = '01' if player < 5 else '02'
    mine = set(nets[:5] if player < 5 else nets[5:])
    both = team_sight(R, t1)
    sight = both[team]
    tracked = set(both['01']) | set(both['02'])        # units whose sight the server keeps (not missiles, not 0)
    role = ROLES_BY_SLOT[player % 5]
    lo, hi = (1, 5) if player < 5 else (6, 10)
    kept_fx = set()
    all_fx = {i for x in theirs if x[1] == 10 and len(x) > 3 for i in x[3][2]}
    out = []
    for x in theirs:
        t, pid, net = x[:3]
        if pid == 150:
            if net != me and (len(x) < 5 or x[4] != me):
                continue
        elif pid == 818:
            # [m: live, 254 of 254] a player is told its own champion's gold gains only
            if net != me:
                continue
        elif pid == 264:
            # [m: live] a player gets its own progress only (+0x15 = 1 - 5 for team 1, 6 - 10 for team 2; +0x18 role)
            if len(x) < 4 or x[3] != (role, True) and not (x[3][0] == role and lo <= x[3][1] <= hi):
                continue
        elif pid == 10 and len(x) > 3:
            # [m: live - a player gets effects of enemy champions too] an effect goes when its caster or the unit it is
            # bound to is its team's or seen by its team (the server's own rule: effects.seen); its 584 follows it
            us = x[3][1]
            if us and not any(u in mine or (u in sight and any(a <= t <= b for a, b in sight[u])) or u not in tracked
                              for u in us):
                continue
            kept_fx.update(x[3][2])
        elif pid == 584 and len(x) > 3:
            if x[3][1] not in kept_fx and x[3][1] in all_fx:
                continue
        elif net and net not in mine and net in tracked:
            if not any(a <= t <= b for a, b in sight.get(net, ())):
                continue
        out.append(x[:4] if pid == 150 else x[:3])     # damage keeps the name it carries (the strict line)
    return out


# [m: every replay] the champions' order: top, jungle, mid, bottom, support in each team; 264's position ids
ROLES_BY_SLOT = (0, 1, 2, 3, 4)


def monster_names(R, t1):
    """replay monster net -> its name "<Character>.<camp>.<index>" (568 +0x10) [m: the same naming as ours]"""
    import replaydb16 as RD
    out = {}
    for t, ch, pid, net, body, inc in R.flat(ids=(568,)):
        if t > t1:
            break
        v = R.parse(pid, body) or {}
        nm = RD.text(v.get('+0x10') or {})
        if nm:
            out[net] = nm
    return out


def runes_of(R, heroes):
    """each champion's rune page [m: the tooltips' kind-5 entries at 0 s list its six runes and three shards in page
    order, then a hidden one]: the player's choice, an input like the champion"""
    out = {}
    for t, ch, pid, net, body, inc in R.flat(ids=(1052,)):
        if t > 5.0:
            break
        for e in (R.parse(pid, body) or {}).get('+0x10') or []:
            if isinstance(e, dict) and u32(e.get('+0x8')) == 5:
                c, i = u32(e.get('+0xc')), u32(e.get('+0x28'))
                if c in heroes and i not in out.setdefault(c, []):
                    out[c].append(i)
    return {c: ids[:9] for c, ids in out.items() if len(ids) >= 9}


def roles_of(R, heroes):
    """each champion's position, from the role quest buff it starts with [m: 435 at 0 s - tooltips.QUESTS; a jungler's
    95f8870a, a support's 9995dd05 / a40c9e0f]: the player's choice, an input like the champion"""
    by_hash = {'f424ae05': 'TOP', '6402ae09': 'MIDDLE', 'f41aae09': 'BOTTOM', '95f8870a': 'JUNGLE', '9995dd05': 'UTILITY',
               'a40c9e0f': 'UTILITY'}
    out = {}
    for t, ch, pid, net, body, inc in R.flat(ids=(435,)):
        if t > 2.0:
            break
        if net in heroes and net not in out:
            v = R.parse(pid, body) or {}
            if v.get('+0x64') in by_hash:
                out[net] = by_hash[v['+0x64']]
    return out


def run(gid, t0, t1):
    import replaydb16 as RD
    from core.session import Session
    from core.game import DT
    from core import packets as P
    R = RD.Replay(os.path.join(DATA, 'rofl', f'{gid}.rofl'))
    found = R.heroes
    nets = sorted(n for n in found if n < 0x40000100)[:10]      # the ten champions (a pet / clone casting under its name has a later id)
    if len(nets) != 10:
        print(f'{len(nets)} champions recognised in the replay (10 needed for a roster): {[found[n]["champion"] for n in nets]}')
    roles = roles_of(R, set(nets))
    perks = runes_of(R, set(nets))
    roster = [{'champion': found[n]['champion'], 'role': roles.get(n), 'perks': perks.get(n)} for n in nets][:10] + [{} for _ in range(max(0, 10 - len(nets)))]
    their_minions = minion_idents(R, t1)
    their_monsters = monster_names(R, t1)
    synced = dict(their_minions)
    synced.update({n: ('monster', nm) for n, nm in their_monsters.items()})
    ins, theirs = inputs_of(R, set(nets), t0, t1, synced if not os.environ.get('GOLDEN_FREE_MINIONS') else ())
    if PLAYER is not None:
        theirs = player_view(R, theirs, nets, PLAYER, t1)
    logs = []
    player = PLAYER if PLAYER is not None else None
    # the spectator's match still works out both teams' sight for the game's own rules (core/vision.py: who may aim at
    # whom, Umbral Glaive's unseen buffs); GOLDEN_SIGHT=0 = none
    opts = {'no_fog': True, 'team_sight': os.environ.get('GOLDEN_SIGHT', '1') != '0'} if player is None else {'player_slot': player}
    s = Session(roster, log=logs.append, options=opts)
    g = s.game
    global LAST_GAME
    LAST_GAME = g                                        # analysis tools: our match after the run
    g.start_packets()
    for h in g.heroes:
        h.brain = None
    # [m: live, 2838 of 2838] a player's client is told only the damage its own champion deals or takes; a replay is a
    # spectator's stream with every champion's: our server watches all ten here
    g.watch = {h.net for h in g.heroes} if player is None else {g.heroes[player].net}
    mine = {n: g.heroes[i] for i, n in enumerate(nets[:10])}         # the replay's champion -> our puppet
    our_minions, ident_n, known = {}, collections.Counter(), set()   # identity -> our minion's net
    their_plants = {}                                                # the replay's plant -> ours
    back = {h.net: n for n, h in mine.items()}
    ours, stats = [], collections.Counter()
    k = 0
    as_log, as_next = [], t0      # GOLDEN_AS: our champions' bonus attack speed every second, for tools/as_audit16.py
    # [m: every packet of a replay carries its frame's time] the real server's frames in this match (33 - 34 ms, now and
    # then a long one): ours are stepped on the same moments - the frame clock is the machine's, not the game's, and the
    # scripts count frames (an update every 8) [GOLDEN_FIXED_FRAMES=1: our regular frames]
    frames = [] if os.environ.get('GOLDEN_FIXED_FRAMES') else frame_times(R, t1 + 1.0)
    g.real_frames = bool(frames)
    fi = 0
    while g.t < t1:
        while fi < len(frames) and frames[fi] <= g.t + 1e-6:
            fi += 1
        dt = frames[fi] - g.t if fi < len(frames) else DT
        if os.environ.get('GOLDEN_AS') and g.t >= as_next:
            as_next += 1.0
            as_log += [(round(g.t, 3), n, round(h.as_bonus, 4), h.level, h.alive) for n, h in mine.items()]
        while k < len(ins) and ins[k][0] <= g.t:
            t, kind, net, data = ins[k]
            k += 1
            if kind == 'plant':
                if getattr(g, 'plants', None) is not None:
                    p = g.plants.spawn(*data)
                    if p is not None:
                        their_plants[net] = p
                        stats['plants'] += 1
                continue
            if kind in ('minion_at', 'minion_hp'):
                # the test keeps the lanes the replay's [user 10-12: option A]: our minion of the same identity is put
                # where the real one stood (> 150 off) and given its health - the lane's fights are then the same; a
                # monster by its name (the camps the same way)
                if net in their_monsters:
                    m = next((u for u in reversed(g.monsters) if getattr(u, 'spawn_name', None) == their_monsters[net]), None)
                else:
                    m = g.units.get(our_minions.get(their_minions.get(net)))
                if m is None or not m.alive:
                    continue
                if kind == 'minion_at':
                    if ((m.pos[0] - data[0]) ** 2 + (m.pos[1] - data[1]) ** 2) ** 0.5 > float(os.environ.get('GOLDEN_MINION_SYNC', 75)):
                        m.pos = (float(data[0]), float(data[1]))
                        m.spot = None
                        stats['minion place syncs'] += 1
                else:
                    hp, mx = data
                    if mx:
                        m.max_hp = float(mx)
                    if hp > 0 and abs(m.hp - hp) > 1.0:
                        m.set_hp(hp)
                        stats['minion health syncs'] += 1
                continue
            h = mine.get(net)
            if h is None or (not h.alive and kind not in ('buy', 'sell', 'skill')):
                continue                                 # [the replays] a dead champion still shops
            if kind in ('move', 'teleport'):
                if not data:
                    continue
                far = ((h.pos[0] - data[0][0]) ** 2 + (h.pos[1] - data[0][1]) ** 2) ** 0.5
                if kind == 'teleport' or far > 300.0:
                    if g.spells is not None:
                        g.spells.drop_dash(h)
                    h.teleport(data[0])
                    stats['resyncs' if kind == 'move' else 'teleports'] += 1
                if len(data) > 1:
                    h.order, h.target = None, None
                    h.cancel_attack()                    # a walk in the windup throws the attack away (its 515)
                    h.go(data[1:])
                elif h.order is None and h.path:
                    # [m] a one-point entry is the server telling where the champion stands - it is sent when an attack
                    # or cast begins too: not a new order (taking it for one threw away 47 of 266 attacks)
                    h.stop()
            elif kind in ('buy', 'sell') and os.environ.get('GOLDEN_NO_ITEMS'):
                continue
            elif kind == 'target':
                tg = mine.get(data)
                if tg is not None and tg.alive:
                    if h.target != tg.net:
                        h.order_attack(tg.net)
                        stats['champion attack orders'] += 1
                elif data == 0 and h.target is not None and h.target in back:
                    h.order, h.target = None, None
                continue
            elif kind == 'skill':
                slot, rank = data
                if 0 <= slot <= 3:
                    guard = 0
                    while h.spell_levels[slot] < rank and guard < 6:
                        guard += 1
                        if not h.level_spell(slot):
                            # our champion has no point for it yet (its experience is behind): the level it needs
                            h.add_xp(g.data['xp_per_level'][min(16, h.level)] - h.xp + 1)
                            stats['skill levels forced'] += 1
                    stats['skills'] += 1
                continue
            elif kind == 'buy':
                # the player's purchase, made by our shop's own rules (recipe, components, stats); the gold is the
                # puppet's help, like its cooldowns and mana: our match's income is not the replay's
                it = g.shop.db.get(data) if g.shop is not None else None
                if it is None or not it['in_store']:
                    continue                             # given by the server itself (the role quest's item)
                import core.shop as SH
                cost, _ = SH.price(data, h.inventory)
                h.gold = max(h.gold, float(cost))
                ans = g.shop.buy(h, data, anywhere=True)      # the player's purchase: our puppet may stand elsewhere
                stats['buys done' if ' buys ' in str(ans) else 'buys refused'] += 1
                if ' buys ' not in str(ans) and stats['buys refused'] <= 3:
                    logs.append(f'puppet buy refused: {ans}')
            elif kind == 'sell':
                if g.shop is not None:
                    g.shop.sell(h, data, anywhere=True)
                    stats['sells'] += 1
            elif kind == 'cast' and (t >= t0 or not os.environ.get('GOLDEN_LATE_INPUTS')):
                slot, place, target, name_hash = data
                if slot <= 3:
                    while h.spell_levels[slot] < 1:
                        if not h.level_spell(slot):
                            h.add_xp(g.data['xp_per_level'][min(16, h.level)] - h.xp + 1)
                            if not h.level_spell(slot):
                                break
                    h.cooldowns[slot] = 0.0
                    h.slot_names[slot] = h.slot_names[slot]
                h.casting_until = 0.0
                h.set_par(h.max_par)
                tg = mine.get(target)
                ans = g.spells.request(h, {'slot': slot, 'target': tg.net if tg else 0, 'target_place': place or h.pos,
                                           'cursor': place or h.pos, 'caster_place': h.pos, 'flags': 0,
                                           'hash': name_hash if slot >= 6 else 0})
                stats['item casts asked' if slot >= 6 else 'casts asked'] += 1
                stats['item casts done' if slot >= 6 else 'casts done'] += (' uses ' in str(ans) or 'recall' in str(ans).lower())                     if slot >= 6 else ' casts ' in str(ans)
            elif kind == 'attack' and (t >= t0 or not os.environ.get('GOLDEN_LATE_INPUTS')):
                tnet, there, me = data
                tg = mine.get(tnet)
                if tg is None and tnet in their_monsters:
                    tg = next((u for u in reversed(g.monsters) if getattr(u, 'spawn_name', None) == their_monsters[tnet]
                               and u.alive), None)
                    if tg is not None:
                        stats['attacks at the same monster'] += 1
                if tg is None and tnet in their_plants:
                    tg = their_plants[tnet] if their_plants[tnet].targetable else None
                    stats['attacks at a plant'] += 1
                if tg is None and tnet in their_minions:
                    tg = g.units.get(our_minions.get(their_minions[tnet]))
                    if tg is not None and tg.alive:
                        stats['attacks at the same minion'] += 1
                    else:
                        tg = None
                if tg is None and there is not None:
                    # a minion, a monster or a structure: ours have other ids - our enemy unit nearest to the place the
                    # real target stood
                    near = [(((u.pos[0] - there[0]) ** 2 + (u.pos[1] - there[1]) ** 2) ** 0.5, u) for u in g.units.values()
                            if u.alive and u.targetable and u.team != h.team and not u.is_hero]
                    near = [x for x in near if x[0] <= 300.0 + x[1].radius]
                    tg = min(near, key=lambda x: x[0])[1] if near else None
                if tg is not None and tg.alive:
                    if me is not None and not h.in_reach(tg) and ((tg.pos[0] - me[0]) ** 2 + (tg.pos[1] - me[1]) ** 2) ** 0.5 <= h.reach(tg) + 25.0:
                        # the real champion began this attack from there (its 906): ours, a little off, is put there
                        # instead of walking up to it - the minions' place sync's rule for a champion's attack
                        h.pos, h.path = (float(me[0]), float(me[1])), None
                        stats['attack place syncs'] += 1
                    h.order_attack(tg.net)
                    stats['attacks ordered'] += 1
                else:
                    stats['attacks with no unit of ours near'] += 1
                    if there is not None and os.environ.get('GOLDEN_WHY'):
                        far = min((((u.pos[0] - there[0]) ** 2 + (u.pos[1] - there[1]) ** 2) ** 0.5 for u in g.units.values()
                                   if u.alive and u.team != h.team and not u.is_hero and u.kind == 'minion'), default=99999)
                        logs.append(f'nounit {t:.1f} {h.name} {far:.0f}')
        for m in g.minions:                              # our minions spawned this frame: their identities
            if m.net not in known:
                known.add(m.net)
                key = (P.u32(m.barracks_net), f'{m.mtype:02x}', f'{m.wave & 0xff:02x}')
                our_minions[key + (ident_n[key],)] = m.net
                g.golden_idents = getattr(g, 'golden_idents', {})
                g.golden_idents[m.net] = key + (ident_n[key],)
                ident_n[key] += 1
        for ch, pid, net, body in g.step(dt):
            if g.t >= t0 and pid == 239:
                # our containers opened like the replay's (R.flat): a 626 spawn, a minion's 439 travel inside one
                for p2, n2, b2 in R.inner(R.parse(239, body) or {}):
                    ours.append((g.t, p2, back.get(n2, n2)))
                continue
            if g.t >= t0 and pid != 239:
                if pid == 150 and not KEEP_BODY.get(pid):
                    ours.append((g.t, pid, back.get(net, net), (R.parse(150, body) or {}).get('+0x2c')))
                    continue
                ours.append((g.t, pid, back.get(net, net)) + ((body,) if KEEP_BODY.get(pid) else ()))
    if as_log:
        os.makedirs(OUT, exist_ok=True)
        json.dump(as_log, open(os.path.join(OUT, f'as_{gid}.json'), 'w'))
    return theirs, ours, stats, set(nets), [found[n]['champion'] for n in nets], logs


STRICT = -150                    # the strict damage row: kind, champion, time AND the spell / attack name it carries


def pair_counts(theirs, ours, heroes):
    """{pid: [replay, ours, paired within TOL]} by kind (+ the champion it is about); STRICT: damage (150) paired only
    when it also carries the same name (+0x2c) - the content check, not only the moment"""
    A, B = collections.defaultdict(list), collections.defaultdict(list)
    for side, rows in ((A, theirs), (B, ours)):
        for x in rows:
            t, pid, net = x[:3]
            who = net if net in heroes else -1
            side[(pid, who)].append(t)
            if pid == 150 and len(x) > 3:
                side[(STRICT, who, x[3])].append(t)
    per = collections.defaultdict(lambda: [0, 0, 0])
    for key in set(A) | set(B):
        a, b = sorted(A.get(key, [])), sorted(B.get(key, []))
        i = j = m = 0
        while i < len(a) and j < len(b):
            if abs(a[i] - b[j]) <= TOL:
                m, i, j = m + 1, i + 1, j + 1
            elif a[i] < b[j]:
                i += 1
            else:
                j += 1
        p = per[key[0]]
        p[0], p[1], p[2] = p[0] + len(a), p[1] + len(b), p[2] + m
    return dict(per)


def compare(theirs, ours, heroes):
    names = json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'packet_names16.json')))
    per = pair_counts(theirs, ours, heroes)
    strict = per.pop(STRICT, [0, 0, 0])
    rows = sorted(per.items(), key=lambda x: -x[1][0])
    tot = [sum(p[i] for _, p in rows) for i in range(3)]
    lines = [f'{tot[0]} packets in the replay, {tot[1]} from our server, {tot[2]} pair up within {TOL} s = '
             f'{100.0 * tot[2] / max(1, tot[0]):.1f} % of the replay reproduced; {sum(1 for _, p in rows if p[0] and not p[1])} kinds '
             f'the replay has and we never send, {sum(1 for _, p in rows if p[1] and not p[0])} kinds only we send', '',
             f'damage (150) paired with the same spell / attack name too: {strict[2]} of {strict[0]} = '
             f'{100.0 * strict[2] / max(1, strict[0]):.1f} % (by moment only: {per.get(150, [0, 0, 0])[2]})', '',
             f'{"id":>5} {"name":34s} {"replay":>7} {"ours":>7} {"paired":>7}   share']
    for pid, (a, b, m) in rows:
        lines.append(f'{pid:5d} {names.get(str(pid), "?")[:34]:34s} {a:7d} {b:7d} {m:7d}   {100.0 * m / a:5.1f} %' if a else
                     f'{pid:5d} {names.get(str(pid), "?")[:34]:34s} {a:7d} {b:7d} {m:7d}   only ours')
    return lines


def one(args):
    gid, t0, t1 = args
    try:
        theirs, ours, stats, heroes, champs, logs = run(gid, t0, t1)
    except Exception as e:
        return gid, None, repr(e)[:200]
    return gid, pair_counts(theirs, ours, heroes), ', '.join(champs)


def batch(n, t0, t1, workers=int(os.environ.get('GOLDEN_WORKERS', '4'))):
    """the test over the first n replays -> golden16/summary.txt (every kind's totals, each replay's share)"""
    import multiprocessing as mp
    names = json.load(open(os.path.join(ROOT, 'data', 'exe1620', 'packet_names16.json')))
    gids = sorted(f[:-5] for f in os.listdir(os.path.join(DATA, 'rofl')) if f.endswith('.rofl'))[:n]
    tot = collections.defaultdict(lambda: [0, 0, 0])
    lines = []
    with mp.Pool(workers) as pool:
        for gid, per, info in pool.imap_unordered(one, [(g, t0, t1) for g in gids]):
            if per is None:
                lines.append(f'{gid}: failed {info}')
                continue
            a, b, m = (sum(p[i] for k, p in per.items() if k != STRICT) for i in range(3))
            lines.append(f'{gid}: {100.0 * m / max(1, a):5.1f} %  ({a} replay / {b} ours / {m} paired)  {info}')
            print(lines[-1], flush=True)
            for pid, p in per.items():
                for i in range(3):
                    tot[pid][i] += p[i]
    strict = tot.pop(STRICT, [0, 0, 0])
    a, b, m = (sum(p[i] for p in tot.values()) for i in range(3))
    head = [f'{len(gids)} replays, game seconds {t0:.0f} - {t1:.0f}: {100.0 * m / max(1, a):.1f} % of their packets reproduced '
            f'({a} replay / {b} ours / {m} paired within {TOL} s)',
            f'damage (150) paired with the same spell / attack name too: {strict[2]} of {strict[0]} = '
            f'{100.0 * strict[2] / max(1, strict[0]):.1f} % (by moment only: {tot.get(150, [0, 0, 0])[2]})', ''] + sorted(lines) + ['', f'{"id":>5} {"name":34s} {"replay":>8} {"ours":>8} {"paired":>8}   share']
    for pid, (x, y, z) in sorted(tot.items(), key=lambda kv: -kv[1][0]):
        head.append(f'{pid:5d} {names.get(str(pid), "?")[:34]:34s} {x:8d} {y:8d} {z:8d}   ' + (f'{100.0 * z / x:5.1f} %' if x else 'only ours'))
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, os.environ.get('GOLDEN_SUMMARY', 'summary.txt')), 'w', encoding='utf-8').write(chr(10).join(head) + chr(10))
    print(head[0])


def main():
    argv = sys.argv[1:]
    if argv and argv[0] == 'batch':
        t0 = float(argv[argv.index('--from') + 1]) if '--from' in argv else 90.0
        t1 = float(argv[argv.index('--to') + 1]) if '--to' in argv else 300.0
        return batch(int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 12, t0, t1)
    if not argv or argv[0] == 'list':
        print(' '.join(sorted(f[:-5] for f in os.listdir(os.path.join(DATA, 'rofl')) if f.endswith('.rofl'))[:200]))
        return
    gid = argv[0]
    t0 = float(argv[argv.index('--from') + 1]) if '--from' in argv else 90.0
    t1 = float(argv[argv.index('--to') + 1]) if '--to' in argv else 300.0
    theirs, ours, stats, heroes, champs, logs = run(gid, t0, t1)
    lines = [f'replay {gid}, game seconds {t0:.0f} - {t1:.0f}; champions: {", ".join(champs)}',
             'puppets: ' + ', '.join(f'{k} {v}' for k, v in sorted(stats.items()))] + compare(theirs, ours, heroes)
    errs = [x for x in logs if 'template' in x or 'Traceback' in x]
    if errs:
        lines += ['', f'{len(errs)} server errors, e.g. {errs[0][:160]}']
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, f'{gid}.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:80]))


if __name__ == '__main__':
    main()
