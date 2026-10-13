"""Our world (server/world.py) run without a client, and every packet it writes read back through Riot's own reader
(pkt_schema.decode runs the client's packet reader in the emulator): a packet the reader refuses, or reads to other
values than we meant, shows here instead of in a crashed client.

  check_world.py [seconds=150]

A champion of the blue team is put next to the red mid outer turret from 100 s on (the turret must choose it and
attack), and at 120 s it "kills" that turret (the fall must open the inner turret).
"""
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'server'))
import lol_packets as LP  # noqa: E402
import pkt_schema as PS  # noqa: E402
import pkt_tree as PT  # noqa: E402
import replication as RP  # noqa: E402
import waypoints as Wp  # noqa: E402
import world as W  # noqa: E402

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
HERO = 0x4000001e
CODEC = os.path.join(ROOT, 'data', 'exe133', 'codec')


def main():
    w = W.World()
    print('templates that come out as the real bytes when unchanged:',
          {k: [r.exact for r in v] for k, v in w.real.items()})
    red_mid = next(tu for tu in w.turrets.values() if tu.name == 'Turret_T2_C_05_A')
    packets = collections.defaultdict(list)
    events = collections.Counter()
    hero_hits = []
    t, killed = 0.0, False
    stuck = collections.Counter()
    while t < SECONDS:
        if t >= 100:
            w.set_hero(HERO, 'blue', (red_mid.pos[0] - 500, red_mid.pos[1] - 400))
        if t >= 120 and not killed:
            killed = True
            for ch, data, what in w.hit(t, HERO, red_mid.net, 99999.0):
                packets[struct.unpack_from('<H', data)[0]].append((t, ch, data, what))
            # the jungle: one hit on the red buff (it must fight back), the raptor camp killed (it must return)
            for net, mo in list(w.monsters.items()):
                dmg = 50.0 if mo.name == 'SRU_Red4.1.1' else (99999.0 if 'Razorbeak' in mo.name and mo.camp == '3' else 0.0)
                if dmg:
                    for ch, data, what in w.hit(t, HERO, net, dmg):
                        packets[struct.unpack_from('<H', data)[0]].append((t, ch, data, what))
        for ch, data, what in w.tick(t):
            packets[struct.unpack_from('<H', data)[0]].append((t, ch, data, what))
        for ev in w.events:
            events[ev[0]] += 1
            if ev[0] == 'hero_hit':
                hero_hits.append((round(ev[1], 2), hex(ev[2]), round(ev[4], 1)))
        w.events = []
        t += 1 / 30
    # the end: the red base falls to the champion, turret after turret, then the nexus
    for tier in ('inner', 'inhibitor', 'dampener', 'nexus', 'hq'):
        for tu in list(w.turrets.values()):
            if tu.team == 'red' and tu.tier == tier and (tier in ('nexus', 'hq') or tu.lane == 'mid'):
                for ch, data, what in w.hit(t, HERO, tu.net, 99999.0):
                    packets[struct.unpack_from('<H', data)[0]].append((t, ch, data, what))
    for k in range(200):
        for ch, data, what in w.tick(t + k / 30):
            packets[struct.unpack_from('<H', data)[0]].append((t, ch, data, what))
    for ev in w.events:
        events[ev[0]] += 1
    print('match over, loser:', w.over)
    print('events:', dict(events), 'first hits on the champion:', hero_hits[:4])
    print('minions alive', len(w.minions), 'deaths', w.deaths, 'turrets fallen', w.turret_deaths,
          'open turrets', sorted(tu.name for tu in w.turrets.values() if tu.open))
    print('monsters', len(w.monsters), 'with new ids', sum(1 for n in w.monsters if n >= W.NET_BASE),
          '| bots:', [(b.champion, b.team[0], b.lane, round(b.hp), 'alive' if b.alive else 'dead',
                       tuple(round(c) for c in b.pos(t))) for b in w.bots.values()])
    print('what events said:', {k: v for k, v in events.items()})
    # a champion's death and return, as lnp_server.py builds them from the same templates
    f32 = struct.pack('<f', 12.5).hex()
    for key, change in (('herodeath_568', None), ('herodeath_780', {'+0xc': f32}),
                        ('herodeath_417', {'+0xc': f32, '+0x2c': struct.pack('<I', red_mid.net).hex()}),
                        ('herodeath_440', {'+0xc': struct.pack('<I', HERO).hex()}),
                        ('respawn_128', {'+0xc': struct.pack('<ff', 394.77, 461.57).hex(), '+0x14': struct.pack('<f', 0.0).hex()})):
        r = w.real[key][0]
        ch, data, what = r.packet(HERO, (lambda v, c=change: v.update(c)) if change else None, key)
        packets[r.pid].append((0.0, ch, data, key))
    bad = 0
    for pid in sorted(packets):
        items = packets[pid]
        if pid == 552:
            # through Riot's reader (the emulator): it must take the packet whole; the header's unit count (kept
            # coded in the object at +0xa: one code per count) must be the number of units we put in, and the
            # sequence value must never go down
            import packet_emu as P
            import sync552
            table, emu = P.table(), P.Emu()
            ok, codes, last, down, sizes = 0, {}, 0, 0, collections.Counter()
            for _, ch, data, what in items[:1500]:
                good, left, o = emu.deserialize(table[552], 552, 0, data[6:])
                if not (good and left == 0 and o):
                    print('     REFUSED by the reader:', what, data[:30].hex())
                    continue
                head_len = next(k for k in (3, 4, 5, 6, 7) if LP.split_552(data[6:]) and len(LP.split_552(data[6:])[0]) == k)
                n = len(LP.split_entries(LP.split_552(data[6:])[1]))
                sizes[n] += 1
                code = struct.unpack_from('<H', o, 0x0a)[0]
                value = sync552.value_of(o)
                down += value < last
                last = value
                if codes.setdefault(n, code) == code and list(codes.values()).count(code) == 1:
                    ok += 1
                else:
                    print(f'     count {n} read as code {code}, expected {codes[n]}: {what}')
            checked = min(len(items), 1500)
            print(f'{pid:4d} x{len(items):5d}  read back {ok} of the first {checked}; units per packet {dict(sorted(sizes.items()))}; '
                  f'value went down {down} times')
            bad += checked - ok + down
            continue
        if not os.path.exists(os.path.join(CODEC, f'{pid}.tree.json')):
            print(f'{pid:4d} x{len(items):5d}  no schema to read it back with')
            continue
        sc, tr = PS.Schema.load(pid), PT.Tree(pid)
        ok, sample, sizes = 0, None, collections.Counter()
        seen = set()
        for _, ch, data, what in items:
            key = data[6:]
            if key in seen:
                ok += 1
                continue
            v = PS.decode(tr, sc, data)
            if v is not None:
                ok += 1
                seen.add(key)
                sample = sample or (what, v)
                if pid == 595:
                    units = RP.parse(bytes.fromhex(v['+0xc']['text']))
                    sizes[len(units)] += 1
            else:
                print('     REFUSED by the reader:', what, data[:40].hex())
        bad += len(items) - ok
        print(f'{pid:4d} x{len(items):5d}  read back: {ok}   e.g. {sample[0] if sample else ""}: {json.dumps(sample[1])[:150] if sample else ""}')
    print('packets the reader refused:', bad)


if __name__ == '__main__':
    main()
