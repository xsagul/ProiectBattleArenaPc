"""What the client holds about our world's units, set against what the server holds.

The client side is ba_host.dll's census (client-src/ba_host.c: a probe named "census ..." in game/ba_probes.txt
writes game/ba_census.log: once a second, for every net id of the ranges, pieces of the client's own object). The
server side is lnp_server.py's state log (environment WORLD_STATE_LOG=<file>: every second each lane minion's health,
place and target, and a line for every death). Both carry the wall clock, so they line up without guessing.

  census.py <match folder>            data/exe133/match_<name> with ba_census.log and world_state.txt
  census.py <match folder> find       also search the object for where it keeps its place (x, y, z floats)

Client object offsets used (13.3): +0x218 the "dead" flag (a guarded byte, read as the client's rva 0x15c030 does),
+0xe7c mHP, +0xe8c mMaxHP, +0xd04 mIsTargetable, +0x111c ActionState (the replicated values' slots: repl_names.json),
POS the unit's place (found with `find`).
"""
import collections
import math
import os
import struct
import sys

POS = 0x224          # x, y, z floats (`find` on match_census1: 697 of 778 samples; 0x1dc holds a second copy)


def guarded_byte(b):
    """a guarded byte as the client reads it (rva 0x15c030): [0] written flag, [1] count of key dwords, [2] count of
    key bytes, [3..] the key, [4] which of the kept values is current, [5 + that] the value"""
    n, m, idx = b[1], b[2], b[4]
    v = b[5 + (idx & 3)]
    if n:
        v ^= ~b[3] & 0xff
    if m == 1:
        v ^= ~b[3] & 0xff
    return v


def read_census(path):
    """[(unix seconds, {net: {offset: bytes}})]"""
    rounds = []
    for line in open(path):
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'T':
            rounds.append((int(parts[1]) / 1000.0, {}))
        elif rounds:
            net = int(parts[0], 16)
            pieces = {'ptr': int(parts[1], 16)}
            for p in parts[2:]:
                off, _, hx = p.partition(':')
                pieces[int(off, 16)] = bytes.fromhex(hx)
            rounds[-1][1][net] = pieces
    return rounds


def read_state(path):
    """([(unix seconds, game time, {net: (team, lane, kind, hp, x, z, target, flags)})], {net: (unix, game t, killer)})"""
    rounds, deaths = [], {}
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == 'T':
            rounds.append((int(p[1]) / 1000.0, float(p[2]), {}))
        elif p[0] == 'D':
            deaths[int(p[3], 16)] = (int(p[1]) / 1000.0, float(p[2]), int(p[4], 16))
        elif rounds:
            rounds[-1][2][int(p[0], 16)] = (p[1], p[2], p[3], float(p[4]), float(p[5]), float(p[6]), int(p[7], 16), p[8])
    return rounds, deaths


def piece(pieces, off, n):
    """n bytes at an object offset, from whichever dumped piece holds them"""
    for o, b in pieces.items():
        if isinstance(o, int) and o <= off and off + n <= o + len(b):
            return b[off - o:off - o + n]
    return None


def f32(pieces, off):
    b = piece(pieces, off, 4)
    return struct.unpack('<f', b)[0] if b else None


def main():
    folder = sys.argv[1]
    census = read_census(os.path.join(folder, 'ba_census.log'))
    state, deaths = read_state(os.path.join(folder, 'world_state.txt'))
    print(f'client rounds {len(census)}, server rounds {len(state)}, server deaths {len(deaths)}')
    if not census or not state:
        return
    times = [s[0] for s in state]

    def server_at(t):
        i = min(range(len(times)), key=lambda k: abs(times[k] - t))
        return state[i]

    if len(sys.argv) > 2 and sys.argv[2] == 'find':
        # where the object keeps its place: float pairs (x at o, z at o + 8) near the server's place of that unit
        votes = collections.Counter()
        n = 0
        for t, units in census:
            st = server_at(t)
            if abs(st[0] - t) > 0.6:
                continue
            for net, pieces in units.items():
                if net not in st[2]:
                    continue
                x, z = st[2][net][4], st[2][net][5]
                b = pieces.get(0)
                if not b:
                    continue
                n += 1
                for o in range(0, len(b) - 12):
                    fx, fz = struct.unpack_from('<f', b, o)[0], struct.unpack_from('<f', b, o + 8)[0]
                    if abs(fx - x) < 150 and abs(fz - z) < 150:
                        votes[o] += 1
        print('samples', n, 'offsets where (x, ?, z) is near the server place:', [(hex(o), c) for o, c in votes.most_common(12)])
        return

    kinds = {'04': 'melee', '05': 'caster', '06': 'cannon'}
    info = {}
    for _, _, units in state:
        for net, u in units.items():
            info.setdefault(net, u)
    game_of = lambda t: server_at(t)[1] + (t - server_at(t)[0])
    # 1. every death of the server: what the client holds afterwards
    print('\n--- units dead on the server: the client after the death (seconds after -> dead flag / mHP / in table)')
    still = 0
    for net, (td, gt, killer) in sorted(deaths.items(), key=lambda kv: kv[1][0]):
        row = []
        last_alive = None
        for t, units in census:
            if t < td - 1.2:
                continue
            p = units.get(net)
            dt = t - td
            if p is None:
                row.append(f'{dt:+.0f}:gone')
                break
            dead = guarded_byte(piece(p, 0x218, 10))
            hp = f32(p, 0xe7c)
            row.append(f'{dt:+.0f}:{"DEAD" if dead else "alive"}/{hp:.0f}')
            if not dead and dt > 1.5:
                last_alive = dt
        u = info.get(net, ('?', '?', '?'))
        flag = ''
        if last_alive is not None:
            still += 1
            flag = f'   <-- the client still has it alive {last_alive:.0f} s after its death'
        print(f'{net:#x} {u[0]:4s} {u[1]:3s} {kinds.get(u[2], u[2]):6s} died {gt:7.2f} by {killer:#x}: ' + ' '.join(row[:14]) + flag)
    print(f'{still} of {len(deaths)} dead units stay alive in the client')
    # 2. living units: the client's place against the server's
    print('\n--- living units: distance between the client\'s place and the server\'s, by round')
    worst = collections.defaultdict(list)
    for t, units in census:
        st = server_at(t)
        if abs(st[0] - t) > 0.6:
            continue
        for net, p in units.items():
            if net not in st[2] or net in deaths and deaths[net][0] < t:
                continue
            x, z = f32(p, POS), f32(p, POS + 8)
            if x is None:
                continue
            d = math.hypot(x - st[2][net][4], z - st[2][net][5])
            worst[net].append((st[1], d, (round(x), round(z)), (round(st[2][net][4]), round(st[2][net][5])), st[2][net][7]))
    far = 0
    for net, rows in sorted(worst.items()):
        bad = [r for r in rows if r[1] > 250]
        if bad:
            far += 1
            u = info.get(net, ('?', '?', '?'))
            print(f'{net:#x} {u[0]:4s} {u[1]:3s} {kinds.get(u[2], u[2]):6s}: {len(bad)} of {len(rows)} rounds more than 250 apart; '
                  + ' '.join(f'{r[0]:.0f}s:{r[1]:.0f}(client {r[2]} server {r[3]} {r[4]})' for r in bad[:4]))
    print(f'{far} of {len(worst)} living units were more than 250 away from the server\'s place at some time')


if __name__ == '__main__':
    main()
