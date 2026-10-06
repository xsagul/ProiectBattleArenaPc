"""Packet 574 = the game info (13.3 client: "Game Info Received", then one "ROST" log line per player), written by our
server through the nested writer learnt from Riot's reader (server/pkt_schema.py, data/exe133/codec/
574.tree.json). The values of the replay's own 574 (data/exe133/codec/574.values.json, `pkt_schema.py dump 574`)
are the template; this module names the parts a server changes.

Where things are (struct offsets; meaning taken from the values and the client's ROST log of the same packet):
  root (reader rva 0x88d530)
    +0x14  the receiving client's own player slot (1..51; 17 = the replay's spectator)
    +0x28  player records (reader rva 0x908710), one per summoner:
             +0x28 summoner id (u64), +0x30 PUUID, +0x6c summoner name, +0x78 profile icon, +0x98 slot,
             +0x8 [challenges json, regalia json, ...], +0x8c [their keys]
    +0x34  match configuration (reader rva 0x8feb90): +0xc queue ("Worlds_TrophyOnly"), +0x1c game type
           ("MATCHED_GAME"), +0x70 "teambuilder-match-<game id>", +0xd0 version text, +0xe8 platform ("KR"),
           +0x10c game mode ("CLASSIC"), +0xdc mutators, ...
    +0x14c in-game player list (reader rva 0x907980, +0x8 = records of reader rva 0x902a30), one per slot:
             +0x8 team (100 / 200), +0xc slot, +0x84 skin, +0x94 and +0xd8 champion, +0xa4 and +0xe8 role
             ("TOP" ...), +0x6c champion mastery level, +0x3c / +0xf4 rank tier, +0xb0 division
"""
import copy
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pkt_schema as S  # noqa: E402

VALUES = os.path.join(S.OUT, '574.values.json')
_sc = None


def schema():
    global _sc
    if _sc is None:
        _sc = S.Schema.load(574)
    return _sc


def template():
    return json.load(open(VALUES))


def text(v):
    return bytes.fromhex(v['text']).decode('utf8')


def mk_text(s):
    return {'text': s.encode('utf8').hex()}


def u32(h):
    return struct.unpack('<I', bytes.fromhex(h))[0]


def mk_u32(n):
    return struct.pack('<I', n).hex()


def summoners(v):
    return v['+0x28']


def ingame(v):
    return v['+0x14c']['+0x8']


def by_slot(v, slot):
    """(summoner record or None, in-game record) of a player slot"""
    s = next((p for p in summoners(v) if p['+0x98'] == f'{slot:02x}'), None)
    g = next((p for p in ingame(v) if p['+0xc'] == f'{slot:02x}'), None)
    return s, g


def set_local_slot(v, slot):
    v['+0x14'] = f'{slot:02x}'


def set_name(v, slot, name):
    s, g = by_slot(v, slot)
    s['+0x6c'] = mk_text(name)


def set_champion(v, slot, champion, skin=None, champion_id=None):
    """champion_id: the numeric id at +0x80 (Darius 122, Nidalee 76 in the replay)"""
    s, g = by_slot(v, slot)
    g['+0x94'] = mk_text(champion)
    g['+0xd8'] = mk_text(champion)
    if champion_id is not None:
        g['+0x80'] = mk_u32(champion_id)
    if skin is not None:
        g['+0x84'] = mk_u32(skin)


def roster(v):
    out = []
    for g in ingame(v):
        slot = int(g['+0xc'], 16)
        s, _ = by_slot(v, slot)
        out.append({'slot': slot, 'team': u32(g['+0x8']), 'champion': text(g['+0x94']), 'skin': u32(g['+0x84']),
                    'role': text(g['+0xa4']), 'name': text(s['+0x6c']) if s else None})
    return out


def build(v):
    """values -> body of packet 574 (after [u16 id][u32 net id])"""
    return schema().encode(v)


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
    v = template()
    print('local slot', int(v['+0x14'], 16))
    for p in roster(v):
        print(p)
