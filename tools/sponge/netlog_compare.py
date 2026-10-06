"""Our server's stream next to Riot's: what each sends, when, with what values.

Ours: a .banl written by `server.exe --netlog <file>` (a match, or `--simulate S`): "BANL", u32 version, then records
i64 tick, u8 channel, u32 length, the message (common/include/ba/Protocol.h). Riot's: the 13.3 replay, each packet
read by the client's own deserializer (tools/sponge/packet_emu.py), fields in clear.

  netlog_compare.py waves <ours.banl>        minion waves: when, how many, per barracks / team
  netlog_compare.py kinds <ours.banl>        our message kinds: count, first / last second
"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TICK = 0.033
MSG = {1: 'Hello', 2: 'MoveOrder', 3: 'AttackOrder', 4: 'SpawnDummy', 5: 'CastSpell', 6: 'LevelSpell', 7: 'BuyItem',
       8: 'SellItem', 9: 'UseItem', 64: 'Welcome', 65: 'UnitSpawn', 66: 'Waypoints', 67: 'UnitHealth', 68: 'UnitAttack',
       69: 'Missile', 70: 'UnitDeath', 72: 'UnitRemove', 71: 'UnitHit', 73: 'UnitRespawn', 74: 'GameEnd', 75: 'UnitStats',
       76: 'UnitSpells', 77: 'SpellCast', 78: 'BuffChange', 79: 'SkillMissile', 80: 'SkillMissileEnd', 81: 'Dash',
       82: 'Effect', 83: 'Animation', 84: 'GroundEffect', 85: 'UnitItems'}


def read_banl(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'BANL', 'not a netlog'
    at = 8
    while at + 13 <= len(d):  # a server killed mid-write leaves a cut record at the end: stop there
        tick, ch, n = struct.unpack_from('<qBI', d, at)
        at += 13
        if at + n > len(d):
            break
        yield tick, ch, d[at:at + n]
        at += n


class R:
    def __init__(self, b):
        self.b, self.at = b, 1

    def get(self, fmt):
        v = struct.unpack_from('<' + fmt, self.b, self.at)
        self.at += struct.calcsize('<' + fmt)
        return v if len(v) > 1 else v[0]

    def str(self):
        n = self.get('H')
        s = self.b[self.at:self.at + n].decode('utf-8', 'replace')
        self.at += n
        return s


def our_spawns(path):
    """(seconds, id, team, character) of every UnitSpawn"""
    for tick, ch, m in read_banl(path):
        if m[0] == 65:
            r = R(m)
            uid, team = r.get('I'), r.get('B')
            yield tick * TICK, uid, team, r.str()


def riot_minion_spawns():
    """(seconds in the packet, net id, barracks net id, the other fields) of every packet 98 (BarrackSpawnUnit)"""
    import packet_emu as pe
    t = pe.table()
    emu = pe.Emu()
    for tm, ch, pid, obj, body in pe.packets(pe.ROFL, 98):
        tr = {}
        emu.deserialize(t[98], 98, obj, body, tr)
        f = {off: raw for off, raw, hid, w in pe.plain_fields(tr['writes_obj'], t[98]['size'])} if 'writes_obj' in tr else None
        if f is None:
            p, n = tr['blocks'][0]
            local = [(w, a - p, s, v) for w, a, s, v in tr['writes'] if p <= a < p + n]
            f = {off: raw for off, raw, hid, w in pe.plain_fields(local, n)}
        yield (struct.unpack('<f', f[0xc])[0], struct.unpack('<I', f[0x10])[0], struct.unpack('<I', f[0x1c])[0],
               f[0x14][0], f[0x15][0], struct.unpack('<H', f[0x16])[0], f[0x18][0], f[0x20][0])


def waves(path):
    ours = [s for s in our_spawns(path) if 'Minion' in s[3]]
    riot = list(riot_minion_spawns())

    def group(rows, key_t):
        out = []
        for r in sorted(rows, key=key_t):
            if out and key_t(r) - key_t(out[-1][-1]) < 5:
                out[-1].append(r)
            else:
                out.append([r])
        return out
    gw_o = group(ours, lambda r: r[0])
    gw_r = group(riot, lambda r: r[0])
    print(f'minions: ours {len(ours)} in {len(gw_o)} waves, Riot {len(riot)} in {len(gw_r)} waves')
    print(f'{"wave":>4} | {"Riot s":>8} {"n":>3} {"barracks":>8} {"+14/+15/+16/+18/+20 (first)":>28} | {"ours s":>8} {"n":>3}  types')
    for i in range(max(len(gw_o), len(gw_r))):
        a = gw_r[i] if i < len(gw_r) else None
        b = gw_o[i] if i < len(gw_o) else None
        ra = f'{a[0][0]:8.3f} {len(a):3d} {len({x[2] for x in a}):8d} {str(a[0][3:]):>28}' if a else ' ' * 50
        types = collections.Counter(x[3].replace('SRU_', '').replace('Minion', '') for x in b) if b else {}
        rb = f'{b[0][0]:8.3f} {len(b):3d}  ' + ' '.join(f'{k}:{v}' for k, v in sorted(types.items())) if b else ''
        print(f'{i + 1:4d} | {ra} | {rb}')


def kinds(path):
    c, first, last = collections.Counter(), {}, {}
    for tick, ch, m in read_banl(path):
        k = MSG.get(m[0], m[0])
        c[k] += 1
        first.setdefault(k, tick * TICK)
        last[k] = tick * TICK
    for k, n in c.most_common():
        print(f'{k:16} {n:8d}  first {first[k]:8.2f}  last {last[k]:8.2f}')


if __name__ == '__main__':
    {'waves': waves, 'kinds': kinds}[sys.argv[1]](sys.argv[2])
