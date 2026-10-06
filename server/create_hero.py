"""Packet 79 = the creation of a champion, written by our server (13.3 client).

The client's handler (listener rva 0x355f80 case 79 -> rva 0x365650) logs "Spawn Champion Request {ChampionName}
[{#SummonerName}] SkinID({SkinID}) NetID({NetID})". The wire format comes from Riot's reader (rva 0x875990), learnt
mode by mode by server/pkt_codec.py into data/exe133/codec/79.json. Write-up: docs/MIGRARE_12.23.md
"Pachetul 79".

Fields (object offset in the packet; what the handler does with it, read in its code):
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pkt_codec as C  # noqa: E402

# name, offset, type, where it goes in the client (rva of the handler code / called function)
FIELDS = [
    ('net_id',      0x18, 'u32',  'NetID in the log; the new hero object'),
    ('champion',    0x20, 'str',  'ChampionName in the log; preloaded (rva 0x2e92d0) and created (rva 0x1a2d90)'),
    ('summoner',    0x30, 'str',  'SummonerName in the log (a bot gets "game_bot_<champion>" instead)'),
    ('slot',        0x2c, 'u8',   'player slot 1..51 (the reader rejects others); equal to the local slot = your hero'),
    ('team_order',  0x68, 'bool', '1 -> team 100, 0 -> team 200 (rva 0x365b07)'),
    ('skin',        0x64, 'u32',  'SkinID in the log'),
    ('position',    0x44, 'vec3', 'where the hero is created'),
    ('facing',      0x0c, 'vec3', 'set on the hero at +0x1bec (rva 0x21a340, 0x179610)'),
    ('mastery',     0x58, 'u8',   'champion mastery level: goes to the MasteryBadge code (rva 0x237bc0)'),
    ('bot',         0x52, 'bool', 'the summoner name becomes "game_bot_<champion>" (rva 0x365801)'),
    ('state',       0x1c, 'u8',   '2 -> rva 0x1a7cf0 (refers to "Death") with death_a, death_b; 1 -> rva 0x1a7f40'),
    ('death_a',     0x3c, 'f32',  'first float given to rva 0x1a7cf0 when state = 2'),
    ('death_b',     0x54, 'f32',  'second float given to rva 0x1a7cf0 when state = 2'),
    ('until',       0x5c, 'f32',  'a game time: when later than now, flag_60 and flag_51 are applied (rva 0x36601d)'),
    ('flag_60',     0x60, 'bool', 'given to rva 0x178850 while `until` is ahead'),
    ('flag_51',     0x51, 'bool', 'given to rva 0x11ef60 on the hero (+0x10f8) while `until` is ahead'),
    ('flag_61',     0x61, 'bool', 'when set, rva 0x1b7d10 is called on the hero'),
    ('flag_0a',     0x0a, 'bool', 'kept in the hero at +0x3e08 (an encoded member)'),
    ('value_2d',    0x2d, 'u8',   'written to +0x10 of what the hero\'s vtable[0xcc/4] returns'),
    ('value_53',    0x53, 'u8',   'passed to the hero creation (rva 0x1a2d90, 8th argument); nonzero + your hero -> rva 0x11dad0, 0x11dba0'),
    ('flag_40',     0x40, 'bool', 'read by the handler into a local (rva 0x365ba3); use not traced'),
    ('value_50',    0x50, 'u8',   'not read by the handler'),
    ('value_69',    0x69, 'u8',   'not read by the handler'),
]


def _to_bytes(t, v):
    if t == 'str':
        return v.encode('utf8') if isinstance(v, str) else bytes(v)
    if t in ('u8', 'bool'):
        return bytes([int(v)])
    if t == 'u32':
        return struct.pack('<I', v)
    if t == 'f32':
        return struct.pack('<f', v)
    if t == 'vec3':
        return struct.pack('<3f', *v)
    raise ValueError(t)


def _from_bytes(t, b):
    if t == 'str':
        return b.decode('utf8')
    if t in ('u8', 'bool'):
        return b[0]
    if t == 'u32':
        return struct.unpack('<I', b)[0]
    if t == 'f32':
        return struct.unpack('<f', b)[0]
    if t == 'vec3':
        return list(struct.unpack('<3f', b))
    raise ValueError(t)


_spec = None


def spec():
    global _spec
    if _spec is None:
        _spec = C.load(79)
    return _spec


def build(hero, modes=None):
    """{name: value} -> body of packet 79 (after [u16 id][u32 net id]; Riot sends 79 with net id 0)"""
    vals = {off: _to_bytes(t, hero[name]) for name, off, t, _ in FIELDS}
    return C.encode(spec(), vals, modes)


def read(body):
    """body -> {name: value}, through Riot's reader in the emulator"""
    vals = C.decode(79, body, spec())
    if vals is None:
        return None
    return {name: _from_bytes(t, vals[off]) for name, off, t, _ in FIELDS}


HEROES = os.path.join(C.P.RES, 's2c_79_heroes.json')


def dump():
    """the ten 79s of replay keyframe 1, as named fields -> data/exe133/s2c_79_heroes.json"""
    import pkt_modes as PM
    heroes = [read(b) for b in PM.packets(79)]
    with open(HEROES, 'w', encoding='utf8') as f:
        json.dump(heroes, f, ensure_ascii=False, indent=1)
    for h in heroes:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items()})
    print('->', HEROES)


def load_heroes():
    return json.load(open(HEROES, encoding='utf8'))


if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        dump()
