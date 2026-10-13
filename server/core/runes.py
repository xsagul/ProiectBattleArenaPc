"""Runes: the page a champion enters the match with.

The client learns it from packet 905 of the start state [m: the ten of the live recording, read with the format
tools learnt from the client's reader]: the struct at +0x10 holds
    +0x44  the primary tree (8000 Precision, 8100 Domination, 8200 Sorcery, 8300 Inspiration, 8400 Resolve)
    +0x4c  the keystone                +0x11c the secondary tree
    +0x54  ten numbers: the six runes (keystone first), the three stat shards, 0
    +0x88 and +0x114  the two summoner spells (ELF hashes of their names)
    +0xc   fourteen cosmetic ids (a human's emotes ...), +0x50 the summoner's level, +0x8 its icon
The game's files hold no recommended pages (ChampionRuneRecommendationsContext is empty: the client gets them from
Riot's service), so the pages here are the five the recording's players and bots entered with, given by a
champion's class as the recording gives them [a: which class gets which].

What a rune DOES is the scripts' (not in the client). The simulation applies the stat shards [wiki values] and
nothing else yet; the keystones are shown, not played.
"""
import struct

from . import packets as P

# name -> (primary tree, secondary tree, the nine ids) [m: the recording's 905s]
PAGES = {
    'Conqueror': (8000, 8400, [8010, 9111, 9105, 8299, 8429, 8451, 5008, 5008, 5001]),          # Garen (the human)
    'Electrocute': (8100, 8000, [8112, 8139, 8140, 8135, 9111, 8014, 5005, 5008, 5001]),        # Zaahen, Lissandra
    'PressTheAttack': (8000, 8200, [8005, 9111, 9104, 8014, 8233, 8236, 5005, 5008, 5001]),     # Tristana, MissFortune, MasterYi, Tryndamere
    'SummonAery': (8200, 8100, [8229, 8226, 8210, 8236, 8140, 8105, 5008, 5008, 5001]),         # Morgana, Xerath
    'GraspOfTheUndying': (8400, 8200, [8437, 8446, 8444, 8451, 8224, 8237, 5008, 5001, 5001]),  # Galio
}
BY_CLASS = {'fighter': 'Conqueror', 'assassin': 'Electrocute', 'marksman': 'PressTheAttack', 'mage': 'SummonAery',
            'support': 'SummonAery', 'tank': 'GraspOfTheUndying'}
# stat shards [wiki]: adaptive force 9 (5.4 attack damage or 9 ability power), 10 % attack speed, 8 ability haste,
# 10-180 health with level, 65 health, 2.5 % move speed, 15 % tenacity
ADAPTIVE, ATTACK_SPEED, HASTE, HEALTH_SCALING, HEALTH, MOVE_SPEED, TENACITY = 5008, 5005, 5007, 5001, 5011, 5010, 5013


def tags_of(name):
    from . import gamedata as G
    c = next((c for c in G.champion_index() if c['alias'] == name), None)
    return [str(t).lower() for t in (c or {}).get('tags', []) if t]


def page_for(name):
    """the page of a champion by its first class tag"""
    for t in tags_of(name):
        if t in BY_CLASS:
            return BY_CLASS[t]
    return 'Conqueror'


def shard_mods(hero, ids):
    """the stat shards' modifiers for this champion at its level"""
    mods = {}
    tags = tags_of(hero.name)
    magic = hero.ap > hero.bonus.get('ad', 0.0) or (tags[:1] in (['mage'], ['support']))

    def add(k, x):
        mods[k] = mods.get(k, 0.0) + x
    for i in ids[6:9]:
        if i == ADAPTIVE:
            add('ap' if magic else 'ad', 9.0 if magic else 5.4)
        elif i == ATTACK_SPEED:
            add('as', 0.10)
        elif i == HASTE:
            add('haste', 8.0)
        elif i == HEALTH_SCALING:
            add('hp', 10.0 + 170.0 * (hero.level - 1) / 17.0)
        elif i == HEALTH:
            add('hp', 65.0)
        elif i == MOVE_SPEED:
            add('ms_pct', 0.025)
        elif i == TENACITY:
            add('tenacity', 0.15)
    return mods


def tree_of(perk):
    """the path a rune belongs to [the perk ids' ranges: 80xx / 91xx Precision, 81xx / 99xx Domination, 82xx Sorcery,
    83xx Inspiration, 84xx Resolve]"""
    if 8000 <= perk < 8100 or 9100 <= perk < 9200:
        return 8000
    if 8100 <= perk < 8200 or 9900 <= perk < 10000:
        return 8100
    return perk // 100 * 100 if 8200 <= perk < 8500 else 8000


def custom_page(net, ids):
    """a whole page given by its ids (six runes, three shards: the replays' tooltips, 1052 kind 5) -> its name"""
    ids = [int(i) for i in ids][:9]
    ids += [5008] * (9 - len(ids))
    name = f'page_{net:x}'
    PAGES[name] = (tree_of(ids[0]), tree_of(ids[4]), ids)
    return name


def apply(hero):
    hero.mods['runes'] = shard_mods(hero, PAGES[hero.rune_page][2])


def packet(pk, body, hero):
    """the recorded 905 of the slot with this champion's page and summoner spells"""
    import pkt_schema as PS
    sc = pk.schema(905)
    v = PS.parse(sc, body)
    s = v['+0x10']
    primary, secondary, ids = PAGES[hero.rune_page]
    s['+0x44'], s['+0x4c'], s['+0x11c'] = P.u32(primary), P.u32(ids[0]), P.u32(secondary)
    s['+0x54'] = struct.pack('<10I', *ids, 0).hex()
    spells = getattr(hero, 'summoners', None)
    if spells and len(spells) == 2:
        both = struct.pack('<2I', P.elf(spells[0]), P.elf(spells[1])).hex()
        s['+0x88'] = s['+0x114'] = both
    return sc.encode(v)
